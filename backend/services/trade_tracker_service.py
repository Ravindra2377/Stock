import sqlite3
import yfinance as yf
import json
import os
from datetime import datetime, timedelta
import pandas as pd

db_path = os.path.join(os.path.dirname(__file__), '..', 'history.db')

class TradeTrackerService:
    @staticmethod
    def create_physical_trade(ticker: str, strategy: str, entry: float, stop: float, target: float):
        """
        Creates a new trade entry in the 'trades' table based on physical risk (1% cap).
        """
        try:
            # Institutional Position Sizing: 1% risk on $100,000 capital
            capital = 100000.0
            risk_per_trade = capital * 0.01
            
            risk_per_share = abs(entry - stop)
            if risk_per_share <= 0: return None
            
            qty = int(risk_per_trade / risk_per_share)
            capital_used = qty * entry
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("""
                INSERT INTO trades (symbol, strategy, entry_price, stop_loss, target, quantity, capital_used, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN')
            """, (ticker, strategy, entry, stop, target, qty, capital_used))
            
            trade_id = c.lastrowid
            conn.commit()
            conn.close()
            return {"id": trade_id, "symbol": ticker, "qty": qty, "risk": risk_per_trade}
        except Exception as e:
            print(f"Error creating trade: {e}")
            return None

    @staticmethod
    def settle_physical_trades():
        """
        Monitors 'OPEN' physical trades and reconciles them against historical data (Daily OHLC).
        """
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            c.execute("SELECT id, symbol, strategy, entry_price, stop_loss, target, quantity, created_at FROM trades WHERE status = 'OPEN'")
            open_trades = c.fetchall()
            
            settled_count = 0
            for tid, symbol, strategy, entry, stop, target, qty, created_at in open_trades:
                # Use yfinance to check if target/stop hit since created_at
                start_date = created_at.split(" ")[0]
                df = yf.download(symbol, start=start_date, progress=False)
                
                if df.empty: continue
                
                outcome = None
                exit_price = 0.0
                exit_reason = ""
                exit_date = None
                
                # Check LONG settlement (assuming long for simplicity, or we can add direction to trades table)
                # Actually, in our generate_trade_structure, we use stop < entry for Long.
                direction = "LONG" if stop < entry else "SHORT"
                
                for idx, row in df.iterrows():
                    high, low = row['High'], row['Low']
                    if direction == "LONG":
                        if low <= stop:
                            outcome = "LOSS"
                            exit_price = stop
                            exit_reason = "STOP"
                            exit_date = idx
                            break
                        elif high >= target:
                            outcome = "WIN"
                            exit_price = target
                            exit_reason = "TARGET"
                            exit_date = idx
                            break
                    else: # SHORT
                        if high >= stop:
                            outcome = "LOSS"
                            exit_price = stop
                            exit_reason = "STOP"
                            exit_date = idx
                            break
                        elif low <= target:
                            outcome = "WIN"
                            exit_price = target
                            exit_reason = "TARGET"
                            exit_date = idx
                            break
                
                if outcome:
                    # Calculate R-Multiple + Actual PnL
                    risk = float(abs(float(entry) - float(stop)))
                    pnl = float((float(exit_price) - float(entry)) * float(qty)) if direction == "LONG" else float((float(entry) - float(exit_price)) * float(qty))
                    pnl_r = float(pnl / (risk * float(qty))) if (risk * float(qty)) > 0 else 0.0

                    
                    c.execute("""
                        UPDATE trades 
                        SET status = 'CLOSED', exit_price = ?, exit_time = ?, exit_reason = ?, pnl = ?, pnl_r = ? 
                        WHERE id = ?
                    """, (float(exit_price), str(exit_date.strftime("%Y-%m-%d %H:%M:%S")) if exit_date is not None else None, str(exit_reason), float(pnl), float(round(float(pnl_r), 2)), tid))

                    
                    # Feed back into Strategy Stats
                    TradeTrackerService._update_strategy_stats(c, strategy, outcome, pnl, pnl_r)
                    settled_count += 1
            
            conn.commit()
            conn.close()
            return {"settled": settled_count}
        except Exception as e:
            print(f"Error settling trades: {e}")
            return {"error": str(e)}

    @staticmethod
    def _update_strategy_stats(cursor, strategy, outcome, pnl, pnl_r):
        """Internal helper to update the self-learning loop."""
        # Ensure strategy exists
        cursor.execute("INSERT OR IGNORE INTO strategy_stats (strategy) VALUES (?)", (strategy,))
        
        # Update counts
        win_inc = 1 if outcome == "WIN" else 0
        loss_inc = 1 if outcome == "LOSS" else 0
        
        cursor.execute("""
            UPDATE strategy_stats 
            SET total_trades = total_trades + 1, 
                wins = wins + ?, 
                losses = losses + ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE strategy = ?
        """, (win_inc, loss_inc, strategy))
        
        # Recalculate WR, PF, Expectancy
        cursor.execute("SELECT wins, losses, total_trades FROM strategy_stats WHERE strategy = ?", (strategy,))
        wins, losses, total = cursor.fetchone()
        
        win_rate = (float(wins) / float(total)) * 100.0 if total > 0 else 0.0

        
        # Simple R-based expectancy
        # We fetch all closed trades for this strategy to get true avg_r
        # (Alternatively, we can track running sums in strategy_stats table)
        # For simplicity in this loop, we'll just update WR for now.
        cursor.execute("UPDATE strategy_stats SET win_rate = ? WHERE strategy = ?", (float(round(float(win_rate), 2)), str(strategy)))


    @staticmethod
    def get_strategy_pf(strategy: str) -> float:
        """Fetches the Profit Factor for a strategy to use in the dynamic weighting loop."""
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT profit_factor FROM strategy_stats WHERE strategy = ?", (strategy,))
            res = c.fetchone()
            conn.close()
            return res[0] if res else 1.0 # Default to 1.0 (neutral)
        except:
            return 1.0

    @staticmethod
    def get_portfolio():
        """Aggregates all trades and returns the physical 'Truth' dashboard."""
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("SELECT * FROM trades ORDER BY created_at DESC")
            trades = [dict(row) for row in c.fetchall()]
            
            c.execute("SELECT * FROM strategy_stats")
            stats = [dict(row) for row in c.fetchall()]
            
            conn.close()
            
            active = [t for t in trades if t['status'] == 'OPEN']
            closed = [t for t in trades if t['status'] == 'CLOSED']
            
            total_r = sum([float(t['pnl_r']) for t in closed if t['pnl_r'] is not None])

            
            return {
                "active_trades": active,
                "closed_trades": closed,
                "strategy_stats": stats,
                "summary": {
                    "total_equity_r": float(round(float(total_r), 2)),
                    "active_risk_r": float(len(active)) * 1.0,
                    "win_rate": float(round(float((len([t for t in closed if t['exit_reason'] == 'TARGET']) / len(closed) * 100.0)), 1)) if closed else 0.0
                }

            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_active_risk() -> float:
        """Systemic risk cap: 1.0R per trade."""
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM trades WHERE status = 'OPEN'")
            count = c.fetchone()[0] or 0
            conn.close()
            return float(count) # Each trade is 1% risk (1R)
        except:
            return 0.0
