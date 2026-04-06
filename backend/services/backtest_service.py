import pandas as pd
from typing import Dict, Any, List
from .stock_service import StockService
from .indicator_service import IndicatorService

class BacktestService:
    @staticmethod
    def run_backtest(ticker: str, period: str = "1y") -> Dict[str, Any]:
        """
        Simulates the v5.0 Quant Execution Engine over historical data
        to derive exact Win Rate, Profit Factor, and EV Edge.
        """
        try:
            # 1. Fetch raw data
            df = StockService.get_stock_data(ticker, period=period)
            if df.empty or len(df) < 100:
                return {"error": "Insufficient data"}
                
            # 2. Add technical indicators perfectly
            df = IndicatorService.calculate_indicators(df)
            
            # Start backtest after 60 days to allow SMAs/EMAs to warm up
            start_idx = 60
            
            trades = []
            open_trade = None
            
            for i in range(start_idx, len(df)):
                current_bar = df.iloc[i]
                
                # Check if we have an open trade
                if open_trade:
                    # Check if target or stop was hit
                    high = current_bar['High']
                    low = current_bar['Low']
                    
                    duration = i - open_trade['entry_idx']
                    time_exit = duration >= 15
                    
                    if open_trade['direction'] == 'LONG':
                        if low <= open_trade['stop']:
                            open_trade['outcome'] = 'LOSS'
                            # include 0.1% negative slippage on exit
                            open_trade['exit_price'] = open_trade['stop'] * 0.999
                            open_trade['loss_amt'] = abs(open_trade['entry_price'] - open_trade['exit_price'])
                            trades.append(open_trade)
                            open_trade = None
                        elif high >= open_trade['target']:
                            open_trade['outcome'] = 'WIN'
                            open_trade['exit_price'] = open_trade['target'] * 0.999 
                            open_trade['win_amt'] = abs(open_trade['exit_price'] - open_trade['entry_price'])
                            trades.append(open_trade)
                            open_trade = None
                        elif time_exit:
                            open_trade['exit_price'] = current_bar['Close'] * 0.999
                            diff = open_trade['exit_price'] - open_trade['entry_price']
                            open_trade['outcome'] = 'WIN' if diff > 0 else 'LOSS'
                            open_trade['win_amt'] = max(0, diff)
                            open_trade['loss_amt'] = max(0, -diff)
                            trades.append(open_trade)
                            open_trade = None
                            
                    elif open_trade['direction'] == 'SHORT':
                        if high >= open_trade['stop']:
                            open_trade['outcome'] = 'LOSS'
                            open_trade['exit_price'] = open_trade['stop'] * 1.001
                            open_trade['loss_amt'] = abs(open_trade['exit_price'] - open_trade['entry_price'])
                            trades.append(open_trade)
                            open_trade = None
                        elif low <= open_trade['target']:
                            open_trade['outcome'] = 'WIN'
                            open_trade['exit_price'] = open_trade['target'] * 1.001
                            open_trade['win_amt'] = abs(open_trade['entry_price'] - open_trade['exit_price'])
                            trades.append(open_trade)
                            open_trade = None
                        elif time_exit:
                            open_trade['exit_price'] = current_bar['Close'] * 1.001
                            diff = open_trade['entry_price'] - open_trade['exit_price']
                            open_trade['outcome'] = 'WIN' if diff > 0 else 'LOSS'
                            open_trade['win_amt'] = max(0, diff)
                            open_trade['loss_amt'] = max(0, -diff)
                            trades.append(open_trade)
                            open_trade = None
                            
                # If no open trade, look for entries
                if not open_trade:
                    # Lookback window exactly simulating "now"
                    window = df.iloc[:i+1].copy()
                    
                    # Compute signal structure
                    signal = IndicatorService.generate_signals(ticker, window, weekly_df=None)
                    
                    trade_struct = signal.get('trade', {})
                    direction = trade_struct.get('direction', 'WAIT')
                    
                    if direction != 'WAIT':
                        # Validated by v5 filters (is_positive EV, RR >= 1.5)
                        rr = trade_struct.get('rr_value', 0)
                        ev = signal.get('expected_value', {}).get('ev', 0)
                        
                        # Only take trades that passed the strict UI block
                        is_blocked = any("V5 FILTER" in warn for warn in signal.get('risk_warnings', []))
                        
                        if not is_blocked and rr >= 1.5:
                            
                            strat = "GENERIC"
                            if signal.get('breakout', {}).get('status') == 'CONFIRMED':
                                strat = "BREAKOUT"
                            elif signal.get('regime', {}).get('regime') == 'TRENDING':
                                strat = "TREND_CONT"
                            elif signal.get('regime', {}).get('regime') == 'SIDEWAYS':
                                strat = "MEAN_REVERSION"
                            
                            # 0.1% fill slippage assumption
                            fill_entry = trade_struct.get('entry', current_bar['Close'])
                            fill_entry = fill_entry * 1.001 if direction == 'LONG' else fill_entry * 0.999
                            
                            open_trade = {
                                'entry_idx': i,
                                'strategy': strat,
                                'entry_date': current_bar.name.strftime('%Y-%m-%d'),
                                'direction': direction,
                                'entry_price': fill_entry,
                                'target': trade_struct.get('targets', [0])[0],
                                'stop': trade_struct.get('stop_loss', 0),
                                'rr_val': rr,
                                'ev': ev,
                                'outcome': 'PENDING',
                                'exit_price': 0,
                                'win_amt': 0,
                                'loss_amt': 0
                            }
                            
            # Process results
            completed_trades = [t for t in trades if t['outcome'] in ('WIN', 'LOSS')]
            
            wins = [t for t in completed_trades if t['outcome'] == 'WIN']
            losses = [t for t in completed_trades if t['outcome'] == 'LOSS']
            
            win_count = len(wins)
            loss_count = len(losses)
            total = len(completed_trades)
            
            gross_profit = sum(t['win_amt'] for t in wins)
            gross_loss = sum(t['loss_amt'] for t in losses)
            
            win_rate = round((win_count / total * 100), 1) if total > 0 else 0
            profit_factor = round((gross_profit / gross_loss), 2) if gross_loss > 0 else (99.9 if gross_profit > 0 else 0)
            
            avg_win = gross_profit / win_count if win_count > 0 else 0
            avg_loss = gross_loss / loss_count if loss_count > 0 else 0
            avg_rr = round((avg_win / avg_loss), 2) if avg_loss > 0 else 0
            
            # Use raw win_rate ratio (0.0 to 1.0) for math
            wr_ratio = win_count / total if total > 0 else 0
            lr_ratio = 1.0 - wr_ratio
            historical_ev_dollar = (wr_ratio * avg_win) - (lr_ratio * avg_loss)
            historical_ev = round(historical_ev_dollar / avg_loss, 2) if avg_loss > 0 else 0.0

            # Adv Drawdown + Strategy Tracking
            peak = 0
            current_pnl = 0
            max_dd = 0
            current_streak = 0
            max_losing_streak = 0
            strat_map = {}
            
            for t in completed_trades:
                # Approximate 1R unit scale PnL
                if avg_loss > 0:
                    r_pnl = (t['win_amt'] - t['loss_amt']) / avg_loss
                else: 
                    r_pnl = t['win_amt'] - t['loss_amt']
                
                current_pnl += r_pnl
                if current_pnl > peak: peak = current_pnl
                dd = peak - current_pnl
                if dd > max_dd: max_dd = dd
                
                if t['outcome'] == 'LOSS':
                    current_streak += 1
                    if current_streak > max_losing_streak: max_losing_streak = current_streak
                else:
                    current_streak = 0
                    
                s = t['strategy']
                if s not in strat_map: strat_map[s] = {'wins': 0, 'losses': 0, 'gross_p': 0, 'gross_l': 0}
                if t['outcome'] == 'WIN': 
                    strat_map[s]['wins'] += 1
                    strat_map[s]['gross_p'] += t['win_amt']
                else: 
                    strat_map[s]['losses'] += 1
                    strat_map[s]['gross_l'] += t['loss_amt']

            # Phase 12: Quantitative Confidence Engine (f(sample_size, variance, pf))
            sample_weight = min(1.0, total / 300.0)
            pf_weight = min(1.5, profit_factor / 1.5)

            # Simple variance heuristic via Max Drawdown penalization
            variance_penalty = max(0, 1.0 - (max_dd / max(1, current_pnl))) if current_pnl > 0 else 0.5

            # Weighted algorithmic confidence
            raw_conf = (sample_weight * 0.4 + (pf_weight / 1.5) * 0.4 + variance_penalty * 0.2) * 100
            numeric_confidence = round(min(100, max(0, raw_conf)), 1)

            if numeric_confidence > 80:
                confidence_label = "VERY HIGH"
            elif numeric_confidence >= 60:
                confidence_label = "MEDIUM-HIGH"
            elif numeric_confidence >= 40:
                confidence_label = "MEDIUM"
            else:
                confidence_label = "LOW"
                
            strat_metrics = []
            for s, counts in strat_map.items():
                tw = counts['wins']
                tl = counts['losses']
                ts = tw + tl
                if ts == 0: continue
                
                wr = tw / ts
                gp = counts['gross_p']
                gl = counts['gross_l']
                pf_s = gp / gl if gl > 0 else (99.9 if gp > 0 else 0)
                
                # Phase 11: Strategy Ranking Engine (Score = PF * WR * ConsistencyWeight)
                consistency = min(1.0, ts / 30.0)
                strat_score = pf_s * wr * 100 * consistency
                
                # Phase 12: Kill Losing Strategies
                is_disabled = (pf_s < 1.0 and ts > 100)
                
                strat_metrics.append({
                    "name": s,
                    "trades": ts,
                    "win_rate": round(wr * 100, 1),
                    "profit_factor": round(pf_s, 2),
                    "score": round(strat_score, 1),
                    "disabled": is_disabled
                })
                
            strat_metrics.sort(key=lambda x: x['score'], reverse=True)
            best_strat = strat_metrics[0] if strat_metrics else None
            
            return {
                "ticker": ticker,
                "strategy_edge": {
                    "total_trades_taken": total,
                    "confidence": numeric_confidence,
                    "confidence_label": confidence_label,
                    "win_rate": win_rate,
                    "profit_factor": profit_factor,
                    "avg_rr": avg_rr,
                    "historical_ev": historical_ev,
                    "historical_ev_dollar": round(historical_ev_dollar, 2),
                    "max_drawdown_r": round(max_dd, 2),
                    "max_losing_streak": max_losing_streak,
                    "segments": strat_metrics,
                    "best_strategy": best_strat
                }
            }
        except Exception as e:
            return {"error": str(e)}
