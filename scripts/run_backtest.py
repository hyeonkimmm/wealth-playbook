#!/usr/bin/env python3
"""
Wealth Playbook - Backtest Engine & Chart Generator
언제든 시작일(--start)과 종료일(--end)을 지정하여 백테스트를 실행하고,
결과 표와 SVG 차트를 자동으로 생성/갱신합니다.

사용 예시:
  python scripts/run_backtest.py --start 2012-01-01 --end 2025-12-31
  python scripts/run_backtest.py --start 2015-01-01 --end 2026-06-30
"""

import argparse
import os
import yfinance as yf
import pandas as pd
import numpy as np

def parse_args():
    parser = argparse.ArgumentParser(description="Wealth Playbook Backtest Runner")
    parser.add_argument("--start", type=str, default="2012-01-01", help="백테스트 시작일 (기본: 2012-01-01)")
    parser.add_argument("--end", type=str, default="2025-12-31", help="백테스트 종료일 (기본: 2025-12-31)")
    parser.add_argument("--monthly", type=float, default=100.0, help="월 적립금 (단위: 만원, 기본: 100)")
    return parser.parse_args()

def calc_stats(series):
    total_return = series.iloc[-1] / series.iloc[0] - 1
    years = (series.index[-1] - series.index[0]).days / 365.25
    cagr = (series.iloc[-1] / series.iloc[0]) ** (1 / years) - 1
    
    cummax = series.cummax()
    dd = (series - cummax) / cummax
    mdd = dd.min()
    
    s_2022 = series.loc['2022-01-01':'2022-12-31']
    ret_2022 = s_2022.iloc[-1] / s_2022.iloc[0] - 1 if len(s_2022) > 0 else np.nan
    mdd_2022 = ((s_2022 - s_2022.cummax()) / s_2022.cummax()).min() if len(s_2022) > 0 else np.nan
    
    return {
        'total_return': total_return,
        'cagr': cagr,
        'mdd': mdd,
        'ret_2022': ret_2022,
        'mdd_2022': mdd_2022
    }

def sim_band(data, band=0.10):
    prices = data[['QLD', 'SCHD']].values
    dates = data.index
    n = len(prices)
    portfolio_val = np.zeros(n)
    portfolio_val[0] = 10000
    shares = np.zeros(2)
    shares[0] = (portfolio_val[0] * 0.7) / prices[0, 0]
    shares[1] = (portfolio_val[0] * 0.3) / prices[0, 1]
    rebal_count = 0
    
    for i in range(1, n):
        val_0 = shares[0] * prices[i, 0]
        val_1 = shares[1] * prices[i, 1]
        tot = val_0 + val_1
        portfolio_val[i] = tot
        w0 = val_0 / tot
        if w0 >= (0.7 + band) or w0 <= (0.7 - band):
            shares[0] = (tot * 0.7) / prices[i, 0]
            shares[1] = (tot * 0.3) / prices[i, 1]
            rebal_count += 1
            
    s = pd.Series(portfolio_val, index=dates)
    st = calc_stats(s)
    st['rebal_count'] = rebal_count
    return s, st

def sim_dca(data, key, band=0.10, monthly_money=100.0):
    month_starts = set(data.resample('MS').first().index)
    total_inv = 0.0
    shares_0 = 0.0
    shares_1 = 0.0
    shares_single = 0.0
    val_history = []
    rebal_count = 0
    
    for dt in data.index:
        p_qld = data.loc[dt, 'QLD']
        p_schd = data.loc[dt, 'SCHD']
        
        if dt in month_starts:
            total_inv += monthly_money
            if key == '7:3':
                curr0 = shares_0 * p_qld
                curr1 = shares_1 * p_schd
                tot = curr0 + curr1 + monthly_money
                t0, t1 = tot * 0.7, tot * 0.3
                need0 = max(0, t0 - curr0)
                need1 = max(0, t1 - curr1)
                if need0 + need1 > 0:
                    a0 = monthly_money * (need0 / (need0 + need1))
                    a1 = monthly_money * (need1 / (need0 + need1))
                else:
                    a0, a1 = monthly_money * 0.7, monthly_money * 0.3
                shares_0 += a0 / p_qld
                shares_1 += a1 / p_schd
            else:
                shares_single += monthly_money / data.loc[dt, key]
                
        if key == '7:3':
            curr0 = shares_0 * p_qld
            curr1 = shares_1 * p_schd
            tot = curr0 + curr1
            if tot > 0:
                w0 = curr0 / tot
                if w0 >= (0.7 + band) or w0 <= (0.7 - band):
                    shares_0 = (tot * 0.7) / p_qld
                    shares_1 = (tot * 0.3) / p_schd
                    rebal_count += 1
            val = tot
        else:
            val = shares_single * data.loc[dt, key]
        val_history.append(val)
        
    s = pd.Series(val_history, index=data.index)
    final_val = s.iloc[-1]
    ret = (final_val - total_inv) / total_inv
    cummax = s.cummax()
    mdd = ((s - cummax) / cummax).min()
    return total_inv, final_val, ret, mdd, rebal_count

def generate_svg_chart(start_yr, end_yr, stats_dict, output_paths):
    cagr_qld = stats_dict['QLD']['cagr'] * 100
    mdd_qld = stats_dict['QLD']['mdd_2022'] * 100
    
    cagr_barbell = stats_dict['7:3_10']['cagr'] * 100
    mdd_barbell = stats_dict['7:3_10']['mdd_2022'] * 100
    
    cagr_qqq = stats_dict['QQQ']['cagr'] * 100
    mdd_qqq = stats_dict['QQQ']['mdd_2022'] * 100
    
    cagr_spy = stats_dict['SPY']['cagr'] * 100
    mdd_spy = stats_dict['SPY']['mdd_2022'] * 100
    
    cagr_schd = stats_dict['SCHD']['cagr'] * 100
    mdd_schd = stats_dict['SCHD']['mdd_2022'] * 100

    years_count = end_yr - start_yr + 1

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 370" width="100%" height="100%">
  <defs>
    <style>
      .bg {{ fill: #f8fafc; stroke: #e2e8f0; stroke-width: 1.5; rx: 16px; }}
      .title {{ font-family: -apple-system, BlinkMacSystemFont, "Pretendard", sans-serif; font-size: 18px; font-weight: 800; fill: #0f172a; }}
      .subtitle {{ font-family: -apple-system, BlinkMacSystemFont, "Pretendard", sans-serif; font-size: 12px; fill: #64748b; }}
      .axis-label {{ font-family: -apple-system, BlinkMacSystemFont, "Pretendard", sans-serif; font-size: 13px; font-weight: 700; fill: #1e293b; text-anchor: middle; }}
      .bar-cagr {{ fill: #2563eb; rx: 4px; }}
      .bar-cagr-highlight {{ fill: #1d4ed8; rx: 4px; }}
      .bar-mdd {{ fill: #ef4444; rx: 4px; }}
      .val-label {{ font-family: -apple-system, BlinkMacSystemFont, "Pretendard", sans-serif; font-size: 12px; font-weight: 700; fill: #0f172a; text-anchor: middle; }}
      .legend-text {{ font-family: -apple-system, BlinkMacSystemFont, "Pretendard", sans-serif; font-size: 11.5px; fill: #475569; }}
    </style>
  </defs>

  <rect x="2" y="2" width="796" height="366" class="bg"/>
  <text x="32" y="38" class="title">{years_count}년간({start_yr}~{end_yr}) 실전 백테스트 성과 비교</text>
  <text x="32" y="58" class="subtitle">배당 재투자 반영 실제 수정주가 기반 · 연평균 성장률(CAGR) vs 2022년 하락장 최대낙폭(MDD)</text>

  <!-- Legend -->
  <g transform="translate(560, 26)">
    <rect x="0" y="0" width="14" height="14" fill="#2563eb" rx="3"/>
    <text x="20" y="11" class="legend-text">연평균 성장률 (CAGR)</text>
    <rect x="150" y="0" width="14" height="14" fill="#ef4444" rx="3"/>
    <text x="170" y="11" class="legend-text">2022 하락장 MDD</text>
  </g>

  <!-- Zero Line -->
  <line x1="40" y1="210" x2="760" y2="210" stroke="#94a3b8" stroke-width="1.5"/>

  <!-- 1. QLD 100% -->
  <g transform="translate(105, 0)">
    <rect x="-30" y="{210 - cagr_qld * 4}" width="28" height="{cagr_qld * 4}" class="bar-cagr" fill="#93c5fd"/>
    <text x="-16" y="{210 - cagr_qld * 4 - 8}" class="val-label">+{cagr_qld:.1f}%</text>
    <rect x="2" y="210" width="28" height="{abs(mdd_qld) * 1.2}" class="bar-mdd"/>
    <text x="16" y="{210 + abs(mdd_qld) * 1.2 + 16}" class="val-label" fill="#dc2626">{mdd_qld:.1f}%</text>
    <text x="0" y="328" class="axis-label">QLD (100%)</text>
  </g>

  <!-- 2. 7:3 바벨 전략 (Highlight) -->
  <g transform="translate(250, 0)">
    <rect x="-46" y="70" width="92" height="248" fill="#eff6ff" rx="8" stroke="#3b82f6" stroke-width="1.5" stroke-dasharray="3,3"/>
    <rect x="-30" y="{210 - cagr_barbell * 4}" width="28" height="{cagr_barbell * 4}" class="bar-cagr-highlight"/>
    <text x="-16" y="{210 - cagr_barbell * 4 - 8}" class="val-label" fill="#1d4ed8" font-size="13px">+{cagr_barbell:.1f}%</text>
    <rect x="2" y="210" width="28" height="{abs(mdd_barbell) * 1.2}" class="bar-mdd" fill="#f87171"/>
    <text x="16" y="{210 + abs(mdd_barbell) * 1.2 + 16}" class="val-label" fill="#dc2626">{mdd_barbell:.1f}%</text>
    <text x="0" y="338" class="axis-label" fill="#1d4ed8">★ 7:3 바벨</text>
  </g>

  <!-- 3. QQQ (나스닥 100) -->
  <g transform="translate(395, 0)">
    <rect x="-30" y="{210 - cagr_qqq * 4}" width="28" height="{cagr_qqq * 4}" class="bar-cagr" fill="#94a3b8"/>
    <text x="-16" y="{210 - cagr_qqq * 4 - 8}" class="val-label">+{cagr_qqq:.1f}%</text>
    <rect x="2" y="210" width="28" height="{abs(mdd_qqq) * 1.2}" class="bar-mdd" fill="#fca5a5"/>
    <text x="16" y="{210 + abs(mdd_qqq) * 1.2 + 16}" class="val-label" fill="#dc2626">{mdd_qqq:.1f}%</text>
    <text x="0" y="328" class="axis-label">QQQ (1배)</text>
  </g>

  <!-- 4. SPY (S&P 500) -->
  <g transform="translate(540, 0)">
    <rect x="-30" y="{210 - cagr_spy * 4}" width="28" height="{cagr_spy * 4}" class="bar-cagr" fill="#cbd5e1"/>
    <text x="-16" y="{210 - cagr_spy * 4 - 8}" class="val-label">+{cagr_spy:.1f}%</text>
    <rect x="2" y="210" width="28" height="{abs(mdd_spy) * 1.2}" class="bar-mdd" fill="#fca5a5"/>
    <text x="16" y="{210 + abs(mdd_spy) * 1.2 + 16}" class="val-label" fill="#dc2626">{mdd_spy:.1f}%</text>
    <text x="0" y="328" class="axis-label">SPY (S&amp;P 500)</text>
  </g>

  <!-- 5. SCHD (배당) -->
  <g transform="translate(685, 0)">
    <rect x="-30" y="{210 - cagr_schd * 4}" width="28" height="{cagr_schd * 4}" class="bar-cagr" fill="#cbd5e1"/>
    <text x="-16" y="{210 - cagr_schd * 4 - 8}" class="val-label">+{cagr_schd:.1f}%</text>
    <rect x="2" y="210" width="28" height="{abs(mdd_schd) * 1.2}" class="bar-mdd" fill="#86efac"/>
    <text x="16" y="{210 + abs(mdd_schd) * 1.2 + 16}" class="val-label" fill="#15803d">{mdd_schd:.1f}%</text>
    <text x="0" y="328" class="axis-label">SCHD (배당)</text>
  </g>
</svg>
"""
    for path in output_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(svg)
    print(f"[SVG 갱신 완료] {len(output_paths)}개 파일 업데이트")

def main():
    args = parse_args()
    print(f"=== 백테스트 시작: {args.start} ~ {args.end} ===")
    
    tickers = ['QLD', 'SCHD', 'QQQ', 'SPY']
    raw = yf.download(tickers, start=args.start, end=args.end)['Close']
    data = raw.dropna()
    
    start_dt = data.index[0]
    end_dt = data.index[-1]
    years_diff = (end_dt - start_dt).days / 365.25
    print(f"실제 데이터 수집: {start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')} (총 {len(data)} 거래일, 약 {years_diff:.1f}년)")

    # 1. 거치식
    st_qld = calc_stats(data['QLD'])
    st_schd = calc_stats(data['SCHD'])
    st_qqq = calc_stats(data['QQQ'])
    st_spy = calc_stats(data['SPY'])
    _, st_barbell10 = sim_band(data, 0.10)
    _, st_barbell20 = sim_band(data, 0.20)
    
    stats_dict = {
        'QLD': st_qld,
        'SCHD': st_schd,
        'QQQ': st_qqq,
        'SPY': st_spy,
        '7:3_10': st_barbell10,
        '7:3_20': st_barbell20
    }

    print("\n--- 1. 일시불 거치식 투자 성과 ---")
    rows = [
        ("★ 7:3 바벨 (±10%p)", st_barbell10['total_return'], st_barbell10['cagr'], st_barbell10['mdd'], st_barbell10['ret_2022'], st_barbell10['mdd_2022'], f"{st_barbell10['rebal_count']}회"),
        ("7:3 바벨 (±20%p)", st_barbell20['total_return'], st_barbell20['cagr'], st_barbell20['mdd'], st_barbell20['ret_2022'], st_barbell20['mdd_2022'], f"{st_barbell20['rebal_count']}회"),
        ("QLD (2배 레버리지 100%)", st_qld['total_return'], st_qld['cagr'], st_qld['mdd'], st_qld['ret_2022'], st_qld['mdd_2022'], "-"),
        ("QQQ (나스닥 100 지수)", st_qqq['total_return'], st_qqq['cagr'], st_qqq['mdd'], st_qqq['ret_2022'], st_qqq['mdd_2022'], "-"),
        ("SPY (S&P 500 지수)", st_spy['total_return'], st_spy['cagr'], st_spy['mdd'], st_spy['ret_2022'], st_spy['mdd_2022'], "-"),
        ("SCHD (배당다우존스 100%)", st_schd['total_return'], st_schd['cagr'], st_schd['mdd'], st_schd['ret_2022'], st_schd['mdd_2022'], "-"),
    ]
    df_lump = pd.DataFrame(rows, columns=["전략", "총수익률", "CAGR", "전체 MDD", "2022 수익률", "2022 MDD", "리밸런싱"])
    df_lump["총수익률"] = df_lump["총수익률"].apply(lambda x: f"+{x*100:.1f}%")
    df_lump["CAGR"] = df_lump["CAGR"].apply(lambda x: f"{x*100:.2f}%")
    df_lump["전체 MDD"] = df_lump["전체 MDD"].apply(lambda x: f"{x*100:.2f}%")
    df_lump["2022 수익률"] = df_lump["2022 수익률"].apply(lambda x: f"{x*100:.2f}%")
    df_lump["2022 MDD"] = df_lump["2022 MDD"].apply(lambda x: f"{x*100:.2f}%")
    print(df_lump.to_string(index=False))

    # 2. 적립식
    print(f"\n--- 2. 월 {args.monthly:.0f}만원 적립식 투자 성과 ---")
    dca_rows = []
    for name, key, band in [
        ("★ 7:3 바벨 (±10%p)", "7:3", 0.10),
        ("7:3 바벨 (±20%p)", "7:3", 0.20),
        ("QLD 적립 (100%)", "QLD", 0),
        ("QQQ 적립 (나스닥 100)", "QQQ", 0),
        ("SPY 적립 (S&P 500)", "SPY", 0),
        ("SCHD 적립 (배당 100%)", "SCHD", 0),
    ]:
        tot_inv, fin_val, ret, mdd, reb = sim_dca(data, key, band, args.monthly)
        dca_rows.append({
            "전략": name,
            "총 납입 원금": f"{tot_inv:.0f}만 원",
            "최종 평가 금액": f"{fin_val:.0f}만 원",
            "누적 수익률": f"+{ret*100:.1f}%",
            "적립식 MDD": f"{mdd*100:.2f}%",
            "강제 스위칭": f"{reb}회"
        })
    df_dca = pd.DataFrame(dca_rows)
    print(df_dca.to_string(index=False))

    # 3. SVG 차트 파일 갱신
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    chart_paths = [
        os.path.join(root_dir, "assets", "backtest-cagr-chart.svg"),
        os.path.join(root_dir, "strategies", "assets", "backtest-cagr-chart.svg")
    ]
    generate_svg_chart(start_dt.year, end_dt.year, stats_dict, chart_paths)

if __name__ == "__main__":
    main()
