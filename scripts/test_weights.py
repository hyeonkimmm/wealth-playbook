#!/Users/kimhyun/dev/wealth-engine/.venv/bin/python
"""
Deep inspection of QLD weights, DCA behavior, and realistic execution frictions.
"""
import yfinance as yf
import pandas as pd
import numpy as np

def run_deep_checks():
    raw = yf.download(['QLD', 'SCHD'], start='2012-01-01', end='2025-12-31')
    close_data = raw['Close'].dropna()
    open_data = raw['Open'].dropna()
    
    # Check weight distributions for DCA without any forced switching
    month_starts = set(close_data.resample('MS').first().index)
    
    # Pure smart DCA (band = infinity)
    shares_0 = 0.0
    shares_1 = 0.0
    monthly_money = 100.0
    dca_weights = []
    
    for dt in close_data.index:
        p_qld = close_data.loc[dt, 'QLD']
        p_schd = close_data.loc[dt, 'SCHD']
        
        if dt in month_starts:
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
            
        curr0 = shares_0 * p_qld
        curr1 = shares_1 * p_schd
        tot = curr0 + curr1
        w0 = curr0 / tot if tot > 0 else 0.7
        dca_weights.append((dt, w0, tot))
        
    df_weights = pd.DataFrame(dca_weights, columns=['Date', 'QLD_Weight', 'Total_Val']).set_index('Date')
    print("=== PURE SMART DCA WEIGHT STATS (No forced rebalance) ===")
    print(f"Max QLD Weight: {df_weights['QLD_Weight'].max()*100:.2f}% on {df_weights['QLD_Weight'].idxmax().strftime('%Y-%m-%d')}")
    print(f"Min QLD Weight: {df_weights['QLD_Weight'].min()*100:.2f}% on {df_weights['QLD_Weight'].idxmin().strftime('%Y-%m-%d')}")
    
    # Let's check 2020-2021 peak and 2022 bottom
    w_2020_2021 = df_weights.loc['2020-01-01':'2021-12-31']
    print(f"2020-2021 Max QLD Weight: {w_2020_2021['QLD_Weight'].max()*100:.2f}% on {w_2020_2021['QLD_Weight'].idxmax().strftime('%Y-%m-%d')}")
    
    w_2022 = df_weights.loc['2022-01-01':'2022-12-31']
    print(f"2022 Min QLD Weight: {w_2022['QLD_Weight'].min()*100:.2f}% on {w_2022['QLD_Weight'].idxmin().strftime('%Y-%m-%d')}")
    
    w_2024 = df_weights.loc['2024-01-01':'2024-12-31']
    print(f"2024 Max QLD Weight: {w_2024['QLD_Weight'].max()*100:.2f}% on {w_2024['QLD_Weight'].idxmax().strftime('%Y-%m-%d')}")

    # Check for Lump-sum pure buy & hold weight stats
    # Starts at 70:30
    p0_0 = close_data.iloc[0]['QLD']
    p1_0 = close_data.iloc[0]['SCHD']
    s0 = 7000.0 / p0_0
    s1 = 3000.0 / p1_0
    lump_w = []
    for dt in close_data.index:
        v0 = s0 * close_data.loc[dt, 'QLD']
        v1 = s1 * close_data.loc[dt, 'SCHD']
        lump_w.append(v0 / (v0 + v1))
    s_lump_w = pd.Series(lump_w, index=close_data.index)
    print("\n=== LUMP-SUM BUY & HOLD (NO REBALANCE AT ALL) ===")
    print(f"Max QLD Weight: {s_lump_w.max()*100:.2f}% on {s_lump_w.idxmax().strftime('%Y-%m-%d')}")
    print(f"Min QLD Weight: {s_lump_w.min()*100:.2f}% on {s_lump_w.idxmin().strftime('%Y-%m-%d')}")
    print(f"End QLD Weight: {s_lump_w.iloc[-1]*100:.2f}%")

if __name__ == '__main__':
    run_deep_checks()
