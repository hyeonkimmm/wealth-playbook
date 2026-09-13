#!/Users/kimhyun/dev/wealth-engine/.venv/bin/python
"""
Realistic Engine Simulation:
Compare run_backtest.py assumptions vs wealth-engine realistic assumptions:
1. Benchmark: Pure frictionless (current run_backtest.py)
2. Friction 1: Fees (0.015% for domestic ETF or 0.07% for US direct) + Slippage (5 bps)
3. Friction 2: Next-day Open execution (Signal on Close(t) -> Fill on Open(t+1))
4. Friction 3: Rulebook fidelity: Monthly-only inspection vs Daily inspection
5. Friction 4: Integer shares vs Fractional shares
"""

import yfinance as yf
import pandas as pd
import numpy as np

def run_frictions_test():
    raw = yf.download(['QLD', 'SCHD'], start='2012-01-01', end='2025-12-31')
    close = raw['Close'].dropna()
    opens = raw['Open'].dropna()
    dates = close.index
    
    # -------------------------------------------------------------
    # 1. LUMP-SUM COMPARISONS
    # -------------------------------------------------------------
    print("==================================================")
    print("1. LUMP-SUM REALISTIC SIMULATION COMPARISON")
    print("==================================================")
    
    # We will test bands: 0.10, 0.15, 0.20
    # under 3 execution modes:
    # Mode A: Frictionless Same-Day Close (Current run_backtest.py)
    # Mode B: With Fee (0.015%) + Slippage (5 bps) on Same-Day Close
    # Mode C: Next-Day Open Execution with Fee (0.015%) + Slippage (5 bps)
    # Mode D: Monthly-Only Check with Next-Day Open + Fee + Slippage
    
    fee_rate = 0.00015  # 0.015% (ISA domestic ETF standard)
    slip_rate = 0.0005  # 5 bps
    total_cost_rate = fee_rate + slip_rate  # 6.5 bps per transaction
    
    def sim_lump(mode, band):
        # Initial state
        p0_qld = close.iloc[0]['QLD']
        p0_schd = close.iloc[0]['SCHD']
        
        # Initial buy cost
        cap = 10000.0
        if mode in ['B', 'C', 'D']:
            # Buy with cost
            val_qld = cap * 0.7 * (1.0 - total_cost_rate)
            val_schd = cap * 0.3 * (1.0 - total_cost_rate)
            sh_qld = val_qld / p0_qld
            sh_schd = val_schd / p0_schd
        else:
            sh_qld = (cap * 0.7) / p0_qld
            sh_schd = (cap * 0.3) / p0_schd
            
        n = len(dates)
        val_history = np.zeros(n)
        val_history[0] = cap
        rebal_count = 0
        
        month_starts = set(close.resample('MS').first().index)
        pending_rebal = False
        
        for i in range(1, n):
            dt = dates[i]
            p_q = close.iloc[i]['QLD']
            p_s = close.iloc[i]['SCHD']
            
            # If pending rebal from previous day (Mode C or D)
            if pending_rebal:
                # Execute at today's Open
                op_q = opens.iloc[i]['QLD']
                op_s = opens.iloc[i]['SCHD']
                tot_open = sh_qld * op_q + sh_schd * op_s
                target_q = tot_open * 0.7
                target_s = tot_open * 0.3
                
                # Turnover
                turnover = abs(sh_qld * op_q - target_q)
                cost = turnover * (total_cost_rate * 2) # sell one, buy the other
                
                net_tot = tot_open - cost
                sh_qld = (net_tot * 0.7) / op_q
                sh_schd = (net_tot * 0.3) / op_s
                rebal_count += 1
                pending_rebal = False
                
            val_q = sh_qld * p_q
            val_s = sh_schd * p_s
            tot = val_q + val_s
            val_history[i] = tot
            w0 = val_q / tot
            
            # Check trigger
            should_check = True
            if mode == 'D':
                should_check = (dt in month_starts)
                
            if should_check and (w0 >= 0.7 + band or w0 <= 0.7 - band):
                if mode in ['A', 'B']:
                    # Same day close
                    turnover = abs(val_q - tot * 0.7)
                    cost = turnover * (total_cost_rate * 2) if mode == 'B' else 0.0
                    net_tot = tot - cost
                    sh_qld = (net_tot * 0.7) / p_q
                    sh_schd = (net_tot * 0.3) / p_s
                    rebal_count += 1
                    val_history[i] = sh_qld * p_q + sh_schd * p_s
                elif mode in ['C', 'D']:
                    pending_rebal = True
                    
        s = pd.Series(val_history, index=dates)
        years = (dates[-1] - dates[0]).days / 365.25
        cagr = (s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1
        cummax = s.cummax()
        mdd = ((s - cummax) / cummax).min()
        s_2022 = s.loc['2022-01-01':'2022-12-31']
        mdd_2022 = ((s_2022 - s_2022.cummax()) / s_2022.cummax()).min()
        return {
            'cagr': cagr,
            'mdd': mdd,
            'mdd_2022': mdd_2022,
            'rebal_count': rebal_count,
            'final_val': s.iloc[-1]
        }
        
    results = []
    for band_name, band in [('+-10%p', 0.10), ('+-15%p', 0.15), ('+-20%p', 0.20)]:
        res_A = sim_lump('A', band)
        res_B = sim_lump('B', band)
        res_C = sim_lump('C', band)
        res_D = sim_lump('D', band)
        results.append({
            'Band': band_name,
            'Mode A (Orig)': f"CAGR {res_A['cagr']*100:.2f}%, 2022 {res_A['mdd_2022']*100:.2f}%, Reb {res_A['rebal_count']}회",
            'Mode B (Cost)': f"CAGR {res_B['cagr']*100:.2f}%, 2022 {res_B['mdd_2022']*100:.2f}%, Reb {res_B['rebal_count']}회",
            'Mode C (NextOpen)': f"CAGR {res_C['cagr']*100:.2f}%, 2022 {res_C['mdd_2022']*100:.2f}%, Reb {res_C['rebal_count']}회",
            'Mode D (MonthCheck)': f"CAGR {res_D['cagr']*100:.2f}%, 2022 {res_D['mdd_2022']*100:.2f}%, Reb {res_D['rebal_count']}회",
        })
    df_res = pd.DataFrame(results)
    for col in df_res.columns:
        print(f"[{col}]")
        for i, r in df_res.iterrows():
            print(f"  {r['Band']}: {r[col]}")
            
    # -------------------------------------------------------------
    # 2. DCA COMPARISONS
    # -------------------------------------------------------------
    print("\n==================================================")
    print("2. DCA REALISTIC SIMULATION COMPARISON")
    print("==================================================")
    
    def sim_dca_modes(mode, band, monthly_money=100.0):
        month_starts = set(close.resample('MS').first().index)
        total_inv = 0.0
        sh_q = 0.0
        sh_s = 0.0
        val_history = []
        rebal_count = 0
        pending_rebal = False
        cash = 0.0
        
        for i in range(len(dates)):
            dt = dates[i]
            p_q = close.iloc[i]['QLD']
            p_s = close.iloc[i]['SCHD']
            
            # Next-day open execution for DCA rebalancing
            if pending_rebal:
                op_q = opens.iloc[i]['QLD']
                op_s = opens.iloc[i]['SCHD']
                tot_open = sh_q * op_q + sh_s * op_s
                t_q = tot_open * 0.7
                t_s = tot_open * 0.3
                turnover = abs(sh_q * op_q - t_q)
                cost = turnover * (total_cost_rate * 2) if mode in ['B', 'C', 'D'] else 0.0
                net_tot = tot_open - cost
                sh_q = (net_tot * 0.7) / op_q
                sh_s = (net_tot * 0.3) / op_s
                rebal_count += 1
                pending_rebal = False
                
            if dt in month_starts:
                total_inv += monthly_money
                curr0 = sh_q * p_q
                curr1 = sh_s * p_s
                tot = curr0 + curr1 + monthly_money
                t0, t1 = tot * 0.7, tot * 0.3
                need0 = max(0, t0 - curr0)
                need1 = max(0, t1 - curr1)
                if need0 + need1 > 0:
                    a0 = monthly_money * (need0 / (need0 + need1))
                    a1 = monthly_money * (need1 / (need0 + need1))
                else:
                    a0, a1 = monthly_money * 0.7, monthly_money * 0.3
                    
                if mode in ['B', 'C', 'D']:
                    a0 *= (1.0 - total_cost_rate)
                    a1 *= (1.0 - total_cost_rate)
                sh_q += a0 / p_q
                sh_s += a1 / p_s
                
            curr0 = sh_q * p_q
            curr1 = sh_s * p_s
            tot = curr0 + curr1
            w0 = curr0 / tot if tot > 0 else 0.7
            
            should_check = True
            if mode == 'D':
                should_check = (dt in month_starts)
                
            if should_check and (w0 >= 0.7 + band or w0 <= 0.7 - band):
                if mode in ['A', 'B']:
                    turnover = abs(curr0 - tot * 0.7)
                    cost = turnover * (total_cost_rate * 2) if mode == 'B' else 0.0
                    net_tot = tot - cost
                    sh_q = (net_tot * 0.7) / p_q
                    sh_s = (net_tot * 0.3) / p_s
                    rebal_count += 1
                elif mode in ['C', 'D']:
                    pending_rebal = True
                    
            tot = sh_q * p_q + sh_s * p_s
            val_history.append(tot)
            
        s = pd.Series(val_history, index=dates)
        fin_val = s.iloc[-1]
        cummax = s.cummax()
        mdd = ((s - cummax) / cummax).min()
        s_2022 = s.loc['2022-01-01':'2022-12-31']
        mdd_2022 = ((s_2022 - s_2022.cummax()) / s_2022.cummax()).min()
        return {
            'fin_val': fin_val,
            'mdd': mdd,
            'mdd_2022': mdd_2022,
            'rebal_count': rebal_count
        }
        
    dca_res = []
    for band_name, band in [('+-10%p', 0.10), ('+-15%p', 0.15), ('+-20%p', 0.20)]:
        res_A = sim_dca_modes('A', band)
        res_B = sim_dca_modes('B', band)
        res_C = sim_dca_modes('C', band)
        res_D = sim_dca_modes('D', band)
        dca_res.append({
            'Band': band_name,
            'Mode A (Orig)': f"{res_A['fin_val']:.0f}만, MDD {res_A['mdd_2022']*100:.2f}%, Reb {res_A['rebal_count']}회",
            'Mode B (Cost)': f"{res_B['fin_val']:.0f}만, MDD {res_B['mdd_2022']*100:.2f}%, Reb {res_B['rebal_count']}회",
            'Mode C (NextOpen)': f"{res_C['fin_val']:.0f}만, MDD {res_C['mdd_2022']*100:.2f}%, Reb {res_C['rebal_count']}회",
            'Mode D (MonthCheck)': f"{res_D['fin_val']:.0f}만, MDD {res_D['mdd_2022']*100:.2f}%, Reb {res_D['rebal_count']}회",
        })
    df_dca_res = pd.DataFrame(dca_res)
    for col in df_dca_res.columns:
        print(f"[{col}]")
        for i, r in df_dca_res.iterrows():
            print(f"  {r['Band']}: {r[col]}")

if __name__ == '__main__':
    run_frictions_test()
