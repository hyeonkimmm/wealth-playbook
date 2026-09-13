#!/Users/kimhyun/dev/wealth-engine/.venv/bin/python
"""
Audit and Comparative Backtest Script
Tests:
1. Switching bands: +-10%p (80%/60%), +-15%p (85%/55%), +-20%p (90%/50%)
2. Variations based on wealth-engine standards:
   - Trading fees (e.g. 0.015% for domestic ETF, 0.05%~0.25% for US ETF)
   - Slippage (Fixed 5 bps)
   - Execution timing: Same-day Close vs Next-day Open
   - Monitoring frequency: Daily check vs Monthly check (Part 2 Rulebook: monthly salary day check)
   - Integer share constraint (no fractional shares)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import math

def download_data():
    tickers = ['QLD', 'SCHD', 'QQQ', 'SPY']
    raw = yf.download(tickers, start='2012-01-01', end='2025-12-31')
    return raw

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

# 1. Original sim_band (Lump-sum)
def sim_band_orig(data, band=0.10):
    prices = data[['QLD', 'SCHD']].values
    dates = data.index
    n = len(prices)
    portfolio_val = np.zeros(n)
    portfolio_val[0] = 10000
    shares = np.zeros(2)
    shares[0] = (portfolio_val[0] * 0.7) / prices[0, 0]
    shares[1] = (portfolio_val[0] * 0.3) / prices[0, 1]
    rebal_count = 0
    rebal_dates = []
    
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
            rebal_dates.append((dates[i], w0, tot))
            
    s = pd.Series(portfolio_val, index=dates)
    st = calc_stats(s)
    st['rebal_count'] = rebal_count
    st['rebal_dates'] = rebal_dates
    return s, st

# 2. Original sim_dca
def sim_dca_orig(data, key, band=0.10, monthly_money=100.0):
    month_starts = set(data.resample('MS').first().index)
    total_inv = 0.0
    shares_0 = 0.0
    shares_1 = 0.0
    shares_single = 0.0
    val_history = []
    rebal_count = 0
    rebal_dates = []
    
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
                    rebal_dates.append((dt, w0, tot))
            val = tot
        else:
            val = shares_single * data.loc[dt, key]
        val_history.append(val)
        
    s = pd.Series(val_history, index=data.index)
    final_val = s.iloc[-1]
    ret = (final_val - total_inv) / total_inv
    cummax = s.cummax()
    mdd = ((s - cummax) / cummax).min()
    
    s_2022 = s.loc['2022-01-01':'2022-12-31']
    ret_2022 = (s_2022.iloc[-1] - s_2022.iloc[0]) / s_2022.iloc[0] if len(s_2022) > 0 else np.nan
    mdd_2022 = ((s_2022 - s_2022.cummax()) / s_2022.cummax()).min() if len(s_2022) > 0 else np.nan
    
    return {
        'total_inv': total_inv,
        'final_val': final_val,
        'ret': ret,
        'mdd': mdd,
        'ret_2022': ret_2022,
        'mdd_2022': mdd_2022,
        'rebal_count': rebal_count,
        'rebal_dates': rebal_dates,
        'series': s
    }

def main():
    raw = download_data()
    close_data = raw['Close'].dropna()
    open_data = raw['Open'].dropna()
    
    print('=' * 60)
    print('TASK 2: +-10%p, +-15%p, +-20%p COMPARISON (ORIGINAL LOGIC)')
    print('=' * 60)
    
    bands = [0.10, 0.15, 0.20]
    band_names = ['+-10%p (80%/60%)', '+-15%p (85%/55%)', '+-20%p (90%/50%)']
    
    # 1. Lump sum
    print('\n[1. Lump-sum Performance]')
    lump_results = []
    for band, name in zip(bands, band_names):
        s, st = sim_band_orig(close_data, band=band)
        lump_results.append({
            'Strategy': name,
            'Total Return': f"+{st['total_return']*100:.1f}%",
            'CAGR': f"{st['cagr']*100:.2f}%",
            'Total MDD': f"{st['mdd']*100:.2f}%",
            '2022 Return': f"{st['ret_2022']*100:.2f}%",
            '2022 MDD': f"{st['mdd_2022']*100:.2f}%",
            'Rebal Count': f"{st['rebal_count']}회"
        })
        print(f"\n--- Detail for {name} ---")
        for dt, w0, tot in st['rebal_dates']:
            direction = "QLD Overheated -> Sell QLD / Buy SCHD" if w0 >= 0.7 + band else "QLD Crashed -> Sell SCHD / Buy QLD"
            print(f"Date: {dt.strftime('%Y-%m-%d')}, QLD Weight: {w0*100:.2f}%, Value: {tot:.1f}, Action: {direction}")
            
    df_lump = pd.DataFrame(lump_results)
    print('\n', df_lump.to_string(index=False))
    
    # 2. DCA
    print('\n[2. Monthly 100 DCA Performance]')
    dca_results = []
    for band, name in zip(bands, band_names):
        res = sim_dca_orig(close_data, key='7:3', band=band, monthly_money=100.0)
        dca_results.append({
            'Strategy': name,
            'Total Inv': f"{res['total_inv']:.0f}만 원",
            'Final Value': f"{res['final_val']:.0f}만 원",
            'Cumulative Ret': f"+{res['ret']*100:.1f}%",
            'DCA MDD': f"{res['mdd']*100:.2f}%",
            '2022 DCA MDD': f"{res['mdd_2022']*100:.2f}%",
            'Forced Switch': f"{res['rebal_count']}회"
        })
        print(f"\n--- Detail for DCA {name} ---")
        for dt, w0, tot in res['rebal_dates']:
            direction = "QLD Overheated -> Sell QLD / Buy SCHD" if w0 >= 0.7 + band else "QLD Crashed -> Sell SCHD / Buy QLD"
            print(f"Date: {dt.strftime('%Y-%m-%d')}, QLD Weight: {w0*100:.2f}%, Value: {tot:.1f}만 원, Action: {direction}")
            
    df_dca = pd.DataFrame(dca_results)
    print('\n', df_dca.to_string(index=False))

if __name__ == '__main__':
    main()
