# 월급날 리밸런싱 계산기

현재 보유 중인 주식 수량과 주가, 그리고 이번 달 월급(적립금)을 입력하면 **목표 비율(70:30)을 맞추기 위해 이번 달에 어떤 종목을 몇 주 매수(또는 스위칭)해야 하는지** 자동으로 계산해 주는 실전 도구입니다.

---

<div id="calc-container" style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 16px; padding: 28px 24px; margin: 2rem 0; box-shadow: 0 4px 20px rgba(0,0,0,0.04); font-family: -apple-system, BlinkMacSystemFont, 'Pretendard', sans-serif;">

  <!-- Form Grid -->
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; margin-bottom: 24px;">
    
    <!-- 1. 월 적립금 -->
    <div style="background: #f8fafc; padding: 18px; border-radius: 12px; border: 1px solid #e2e8f0;">
      <label style="display: block; font-size: 13px; font-weight: 700; color: #1e293b; margin-bottom: 8px;">
        당월 투자 가능 금액 (월급 + 배당금)
      </label>
      <div style="display: flex; align-items: center;">
        <input type="number" id="inp-cash" value="1000000" step="50000" style="width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 16px; font-weight: 700; color: #0f172a; outline: none;" oninput="recalc()"/>
        <span style="margin-left: 8px; font-weight: 700; color: #64748b; font-size: 14px;">원</span>
      </div>
      <div style="font-size: 11.5px; color: #64748b; margin-top: 6px;">이번 달 투자 여유 자금과 통장에 들어온 월배당금 합산</div>
    </div>

    <!-- 2. 목표 비중 & 밴드 -->
    <div style="background: #f8fafc; padding: 18px; border-radius: 12px; border: 1px solid #e2e8f0;">
      <label style="display: block; font-size: 13px; font-weight: 700; color: #1e293b; margin-bottom: 8px;">
        전략 옵션 설정
      </label>
      <div style="display: flex; gap: 12px; margin-bottom: 8px;">
        <div style="flex: 1;">
          <span style="font-size: 11.5px; color: #64748b; display: block; margin-bottom: 4px;">목표 비중 (레버리지:배당)</span>
          <select id="inp-ratio" style="width: 100%; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px; font-weight: 600;" onchange="recalc()">
            <option value="0.7">70 : 30 (표준 바벨)</option>
            <option value="0.6">60 : 40 (중도형)</option>
            <option value="0.5">50 : 50 (초보 안정형)</option>
          </select>
        </div>
        <div style="flex: 1;">
          <span style="font-size: 11.5px; color: #64748b; display: block; margin-bottom: 4px;">강제 리밸런싱 밴드</span>
          <select id="inp-band" style="width: 100%; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px; font-weight: 600;" onchange="recalc()">
            <option value="0.10">±10%p (권장: 80% / 60%)</option>
            <option value="0.20">±20%p (초게으름: 90% / 50%)</option>
          </select>
        </div>
      </div>
      <div style="font-size: 11.5px; color: #64748b;">밴드를 이탈하면 월급 외에 기존 주식 스위칭 권고</div>
    </div>
  </div>

  <!-- Assets Input Table -->
  <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
    <div style="font-size: 14px; font-weight: 700; color: #0f172a; margin-bottom: 16px;">현재 보유 자산 현황 입력</div>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;">
      <!-- 공격수 QLD -->
      <div style="border-left: 4px solid #2563eb; padding-left: 14px;">
        <div style="font-size: 13.5px; font-weight: 700; color: #1d4ed8;">공격수: TIGER 미국나스닥100레버리지 (262330)</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;">
          <div>
            <span style="font-size: 11px; color: #64748b; display: block;">현재 보유 수량</span>
            <input type="number" id="inp-qld-qty" value="500" style="width: 100%; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; font-weight: 600;" oninput="recalc()"/>
          </div>
          <div>
            <span style="font-size: 11px; color: #64748b; display: block;">현재 1주당 가격 (원)</span>
            <input type="number" id="inp-qld-price" value="23500" step="100" style="width: 100%; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; font-weight: 600;" oninput="recalc()"/>
          </div>
        </div>
        <div style="font-size: 12px; color: #475569; margin-top: 8px;">
          평가금액: <strong id="out-qld-eval" style="color:#0f172a;">-</strong>
        </div>
      </div>

      <!-- 수비수 SCHD -->
      <div style="border-left: 4px solid #16a34a; padding-left: 14px;">
        <div style="font-size: 13.5px; font-weight: 700; color: #15803d;">수비수: TIGER 미국배당다우존스 (458730)</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;">
          <div>
            <span style="font-size: 11px; color: #64748b; display: block;">현재 보유 수량</span>
            <input type="number" id="inp-schd-qty" value="400" style="width: 100%; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; font-weight: 600;" oninput="recalc()"/>
          </div>
          <div>
            <span style="font-size: 11px; color: #64748b; display: block;">현재 1주당 가격 (원)</span>
            <input type="number" id="inp-schd-price" value="12500" step="50" style="width: 100%; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; font-weight: 600;" oninput="recalc()"/>
          </div>
        </div>
        <div style="font-size: 12px; color: #475569; margin-top: 8px;">
          평가금액: <strong id="out-schd-eval" style="color:#0f172a;">-</strong>
        </div>
      </div>
    </div>
  </div>

  <!-- Result Dashboard -->
  <div style="background: #f1f5f9; border-radius: 12px; padding: 22px; border: 1px solid #cbd5e1;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
      <div style="font-size: 13px; font-weight: 700; color: #475569;">현재 계좌 비중 현황</div>
      <div style="font-size: 12px; color: #64748b;">총 자산 평가액: <strong id="out-total-asset" style="color:#0f172a; font-size:14px;">-</strong></div>
    </div>

    <!-- Visual Ratio Progress Bar -->
    <div style="height: 28px; background: #e2e8f0; border-radius: 8px; overflow: hidden; display: flex; margin-bottom: 12px;">
      <div id="bar-qld" style="background: #2563eb; color: #ffffff; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; transition: width 0.3s ease;">-</div>
      <div id="bar-schd" style="background: #16a34a; color: #ffffff; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; transition: width 0.3s ease;">-</div>
    </div>

    <!-- Action Callout Box -->
    <div id="action-box" style="background: #ffffff; border-radius: 10px; padding: 20px; border-left: 6px solid #2563eb; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
        <span id="badge-status" style="display: inline-block; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 9999px; background: #dbeafe; color: #1d4ed8;">계산 중</span>
        <span id="txt-status-title" style="font-size: 15px; font-weight: 800; color: #0f172a;">-</span>
      </div>
      <div id="txt-action-detail" style="font-size: 14px; font-weight: 600; color: #1e293b; line-height: 1.6;">-</div>
      <div id="txt-after-sim" style="font-size: 12px; color: #64748b; margin-top: 10px; padding-top: 10px; border-top: 1px dashed #e2e8f0;">-</div>
    </div>

  </div>

</div>

<script>
function fmtWon(val) {
  return Math.round(val).toLocaleString() + '원';
}

function recalc() {
  const cash = parseFloat(document.getElementById('inp-cash').value) || 0;
  const targetRatio = parseFloat(document.getElementById('inp-ratio').value) || 0.7;
  const band = parseFloat(document.getElementById('inp-band').value) || 0.10;

  const qldQty = parseFloat(document.getElementById('inp-qld-qty').value) || 0;
  const qldPrice = parseFloat(document.getElementById('inp-qld-price').value) || 0;
  const schdQty = parseFloat(document.getElementById('inp-schd-qty').value) || 0;
  const schdPrice = parseFloat(document.getElementById('inp-schd-price').value) || 0;

  const qldVal = qldQty * qldPrice;
  const schdVal = schdQty * schdPrice;
  const totalVal = qldVal + schdVal;

  document.getElementById('out-qld-eval').innerText = fmtWon(qldVal);
  document.getElementById('out-schd-eval').innerText = fmtWon(schdVal);
  document.getElementById('out-total-asset').innerText = fmtWon(totalVal + cash);

  if (totalVal === 0) {
    document.getElementById('bar-qld').style.width = '70%';
    document.getElementById('bar-qld').innerText = '70%';
    document.getElementById('bar-schd').style.width = '30%';
    document.getElementById('bar-schd').innerText = '30%';
    return;
  }

  const currentQldPct = qldVal / totalVal;
  const currentSchdPct = schdVal / totalVal;

  const qldBarWidth = Math.max(15, Math.min(85, currentQldPct * 100));
  document.getElementById('bar-qld').style.width = qldBarWidth + '%';
  document.getElementById('bar-qld').innerText = 'QLD ' + (currentQldPct * 100).toFixed(1) + '%';

  document.getElementById('bar-schd').style.width = (100 - qldBarWidth) + '%';
  document.getElementById('bar-schd').innerText = 'SCHD ' + (currentSchdPct * 100).toFixed(1) + '%';

  const actionBox = document.getElementById('action-box');
  const badgeStatus = document.getElementById('badge-status');
  const statusTitle = document.getElementById('txt-status-title');
  const actionDetail = document.getElementById('txt-action-detail');
  const afterSim = document.getElementById('txt-after-sim');

  const upperLimit = targetRatio + band;
  const lowerLimit = targetRatio - band;

  // Case 1: 상승장 과열 (80% 도달) ➔ 스위칭 매도
  if (currentQldPct >= upperLimit) {
    actionBox.style.borderLeftColor = '#dc2626';
    badgeStatus.style.background = '#fee2e2';
    badgeStatus.style.color = '#b91c1c';
    badgeStatus.innerText = '상승장 익절 스위칭 트리거';
    statusTitle.innerText = '나스닥 과열: 레버리지를 일부 매도해 수익을 확정하세요';

    // 70:30 맞추기 위한 매도 금액 계산
    const targetQldVal = (totalVal + cash) * targetRatio;
    const excessQldVal = qldVal - targetQldVal;
    const sellQldShares = Math.floor(excessQldVal / qldPrice);
    const proceeds = sellQldShares * qldPrice;
    const totalToBuySchd = proceeds + cash;
    const buySchdShares = Math.floor(totalToBuySchd / schdPrice);

    actionDetail.innerHTML = 
      '1. <strong>TIGER 나스닥 레버리지</strong>를 <span style="color:#dc2626; font-size:16px;">' + sellQldShares.toLocaleString() + '주</span> 매도하여 약 ' + fmtWon(proceeds) + ' 이익을 확정하세요.<br>' +
      '2. 매도 대금 + 당월 적립금으로 <strong>TIGER 미국배당다우존스</strong>를 <span style="color:#16a34a; font-size:16px;">' + buySchdShares.toLocaleString() + '주</span> 매수하세요.';

    const newQld = qldVal - (sellQldShares * qldPrice);
    const newSchd = schdVal + (buySchdShares * schdPrice);
    const newTotal = newQld + newSchd;
    afterSim.innerText = '스위칭 후 예상 비중: QLD ' + ((newQld/newTotal)*100).toFixed(1) + '% : SCHD ' + ((newSchd/newTotal)*100).toFixed(1) + '% (목표 복원 완료)';
  }
  // Case 2: 하락장 폭락 (60% 도달) ➔ 바닥줍기 스위칭
  else if (currentQldPct <= lowerLimit) {
    actionBox.style.borderLeftColor = '#16a34a';
    badgeStatus.style.background = '#dcfce7';
    badgeStatus.style.color = '#15803d';
    badgeStatus.innerText = '하락장 저가매수 스위칭 트리거';
    statusTitle.innerText = '나스닥 폭락: 덜 떨어진 배당주를 팔아 레버리지 평단을 대폭 낮추세요';

    const targetSchdVal = (totalVal + cash) * (1 - targetRatio);
    const excessSchdVal = schdVal - targetSchdVal;
    const sellSchdShares = Math.floor(excessSchdVal / schdPrice);
    const proceeds = sellSchdShares * schdPrice;
    const totalToBuyQld = proceeds + cash;
    const buyQldShares = Math.floor(totalToBuyQld / qldPrice);

    actionDetail.innerHTML = 
      '1. <strong>TIGER 미국배당다우존스</strong>를 <span style="color:#dc2626; font-size:16px;">' + sellSchdShares.toLocaleString() + '주</span> 매도하세요.<br>' +
      '2. 매도 대금 + 당월 적립금으로 <strong>TIGER 나스닥 레버리지</strong>를 <span style="color:#2563eb; font-size:16px;">' + buyQldShares.toLocaleString() + '주</span> 집중 매수하세요.';

    const newQld = qldVal + (buyQldShares * qldPrice);
    const newSchd = schdVal - (sellSchdShares * schdPrice);
    const newTotal = newQld + newSchd;
    afterSim.innerText = '스위칭 후 예상 비중: QLD ' + ((newQld/newTotal)*100).toFixed(1) + '% : SCHD ' + ((newSchd/newTotal)*100).toFixed(1) + '% (반등 탄력 극대화)';
  }
  // Case 3: 밴드 내 정상 범위 ➔ 스마트 적립 (매도 없이 부족한 쪽 매수)
  else {
    actionBox.style.borderLeftColor = '#2563eb';
    badgeStatus.style.background = '#dbeafe';
    badgeStatus.style.color = '#1d4ed8';
    badgeStatus.innerText = '정상 밴드 내 (스마트 적립 매수)';
    statusTitle.innerText = '기존 주식 매도 없이, 이번 달 적립금으로 부족한 종목만 채워 넣으세요';

    const grandTotal = totalVal + cash;
    const targetQldVal = grandTotal * targetRatio;
    const targetSchdVal = grandTotal * (1 - targetRatio);

    const needQldVal = Math.max(0, targetQldVal - qldVal);
    const needSchdVal = Math.max(0, targetSchdVal - schdVal);

    let allocQld = 0;
    let allocSchd = 0;

    if (needQldVal + needSchdVal > 0) {
      allocQld = cash * (needQldVal / (needQldVal + needSchdVal));
      allocSchd = cash * (needSchdVal / (needQldVal + needSchdVal));
    } else {
      allocQld = cash * targetRatio;
      allocSchd = cash * (1 - targetRatio);
    }

    const buyQldShares = Math.floor(allocQld / qldPrice);
    const buySchdShares = Math.floor(allocSchd / schdPrice);

    let actionText = '';
    if (buyQldShares > 0 && buySchdShares > 0) {
      actionText = '• <strong>TIGER 나스닥 레버리지:</strong> 약 ' + buyQldShares.toLocaleString() + '주 매수 (' + fmtWon(buyQldShares * qldPrice) + ')<br>' +
                   '• <strong>TIGER 미국배당다우존스:</strong> 약 ' + buySchdShares.toLocaleString() + '주 매수 (' + fmtWon(buySchdShares * schdPrice) + ')';
    } else if (buyQldShares > 0) {
      actionText = '이번 달 적립금으로 <strong>TIGER 나스닥 레버리지</strong>만 <span style="color:#2563eb; font-size:16px;">' + buyQldShares.toLocaleString() + '주</span> (' + fmtWon(buyQldShares * qldPrice) + ') 집중 매수하세요.';
    } else if (buySchdShares > 0) {
      actionText = '이번 달 적립금으로 <strong>TIGER 미국배당다우존스</strong>만 <span style="color:#16a34a; font-size:16px;">' + buySchdShares.toLocaleString() + '주</span> (' + fmtWon(buySchdShares * schdPrice) + ') 집중 매수하세요.';
    } else {
      actionText = '적립금 금액이 주가보다 적어 매수 가능 수량이 없습니다. 적립금을 예수금으로 유지하세요.';
    }

    actionDetail.innerHTML = actionText;

    const newQld = qldVal + (buyQldShares * qldPrice);
    const newSchd = schdVal + (buySchdShares * schdPrice);
    const newTotal = newQld + newSchd;
    afterSim.innerText = '매수 후 예상 비중: QLD ' + ((newQld/newTotal)*100).toFixed(1) + '% : SCHD ' + ((newSchd/newTotal)*100).toFixed(1) + '% (7:3 복구 완료)';
  }
}

// 최초 실행
setTimeout(recalc, 100);
</script>

---

## 계산기 활용 요령

1. **매월 월급날 다음 날 딱 1회만 계산하세요.**
   * 평소 장중에 주가를 수시로 입력할 필요가 없습니다.
2. **단수주(자투리 금액) 처리:**
   * 1주 단위로 매수하고 남은 몇천 원~몇만 원의 자투리 잔돈은 계좌 예수금으로 그대로 남겨두었다가 다음 달 배당금과 함께 사용하시면 됩니다.
3. **스위칭이 뜰 때만 매도하세요:**
   * '스마트 적립 매수' 상태에서는 기존 주식을 1주도 팔 필요 없이 오직 사는 것만으로 비율이 맞춰집니다.
   * '스위칭 트리거'가 떴을 때만 안내된 수량만큼 매도 후 즉시 반대 종목을 매수하시면 됩니다.
