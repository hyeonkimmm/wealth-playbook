"""
실시간 및 최신 장마감 ETF 가격 수집기
===================================
TIGER 미국나스닥100레버리지(합성) (418660) 및
TIGER 미국배당다우존스 (458730)의 최신 시세를 수집하여
assets/data/latest-prices.json 파일로 저장합니다.
"""

import json
import os
import urllib.request
from datetime import datetime
import pytz

def fetch_latest_prices():
    url = "https://finance.naver.com/api/sise/etfItemList.nhn"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read().decode("cp949")
        data = json.loads(content)
        items = data["result"]["etfItemList"]

    target_codes = {
        "418660": "TIGER 미국나스닥100레버리지(합성)",
        "458730": "TIGER 미국배당다우존스"
    }

    results = {}
    for item in items:
        code = item.get("itemcode")
        if code in target_codes:
            results[code] = {
                "name": target_codes[code],
                "price": int(item.get("nowVal", 0)),
                "change": int(item.get("changeVal", 0)),
                "change_rate": float(item.get("changeRate", 0.0)),
                "market_sum": int(item.get("marketSum", 0)),
                "volume": int(item.get("quant", 0))
            }

    # 한국 표준시(KST) 타임스탬프
    kst = pytz.timezone("Asia/Seoul")
    now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S KST")

    payload = {
        "updated_at": now_kst,
        "prices": results
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "latest-prices.json")

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Successfully updated ETF prices at {now_kst}:")
    for code, info in results.items():
        print(f"  [{code}] {info['name']}: {info['price']:,}원 ({info['change_rate']:+.2f}%)")

    return payload

if __name__ == "__main__":
    fetch_latest_prices()
