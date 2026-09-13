#!/Users/kimhyun/dev/wealth-engine/.venv/bin/python
"""
Extract detailed trade dates and market events for 10, 15, 20 bands.
"""
import yfinance as yf
import pandas as pd
import numpy as np

def detail_dates():
    raw = yf.download(['QLD', 'SCHD'], start='2012-01-01', end='2025-12-31')['Close'].dropna()
    
    for band, name in [(0.10, '+-10%p'), (0.15, '+-15%p'), (0.20, '+-20%p')]:
        print(f"\n==================== {name} LUMP-SUM TRADES ====================")
        prices = raw[['QLD', 'SCHD']].values
        dates = raw.index
        n = len(prices)
        val = 10000.0
        sh0 = (val * 0.7) / prices[0, 0]
        sh1 = (val * 0.3) / prices[0, 1]
        
        for i in range(1, n):
            v0 = sh0 * prices[i, 0]
            v1 = sh1 * prices[i, 1]
            tot = v0 + v1
            w0 = v0 / tot
            if w0 >= 0.7 + band or w0 <= 0.7 - band:
                side = "PROFIT-TAKE (Sell QLD -> Buy SCHD)" if w0 >= 0.7 + band else "BOTTOM-BUY (Sell SCHD -> Buy QLD)"
                print(f"[{dates[i].strftime('%Y-%m-%d')}] QLD P: ${prices[i, 0]:.2f}, SCHD P: ${prices[i, 1]:.2f} | QLD W: {w0*100:.2f}% | Val: ${tot:,.0f} | {side}")
                sh0 = (tot * 0.7) / prices[i, 0]
                sh1 = (tot * 0.3) / prices[i, 1]

    for band, name in [(0.10, '+-10%p'), (0.15, '+-15%p'), (0.20, '+-20%p')]:
        print(f"\n==================== {name} DCA TRADES ====================")
        month_starts = set(raw.resample('MS').first().index)
        sh0 = 0.0
        sh1 = 0.0
        monthly = 100.0
        for dt in raw.index:
            p0 = raw.loc[dt, 'QLD']
            p1 = raw.loc[dt, 'SCHD']
            if dt in month_starts:
                c0 = sh0 * p0
                c1 = sh1 * p1
                tot = c0 + c1 + monthly
                t0, t1 = tot * 0.7, tot * 0.3
                n0 = max(0, t0 - c0)
                n1 = max(0, t1 - c1)
                if n0 + n1 > 0:
                    a0 = monthly * (n0 / (n0 + n1))
                    a1 = monthly * (n1 / (n0 + n1))
                else:
                    a0, a1 = monthly * 0.7, monthly * 0.3
                sh0 += a0 / p0
                sh1 += a1 / p1
            c0 = sh0 * p0
            c1 = sh1 * p1
            tot = c0 + c1
            if tot > 0:
                w0 = c0 / tot
                if w0 >= 0.7 + band or w0 <= 0.7 - band:
                    side = "PROFIT-TAKE (Sell QLD -> Buy SCHD)" if w0 >= 0.7 + band else "BOTTOM-BUY (Sell SCHD -> Buy QLD)"
                    print(f"[{dt.strftime('%Y-%m-%d')}] QLD P: ${p0:.2f}, SCHD P: ${p1:.2f} | QLD W: {w0*100:.2f}% | Val: {tot:,.0f}만원 | {side}")
                    sh0 = (tot * 0.7) / p0
                    sh1 = (tot * 0.3) / p1

if __name__ == '__main__':
    detail_dates()
