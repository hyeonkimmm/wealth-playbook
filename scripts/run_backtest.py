import yfinance as yf
import pandas as pd
import numpy as np

data = yf.download(['QLD', 'SCHD', 'QQQ', 'SPY'], start='2012-01-01', end='2024-12-31')['Close'].dropna()

# 1. 일시불(Lump-sum) 거치식 백테스트
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
        '총수익률': f"{total_return*100:.1f}%",
        'CAGR(연평균)': f"{cagr*100:.2f}%",
        '전체 MDD': f"{mdd*100:.2f}%",
        '2022년 수익률': f"{ret_2022*100:.2f}%",
        '2022년 MDD': f"{mdd_2022*100:.2f}%"
    }

def sim_band_rebalance(data, target_w=(0.7, 0.3), band=0.10):
    prices = data[['QLD', 'SCHD']].values
    dates = data.index
    n = len(prices)
    
    portfolio_val = np.zeros(n)
    portfolio_val[0] = 10000
    shares = np.zeros(2)
    shares[0] = (portfolio_val[0] * target_w[0]) / prices[0, 0]
    shares[1] = (portfolio_val[0] * target_w[1]) / prices[0, 1]
    
    rebal_count = 0
    
    for i in range(1, n):
        val_0 = shares[0] * prices[i, 0]
        val_1 = shares[1] * prices[i, 1]
        total_val = val_0 + val_1
        portfolio_val[i] = total_val
        
        w_0 = val_0 / total_val
        if w_0 >= (target_w[0] + band) or w_0 <= (target_w[0] - band):
            shares[0] = (total_val * target_w[0]) / prices[i, 0]
            shares[1] = (total_val * target_w[1]) / prices[i, 1]
            rebal_count += 1
            
    s = pd.Series(portfolio_val, index=dates)
    stats = calc_stats(s)
    stats['리밸런싱 횟수'] = f"{rebal_count}회"
    return s, stats

s_rebal, stats_rebal = sim_band_rebalance(data)

results = {
    '7:3 바벨 리밸런싱': stats_rebal,
    'QLD (100% 몰빵)': calc_stats(data['QLD']),
    'QQQ (나스닥 1배)': calc_stats(data['QQQ']),
    'SCHD (배당 100%)': calc_stats(data['SCHD']),
    'SPY (S&P 500)': calc_stats(data['SPY']),
}

df_res = pd.DataFrame(results).T
print("=== 거치식(12년) 백테스트 결과 ===")
print(df_res.to_string())

# 2. 월 100만원 적립식 시뮬레이션
month_starts = set(data.resample('MS').first().index)

def run_dca_sim(ticker_or_rebal):
    total_inv = 0.0
    shares_0 = 0.0
    shares_1 = 0.0
    shares_single = 0.0
    val_history = []
    
    monthly_money = 100.0 # 100만원 기준
    
    for dt in data.index:
        p_qld = data.loc[dt, 'QLD']
        p_schd = data.loc[dt, 'SCHD']
        
        if dt in month_starts:
            total_inv += monthly_money
            if ticker_or_rebal == '7:3_rebal':
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
                p = data.loc[dt, ticker_or_rebal]
                shares_single += monthly_money / p
                
        if ticker_or_rebal == '7:3_rebal':
            val = shares_0 * p_qld + shares_1 * p_schd
        else:
            val = shares_single * data.loc[dt, ticker_or_rebal]
        val_history.append(val)
        
    s = pd.Series(val_history, index=data.index)
    final_val = s.iloc[-1]
    ret = (final_val - total_inv) / total_inv
    cummax = s.cummax()
    mdd = ((s - cummax) / cummax).min()
    return total_inv, final_val, ret, mdd

print("\n=== 월 100만원 적립식(2012~2024년 13년간) 성과 ===")
for name, key in [('7:3 바벨 적립', '7:3_rebal'), ('QQQ 적립', 'QQQ'), ('QLD 적립', 'QLD'), ('SCHD 적립', 'SCHD'), ('SPY 적립', 'SPY')]:
    tot, fin, r, m = run_dca_sim(key)
    print(f"{name:15} | 원금: {tot:.0f}만원 ➔ 최종: {fin:.0f}만원 | 수익률: +{r*100:.1f}% | 적립식 MDD: {m*100:.2f}%")
