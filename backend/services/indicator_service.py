import pandas as pd
import numpy as np
import ta
from typing import Dict, Any, List, Tuple

class IndicatorService:
    """
    Pro Trading Engine v2.0
    ─────────────────────────
    Behavior-based prediction system with:
    - Market Regime Detection (Trending/Sideways/Volatile)
    - Dynamic Weight Engine (shifts by regime)
    - Confirmed Breakout Detection (not just price > resistance)
    - Smart Support/Resistance Zones (cluster-based)
    - Deep Volume Intelligence + Smart Money Detection
    - Trade Structure (Entry/Target/Stop Loss with ATR)
    - Multi-Timeframe Confirmation
    - Momentum Strength & Signal Quality Tiers
    """

    # ─── Regime-Adaptive Weights ──────────────────────────────────
    REGIME_WEIGHTS = {
        "TRENDING": {
            'macd': 0.22, 'sma_cross': 0.15, 'ema_cross': 0.12,
            'rsi': 0.05, 'stochastic': 0.05, 'volume': 0.18,
            'breakout': 0.13, 'bollinger': 0.05, 'trend_200': 0.05,
        },
        "SIDEWAYS": {
            'macd': 0.08, 'sma_cross': 0.08, 'ema_cross': 0.08,
            'rsi': 0.22, 'stochastic': 0.18, 'volume': 0.12,
            'breakout': 0.08, 'bollinger': 0.12, 'trend_200': 0.04,
        },
        "VOLATILE": {
            'macd': 0.12, 'sma_cross': 0.08, 'ema_cross': 0.08,
            'rsi': 0.12, 'stochastic': 0.10, 'volume': 0.18,
            'breakout': 0.18, 'bollinger': 0.08, 'trend_200': 0.06,
        },
    }

    # ═══════════════════════════════════════════════════════════════
    #  CALCULATE ALL INDICATORS
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or len(df) < 30:
            return df

        close = df['Close']
        high = df['High'] if 'High' in df.columns else close
        low = df['Low'] if 'Low' in df.columns else close
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))

        # RSI
        df['RSI'] = ta.momentum.RSIIndicator(close=close, window=14).rsi()

        # Moving Averages
        df['SMA_20'] = ta.trend.SMAIndicator(close=close, window=20).sma_indicator()
        df['SMA_50'] = ta.trend.SMAIndicator(close=close, window=50).sma_indicator()
        df['SMA_200'] = ta.trend.SMAIndicator(close=close, window=200).sma_indicator()
        df['EMA_12'] = ta.trend.EMAIndicator(close=close, window=12).ema_indicator()
        df['EMA_26'] = ta.trend.EMAIndicator(close=close, window=26).ema_indicator()
        df['EMA_20'] = ta.trend.EMAIndicator(close=close, window=20).ema_indicator()
        df['EMA_50'] = ta.trend.EMAIndicator(close=close, window=50).ema_indicator()

        # MACD
        macd = ta.trend.MACD(close=close)
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        df['MACD_Diff'] = macd.macd_diff()

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(close=close)
        df['BB_High'] = bb.bollinger_hband()
        df['BB_Low'] = bb.bollinger_lband()
        df['BB_Mid'] = bb.bollinger_mavg()

        # ADX
        try:
            adx_ind = ta.trend.ADXIndicator(high=high, low=low, close=close, window=14)
            df['ADX'] = adx_ind.adx()
            df['DI_Plus'] = adx_ind.adx_pos()
            df['DI_Minus'] = adx_ind.adx_neg()
        except:
            df['ADX'] = 0; df['DI_Plus'] = 0; df['DI_Minus'] = 0

        # Stochastic
        try:
            stoch = ta.momentum.StochasticOscillator(high=high, low=low, close=close)
            df['Stoch_K'] = stoch.stoch()
            df['Stoch_D'] = stoch.stoch_signal()
        except:
            df['Stoch_K'] = 50; df['Stoch_D'] = 50

        # ATR (Average True Range)
        try:
            df['ATR'] = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
        except:
            df['ATR'] = 0

        # Volume Average
        df['Vol_Avg_20'] = volume.rolling(window=20).mean()

        # Rate of Change (Momentum Acceleration)
        df['ROC_5'] = close.pct_change(5) * 100
        df['ROC_10'] = close.pct_change(10) * 100

        # Candle Body Size
        df['Body_Size'] = abs(df['Close'] - df['Open']) if 'Open' in df.columns else 0
        df['Avg_Body'] = df['Body_Size'].rolling(window=20).mean() if 'Open' in df.columns else 0

        # ATR Average (for volatility regime)
        df['ATR_Avg'] = df['ATR'].rolling(window=20).mean() if 'ATR' in df.columns else 0

        return df

    # ═══════════════════════════════════════════════════════════════
    #  MARKET REGIME DETECTION
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def detect_regime(df: pd.DataFrame) -> Dict[str, Any]:
        """Classify market as TRENDING, SIDEWAYS, or VOLATILE."""
        if df.empty or len(df) < 30:
            return {"regime": "SIDEWAYS", "strength": "weak", "detail": "Insufficient data"}

        last = df.iloc[-1]
        adx = last.get('ADX', 0)
        atr = last.get('ATR', 0)
        atr_avg = last.get('ATR_Avg', atr)
        di_plus = last.get('DI_Plus', 0)
        di_minus = last.get('DI_Minus', 0)

        # Trend strength from EMA separation
        ema_20 = last.get('EMA_20', 0)
        ema_50 = last.get('EMA_50', 0)
        trend_gap = 0
        if ema_50 and ema_50 != 0:
            trend_gap = abs(ema_20 - ema_50) / ema_50 * 100

        # Volatility check
        volatile = False
        if atr_avg and atr_avg > 0 and atr > 1.5 * atr_avg:
            volatile = True

        if volatile and adx < 25:
            regime = "VOLATILE"
            if atr > 2.0 * atr_avg:
                strength = "extreme"
                detail = "Extreme volatility detected — ATR well above average"
            else:
                strength = "high"
                detail = "High volatility with no clear trend direction"
        elif adx > 25 and trend_gap > 0.5:
            regime = "TRENDING"
            direction = "BULLISH" if di_plus > di_minus else "BEARISH"
            if adx > 40 and trend_gap > 1.5:
                strength = "strong"
                detail = f"Strong {direction} trend — ADX {adx:.0f}, EMAs diverging"
            else:
                strength = "moderate"
                detail = f"Moderate {direction} trend — ADX {adx:.0f}"
        else:
            regime = "SIDEWAYS"
            if adx < 15:
                strength = "flat"
                detail = "Very low directional movement — choppy/range-bound"
            else:
                strength = "weak"
                detail = "Weak trend — market consolidating"

        return {"regime": regime, "strength": strength, "detail": detail}

    # ═══════════════════════════════════════════════════════════════
    #  SMART SUPPORT/RESISTANCE ZONES (Cluster-based)
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def find_sr_zones(df: pd.DataFrame, lookback: int = 60, tolerance_pct: float = 0.5) -> Dict[str, Any]:
        """Find support/resistance zones using cluster detection."""
        if df.empty or len(df) < lookback:
            lookback = max(len(df) - 1, 20)

        recent = df.tail(lookback)
        highs = recent['High'].values if 'High' in df.columns else recent['Close'].values
        lows = recent['Low'].values if 'Low' in df.columns else recent['Close'].values
        close = float(df['Close'].iloc[-1])

        # Collect pivot points (local highs/lows)
        pivots = []
        for i in range(2, len(recent) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                pivots.append(('R', float(highs[i])))
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                pivots.append(('S', float(lows[i])))

        # Cluster nearby pivots into zones
        resistance_zones = []
        support_zones = []

        for ptype, price in pivots:
            tolerance = close * (tolerance_pct / 100)
            if ptype == 'R' and price > close:
                merged = False
                for zone in resistance_zones:
                    if abs(price - zone['price']) < tolerance:
                        zone['touches'] += 1
                        zone['price'] = (zone['price'] + price) / 2
                        merged = True
                        break
                if not merged:
                    resistance_zones.append({'price': price, 'touches': 1})
            elif ptype == 'S' and price < close:
                merged = False
                for zone in support_zones:
                    if abs(price - zone['price']) < tolerance:
                        zone['touches'] += 1
                        zone['price'] = (zone['price'] + price) / 2
                        merged = True
                        break
                if not merged:
                    support_zones.append({'price': price, 'touches': 1})

        # Sort by touches (strongest zones first)
        resistance_zones.sort(key=lambda z: z['touches'], reverse=True)
        support_zones.sort(key=lambda z: z['touches'], reverse=True)

        # Fallback: simple high/low if no pivots found
        if not resistance_zones:
            resistance_zones = [{'price': float(max(highs)), 'touches': 1}]
        if not support_zones:
            support_zones = [{'price': float(min(lows)), 'touches': 1}]

        return {
            "resistance": [{'price': round(z['price'], 2), 'touches': z['touches']} for z in resistance_zones[:3]],
            "support": [{'price': round(z['price'], 2), 'touches': z['touches']} for z in support_zones[:3]],
        }

    # ═══════════════════════════════════════════════════════════════
    #  CONFIRMED BREAKOUT DETECTION
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def detect_breakout(df: pd.DataFrame, sr_zones: Dict) -> Dict[str, Any]:
        """Detect confirmed breakouts with volume + candle strength."""
        if df.empty or len(df) < 3:
            return {"status": "NONE", "type": None, "detail": "Insufficient data"}

        last = df.iloc[-1]
        prev = df.iloc[-2]
        close = float(last['Close'])
        prev_close = float(prev['Close'])
        volume = float(last.get('Volume', 0))
        vol_avg = float(last.get('Vol_Avg_20', volume))
        body = float(last.get('Body_Size', 0))
        avg_body = float(last.get('Avg_Body', body))

        resistances = sr_zones.get('resistance', [])
        supports = sr_zones.get('support', [])

        vol_spike = volume > 1.5 * vol_avg if vol_avg > 0 else False
        strong_candle = body > avg_body * 1.2 if avg_body > 0 else False

        # Check BULLISH breakout
        for r in resistances:
            r_price = r['price']
            if close > r_price and prev_close <= r_price:
                if vol_spike and strong_candle:
                    return {
                        "status": "CONFIRMED",
                        "type": "BULLISH",
                        "level": r_price,
                        "detail": f"Confirmed breakout above ₹{r_price:.2f} with volume spike + strong candle"
                    }
                elif vol_spike:
                    return {
                        "status": "ATTEMPT",
                        "type": "BULLISH",
                        "level": r_price,
                        "detail": f"Breakout attempt above ₹{r_price:.2f} — volume confirms but candle weak"
                    }
                else:
                    return {
                        "status": "WEAK",
                        "type": "BULLISH",
                        "level": r_price,
                        "detail": f"Weak breakout above ₹{r_price:.2f} — low volume, possible fake-out"
                    }

        # Check BEARISH breakdown
        for s in supports:
            s_price = s['price']
            if close < s_price and prev_close >= s_price:
                if vol_spike and strong_candle:
                    return {
                        "status": "CONFIRMED",
                        "type": "BEARISH",
                        "level": s_price,
                        "detail": f"Confirmed breakdown below ₹{s_price:.2f} with heavy selling"
                    }
                elif vol_spike:
                    return {
                        "status": "ATTEMPT",
                        "type": "BEARISH",
                        "level": s_price,
                        "detail": f"Breakdown attempt below ₹{s_price:.2f}"
                    }

        return {"status": "NONE", "type": None, "detail": "No breakout detected at key levels"}

    # ═══════════════════════════════════════════════════════════════
    #  DEEP VOLUME INTELLIGENCE + SMART MONEY DETECTION
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def analyze_volume(df: pd.DataFrame) -> Dict[str, Any]:
        """Deep volume analysis: spikes, trends, divergence, smart money."""
        if df.empty or len(df) < 10:
            return {"spike": False, "trend": "flat", "divergence": None, "smart_money": None, "detail": "Not enough data"}

        last = df.iloc[-1]
        close = float(last['Close'])
        volume = float(last.get('Volume', 0))
        vol_avg = float(last.get('Vol_Avg_20', volume))

        # Volume spike
        vol_ratio = volume / vol_avg if vol_avg > 0 else 1
        spike = vol_ratio > 2.0
        moderate_spike = vol_ratio > 1.5

        # Volume trend (5-day)
        vols = df['Volume'].tail(5).values
        vol_trend = "rising" if len(vols) >= 5 and vols[-1] > vols[0] * 1.2 else \
                    "falling" if len(vols) >= 5 and vols[-1] < vols[0] * 0.8 else "flat"

        # Price direction
        price_up = close > float(df['Close'].iloc[-2])
        price_change_5d = (close - float(df['Close'].iloc[-6])) / float(df['Close'].iloc[-6]) * 100 if len(df) > 6 else 0

        # Price-Volume Divergence
        divergence = None
        if price_change_5d > 2 and vol_trend == "falling":
            divergence = "BEARISH"  # Price up on falling volume = weak rally
        elif price_change_5d < -2 and vol_trend == "falling":
            divergence = "BULLISH"  # Price down on falling volume = weak selling

        # Smart Money Detection
        smart_money = None
        body = float(last.get('Body_Size', 0))
        avg_body = float(last.get('Avg_Body', body))
        strong_candle = body > avg_body * 1.5 if avg_body > 0 else False

        if spike and strong_candle and price_up:
            smart_money = "INSTITUTIONAL BUYING DETECTED"
        elif spike and strong_candle and not price_up:
            smart_money = "INSTITUTIONAL SELLING DETECTED"
        elif spike and price_up:
            smart_money = "Large volume accumulation"
        elif spike and not price_up:
            smart_money = "Large volume distribution"

        # Detail
        parts = []
        if spike:
            parts.append(f"Volume spike ({vol_ratio:.1f}x average)")
        elif moderate_spike:
            parts.append(f"Above-average volume ({vol_ratio:.1f}x)")
        else:
            parts.append("Normal volume")

        parts.append(f"5-day trend: {vol_trend}")

        if divergence == "BEARISH":
            parts.append("⚠ Bearish divergence: price rising on falling volume")
        elif divergence == "BULLISH":
            parts.append("Bullish divergence: selloff on declining volume")

        return {
            "spike": spike or moderate_spike,
            "ratio": round(vol_ratio, 1),
            "trend": vol_trend,
            "divergence": divergence,
            "smart_money": smart_money,
            "detail": ". ".join(parts),
        }

    # ═══════════════════════════════════════════════════════════════
    #  MOMENTUM STRENGTH
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def calculate_momentum(df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate momentum acceleration and strength."""
        if df.empty or len(df) < 12:
            return {"strength": 0, "acceleration": "neutral", "detail": "Insufficient data"}

        last = df.iloc[-1]
        prev = df.iloc[-2]

        roc_5 = float(last.get('ROC_5', 0))
        roc_10 = float(last.get('ROC_10', 0))
        prev_roc_5 = float(prev.get('ROC_5', 0))

        macd_hist = float(last.get('MACD_Diff', 0))
        prev_macd_hist = float(prev.get('MACD_Diff', 0))

        # Acceleration check
        roc_accelerating = roc_5 > prev_roc_5
        macd_accelerating = abs(macd_hist) > abs(prev_macd_hist) and macd_hist * prev_macd_hist > 0

        if roc_accelerating and macd_accelerating:
            if roc_5 > 0:
                acceleration = "ACCELERATING UP"
            else:
                acceleration = "ACCELERATING DOWN"
        elif not roc_accelerating and not macd_accelerating:
            acceleration = "DECELERATING"
        else:
            acceleration = "STEADY"

        # Strength score (0-100)
        strength = 50
        if roc_5 > 5: strength += 15
        elif roc_5 > 2: strength += 8
        elif roc_5 < -5: strength -= 15
        elif roc_5 < -2: strength -= 8

        if macd_hist > 0 and macd_accelerating: strength += 12
        elif macd_hist < 0 and macd_accelerating: strength -= 12

        if roc_10 > 0 and roc_5 > roc_10: strength += 8
        elif roc_10 < 0 and roc_5 < roc_10: strength -= 8

        strength = max(0, min(100, strength))

        detail = f"Momentum {acceleration.lower()}. ROC(5)={roc_5:.1f}%, ROC(10)={roc_10:.1f}%"
        return {"strength": strength, "acceleration": acceleration, "detail": detail}

    # ═══════════════════════════════════════════════════════════════
    #  TRADE STRUCTURE (Entry/Target/Stop Loss)
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def generate_trade_structure(df: pd.DataFrame, sr_zones: Dict, recommendation: str) -> Dict[str, Any]:
        """Generate actionable trade with ATR-based stop loss."""
        if df.empty or len(df) < 5:
            return {}

        last = df.iloc[-1]
        close = float(last['Close'])
        atr = float(last.get('ATR', close * 0.02))

        supports = sr_zones.get('support', [])
        resistances = sr_zones.get('resistance', [])

        if recommendation in ("STRONG BUY", "BUY"):
            entry = close
            stop_loss = max(close - 1.5 * atr, supports[0]['price'] if supports else close * 0.95)
            target_1 = resistances[0]['price'] if resistances else close + 2 * atr
            target_2 = resistances[1]['price'] if len(resistances) > 1 else close + 3 * atr
            risk = entry - stop_loss
            reward = target_1 - entry
            rr = round(reward / risk, 1) if risk > 0 else 0

            return {
                "direction": "LONG",
                "entry": round(entry, 2),
                "stop_loss": round(stop_loss, 2),
                "targets": [round(target_1, 2), round(target_2, 2)],
                "risk_reward": f"1:{rr}",
                "atr": round(atr, 2),
            }
        elif recommendation in ("STRONG SELL", "SELL"):
            entry = close
            stop_loss = min(close + 1.5 * atr, resistances[0]['price'] if resistances else close * 1.05)
            target_1 = supports[0]['price'] if supports else close - 2 * atr
            target_2 = supports[1]['price'] if len(supports) > 1 else close - 3 * atr
            risk = stop_loss - entry
            reward = entry - target_1
            rr = round(reward / risk, 1) if risk > 0 else 0

            return {
                "direction": "SHORT",
                "entry": round(entry, 2),
                "stop_loss": round(stop_loss, 2),
                "targets": [round(target_1, 2), round(target_2, 2)],
                "risk_reward": f"1:{rr}",
                "atr": round(atr, 2),
            }
        else:
            return {
                "direction": "WAIT",
                "entry": None,
                "stop_loss": None,
                "targets": [],
                "risk_reward": "N/A",
                "atr": round(atr, 2),
                "note": "No clear trade setup — wait for confirmation"
            }

    # ═══════════════════════════════════════════════════════════════
    #  INDIVIDUAL INDICATOR SCORERS
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def _score_rsi(rsi, regime):
        if pd.isna(rsi): return 50.0
        # RSI is more important in SIDEWAYS
        if regime == "SIDEWAYS":
            if rsi <= 20: return 95.0
            elif rsi <= 30: return 82.0
            elif rsi <= 40: return 65.0
            elif rsi <= 60: return 50.0
            elif rsi <= 70: return 35.0
            elif rsi <= 80: return 18.0
            else: return 5.0
        else:
            if rsi <= 25: return 80.0
            elif rsi <= 35: return 65.0
            elif rsi <= 65: return 50.0
            elif rsi <= 75: return 35.0
            else: return 20.0

    @staticmethod
    def _score_macd(macd, signal, prev_macd, prev_signal):
        if pd.isna(macd) or pd.isna(signal): return 50.0
        if macd > signal and prev_macd <= prev_signal: return 85.0
        elif macd < signal and prev_macd >= prev_signal: return 15.0
        elif macd > signal:
            diff = abs(macd - signal) / (abs(signal) + 1e-10)
            return min(70 + diff * 100, 80)
        else:
            diff = abs(signal - macd) / (abs(signal) + 1e-10)
            return max(30 - diff * 100, 20)

    @staticmethod
    def _score_sma_cross(sma_20, sma_50, prev_20, prev_50):
        if pd.isna(sma_20) or pd.isna(sma_50): return 50.0
        if sma_20 > sma_50 and prev_20 <= prev_50: return 90.0
        elif sma_20 < sma_50 and prev_20 >= prev_50: return 10.0
        elif sma_20 > sma_50: return 65.0
        else: return 35.0

    @staticmethod
    def _score_ema_cross(ema_12, ema_26, prev_12, prev_26):
        if pd.isna(ema_12) or pd.isna(ema_26): return 50.0
        if ema_12 > ema_26 and prev_12 <= prev_26: return 85.0
        elif ema_12 < ema_26 and prev_12 >= prev_26: return 15.0
        elif ema_12 > ema_26: return 62.0
        else: return 38.0

    @staticmethod
    def _score_bollinger(close, bb_high, bb_low, bb_mid):
        if pd.isna(bb_high) or pd.isna(bb_low) or bb_high == bb_low: return 50.0
        position = (close - bb_low) / (bb_high - bb_low)
        if position <= 0.05: return 90.0
        elif position <= 0.2: return 72.0
        elif position >= 0.95: return 10.0
        elif position >= 0.8: return 28.0
        else: return 50.0

    @staticmethod
    def _score_volume(volume, vol_avg, price_up, vol_analysis):
        if pd.isna(vol_avg) or vol_avg == 0: return 50.0
        ratio = volume / vol_avg

        # Integrate smart money + divergence
        divergence = vol_analysis.get('divergence')
        smart = vol_analysis.get('smart_money')

        if smart and 'BUYING' in smart: return 88.0
        if smart and 'SELLING' in smart: return 12.0

        if divergence == "BEARISH": return 30.0
        if divergence == "BULLISH": return 70.0

        if ratio > 1.5 and price_up: return 80.0
        elif ratio > 1.5 and not price_up: return 20.0
        elif ratio > 1.0 and price_up: return 62.0
        elif ratio > 1.0 and not price_up: return 38.0
        else: return 50.0

    @staticmethod
    def _score_adx(adx, di_plus, di_minus):
        if pd.isna(adx): return 50.0
        if adx < 20: return 50.0
        if di_plus > di_minus:
            if adx > 40: return 85.0
            elif adx > 25: return 70.0
            else: return 58.0
        else:
            if adx > 40: return 15.0
            elif adx > 25: return 30.0
            else: return 42.0

    @staticmethod
    def _score_stochastic(k, d, prev_k, prev_d, regime):
        if pd.isna(k) or pd.isna(d): return 50.0
        # Stochastic more important in SIDEWAYS
        boost = 5 if regime == "SIDEWAYS" else 0
        if k < 20 and k > d and prev_k <= prev_d: return min(90 + boost, 95)
        elif k > 80 and k < d and prev_k >= prev_d: return max(10 - boost, 5)
        elif k < 20: return 75.0
        elif k > 80: return 25.0
        elif k > d: return 58.0
        else: return 42.0

    @staticmethod
    def _score_trend_200(close, sma_200):
        if pd.isna(sma_200) or sma_200 == 0: return 50.0
        pct = ((close - sma_200) / sma_200) * 100
        if pct > 20: return 75.0
        elif pct > 5: return 68.0
        elif pct > 0: return 58.0
        elif pct > -5: return 42.0
        elif pct > -20: return 32.0
        else: return 20.0

    @staticmethod
    def _score_breakout(breakout_data):
        status = breakout_data.get('status', 'NONE')
        btype = breakout_data.get('type')
        if status == "CONFIRMED" and btype == "BULLISH": return 95.0
        elif status == "CONFIRMED" and btype == "BEARISH": return 5.0
        elif status == "ATTEMPT" and btype == "BULLISH": return 75.0
        elif status == "ATTEMPT" and btype == "BEARISH": return 25.0
        elif status == "WEAK" and btype == "BULLISH": return 60.0
        elif status == "WEAK" and btype == "BEARISH": return 40.0
        return 50.0

    # ═══════════════════════════════════════════════════════════════
    #  MULTI-TIMEFRAME CONFIRMATION
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def weekly_confirmation(weekly_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze weekly timeframe for trend confirmation."""
        if weekly_df is None or weekly_df.empty or len(weekly_df) < 20:
            return {"weekly_trend": "unknown", "aligned": False, "boost": 0}

        close = weekly_df['Close']
        sma_20w = close.rolling(20).mean()
        sma_50w = close.rolling(50).mean() if len(close) >= 50 else sma_20w

        last_close = float(close.iloc[-1])
        last_sma20 = float(sma_20w.iloc[-1]) if not pd.isna(sma_20w.iloc[-1]) else last_close
        last_sma50 = float(sma_50w.iloc[-1]) if not pd.isna(sma_50w.iloc[-1]) else last_close

        if last_close > last_sma20 and last_sma20 > last_sma50:
            return {"weekly_trend": "BULLISH", "aligned": True, "boost": 10}
        elif last_close < last_sma20 and last_sma20 < last_sma50:
            return {"weekly_trend": "BEARISH", "aligned": True, "boost": -10}
        else:
            return {"weekly_trend": "MIXED", "aligned": False, "boost": 0}

    # ═══════════════════════════════════════════════════════════════
    #  SIGNAL QUALITY TIER
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def get_signal_quality(score, breakout, volume_data, regime, mtf):
        """Rate the setup quality: A+, A, B, C."""
        confirmed_breakout = breakout.get('status') == "CONFIRMED"
        smart_money = volume_data.get('smart_money') is not None
        aligned = mtf.get('aligned', False)
        strong_regime = regime.get('strength') in ('strong', 'extreme')

        quality_points = 0
        if score >= 75: quality_points += 3
        elif score >= 65: quality_points += 2
        elif score >= 55: quality_points += 1

        if confirmed_breakout: quality_points += 3
        if smart_money: quality_points += 2
        if aligned: quality_points += 2
        if strong_regime: quality_points += 1

        if quality_points >= 8:
            return {"tier": "A+", "label": "ELITE SETUP", "color": "#FFD700"}
        elif quality_points >= 6:
            return {"tier": "A", "label": "STRONG SETUP", "color": "#3DDC84"}
        elif quality_points >= 4:
            return {"tier": "B", "label": "GOOD SETUP", "color": "#4F8EF7"}
        elif quality_points >= 2:
            return {"tier": "C", "label": "WEAK SETUP", "color": "#F0A500"}
        else:
            return {"tier": "D", "label": "NO SETUP", "color": "#FF6B6B"}

    # ═══════════════════════════════════════════════════════════════
    #  MAIN SIGNAL GENERATOR
    # ═══════════════════════════════════════════════════════════════
    @classmethod
    def generate_signals(cls, df: pd.DataFrame, weekly_df: pd.DataFrame = None) -> Dict[str, Any]:
        """Generate the full pro trading analysis."""
        empty_result = {
            "recommendation": "HOLD", "signals": [], "rsi": 0, "last_price": 0,
            "composite_score": 50, "breakdown": {}, "price_change_pct": 0,
            "regime": {"regime": "SIDEWAYS", "strength": "weak", "detail": ""},
            "breakout": {"status": "NONE"}, "volume_intel": {}, "momentum": {},
            "sr_zones": {}, "trade": {}, "mtf": {}, "signal_quality": {"tier": "C"},
        }
        if df.empty or 'RSI' not in df.columns or len(df) < 5:
            return empty_result

        last = df.iloc[-1]
        prev = df.iloc[-2]

        price_change_pct = ((last['Close'] - prev['Close']) / prev['Close']) * 100 if prev['Close'] != 0 else 0
        price_up = last['Close'] > prev['Close']

        # 1. Detect regime
        regime = cls.detect_regime(df)

        # 2. Find S/R zones
        sr_zones = cls.find_sr_zones(df)

        # 3. Detect breakout
        breakout = cls.detect_breakout(df, sr_zones)

        # 4. Volume intelligence
        vol_intel = cls.analyze_volume(df)

        # 5. Momentum
        momentum = cls.calculate_momentum(df)

        # 6. Multi-timeframe
        mtf = cls.weekly_confirmation(weekly_df) if weekly_df is not None else {"weekly_trend": "unknown", "aligned": False, "boost": 0}

        # 7. Score each indicator with regime awareness
        regime_name = regime['regime']
        weights = cls.REGIME_WEIGHTS.get(regime_name, cls.REGIME_WEIGHTS['SIDEWAYS'])

        scores = {}
        scores['rsi'] = cls._score_rsi(last.get('RSI', 50), regime_name)
        scores['macd'] = cls._score_macd(last.get('MACD', 0), last.get('MACD_Signal', 0), prev.get('MACD', 0), prev.get('MACD_Signal', 0))
        scores['sma_cross'] = cls._score_sma_cross(last.get('SMA_20', 0), last.get('SMA_50', 0), prev.get('SMA_20', 0), prev.get('SMA_50', 0))
        scores['ema_cross'] = cls._score_ema_cross(last.get('EMA_12', 0), last.get('EMA_26', 0), prev.get('EMA_12', 0), prev.get('EMA_26', 0))
        scores['bollinger'] = cls._score_bollinger(last['Close'], last.get('BB_High', 0), last.get('BB_Low', 0), last.get('BB_Mid', 0))
        scores['volume'] = cls._score_volume(last.get('Volume', 0), last.get('Vol_Avg_20', 0), price_up, vol_intel)
        scores['stochastic'] = cls._score_stochastic(last.get('Stoch_K', 50), last.get('Stoch_D', 50), prev.get('Stoch_K', 50), prev.get('Stoch_D', 50), regime_name)
        scores['breakout'] = cls._score_breakout(breakout)
        scores['trend_200'] = cls._score_trend_200(last['Close'], last.get('SMA_200', 0))

        # 8. Compute weighted composite
        composite = sum(scores[k] * weights.get(k, 0.1) for k in scores)

        # Apply MTF boost/penalty
        composite += mtf.get('boost', 0)
        composite = max(0, min(100, round(composite, 1)))

        # 9. Human-readable signals
        signals = []
        rsi_val = round(float(last.get('RSI', 0)), 2)

        if scores['rsi'] >= 75: signals.append(f"RSI Oversold ({rsi_val})")
        elif scores['rsi'] <= 25: signals.append(f"RSI Overbought ({rsi_val})")
        if scores['macd'] >= 80: signals.append("Bullish MACD Crossover")
        elif scores['macd'] <= 20: signals.append("Bearish MACD Crossover")
        if scores['sma_cross'] >= 85: signals.append("Golden Cross (SMA 20/50)")
        elif scores['sma_cross'] <= 15: signals.append("Death Cross (SMA 20/50)")
        if breakout['status'] in ('CONFIRMED', 'ATTEMPT'): signals.append(f"Breakout {breakout['status']}: {breakout.get('type', '')}")
        if vol_intel.get('smart_money'): signals.append(vol_intel['smart_money'])
        if momentum.get('acceleration', '').startswith('ACCEL'): signals.append(f"Momentum {momentum['acceleration']}")
        if not signals: signals.append("No strong directional signals")

        # 10. Recommendation
        if composite >= 80: recommendation = "STRONG BUY"
        elif composite >= 65: recommendation = "BUY"
        elif composite >= 45: recommendation = "HOLD"
        elif composite >= 30: recommendation = "SELL"
        else: recommendation = "STRONG SELL"

        # 11. Trade structure
        trade = cls.generate_trade_structure(df, sr_zones, recommendation)

        # 12. Signal quality
        signal_quality = cls.get_signal_quality(composite, breakout, vol_intel, regime, mtf)

        return {
            "recommendation": recommendation,
            "composite_score": composite,
            "signals": signals,
            "rsi": rsi_val,
            "last_price": round(float(last['Close']), 2),
            "breakdown": {k: round(v, 1) for k, v in scores.items()},
            "price_change_pct": round(float(price_change_pct), 2),
            "regime": regime,
            "breakout": breakout,
            "volume_intel": vol_intel,
            "momentum": momentum,
            "sr_zones": sr_zones,
            "trade": trade,
            "mtf": mtf,
            "signal_quality": signal_quality,
        }
