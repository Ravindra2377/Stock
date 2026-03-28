import pandas as pd
import numpy as np
import ta
from typing import Dict, Any, List

class IndicatorService:
    """
    Multi-Factor Technical Analysis Engine.
    Generates a composite score (0-100) from 9 weighted indicators.
    """

    # ─── Indicator Weights (must sum to 1.0) ───────────────────────
    WEIGHTS = {
        'rsi':           0.15,   # Momentum / Overbought-Oversold
        'macd':          0.15,   # Trend momentum
        'sma_cross':     0.12,   # Medium-term trend (SMA 20/50)
        'ema_cross':     0.10,   # Short-term trend (EMA 12/26)
        'bollinger':     0.10,   # Volatility position
        'volume':        0.10,   # Volume conviction
        'adx':           0.08,   # Trend strength
        'stochastic':    0.08,   # Short-term reversal
        'trend_200':     0.12,   # Long-term trend (Price vs SMA 200)
    }

    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators for a given stock."""
        if df.empty or len(df) < 30:
            return df

        close = df['Close']
        high = df['High'] if 'High' in df.columns else close
        low = df['Low'] if 'Low' in df.columns else close
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))

        # ── RSI (14) ──
        df['RSI'] = ta.momentum.RSIIndicator(close=close, window=14).rsi()

        # ── SMA ──
        df['SMA_20'] = ta.trend.SMAIndicator(close=close, window=20).sma_indicator()
        df['SMA_50'] = ta.trend.SMAIndicator(close=close, window=50).sma_indicator()
        df['SMA_200'] = ta.trend.SMAIndicator(close=close, window=200).sma_indicator()

        # ── EMA ──
        df['EMA_12'] = ta.trend.EMAIndicator(close=close, window=12).ema_indicator()
        df['EMA_26'] = ta.trend.EMAIndicator(close=close, window=26).ema_indicator()
        df['EMA_20'] = ta.trend.EMAIndicator(close=close, window=20).ema_indicator()

        # ── MACD ──
        macd = ta.trend.MACD(close=close)
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        df['MACD_Diff'] = macd.macd_diff()

        # ── Bollinger Bands ──
        bb = ta.volatility.BollingerBands(close=close)
        df['BB_High'] = bb.bollinger_hband()
        df['BB_Low'] = bb.bollinger_lband()
        df['BB_Mid'] = bb.bollinger_mavg()

        # ── ADX (Average Directional Index) ──
        try:
            adx_indicator = ta.trend.ADXIndicator(high=high, low=low, close=close, window=14)
            df['ADX'] = adx_indicator.adx()
            df['DI_Plus'] = adx_indicator.adx_pos()
            df['DI_Minus'] = adx_indicator.adx_neg()
        except:
            df['ADX'] = 0
            df['DI_Plus'] = 0
            df['DI_Minus'] = 0

        # ── Stochastic Oscillator ──
        try:
            stoch = ta.momentum.StochasticOscillator(high=high, low=low, close=close)
            df['Stoch_K'] = stoch.stoch()
            df['Stoch_D'] = stoch.stoch_signal()
        except:
            df['Stoch_K'] = 50
            df['Stoch_D'] = 50

        # ── Volume Average ──
        df['Vol_Avg_20'] = volume.rolling(window=20).mean()

        return df

    @staticmethod
    def _score_rsi(rsi: float) -> float:
        """RSI Score: 0-100. Low RSI = bullish, High RSI = bearish."""
        if pd.isna(rsi):
            return 50.0
        if rsi <= 20:
            return 95.0   # Extremely oversold = Strong Buy
        elif rsi <= 30:
            return 80.0   # Oversold = Buy
        elif rsi <= 40:
            return 65.0   # Slightly oversold
        elif rsi <= 60:
            return 50.0   # Neutral
        elif rsi <= 70:
            return 35.0   # Slightly overbought
        elif rsi <= 80:
            return 20.0   # Overbought = Sell
        else:
            return 5.0    # Extremely overbought = Strong Sell

    @staticmethod
    def _score_macd(macd: float, signal: float, prev_macd: float, prev_signal: float) -> float:
        """MACD Score: Crossovers and distance from signal line."""
        if pd.isna(macd) or pd.isna(signal):
            return 50.0

        # Bullish crossover (MACD crosses above Signal)
        if macd > signal and prev_macd <= prev_signal:
            return 85.0
        # Bearish crossover
        elif macd < signal and prev_macd >= prev_signal:
            return 15.0
        # MACD above signal (bullish territory)
        elif macd > signal:
            diff_pct = abs(macd - signal) / (abs(signal) + 1e-10)
            return min(70 + diff_pct * 100, 80)
        # MACD below signal (bearish territory)
        else:
            diff_pct = abs(signal - macd) / (abs(signal) + 1e-10)
            return max(30 - diff_pct * 100, 20)

    @staticmethod
    def _score_sma_cross(sma_20: float, sma_50: float, prev_sma_20: float, prev_sma_50: float) -> float:
        """SMA 20/50 Crossover Score."""
        if pd.isna(sma_20) or pd.isna(sma_50):
            return 50.0

        # Golden Cross (20 crosses above 50)
        if sma_20 > sma_50 and prev_sma_20 <= prev_sma_50:
            return 90.0
        # Death Cross
        elif sma_20 < sma_50 and prev_sma_20 >= prev_sma_50:
            return 10.0
        # 20 above 50 (uptrend)
        elif sma_20 > sma_50:
            return 65.0
        else:
            return 35.0

    @staticmethod
    def _score_ema_cross(ema_12: float, ema_26: float, prev_ema_12: float, prev_ema_26: float) -> float:
        """EMA 12/26 Crossover Score."""
        if pd.isna(ema_12) or pd.isna(ema_26):
            return 50.0

        if ema_12 > ema_26 and prev_ema_12 <= prev_ema_26:
            return 85.0
        elif ema_12 < ema_26 and prev_ema_12 >= prev_ema_26:
            return 15.0
        elif ema_12 > ema_26:
            return 62.0
        else:
            return 38.0

    @staticmethod
    def _score_bollinger(close: float, bb_high: float, bb_low: float, bb_mid: float) -> float:
        """Bollinger Bands Score: Position within the bands."""
        if pd.isna(bb_high) or pd.isna(bb_low) or bb_high == bb_low:
            return 50.0

        position = (close - bb_low) / (bb_high - bb_low)

        if position <= 0.05:
            return 90.0   # At or below lower band = potential bounce
        elif position <= 0.2:
            return 72.0
        elif position >= 0.95:
            return 10.0   # At or above upper band = potential pullback
        elif position >= 0.8:
            return 28.0
        else:
            return 50.0   # Middle = neutral

    @staticmethod
    def _score_volume(volume: float, vol_avg: float, price_change_pct: float) -> float:
        """Volume Score: High volume on up-move = bullish, down-move = bearish."""
        if pd.isna(vol_avg) or vol_avg == 0 or pd.isna(volume):
            return 50.0

        vol_ratio = volume / vol_avg

        if vol_ratio > 1.5 and price_change_pct > 0:
            return 80.0   # High volume on green day = strong conviction
        elif vol_ratio > 1.5 and price_change_pct < 0:
            return 20.0   # High volume on red day = selling pressure
        elif vol_ratio > 1.0 and price_change_pct > 0:
            return 62.0
        elif vol_ratio > 1.0 and price_change_pct < 0:
            return 38.0
        else:
            return 50.0   # Low volume = inconclusive

    @staticmethod
    def _score_adx(adx: float, di_plus: float, di_minus: float) -> float:
        """ADX Score: Measures trend strength + direction."""
        if pd.isna(adx):
            return 50.0

        if adx < 20:
            return 50.0   # No clear trend

        # Strong trend exists
        if di_plus > di_minus:
            # Bullish trend
            if adx > 40:
                return 85.0   # Very strong bullish trend
            elif adx > 25:
                return 70.0
            else:
                return 58.0
        else:
            # Bearish trend
            if adx > 40:
                return 15.0   # Very strong bearish trend
            elif adx > 25:
                return 30.0
            else:
                return 42.0

    @staticmethod
    def _score_stochastic(k: float, d: float, prev_k: float, prev_d: float) -> float:
        """Stochastic Oscillator Score."""
        if pd.isna(k) or pd.isna(d):
            return 50.0

        # Bullish crossover in oversold zone
        if k < 20 and k > d and prev_k <= prev_d:
            return 90.0
        # Bearish crossover in overbought zone
        elif k > 80 and k < d and prev_k >= prev_d:
            return 10.0
        elif k < 20:
            return 75.0   # Oversold
        elif k > 80:
            return 25.0   # Overbought
        elif k > d:
            return 58.0
        else:
            return 42.0

    @staticmethod
    def _score_trend_200(close: float, sma_200: float) -> float:
        """Price vs SMA 200 Score: Long-term trend health."""
        if pd.isna(sma_200) or sma_200 == 0:
            return 50.0

        pct_above = ((close - sma_200) / sma_200) * 100

        if pct_above > 20:
            return 75.0   # Well above 200 SMA
        elif pct_above > 5:
            return 68.0   # Above
        elif pct_above > 0:
            return 58.0   # Slightly above
        elif pct_above > -5:
            return 42.0   # Slightly below
        elif pct_above > -20:
            return 32.0   # Below
        else:
            return 20.0   # Well below 200 SMA

    @classmethod
    def generate_signals(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate a multi-factor composite score (0-100) with detailed breakdown."""
        if df.empty or 'RSI' not in df.columns or len(df) < 3:
            return {
                "recommendation": "NEUTRAL",
                "signals": [],
                "rsi": 0,
                "last_price": 0,
                "composite_score": 50,
                "breakdown": {}
            }

        last = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3] if len(df) >= 3 else prev

        # Price change
        price_change_pct = ((last['Close'] - prev['Close']) / prev['Close']) * 100 if prev['Close'] != 0 else 0

        # ── Score each indicator ──
        scores = {}

        scores['rsi'] = cls._score_rsi(last.get('RSI', 50))

        scores['macd'] = cls._score_macd(
            last.get('MACD', 0), last.get('MACD_Signal', 0),
            prev.get('MACD', 0), prev.get('MACD_Signal', 0)
        )

        scores['sma_cross'] = cls._score_sma_cross(
            last.get('SMA_20', 0), last.get('SMA_50', 0),
            prev.get('SMA_20', 0), prev.get('SMA_50', 0)
        )

        scores['ema_cross'] = cls._score_ema_cross(
            last.get('EMA_12', 0), last.get('EMA_26', 0),
            prev.get('EMA_12', 0), prev.get('EMA_26', 0)
        )

        scores['bollinger'] = cls._score_bollinger(
            last['Close'], last.get('BB_High', 0),
            last.get('BB_Low', 0), last.get('BB_Mid', 0)
        )

        scores['volume'] = cls._score_volume(
            last.get('Volume', 0), last.get('Vol_Avg_20', 0), price_change_pct
        )

        scores['adx'] = cls._score_adx(
            last.get('ADX', 0), last.get('DI_Plus', 0), last.get('DI_Minus', 0)
        )

        scores['stochastic'] = cls._score_stochastic(
            last.get('Stoch_K', 50), last.get('Stoch_D', 50),
            prev.get('Stoch_K', 50), prev.get('Stoch_D', 50)
        )

        scores['trend_200'] = cls._score_trend_200(last['Close'], last.get('SMA_200', 0))

        # ── Weighted composite score ──
        composite = sum(scores[k] * cls.WEIGHTS[k] for k in scores)
        composite = round(composite, 1)

        # ── Generate human-readable signals ──
        signals = []
        rsi_val = round(last.get('RSI', 0), 2)

        if scores['rsi'] >= 75:
            signals.append(f"RSI Oversold ({rsi_val})")
        elif scores['rsi'] <= 25:
            signals.append(f"RSI Overbought ({rsi_val})")

        if scores['macd'] >= 80:
            signals.append("Bullish MACD Crossover")
        elif scores['macd'] <= 20:
            signals.append("Bearish MACD Crossover")

        if scores['sma_cross'] >= 85:
            signals.append("Golden Cross (SMA 20/50)")
        elif scores['sma_cross'] <= 15:
            signals.append("Death Cross (SMA 20/50)")

        if scores['volume'] >= 75:
            signals.append("High Volume Buying")
        elif scores['volume'] <= 25:
            signals.append("High Volume Selling")

        if scores['adx'] >= 70:
            signals.append("Strong Bullish Trend (ADX)")
        elif scores['adx'] <= 30 and last.get('ADX', 0) > 20:
            signals.append("Strong Bearish Trend (ADX)")

        if scores['stochastic'] >= 85:
            signals.append("Stochastic Bullish Reversal")
        elif scores['stochastic'] <= 15:
            signals.append("Stochastic Bearish Reversal")

        if scores['bollinger'] >= 85:
            signals.append("Near Lower Bollinger Band")
        elif scores['bollinger'] <= 15:
            signals.append("Near Upper Bollinger Band")

        if not signals:
            signals.append("No strong directional signals")

        # ── Final recommendation ──
        if composite >= 80:
            recommendation = "STRONG BUY"
        elif composite >= 65:
            recommendation = "BUY"
        elif composite >= 45:
            recommendation = "HOLD"
        elif composite >= 30:
            recommendation = "SELL"
        else:
            recommendation = "STRONG SELL"

        return {
            "recommendation": recommendation,
            "composite_score": composite,
            "signals": signals,
            "rsi": rsi_val,
            "last_price": round(last['Close'], 2),
            "breakdown": {k: round(v, 1) for k, v in scores.items()},
            "price_change_pct": round(price_change_pct, 2),
        }
