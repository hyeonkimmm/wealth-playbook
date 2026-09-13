"""
Wealth Playbook - 월급날 리밸런싱 계산기 정밀 검증 테스트 스위트
============================================================
이 테스트 스위트는 실시간 월급날 리밸런싱 계산기의 수학적 알고리즘 및
실제 브라우저(Playwright Headless) 환경에서의 UI/UX 렌더링을 다각도로 검증합니다.
"""

import math
import subprocess
import time
import pytest
from playwright.sync_api import sync_playwright


# ============================================================================
# 1. 수학적 알고리즘 기준 모델 (Reference Implementation)
# ============================================================================

def simulate_rebalancing(
    cash: float,
    target_ratio: float,
    band: float,
    qld_qty: float,
    qld_price: float,
    schd_qty: float,
    schd_price: float
):
    """index.html 내 JavaScript 계산기 함수와 1:1로 일치하는 순수 파이썬 기준 모델"""
    cash = max(0.0, float(cash))
    qld_qty = max(0.0, float(qld_qty))
    qld_price = max(0.0, float(qld_price))
    schd_qty = max(0.0, float(schd_qty))
    schd_price = max(0.0, float(schd_price))

    if qld_price <= 0 or schd_price <= 0:
        return {"status": "INVALID_PRICE"}

    qld_val = qld_qty * qld_price
    schd_val = schd_qty * schd_price
    total_stock = qld_val + schd_val
    total_all = total_stock + cash

    upper = target_ratio + band
    lower = target_ratio - band
    target_qld_val = total_all * target_ratio
    target_schd_val = total_all * (1.0 - target_ratio)

    # 시나리오 0: 보유 주식이 없는 초기 시작
    if total_stock == 0:
        if cash <= 0:
            return {
                "status": "INITIAL_ZERO_CASH",
                "sell_qld": 0, "sell_schd": 0,
                "buy_qld": 0, "buy_schd": 0,
                "post_qld_pct": 0.0, "post_schd_pct": 0.0
            }
        buy_q = math.floor((cash * target_ratio) / qld_price)
        buy_s = math.floor((cash * (1.0 - target_ratio)) / schd_price)
        spent = (buy_q * qld_price) + (buy_s * schd_price)
        post_q_val = buy_q * qld_price
        post_s_val = buy_s * schd_price
        tot = post_q_val + post_s_val
        return {
            "status": "INITIAL_START",
            "sell_qld": 0, "sell_schd": 0,
            "buy_qld": buy_q, "buy_schd": buy_s,
            "leftover_cash": cash - spent,
            "post_qld_pct": (post_q_val / tot * 100) if tot > 0 else 0.0,
            "post_schd_pct": (post_s_val / tot * 100) if tot > 0 else 0.0
        }

    cur_qld_pct = qld_val / total_stock

    # Case 1: 과열 상승 (상단 밴드 초과)
    if cur_qld_pct >= upper:
        # 하위 조건 1A: 적립금으로 매도 없이 해결 가능
        if qld_val <= target_qld_val:
            def_q = max(0.0, target_qld_val - qld_val)
            def_s = max(0.0, target_schd_val - schd_val)
            if def_q > 0 and def_s > 0:
                alloc_q = def_q
                alloc_s = def_s
            else:
                alloc_q = 0.0
                alloc_s = cash
            b_q = math.floor(alloc_q / qld_price)
            b_s = math.floor(alloc_s / schd_price)
            rem = cash - ((b_q * qld_price) + (b_s * schd_price))
            if rem >= schd_price:
                b_s += math.floor(rem / schd_price)
                rem = cash - ((b_q * qld_price) + (b_s * schd_price))
            if rem >= qld_price and def_q >= def_s:
                b_q += math.floor(rem / qld_price)
                rem = cash - ((b_q * qld_price) + (b_s * schd_price))
            nq = qld_val + (b_q * qld_price)
            ns = schd_val + (b_s * schd_price)
            return {
                "status": "OVERWEIGHT_NO_SELL",
                "sell_qld": 0, "sell_schd": 0,
                "buy_qld": b_q, "buy_schd": b_s,
                "leftover_cash": rem,
                "post_qld_pct": (nq / (nq + ns)) * 100,
                "post_schd_pct": (ns / (nq + ns)) * 100
            }
        # 하위 조건 1B: 진정한 스위칭 필요
        excess_qld = qld_val - target_qld_val
        sell_q = min(int(qld_qty), max(1, math.floor(excess_qld / qld_price)))
        proceeds = sell_q * qld_price
        total_avail = proceeds + cash
        buy_s = math.floor(total_avail / schd_price)
        rem = total_avail - (buy_s * schd_price)
        nq = qld_val - proceeds
        ns = schd_val + (buy_s * schd_price)
        return {
            "status": "OVERWEIGHT_SWITCHING",
            "sell_qld": sell_q, "sell_schd": 0,
            "buy_qld": 0, "buy_schd": buy_s,
            "proceeds": proceeds,
            "leftover_cash": rem,
            "post_qld_pct": (nq / (nq + ns)) * 100,
            "post_schd_pct": (ns / (nq + ns)) * 100
        }

    # Case 2: 시장 폭락 (하단 밴드 하회)
    elif cur_qld_pct <= lower:
        # 하위 조건 2A: 적립금으로 매도 없이 해결 가능
        if schd_val <= target_schd_val:
            def_q = max(0.0, target_qld_val - qld_val)
            def_s = max(0.0, target_schd_val - schd_val)
            if def_q > 0 and def_s > 0:
                alloc_q = def_q
                alloc_s = def_s
            else:
                alloc_q = cash
                alloc_s = 0.0
            b_q = math.floor(alloc_q / qld_price)
            b_s = math.floor(alloc_s / schd_price)
            rem = cash - ((b_q * qld_price) + (b_s * schd_price))
            if rem >= qld_price:
                b_q += math.floor(rem / qld_price)
                rem = cash - ((b_q * qld_price) + (b_s * schd_price))
            if rem >= schd_price and def_s >= def_q:
                b_s += math.floor(rem / schd_price)
                rem = cash - ((b_q * qld_price) + (b_s * schd_price))
            nq = qld_val + (b_q * qld_price)
            ns = schd_val + (b_s * schd_price)
            return {
                "status": "UNDERWEIGHT_NO_SELL",
                "sell_qld": 0, "sell_schd": 0,
                "buy_qld": b_q, "buy_schd": b_s,
                "leftover_cash": rem,
                "post_qld_pct": (nq / (nq + ns)) * 100,
                "post_schd_pct": (ns / (nq + ns)) * 100
            }
        # 하위 조건 2B: 진정한 스위칭 필요
        excess_schd = schd_val - target_schd_val
        sell_s = min(int(schd_qty), max(1, math.floor(excess_schd / schd_price)))
        proceeds = sell_s * schd_price
        total_avail = proceeds + cash
        buy_q = math.floor(total_avail / qld_price)
        rem = total_avail - (buy_q * qld_price)
        nq = qld_val + (buy_q * qld_price)
        ns = schd_val - proceeds
        return {
            "status": "UNDERWEIGHT_SWITCHING",
            "sell_qld": 0, "sell_schd": sell_s,
            "buy_qld": buy_q, "buy_schd": 0,
            "proceeds": proceeds,
            "leftover_cash": rem,
            "post_qld_pct": (nq / (nq + ns)) * 100,
            "post_schd_pct": (ns / (nq + ns)) * 100
        }

    # Case 3: 정상 범위 (스마트 적립)
    else:
        if cash <= 0:
            return {
                "status": "NORMAL_ZERO_CASH",
                "sell_qld": 0, "sell_schd": 0,
                "buy_qld": 0, "buy_schd": 0,
                "post_qld_pct": cur_qld_pct * 100,
                "post_schd_pct": (1.0 - cur_qld_pct) * 100
            }

        def_qld = max(0.0, target_qld_val - qld_val)
        def_schd = max(0.0, target_schd_val - schd_val)

        if def_qld > 0 and def_schd > 0:
            alloc_q = cash * (def_qld / (def_qld + def_schd))
            alloc_s = cash * (def_schd / (def_qld + def_schd))
        elif def_qld > 0:
            alloc_q = cash
            alloc_s = 0.0
        elif def_schd > 0:
            alloc_q = 0.0
            alloc_s = cash
        else:
            alloc_q = cash * target_ratio
            alloc_s = cash * (1.0 - target_ratio)

        b_q = math.floor(alloc_q / qld_price)
        b_s = math.floor(alloc_s / schd_price)

        # 잔여 예수금 흡수
        rem = cash - ((b_q * qld_price) + (b_s * schd_price))
        if rem >= qld_price and def_qld >= def_schd:
            b_q += math.floor(rem / qld_price)
            rem = cash - ((b_q * qld_price) + (b_s * schd_price))
        if rem >= schd_price:
            b_s += math.floor(rem / schd_price)
            rem = cash - ((b_q * qld_price) + (b_s * schd_price))

        nq = qld_val + (b_q * qld_price)
        ns = schd_val + (b_s * schd_price)
        ntot = nq + ns
        return {
            "status": "NORMAL_SMART_ACCUMULATION",
            "sell_qld": 0, "sell_schd": 0,
            "buy_qld": b_q, "buy_schd": b_s,
            "leftover_cash": rem,
            "post_qld_pct": (nq / ntot * 100) if ntot > 0 else 0.0,
            "post_schd_pct": (ns / ntot * 100) if ntot > 0 else 0.0
        }


# ============================================================================
# 2. 알고리즘 수학적 정밀 단위 테스트 (11개 핵심 시나리오)
# ============================================================================

def test_initial_start_zero_stocks():
    """시나리오 1: 보유 주식이 전혀 없고 100만 원 적립금으로 시작하는 경우"""
    res = simulate_rebalancing(
        cash=1_000_000, target_ratio=0.7, band=0.10,
        qld_qty=0, qld_price=23_500,
        schd_qty=0, schd_price=12_500
    )
    assert res["status"] == "INITIAL_START"
    assert res["sell_qld"] == 0
    assert res["sell_schd"] == 0
    # 70만 원 / 23500 = 29주 (681,500원), 30만 원 / 12500 = 24주 (300,000원)
    assert res["buy_qld"] == 29
    assert res["buy_schd"] == 24
    assert res["leftover_cash"] >= 0
    # 매수 후 비중이 70:30에 수렴하는지 검증
    assert 68.0 <= res["post_qld_pct"] <= 72.0
    assert 28.0 <= res["post_schd_pct"] <= 32.0


def test_overweight_with_large_cash_no_sell():
    """시나리오 2: 주식 비중은 85% 과열이나 적립금이 커서 매도 없이 양쪽 배분 매수로 70:30 복구하는 경우"""
    # QLD: 36주 * 23,500 = 846,000원 (84.9%)
    # SCHD: 12주 * 12,500 = 150,000원 (15.1%)
    # 적립금: 1,000,000원 -> 총자산 1,996,000원, 목표 QLD 1,397,200원, 목표 SCHD 598,800원
    # 부족액: QLD +551,200원, SCHD +448,800원
    res = simulate_rebalancing(
        cash=1_000_000, target_ratio=0.7, band=0.10,
        qld_qty=36, qld_price=23_500,
        schd_qty=12, schd_price=12_500
    )
    assert res["status"] == "OVERWEIGHT_NO_SELL"
    # 절대 매도가 발생해서는 안 됨 (음수 매도 방지)
    assert res["sell_qld"] == 0
    assert res["sell_schd"] == 0
    # 적립금으로 양쪽 부족분을 균형 배분 매수
    assert res["buy_qld"] > 0
    assert res["buy_schd"] > 0
    # 매수 후 비중이 정확히 70:30 근방으로 수렴 (69.0% ~ 71.0%)
    assert 69.0 <= res["post_qld_pct"] <= 71.0
    assert 29.0 <= res["post_schd_pct"] <= 31.0


def test_overweight_true_switching_large_portfolio():
    """시나리오 3: 5,000만 원 규모 포트폴리오에서 QLD 85% 과열로 진정한 스위칭이 필요한 경우"""
    # QLD: 1,800주 * 23,500 = 42,300,000원 (84.6%)
    # SCHD: 616주 * 12,500 = 7,700,000원 (15.4%)
    # 적립금: 1,000,000원 -> 총자산 51,000,000원, 목표 QLD 35,700,000원
    res = simulate_rebalancing(
        cash=1_000_000, target_ratio=0.7, band=0.10,
        qld_qty=1800, qld_price=23_500,
        schd_qty=616, schd_price=12_500
    )
    assert res["status"] == "OVERWEIGHT_SWITCHING"
    assert res["sell_qld"] > 0
    assert res["sell_qld"] <= 1800
    assert res["sell_schd"] == 0
    assert res["buy_schd"] > 0
    # 스위칭 후 QLD 비중이 목표 70% 근방(69.0% ~ 71.0%)으로 정밀 복구되는지 검증
    assert 69.0 <= res["post_qld_pct"] <= 71.0
    assert 29.0 <= res["post_schd_pct"] <= 31.0


def test_underweight_with_large_cash_no_sell():
    """시나리오 4: QLD 비중이 55% 폭락 구간이나 적립금이 커서 매도 없이 양쪽 배분 매수로 70:30 복구하는 경우"""
    # QLD: 20주 * 23,500 = 470,000원 (55.6%)
    # SCHD: 30주 * 12,500 = 375,000원 (44.4%)
    # 적립금: 1,000,000원 -> 총자산 1,845,000원
    res = simulate_rebalancing(
        cash=1_000_000, target_ratio=0.7, band=0.10,
        qld_qty=20, qld_price=23_500,
        schd_qty=30, schd_price=12_500
    )
    assert res["status"] == "UNDERWEIGHT_NO_SELL"
    assert res["sell_qld"] == 0
    assert res["sell_schd"] == 0
    # 적립금으로 양쪽 부족분을 균형 배분 매수
    assert res["buy_qld"] > 0
    assert res["buy_schd"] > 0
    # 매수 후 QLD 비중이 70% 근방으로 정확히 복구
    assert 69.0 <= res["post_qld_pct"] <= 71.0
    assert 29.0 <= res["post_schd_pct"] <= 31.0


def test_windfall_cash_allocation_convergence():
    """시나리오 4-1: 극단적으로 큰 적립금(예: 1억 원) 유입 시에도 70:30 비율이 무너지지 않고 수렴하는지 검증"""
    res = simulate_rebalancing(
        cash=100_000_000, target_ratio=0.7, band=0.10,
        qld_qty=100, qld_price=23_500,  # 2.35M
        schd_qty=100, schd_price=12_500  # 1.25M
    )
    # 초기 비중: QLD 65.3% : SCHD 34.7%
    assert res["status"] == "NORMAL_SMART_ACCUMULATION"
    assert res["sell_qld"] == 0
    assert res["sell_schd"] == 0
    assert res["buy_qld"] > 0
    assert res["buy_schd"] > 0
    # 1억 원 유입 후 최종 비중이 정밀하게 69.8% ~ 70.2%에 수렴하는지 검증
    assert 69.8 <= res["post_qld_pct"] <= 70.2
    assert 29.8 <= res["post_schd_pct"] <= 30.2



def test_underweight_true_switching_large_portfolio():
    """시나리오 5: 5,000만 원 규모 포트폴리오에서 폭락으로 QLD 50% 하회 시 진정한 스위칭"""
    # QLD: 1,000주 * 23,500 = 23,500,000원 (47.0%)
    # SCHD: 2,120주 * 12,500 = 26,500,000원 (53.0%)
    # 적립금: 1,000,000원
    res = simulate_rebalancing(
        cash=1_000_000, target_ratio=0.7, band=0.10,
        qld_qty=1000, qld_price=23_500,
        schd_qty=2120, schd_price=12_500
    )
    assert res["status"] == "UNDERWEIGHT_SWITCHING"
    assert res["sell_schd"] > 0
    assert res["sell_schd"] <= 2120
    assert res["sell_qld"] == 0
    assert res["buy_qld"] > 0
    # 스위칭 후 QLD 비중이 70% 근방으로 복구
    assert 69.0 <= res["post_qld_pct"] <= 71.0


def test_normal_band_smart_rebalancing():
    """시나리오 6: 정상 밴드 내(72:28)에서 매도 없이 부족한 종목만 적립금으로 매수하는 경우"""
    # QLD: 500주 * 23,500 = 11,750,000원 (70.1%)
    # SCHD: 400주 * 12,500 = 5,000,000원 (29.9%)
    # 적립금: 1,000,000원
    res = simulate_rebalancing(
        cash=1_000_000, target_ratio=0.7, band=0.10,
        qld_qty=500, qld_price=23_500,
        schd_qty=400, schd_price=12_500
    )
    assert res["status"] == "NORMAL_SMART_ACCUMULATION"
    assert res["sell_qld"] == 0
    assert res["sell_schd"] == 0
    assert res["buy_qld"] > 0
    assert res["buy_schd"] > 0
    assert res["leftover_cash"] >= 0
    assert 69.5 <= res["post_qld_pct"] <= 70.5


def test_normal_band_zero_cash():
    """시나리오 7: 정상 밴드 내이고 당월 적립금이 0원인 경우 (매매 불필요)"""
    res = simulate_rebalancing(
        cash=0, target_ratio=0.7, band=0.10,
        qld_qty=500, qld_price=23_500,
        schd_qty=400, schd_price=12_500
    )
    assert res["status"] == "NORMAL_ZERO_CASH"
    assert res["sell_qld"] == 0
    assert res["sell_schd"] == 0
    assert res["buy_qld"] == 0
    assert res["buy_schd"] == 0


def test_pure_switching_zero_cash():
    """시나리오 8: 당월 적립금이 0원이나 QLD 비중이 85%로 폭등하여 순수 주식 맞바꿈 스위칭"""
    res = simulate_rebalancing(
        cash=0, target_ratio=0.7, band=0.10,
        qld_qty=1800, qld_price=23_500,
        schd_qty=600, schd_price=12_500
    )
    assert res["status"] == "OVERWEIGHT_SWITCHING"
    assert res["sell_qld"] > 0
    assert res["buy_schd"] > 0
    assert 69.0 <= res["post_qld_pct"] <= 71.0


def test_custom_ratio_and_band():
    """시나리오 9: 사용자가 60:40 비율과 ±15%p 밴드를 선택한 경우"""
    res = simulate_rebalancing(
        cash=1_000_000, target_ratio=0.6, band=0.15,
        qld_qty=500, qld_price=23_500,
        schd_qty=600, schd_price=12_500
    )
    # QLD: 11.75M (61.0%), SCHD: 7.5M (39.0%) -> 60% 기준 정상 밴드 내
    assert res["status"] == "NORMAL_SMART_ACCUMULATION"
    assert 59.0 <= res["post_qld_pct"] <= 61.0


def test_tiny_cash_insufficient_for_one_share():
    """시나리오 10: 적립금이 1주 가격보다 작은 경우 (예: 5,000원)"""
    res = simulate_rebalancing(
        cash=5_000, target_ratio=0.7, band=0.10,
        qld_qty=500, qld_price=23_500,
        schd_qty=400, schd_price=12_500
    )
    assert res["status"] == "NORMAL_SMART_ACCUMULATION"
    assert res["buy_qld"] == 0
    assert res["buy_schd"] == 0
    assert res["leftover_cash"] == 5_000


def test_invalid_prices_and_quantities():
    """시나리오 11: 주가가 0 이하이거나 음수 입력이 들어왔을 때 안전 처리"""
    res = simulate_rebalancing(
        cash=1_000_000, target_ratio=0.7, band=0.10,
        qld_qty=10, qld_price=0,
        schd_qty=10, schd_price=12_500
    )
    assert res["status"] == "INVALID_PRICE"


def test_adversarial_single_asset_qld_100_percent():
    """시나리오 12 (Adversarial): QLD만 100% 보유하고 SCHD 0주일 때의 강제 리밸런싱 스위칭 정합성"""
    res = simulate_rebalancing(
        cash=0, target_ratio=0.7, band=0.10,
        qld_qty=1000, qld_price=23_500,
        schd_qty=0, schd_price=12_500
    )
    assert res["status"] == "OVERWEIGHT_SWITCHING"
    assert res["sell_qld"] == 300
    assert res["buy_schd"] == 564
    assert 69.0 <= res["post_qld_pct"] <= 71.0


def test_adversarial_single_asset_schd_100_percent():
    """시나리오 13 (Adversarial): SCHD만 100% 보유하고 QLD 0주일 때의 강제 리밸런싱 스위칭 정합성"""
    res = simulate_rebalancing(
        cash=0, target_ratio=0.7, band=0.10,
        qld_qty=0, qld_price=23_500,
        schd_qty=2000, schd_price=12_500
    )
    assert res["status"] == "UNDERWEIGHT_SWITCHING"
    assert res["sell_schd"] == 1400
    assert res["buy_qld"] == 744
    assert 69.0 <= res["post_qld_pct"] <= 71.0


def test_adversarial_ultra_large_scale_portfolio_10b_krw():
    """시나리오 14 (Adversarial): 100억 원 규모 대형 자산가의 부동소수점 오차 및 오버플로우 한계 검증"""
    res = simulate_rebalancing(
        cash=100_000_000, target_ratio=0.7, band=0.10,
        qld_qty=350_000, qld_price=23_500,
        schd_qty=140_000, schd_price=12_500
    )
    # 총 자산 약 100억 7,500만 원. QLD 비율 82.38% (과열)
    assert res["status"] == "OVERWEIGHT_SWITCHING"
    assert res["sell_qld"] > 0
    assert res["buy_schd"] > 0
    assert 69.5 <= res["post_qld_pct"] <= 70.5


def test_adversarial_exact_boundary_threshold():
    """시나리오 15 (Adversarial): 비중이 정확히 80.00% 경계값에 걸렸을 때 상태 전이 정합성"""
    # QLD: 8,000,000원 / 23,500 = 340.4255 -> 340주 (7,990,000원)
    # SCHD: 2,000,000원 / 12,500 = 160주 (2,000,000원)
    # 총주식: 9,990,000원. QLD 비중 = 79.9799% (정상 밴드)
    # 반대로 QLD를 342주로 올리면 8,037,000원 / 10,037,000원 = 80.073% (과열)
    res_under = simulate_rebalancing(
        cash=0, target_ratio=0.7, band=0.10,
        qld_qty=340, qld_price=23_500,
        schd_qty=160, schd_price=12_500
    )
    assert res_under["status"] == "NORMAL_ZERO_CASH"

    res_over = simulate_rebalancing(
        cash=0, target_ratio=0.7, band=0.10,
        qld_qty=342, qld_price=23_500,
        schd_qty=160, schd_price=12_500
    )
    assert res_over["status"] == "OVERWEIGHT_SWITCHING"


# ============================================================================
# 3. Playwright 브라우저 E2E 검증 (실제 index.html DOM 실행 검증)
# ============================================================================

@pytest.fixture(scope="module")
def local_server():
    """로컬 HTTP 서버를 백그라운드에서 구동하여 실제 브라우저 테스트 환경 제공"""
    proc = subprocess.Popen(
        ["python3", "-m", "http.server", "8877"],
        cwd="/Users/kimhyun/dev/wealth-playbook",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(1.2)
    yield "http://localhost:8877/#/calculator"
    proc.terminate()


def test_e2e_zero_stocks_initial_display(local_server):
    """E2E 테스트 1: 신규 유저(0주 보유) 화면 렌더링 및 계산 결과 확인"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(local_server)
        page.wait_for_selector(".wealth-rebalance-calc-mount")

        # 0주 입력
        page.fill("#calc_0_qld_qty", "0")
        page.fill("#calc_0_schd_qty", "0")
        page.fill("#calc_0_cash", "1000000")
        page.wait_for_timeout(300)

        badge_text = page.locator("#calc_0_status_badge").inner_text()
        title_text = page.locator("#calc_0_status_title").inner_text()
        detail_text = page.locator("#calc_0_action_detail").inner_text()

        assert "신규 포트폴리오 구축" in badge_text
        assert "보유 주식이 없습니다" in title_text
        assert "매도" not in detail_text  # 매도 문구가 절대 없어야 함
        assert "매수" in detail_text

        browser.close()


def test_e2e_overweight_with_large_cash_no_negative_sell(local_server):
    """E2E 테스트 2: 과열 비중이나 적립금이 클 때 음수 매도(-24주)가 발생하지 않는지 확인"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(local_server)
        page.wait_for_selector(".wealth-rebalance-calc-mount")

        # 36주, 12주, 100만 원 입력
        page.fill("#calc_0_qld_qty", "36")
        page.fill("#calc_0_schd_qty", "12")
        page.fill("#calc_0_cash", "1000000")
        page.wait_for_timeout(300)

        badge_text = page.locator("#calc_0_status_badge").inner_text()
        detail_text = page.locator("#calc_0_action_detail").inner_text()

        assert "매도 불필요" in badge_text or "스마트 적립" in badge_text
        assert "-" not in detail_text or "-주" not in detail_text  # 음수 주수 방지
        assert "매도하여" not in detail_text

        browser.close()


def test_e2e_true_switching_render(local_server):
    """E2E 테스트 3: 5,000만 원 계좌에서 85% 과열 시 스위칭 안내가 정상 렌더링되는지 확인"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(local_server)
        page.wait_for_selector(".wealth-rebalance-calc-mount")

        page.fill("#calc_0_qld_qty", "1800")
        page.fill("#calc_0_schd_qty", "616")
        page.fill("#calc_0_cash", "1000000")
        page.wait_for_timeout(300)

        badge_text = page.locator("#calc_0_status_badge").inner_text()
        detail_text = page.locator("#calc_0_action_detail").inner_text()

        assert "스위칭 트리거" in badge_text
        assert "매도하여" in detail_text
        assert "매수" in detail_text

        browser.close()


def test_e2e_quick_cash_buttons(local_server):
    """E2E 테스트 4: 투자 가능 금액 퀵 버튼(+10만, +50만, +100만, 초기화) 인터랙션 확인"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(local_server)
        page.wait_for_selector(".wealth-rebalance-calc-mount")

        # 초기화 버튼 클릭 -> cash 0
        page.click(".btn-cash-reset")
        page.wait_for_timeout(200)
        val = page.locator("#calc_0_cash").input_value()
        assert val == "0"

        # +50만 클릭 -> cash 500,000
        page.click("button.btn-cash-quick:text('+50만')")
        page.wait_for_timeout(200)
        assert page.locator("#calc_0_cash").input_value() == "500000"

        # +100만 클릭 -> cash 1,500,000
        page.click("button.btn-cash-quick:text('+100만')")
        page.wait_for_timeout(200)
        assert page.locator("#calc_0_cash").input_value() == "1500000"

        # +10만 클릭 -> cash 1,600,000
        page.click("button.btn-cash-quick:text('+10만')")
        page.wait_for_timeout(200)
        assert page.locator("#calc_0_cash").input_value() == "1600000"

        browser.close()


def test_e2e_apply_and_undo_simulation(local_server):
    """E2E 테스트 5: 추천 매매 적용 버튼 클릭 시 계좌 수량 가상 갱신 및 되돌리기(실행 취소) 검증"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(local_server)
        page.wait_for_selector(".wealth-rebalance-calc-mount")

        # 1. 초기 상태 입력: QLD 1,800주, SCHD 616주, 예수금 1,000,000원 (과열 스위칭 상태)
        page.fill("#calc_0_qld_qty", "1800")
        page.fill("#calc_0_schd_qty", "616")
        page.fill("#calc_0_cash", "1000000")
        page.wait_for_timeout(300)

        apply_btn = page.locator("#calc_0_btn_apply_sim")
        undo_btn = page.locator("#calc_0_btn_undo_sim")
        sim_banner = page.locator("#calc_0_sim_banner")

        # 적용 버튼 표시, 되돌리기 및 배너 숨김 확인
        assert apply_btn.is_visible()
        assert not undo_btn.is_visible()
        assert not sim_banner.is_visible()

        # 2. 적용하기 버튼 클릭
        apply_btn.click()
        page.wait_for_timeout(300)

        # 배너 표시 및 되돌리기 버튼 표시, 적용 버튼 숨김 확인
        assert sim_banner.is_visible()
        assert undo_btn.is_visible()
        assert not apply_btn.is_visible()

        # 수량 갱신 확인 (QLD 매도, SCHD 매수되어 수량이 변경되었는지)
        new_qld_qty = int(page.locator("#calc_0_qld_qty").input_value())
        new_schd_qty = int(page.locator("#calc_0_schd_qty").input_value())
        assert new_qld_qty < 1800  # QLD 매도
        assert new_schd_qty > 616  # SCHD 매수

        # 갱신 후 비중 확인 (70:30에 정확히 맞추어졌는지)
        qld_bar_text = page.locator("#calc_0_bar_qld").inner_text()
        assert "70." in qld_bar_text or "69." in qld_bar_text

        # 3. 되돌리기 버튼 클릭 (실행 취소)
        undo_btn.click()
        page.wait_for_timeout(300)

        # 원래 수량 및 예수금으로 원복되었는지 확인
        assert page.locator("#calc_0_qld_qty").input_value() == "1800"
        assert page.locator("#calc_0_schd_qty").input_value() == "616"
        assert page.locator("#calc_0_cash").input_value() == "1000000"

        # 배너 숨김 및 적용 버튼 재표시 확인
        assert not sim_banner.is_visible()
        assert not undo_btn.is_visible()
        assert apply_btn.is_visible()

        browser.close()


