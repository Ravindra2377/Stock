import sqlite3
import json
import os
from typing import Dict, Any

db_path = os.path.join(os.path.dirname(__file__), '..', 'history.db')

class FeedbackService:
    @staticmethod
    def init_db():
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            price REAL,
            prediction_json TEXT,
            outcome TEXT
        )''')
        
        # Phase 14: Dynamic Schema expansions for Physical R-Multiple tracking
        try: c.execute("ALTER TABLE predictions ADD COLUMN pnl_r REAL DEFAULT 0.0")
        except sqlite3.OperationalError: pass
            
        try: c.execute("ALTER TABLE predictions ADD COLUMN exit_price REAL DEFAULT 0.0")
        except sqlite3.OperationalError: pass
            
        try: c.execute("ALTER TABLE predictions ADD COLUMN duration INTEGER DEFAULT 0")
        except sqlite3.OperationalError: pass
            
        try: c.execute("ALTER TABLE predictions ADD COLUMN algorithm_version TEXT")
        except sqlite3.OperationalError: pass
            
        conn.commit()
        conn.close()

    @staticmethod
    def log_prediction(ticker: str, price: float, analysis: Dict[str, Any]):
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # Phase 10: Auto-Tracking duplicate protection
            c.execute("SELECT id FROM predictions WHERE ticker = ? AND outcome = 'PENDING'", (ticker,))
            if c.fetchone():
                conn.close()
                return  # Block duplicate live trades
                
            version = analysis.get('algorithm_version', 'UNKNOWN')
            c.execute("INSERT INTO predictions (ticker, price, prediction_json, outcome, algorithm_version) VALUES (?, ?, ?, ?, ?)",
                      (ticker, price, json.dumps(analysis), "PENDING", version))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Failed to log prediction: {e}")

    @staticmethod
    def get_performance_metrics() -> Dict[str, Any]:
        """Calculates Strategy Edge based on logged trade outcomes."""
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # Total trades
            c.execute("SELECT COUNT(*) FROM predictions WHERE outcome != 'PENDING'")
            total_closed = c.fetchone()[0] or 0
            
            c.execute("SELECT COUNT(*) FROM predictions WHERE outcome = 'WIN'")
            total_wins = c.fetchone()[0] or 0
            
            c.execute("SELECT COUNT(*) FROM predictions WHERE outcome = 'LOSS'")
            total_losses = c.fetchone()[0] or 0
            
            c.execute("SELECT COUNT(*) FROM predictions WHERE outcome = 'PENDING'")
            total_pending = c.fetchone()[0] or 0
            
            conn.close()
            
            win_rate = (total_wins / total_closed * 100) if total_closed > 0 else 0.0
            profit_factor = round(total_wins / max(1, total_losses), 2) if total_closed > 0 else 0.0
            
            return {
                "total_trades": total_closed + total_pending,
                "completed_trades": total_closed,
                "pending_trades": total_pending,
                "win_rate": round(win_rate, 1),
                "profit_factor": profit_factor,
                "strategy_edge": "PROFITABLE" if win_rate > 50 else "TESTING" if total_closed < 10 else "NEGATIVE"
            }
        except Exception as e:
            print(f"Failed to fetch metrics: {e}")
            return {
                "win_rate": 0.0, "profit_factor": 0.0, "strategy_edge": "UNKNOWN"
            }

    @staticmethod
    def get_strategy_weight(ticker: str) -> float:
        """Phase 15: Auto-Learning Matrix - Calculates real live PF to adjust weights."""
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT pnl_r FROM predictions WHERE ticker = ? AND outcome IN ('WIN', 'LOSS')", (ticker,))
            results = c.fetchall()
            conn.close()
            
            if len(results) < 5: return 1.0
            
            gross_p = sum([r[0] for r in results if r[0] and r[0] > 0])
            gross_l = abs(sum([r[0] for r in results if r[0] and r[0] < 0]))
            
            real_pf = gross_p / gross_l if gross_l > 0 else (99.9 if gross_p > 0 else 0)
            
            # Multiplier configuration
            if real_pf > 1.5: return 1.30  # +30% Confidence Boost
            if real_pf < 1.0 and len(results) >= 10: return 0.50  # -50% Penalty to force-kill execution 
            return 1.0
        except Exception:
            return 1.0

FeedbackService.init_db()
