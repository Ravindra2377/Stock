import pandas as pd
import numpy as np
import ta
from typing import Dict, Any, List, Tuple
import datetime

class IndicatorService:

    """
    Pro Trading Engine v3.0 — ELITE (PANVI_1.2)
    ──────────────────────────────────────────
    - Market Regime Detection + Dynamic Weights
    - Confirmed Breakout + Trap Detection
    - Smart Money (Compression→Expansion)
    - RSI Slope + Momentum Acceleration
    - ATR-based Trade Structure with R:R Filter (≥1.5)
    - Pullback Entry Suggestions
    - Always-On Risk Assessment
    - Signal Quality Tiers tied to R:R
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

    # CONVICTION_TIERS (Single Source of Truth)
    CONVICTION_TIERS = [
        {"min": 80.0, "max": 100.0, "grade": "a", "label": "EXTREME",  "size_pct": 100},
        {"min": 70.0, "max": 79.0,  "grade": "b", "label": "HIGH",     "size_pct": 75},
        {"min": 65.0, "max": 69.0,  "grade": "c", "label": "MODERATE", "size_pct": 50},
        {"min": 35.0, "max": 64.0,  "grade": "d", "label": "LOW",      "size_pct": 0},
        {"min": 0.0,  "max": 34.0,  "grade": "e", "label": "VERY LOW", "size_pct": 0},
    ]

    ALGORITHM_VERSION = "PANVI_1.2"

    @classmethod
    def _check_earnings_proximity(cls, ticker: str) -> bool:
        """Check if earnings are within 5 days (Robust with Normalized Dates)."""
        try:
            display_ticker = ticker.split('.')[0].upper()
            df_earnings = pd.read_csv('/home/kpanviravindra/Desktop/jiva_t/Stock/backend/earnings_calendar.csv')
            # Standardize tickers in CSV for exact match
            df_earnings['ticker_clean'] = df_earnings['ticker'].apply(lambda x: str(x).split('.')[0].upper())
            row = df_earnings[df_earnings['ticker_clean'] == display_ticker]
            
            if not row.empty:
                earning_date = pd.to_datetime(row['earnings_date'].iloc[0]).normalize()
                today = pd.Timestamp.now().normalize()
                days_to_earnings = (earning_date - today).days
                # Trigger if today is earnings or within 0-5 days
                return 0 <= days_to_earnings <= 5
        except:
            pass
        return False
    @classmethod
    def _get_currency_symbol(cls, ticker: str) -> str:
        """Detect currency by exchange suffix."""
        t = ticker.upper()
        if ".NS" in t or ".BO" in t:
            return "₹"
        elif ".HK" in t:
            return "HK$"
        elif ".L" in t:
            return "£"
        else:
            return "$"

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

        # RSI slope (direction matters more than value)
        df['RSI_Prev'] = df['RSI'].shift(1) if 'RSI' in df.columns else 50
        df['RSI_Slope'] = df['RSI'] - df['RSI_Prev'] if 'RSI' in df.columns else 0

        # ATR compression detection (for smart money)
        df['ATR_5'] = df['ATR'].rolling(5).mean() if 'ATR' in df.columns else 0
        df['ATR_Compress'] = (df['ATR_5'] < df['ATR_Avg'] * 0.7) if 'ATR' in df.columns else False

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
            "resistance": [{'price': float(f"{z['price']:.2f}"), 'touches': int(z['touches'])} for z in list(resistance_zones)[:3]],
            "support": [{'price': float(f"{z['price']:.2f}"), 'touches': int(z['touches'])} for z in list(support_zones)[:3]],
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
    #  TRAP DETECTION (Fake Breakout)
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def detect_trap(df: pd.DataFrame, sr_zones: Dict) -> Dict[str, Any]:
        """Detect fake breakouts: price breaks level then returns."""
        if df.empty or len(df) < 5:
            return {"trap": False, "detail": ""}

        resistances = sr_zones.get('resistance', [])
        supports = sr_zones.get('support', [])

        # Check last 3 bars for trap pattern
        for i in range(-3, -1):
            try:
                bar = df.iloc[i]
                bar_close = float(bar['Close'])
                bar_high = float(bar.get('High', bar_close))
                bar_low = float(bar.get('Low', bar_close))
            except:
                continue

            current_close = float(df.iloc[-1]['Close'])

            # Bull trap: wick above resistance then close back below
            for r in resistances:
                if bar_high > r['price'] and current_close < r['price']:
                    return {
                        "trap": True,
                        "type": "BULL TRAP",
                        "level": r['price'],
                        "detail": f"⚠ Bull trap detected: price pierced {r['price']:.2f} but closed back below — likely stop hunt"
                    }

            # Bear trap: wick below support then close back above
            for s in supports:
                if bar_low < s['price'] and current_close > s['price']:
                    return {
                        "trap": True,
                        "type": "BEAR TRAP",
                        "level": s['price'],
                        "detail": f"Bear trap detected: price dipped below {s['price']:.2f} but recovered — possible accumulation"
                    }

        return {"trap": False, "detail": ""}

    # ═══════════════════════════════════════════════════════════════
    #  DEEP VOLUME INTELLIGENCE + SMART MONEY DETECTION
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def analyze_volume(df: pd.DataFrame) -> Dict[str, Any]:
        """Deep volume analysis: spikes, trends, divergence, smart money with compression→expansion."""
        if df.empty or len(df) < 10:
            return {"spike": False, "ratio": 1.0, "trend": "flat", "divergence": None, "smart_money": None, "detail": "Not enough data"}

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
            divergence = "BEARISH"
        elif price_change_5d < -2 and vol_trend == "falling":
            divergence = "BULLISH"

        # Smart Money Detection — requires compression→expansion
        smart_money = None
        body = float(last.get('Body_Size', 0))
        avg_body = float(last.get('Avg_Body', body))
        strong_candle = body > avg_body * 1.5 if avg_body > 0 else False
        prev_high = float(df['High'].iloc[-2]) if 'High' in df.columns else 0
        prev_low = float(df['Low'].iloc[-2]) if 'Low' in df.columns else close
        was_compressed = bool(last.get('ATR_Compress', False))

        # REAL institutional: compression→expansion + volume spike + strong candle + new high/low
        if spike and strong_candle and price_up and (close > prev_high or was_compressed):
            smart_money = "INSTITUTIONAL BUYING DETECTED"
        elif spike and strong_candle and not price_up and (close < prev_low or was_compressed):
            smart_money = "INSTITUTIONAL SELLING DETECTED"
        elif spike and strong_candle and price_up:
            smart_money = "Large volume accumulation"
        elif spike and strong_candle and not price_up:
            smart_money = "Large volume distribution"
        # Don't label non-strong candles as institutional — that's noise

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
            "spike": bool(spike or moderate_spike),
            "ratio": float(round(float(vol_ratio), 1)),
            "trend": str(vol_trend),
            "divergence": divergence,
            "smart_money": smart_money,
            "detail": ". ".join(parts),
        }


    # ═══════════════════════════════════════════════════════════════
    #  MOMENTUM STRENGTH + RSI SLOPE
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def calculate_momentum(df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate momentum acceleration, RSI slope, and strength."""
        if df.empty or len(df) < 12:
            return {"strength": 0, "acceleration": "neutral", "rsi_slope": 0, "detail": "Insufficient data"}

        last = df.iloc[-1]
        prev = df.iloc[-2]

        roc_5 = float(last.get('ROC_5', 0))
        roc_10 = float(last.get('ROC_10', 0))
        prev_roc_5 = float(prev.get('ROC_5', 0))

        macd_hist = float(last.get('MACD_Diff', 0))
        prev_macd_hist = float(prev.get('MACD_Diff', 0))

        # RSI slope — direction matters more than value
        rsi_slope = float(last.get('RSI_Slope', 0))

        # Acceleration check
        roc_accelerating = roc_5 > prev_roc_5
        macd_accelerating = abs(macd_hist) > abs(prev_macd_hist) and macd_hist * prev_macd_hist > 0
        rsi_accelerating = rsi_slope > 2  # RSI rising fast

        if roc_accelerating and macd_accelerating:
            if roc_5 > 0:
                acceleration = "ACCELERATING UP"
            else:
                acceleration = "ACCELERATING DOWN"
        elif not roc_accelerating and not macd_accelerating:
            acceleration = "DECELERATING"
        else:
            acceleration = "STEADY"

        # Strength score (0-100) — now includes RSI slope
        strength = 50
        if roc_5 > 5: strength += 15
        elif roc_5 > 2: strength += 8
        elif roc_5 < -5: strength -= 15
        elif roc_5 < -2: strength -= 8

        if macd_hist > 0 and macd_accelerating: strength += 12
        elif macd_hist < 0 and macd_accelerating: strength -= 12

        if roc_10 > 0 and roc_5 > roc_10: strength += 8
        elif roc_10 < 0 and roc_5 < roc_10: strength -= 8

        # RSI slope contribution
        if rsi_slope > 5: strength += 8
        elif rsi_slope > 2: strength += 4
        elif rsi_slope < -5: strength -= 8
        elif rsi_slope < -2: strength -= 4

        strength = max(0, min(100, strength))

        rsi_dir = "rising" if rsi_slope > 1 else "falling" if rsi_slope < -1 else "flat"
        detail = f"Momentum {acceleration.lower()}. ROC(5)={roc_5:.1f}%, RSI {rsi_dir} (slope={rsi_slope:.1f})"
        return {"strength": float(strength), "acceleration": str(acceleration), "rsi_slope": float(round(float(rsi_slope), 1)), "detail": str(detail)}


    # ═══════════════════════════════════════════════════════════════
    #  TRADE STRUCTURE (Entry/Target/Stop Loss) + R:R FILTER
    # ═══════════════════════════════════════════════════════════════
    @classmethod
    def generate_trade_structure(cls, df: pd.DataFrame, sr_zones: Dict, recommendation: str, breakout: Dict[str, Any] = {}, overextended: Dict[str, Any] = {}, p_bull: float = 0.5) -> Dict[str, Any]:



        """Generate actionable trade with Panvi Core Brain formulas: Weighted Entry, Prob-Adjusted Targets, Structure Stop."""
        if not overextended: overextended = {}
        if not breakout: breakout = {}
        if df.empty or len(df) < 5:

            return {"direction": "WAIT", "rr_value": 0}

        last = df.iloc[-1]
        close = float(last['Close'])
        atr = float(last.get('ATR', close * 0.02))

        supports = sr_zones.get('support', [])
        resistances = sr_zones.get('resistance', [])

        if recommendation in ("STRONG BUY", "BUY"):
            # Panvi Phase 27: Optimized Weighted Entry Zone
            supports = sr_zones.get('support', [])
            resistances = sr_zones.get('resistance', [])
            
            # Correct Buy Price (50/30/20 Rule)
            support_val = supports[0]['price'] if supports else close * 0.98
            ema_20 = float(last.get('EMA_20', close))
            correct_buy = cls.calculate_correct_buy_price(df, support_val, ema_20)
            
            is_ox = overextended.get('overextended', False) and overextended.get('type') == 'BULLISH'
            entry = correct_buy if is_ox else close
            trade_note = "Value Zone Entry: 50/30/20 weighted optimization enabled."
            
            # Expected Low (Stop): MIN(SwingLow, Support - 0.5 * ATR)
            recent_lows = df.tail(10)['Low']
            swing_low = float(recent_lows.min())
            stop_loss = min(swing_low, support_val - 0.5 * atr)
            
            # Targets: T1 = nearest resistance, T2 = farther
            raw_targets = []
            for r in resistances:
                if r['price'] > close:
                    raw_targets.append(r['price'])
            if not raw_targets:
                raw_targets = [close + 2 * atr, close + 3 * atr]
            elif len(raw_targets) < 2:
                raw_targets.append(raw_targets[-1] + atr)
            raw_targets.sort()
            target_1, target_2 = raw_targets[0], raw_targets[1]
            
            # Expected High (Probability-Adjusted Target)
            # Default to 0.5 if probabilities not yet passed
            p_bull = 0.5
            expected_high = cls.calculate_prob_adjusted_high(p_bull, target_1, target_2)

            risk = abs(float(entry) - float(stop_loss))
            reward = abs(float(target_1) - float(entry))
            rr = float(round(float(reward / risk), 1)) if risk > 0 else 0.0

            pullback_entry = round(correct_buy, 2)

            return {
                "direction": "LONG",
                "entry": round(entry, 2),
                "stop_loss": round(stop_loss, 2),
                "targets": [round(target_1, 2), round(target_2, 2)],
                "risk_reward": f"1:{rr}",
                "rr_value": rr,
                "atr": round(atr, 2),
                "pullback_entry": pullback_entry,
                "expected_high": round(expected_high, 2),
                "expected_low": round(stop_loss, 2),
                "correct_buy_price": round(correct_buy, 2),
                "rr_acceptable": rr >= 1.5,
                "note": trade_note
            }
        elif recommendation in ("STRONG SELL", "SELL"):
            # Sell side follows similar logic for Expected High/Low
            resistances = sr_zones.get('resistance', [])
            supports = sr_zones.get('support', [])
            
            resistance_val = resistances[0]['price'] if resistances else close * 1.02
            ema_20 = float(last.get('EMA_20', close))
            
            # For SHORT, entry is optimized near resistance
            entry = close
            
            # Expected High (Stop for Short)
            recent_highs = df.tail(10)['High']
            swing_high = float(recent_highs.max())
            stop_loss = max(swing_high, resistance_val + 0.5 * atr)

            # Targets
            raw_targets = []
            for s in supports:
                if s['price'] < close:
                    raw_targets.append(s['price'])
            if not raw_targets:
                raw_targets = [close - 2 * atr, close - 3 * atr]
            elif len(raw_targets) < 2:
                raw_targets.append(raw_targets[-1] - atr)
            raw_targets.sort(reverse=True)
            target_1, target_2 = raw_targets[0], raw_targets[1]

            risk = abs(float(stop_loss) - float(entry))
            reward = abs(float(entry) - float(target_1))
            rr = float(round(float(reward / risk), 1)) if risk > 0 else 0.0

            return {
                "direction": "SHORT",
                "entry": round(entry, 2),
                "stop_loss": round(stop_loss, 2),
                "targets": [round(target_1, 2), round(target_2, 2)],
                "risk_reward": f"1:{rr}",
                "rr_value": rr,
                "atr": round(atr, 2),
                "expected_high": round(stop_loss, 2),
                "expected_low": round(target_2, 2),
                "correct_buy_price": round(entry, 2),
                "rr_acceptable": rr >= 1.5,
            }

        else:
            # For HOLD/CHOP, we still want to show the 'Value Zone' and projections
            supports = sr_zones.get('support', [])
            resistances = sr_zones.get('resistance', [])
            ema_20 = float(last.get('EMA_20', close))
            
            support_val = supports[0]['price'] if supports else close * 0.98
            res_val = resistances[0]['price'] if resistances else close * 1.02
            
            # Theoretical Entry (Value Zone)
            correct_buy = cls.calculate_correct_buy_price(df, support_val, ema_20)
            
            # Theoretical Projections
            # Using 50/50 probability proxy for targets if conviction is low
            t1 = res_val
            t2 = res_val + (res_val - support_val) if res_val > support_val else res_val * 1.05
            
                                
            # Use probability proxy for high even in HOLD
            # probability from main context if available, else 0.5
            p_bull_proxy = 0.5
            exp_high = cls.calculate_prob_adjusted_high(p_bull_proxy, t1, t2)
            
            # Stop proxy
            recent_lows = df.tail(10)['Low']
            swing_low = float(recent_lows.min())
            exp_low = min(swing_low, support_val - 0.5 * atr)

            return {
                "direction": "WAIT",
                "entry": None,
                "stop_loss": None,
                "targets": [round(t1, 2), round(t2, 2)],
                "expected_high": round(exp_high, 2),
                "expected_low": round(exp_low, 2),
                "correct_buy_price": round(correct_buy, 2),
                "risk_reward": "N/A",
                "rr_value": 0,
                "atr": round(atr, 2),
                "rr_acceptable": False,
                "note": "Conviction threshold (65) not met. Viewing theoretical projections."
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
    #  PANVI CORE BRAIN: 3-LAYER INPUT SYSTEM
    # ═══════════════════════════════════════════════════════════════

    @classmethod
    def calculate_structure_score(cls, df: pd.DataFrame, sr_zones: Dict, regime: str) -> float:
        """Layer 1: Market Structure (Ground Truth) Score."""
        if df.empty: return 50.0
        last = df.iloc[-1]
        close = float(last['Close'])
        adx = float(last.get('ADX', 20))
        
        # 1. Trend Alignment (ADX + DI)
        trend_score = 50.0
        if adx > 25:
            di_plus = float(last.get('DI_Plus', 0))
            di_minus = float(last.get('DI_Minus', 0))
            if di_plus > di_minus: trend_score = min(100, 50 + (adx - 20) * 2)
            else: trend_score = max(0, 50 - (adx - 20) * 2)
        
        # 2. Level Proximity (Distance to Support vs Resistance)
        level_score = 50.0
        supports = sr_zones.get('support', [])
        resistances = sr_zones.get('resistance', [])
        
        if supports and resistances:
            s_dist = abs(close - supports[0]['price'])
            r_dist = abs(resistances[0]['price'] - close)
            total = s_dist + r_dist
            if total > 0:
                level_score = (r_dist / total) * 100
        
        # 3. Regime Integration
        if regime == "TRENDING": structure_score = (0.6 * trend_score) + (0.4 * level_score)
        elif regime == "SIDEWAYS": structure_score = (0.2 * trend_score) + (0.8 * level_score)
        else: structure_score = (0.4 * trend_score) + (0.6 * level_score)
            
        return float(round(structure_score, 1))


    @staticmethod
    def calculate_indicator_score(scores: Dict[str, float], weights: Dict[str, float]) -> float:
        """Layer 2: Indicators (Confirmation Layer). Normalizes all technicals."""
        if not scores: return 50.0
        total_weight = sum(weights.get(k, 0) for k in scores)
        if total_weight == 0: return 50.0
        
        weighted_sum = sum(scores[k] * weights.get(k, 0) for k in scores)
        return float(round(weighted_sum / total_weight, 1))

    @staticmethod
    def calculate_panvi_fusion(ai_prob: float, ind_score: float, struct_score: float) -> float:
        """Unified Signal Engine: 0.4 AI + 0.3 Indicator + 0.3 Structure."""
        # ai_prob is 0.0-1.0, convert to 0-100
        ai_normalized = ai_prob * 100
        final_score = (0.4 * ai_normalized) + (0.3 * ind_score) + (0.3 * struct_score)
        return float(round(final_score, 1))

    @staticmethod
    def calculate_correct_buy_price(df: pd.DataFrame, support: float, ema: float) -> float:
        """🎯 50/30/20 Value Zone Entry: Support (50%) + EMA (30%) + Mean (20%)."""
        if df.empty: return support
        last = df.iloc[-1]
        close = float(last['Close'])
        high = float(last['High']) if 'High' in df.columns else close
        low = float(last['Low']) if 'Low' in df.columns else close
        mean_price = (high + low + close) / 3
        
        # Weighted Average
        entry = (0.5 * support) + (0.3 * ema) + (0.2 * mean_price)
        return float(round(entry, 2))

    @staticmethod
    def calculate_prob_adjusted_high(p_bull: float, t1: float, t2: float) -> float:
        """📈 Probability-Adjusted Target: Aggressive vs Conservative scaling."""
        # expected_high = (P_bull * target_2) + ((1 - P_bull) * target_1)
        target = (p_bull * t2) + ((1 - p_bull) * t1)
        return float(round(target, 2))

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
    #  SIGNAL QUALITY TIER (tied to R:R)
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def get_signal_quality(score, breakout, volume_data, regime, mtf, trade):
        """Rate setup quality: A+/A/B/C/D — incorporates R:R."""
        confirmed_breakout = breakout.get('status') == "CONFIRMED"
        smart_money = volume_data.get('smart_money') is not None and 'INSTITUTIONAL' in (volume_data.get('smart_money') or '')
        aligned = mtf.get('aligned', False)
        strong_regime = regime.get('strength') in ('strong', 'extreme')
        rr_good = trade.get('rr_value', 0) >= 1.5
        rr_great = trade.get('rr_value', 0) >= 2.5

        quality_points = 0
        if score >= 75: quality_points += 3
        elif score >= 65: quality_points += 2
        elif score >= 55: quality_points += 1

        if confirmed_breakout: quality_points += 3
        if smart_money: quality_points += 2
        if aligned: quality_points += 2
        if strong_regime: quality_points += 1
        if rr_great: quality_points += 2
        elif rr_good: quality_points += 1

        # Cap: never A+ or A if R:R is bad
        if not rr_good and quality_points >= 6:
            quality_points = 5  # downgrade

        if quality_points >= 9:
            return {"tier": "A+", "label": "ELITE SETUP", "color": "#FFD700"}
        elif quality_points >= 7:
            return {"tier": "A", "label": "STRONG SETUP", "color": "#3DDC84"}
        elif quality_points >= 4:
            return {"tier": "B", "label": "GOOD SETUP", "color": "#4F8EF7"}
        elif quality_points >= 2:
            return {"tier": "C", "label": "WEAK SETUP", "color": "#F0A500"}
        else:
            return {"tier": "D", "label": "NO SETUP", "color": "#FF6B6B"}

    # ═══════════════════════════════════════════════════════════════
    #  HEDGE-FUND LOGIC (v4.0) — DEEP ENGINES
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def detect_overextension(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect if price is stretched too far from the 20 EMA using ATR."""
        if df.empty or len(df) < 20: return {"overextended": False, "detail": ""}
        close = float(df['Close'].iloc[-1])
        ema_20 = float(df['EMA_20'].iloc[-1]) if 'EMA_20' in df.columns else close
        atr = float(df['ATR'].iloc[-1]) if 'ATR' in df.columns else (close * 0.02)
        
        if ema_20 == 0 or atr == 0: return {"overextended": False, "detail": ""}
        
        dist = close - ema_20
        atr_dist = dist / atr
        
        if atr_dist > 2.5:
            return {"overextended": True, "type": "BULLISH", "detail": f"Price stretched {atr_dist:.1f} ATRs above trend"}
        elif atr_dist < -2.5:
            return {"overextended": True, "type": "BEARISH", "detail": f"Price stretched {abs(atr_dist):.1f} ATRs below trend"}
        
        return {"overextended": False, "detail": ""}

    @staticmethod
    def map_liquidity(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect equal highs/lows acting as liquidity magnets."""
        if df.empty or len(df) < 15: return {"detected": False, "pools": []}
        
        recent = df.tail(15)
        highs = recent['High'].values if 'High' in recent.columns else recent['Close'].values
        lows = recent['Low'].values if 'Low' in recent.columns else recent['Close'].values
        close = float(df['Close'].iloc[-1])
        
        pools = []
        max_h = max(highs[:-1])
        min_l = min(lows[:-1])
        
        if close < max_h and (max_h - close)/close < 0.03:
            pools.append(f"Buy-side liquidity above at {max_h:.2f}")
        if close > min_l and (close - min_l)/close < 0.03:
            pools.append(f"Sell-side liquidity below at {min_l:.2f}")
            
        return {"detected": len(pools) > 0, "pools": pools}

    @staticmethod
    def detect_trend_phase(regime: Dict, breakout: Dict, momentum: Dict, vol_intel: Dict) -> str:
        """Classify into Accumulation, Breakout, Expansion, Exhaustion."""
        reg = regime.get('regime')
        bo = breakout.get('status')
        accel = momentum.get('acceleration', '')
        smart = vol_intel.get('smart_money') or ''
        
        if reg == "SIDEWAYS":
            if "BUYING" in smart: return "ACCUMULATION"
            elif "SELLING" in smart: return "DISTRIBUTION"
            return "CHOPPY"
        if bo in ["CONFIRMED", "ATTEMPT"]:
            return "BREAKOUT"
        if reg == "TRENDING":
            if "ACCELERATING" in accel: return "EXPANSION (Strong Trend)"
            if accel == "DECELERATING": return "EXHAUSTION (Weakening)"
            return "TRENDING"
        return "UNKNOWN"

    @staticmethod
    def calculate_probabilities(score: float, regime: Dict[str, Any], mtf: Dict[str, Any], market_context: Dict[str, Any] = {}) -> Dict[str, float]:
        bull = float(score)
        bear = float(100.0 - score)
        side = 0.0

        
        if regime['regime'] == 'SIDEWAYS':
            side = 50
            bull *= 0.5
            bear *= 0.5
        elif regime['regime'] == 'VOLATILE':
            side = 20
            bull *= 0.8
            bear *= 0.8
            
        if mtf.get('aligned'):
            if mtf.get('weekly_trend') == 'BULLISH':
                bull += 15.0; bear -= 15.0
            elif mtf.get('weekly_trend') == 'BEARISH':
                bear += 15.0; bull -= 15.0

                
        # V4: Market Context adjustments
        if market_context.get('trend') == 'BULLISH':
            bull += 10; bear -= 10
        elif market_context.get('trend') == 'BEARISH':
            bear += 15; bull -= 10
                
        bull = float(max(5.0, min(95.0, bull)))
        bear = float(max(5.0, min(95.0, bear)))
        side = float(max(5.0, min(95.0, side)))
        total = float(bull + bear + side)

        
        return {
            "bullish": float(round(float(bull / total) * 100.0, 1)),
            "sideways": float(round(float(side / total) * 100.0, 1)),
            "bearish": float(round(float(bear / total) * 100.0, 1))
        }


    @staticmethod
    def generate_playbook(trade: Dict, trend_phase: str, overextended: Dict) -> Dict[str, Any]:
        if trade.get('direction') == 'WAIT':
            return {"plan": ["Wait for market structure to form."], "invalidation": "N/A"}
        
        direction = trade.get('direction')
        entry = trade.get('entry', 0)
        targets = trade.get('targets', [0, 0])
        sl = trade.get('stop_loss', 0)
        pullback = trade.get('pullback_entry')
        
        steps = []
        is_ox = overextended.get('overextended', False)
        
        if is_ox:
            steps.append(f"⏳ Overextended {overextended.get('detail')} — DO NOT CHASE.")
            opt = pullback or (entry * 0.98 if direction == 'LONG' else entry * 1.02)
            steps.append(f"🟢 Best Entry: Pullback to ~{opt:.2f}")
        else:
            if pullback and 'BREAKOUT' in trend_phase:
                steps.append(f"💥 Breakout active. Aggressive entry: {entry:.2f}.")
                steps.append(f"🟢 Best Entry: Retest of {pullback:.2f}")
            elif 'EXPANSION' in trend_phase:
                steps.append(f"🚀 Momentum expansion. Market entry {entry:.2f} acceptable.")
            else:
                steps.append(f"🟢 Accumulate near {entry:.2f}.")
                
        t1 = targets[0] if len(targets) > 0 else 0
        t2 = targets[1] if len(targets) > 1 else t1
        if t1 > 0:
            steps.append(f"🎯 Targets: {t1:.2f} → {t2:.2f}")
        
        inv = f"Close below {sl:.2f} with volume" if direction == 'LONG' else f"Close above {sl:.2f} with volume"
        steps.append(f"🛑 Invalidation: {inv}")
        
        return {"plan": steps, "invalidation": inv}

    @classmethod
    def calculate_ev(cls, probs: Dict[str, float], trade: Dict[str, Any]) -> Dict[str, Any]:
        """EV Engine: (WinRate * AvgWin) - (LossRate * AvgLoss)"""
        if trade.get('direction') == 'WAIT' or not trade.get('targets') or not trade.get('stop_loss'):
            return {"ev": 0.0, "is_positive": False}
            
        entry = float(trade.get('entry', 0))
        target = float(trade.get('targets')[0])
        stop = float(trade.get('stop_loss', 0))
        
        if entry == 0: return {"ev": 0.0, "is_positive": False}
        
        win_amt = abs(target - entry)
        loss_amt = abs(entry - stop)
        
        bull_prob = float(probs.get('bullish', 50)) / 100.0
        bear_prob = float(probs.get('bearish', 50)) / 100.0
        
        if trade.get('direction') == 'LONG':
            win_rate = bull_prob
            loss_rate = bear_prob
        else:
            win_rate = bear_prob
            loss_rate = bull_prob
            
        # Strict formula implementation
        ev_dollar = (win_rate * win_amt) - (loss_rate * loss_amt)
        ev_r = float(round(float(ev_dollar / loss_amt), 2)) if loss_amt > 0 else 0.0
        
        return {"ev": ev_r, "is_positive": bool(ev_dollar > 0)}



    @staticmethod
    def calculate_position_size(trade: Dict[str, Any], capital: float = 100000.0, risk_pct: float = 0.01) -> Dict[str, Any]:

        """Calculates exact shares based on fixed fractional risk."""
        if trade.get('direction') == 'WAIT' or not trade.get('stop_loss'):
            return {"shares": 0, "value": 0, "risk_amount": 0}
            
        entry = float(trade.get('entry', 0))
        stop = float(trade.get('stop_loss', 0))
        
        risk_per_share = abs(entry - stop)
        if risk_per_share == 0: return {"shares": 0, "value": 0, "risk_amount": 0}
        
        max_risk_amount = capital * risk_pct
        shares = int(max_risk_amount // risk_per_share)
        
        return {
            "shares": int(shares),
            "capital_required": float(round(float(shares * entry), 2)),
            "risk_amount": float(round(float(shares * risk_per_share), 2)),
            "capital_pct": float(round(float(((shares * entry) / capital) * 100.0), 1))
        }


    @classmethod
    def _get_tier_info(cls, score: float) -> Dict[str, Any]:
        """Map score to conviction tier details."""
        for tier in cls.CONVICTION_TIERS:
            # Ensure comparison is between floats to satisfy type checkers
            min_val = float(tier["min"])
            max_val = float(tier["max"])
            if min_val <= float(score) <= max_val:
                return tier
        return cls.CONVICTION_TIERS[-1]  # Default to VERY LOW

    @staticmethod
    def _generate_verdict(ticker: str, recommendation: str, score: float, trade: Dict, conviction_label: str) -> str:
        """Panvi v1.2 — Deterministic Verdict Generator (v4 - Institutional)."""
        # Strip suffix for display consistency
        display_ticker = ticker.split(".")[0]
        currency_sim = IndicatorService._get_currency_symbol(ticker)
        
        status = "STABILITY (HOLD)" if recommendation == "WAIT" else f"POTENTIAL {'EXPANSION' if score > 50 else 'CONTRACTION'}"

        if recommendation == "WAIT" or score < 65:
             reason = "market structure weak" if conviction_label == "LOW" else "insufficient conviction"
             return f"Truth Machine: {display_ticker} remains in {status}. Signal blocked due to {reason}."
        
        entry = trade.get('entry', 0)
        stop = trade.get('stop_loss', 0)
        return f"Truth Machine confirms {status} for {display_ticker} with {conviction_label} conviction. Entry near {currency_sim}{entry}, exit strictly if below {currency_sim}{stop}."

    @classmethod
    def generate_signals(cls, ticker: str, df: pd.DataFrame, weekly_df: pd.DataFrame = None, market_context: Dict[str, Any] = {}, strategy_stats: List[Dict[str, Any]] = []) -> Dict[str, Any]:

        """Generate the full pro trading analysis."""
        if market_context is None: market_context = {}
        empty_result = {
            "recommendation": "HOLD", "signals": [], "rsi": 0, "last_price": 0,
            "composite_score": 50, "breakdown": {}, "price_change_pct": 0,
            "regime": {"regime": "SIDEWAYS", "strength": "weak", "detail": ""},
            "breakout": {"status": "NONE"}, "trap": {"trap": False}, "volume_intel": {},
            "momentum": {}, "sr_zones": {}, "trade": {"direction": "WAIT", "rr_value": 0},
            "mtf": {}, "signal_quality": {"tier": "C"}, "risk_warnings": [],
            "trend_phase": "UNKNOWN", "liquidity": {}, "playbook": {}, "probabilities": {},
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

        # 3b. Detect traps (fake breakouts)
        trap = cls.detect_trap(df, sr_zones)

        # 4. Volume intelligence
        vol_intel = cls.analyze_volume(df)

        # 5. Momentum + RSI slope
        momentum = cls.calculate_momentum(df)

        # 6. Multi-timeframe
        mtf = cls.weekly_confirmation(weekly_df) if weekly_df is not None else {"weekly_trend": "unknown", "aligned": False, "boost": 0}

        # 7. Layered Intelligence System
        regime_name = regime['regime']
        weights = cls.REGIME_WEIGHTS.get(regime_name, cls.REGIME_WEIGHTS['SIDEWAYS'])
        struct_score = cls.calculate_structure_score(df, sr_zones, regime_name)
        
        # v1.2 Layer Evidence
        currency_sim = cls._get_currency_symbol(ticker)
        close = float(last['Close'])
        sma20 = float(last.get('SMA_20', close))
        support_val = sr_zones['support'][0]['price'] if sr_zones['support'] else close * 0.98
        dist_to_support = ((close - support_val) / support_val * 100)
        
        l1_evidence = [
            f"Price is {currency_sim}{close:.2f}, nearest support at {currency_sim}{support_val:.2f} (Dist: {dist_to_support:.1f}%)",
            f"Price vs 20-day average: {'Above' if close > sma20 else 'Below'} by {abs(close-sma20)/sma20*100:.1f}%",
            f"Market Regime: {regime_name} ({regime.get('detail', '')})"
        ]

        rsi = float(last.get('RSI', 50))
        macd_hist = float(last.get('MACD_Diff', 0))
        vol_ratio = float(last.get('Volume', 0) / (last.get('Vol_Avg_20', 1) or 1))
        l2_status = "High (Overbought)" if rsi > 70 else "Low (Oversold)" if rsi < 30 else "Normal"
        l2_evidence = [
            f"RSI = {rsi:.1f}. {l2_status} range.",
            f"MACD Momentum: {'Strengthening' if macd_hist > 0 else 'Weakening'} (Diff: {macd_hist:.3f})",
            f"Volume Intensity: {vol_ratio:.1f}x average. {'Institutional involvement' if vol_ratio > 1.5 else 'Normal retail volume'}."
        ]
        
        # Timestamps
        now_ts = datetime.datetime.now().isoformat()

        
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
        
        # Layer 2: Indicators (Normalized)
        ind_score = cls.calculate_indicator_score(scores, weights)

        # Layer 3: AI/Probabilistic Proxy (Technical Probability)
        # In a full flow, this would be updated by AIService fusion
        tech_probs = cls.calculate_probabilities(ind_score, regime, mtf, market_context)
        ai_prob_proxy = tech_probs.get('bullish', 50) / 100.0

        # Unified signal fusion
        composite = cls.calculate_panvi_fusion(ai_prob_proxy, ind_score, struct_score)

        # Apply MTF boost/penalty
        composite += mtf.get('boost', 0)

        # Trap penalty: downgrade score if fake breakout detected
        if trap.get('trap'):
            composite -= 10

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
        if trap.get('trap'): signals.append(f"{trap.get('type', 'TRAP')}: {trap.get('detail', '')}")
        if vol_intel.get('smart_money'): signals.append(vol_intel['smart_money'])
        if momentum.get('acceleration', '').startswith('ACCEL'): signals.append(f"Momentum {momentum['acceleration']}")
        rsi_slope = momentum.get('rsi_slope', 0)
        if abs(rsi_slope) > 3: signals.append(f"RSI {'surging' if rsi_slope > 0 else 'collapsing'} (slope={rsi_slope})")
        if not signals: signals.append("No strong directional signals")

        # 9. Directional Engine: > 65 EXPECT UP, < 35 EXPECT DOWN, Else WAIT
        if composite > 65: recommendation = "EXPECT UP"
        elif composite < 35: recommendation = "EXPECT DOWN"
        else: recommendation = "WAIT"




        # 11. V4 Deep Engines Setup
        overextended = cls.detect_overextension(df)
        
        # 12. Trade structure (pass breakout for pullback entry)
        trade = cls.generate_trade_structure(df, sr_zones, recommendation, breakout, overextended)

        # 12. Signal quality (initial)
        signal_quality = cls.get_signal_quality(composite, breakout, vol_intel, regime, mtf, trade)

        # 13. ALWAYS-ON RISK WARNINGS — there is ALWAYS risk
        risk_warnings = []
        if trade.get('rr_value', 0) < 1.5 and trade.get('direction') != 'WAIT':
            risk_warnings.append(f"Low R:R ({trade.get('rr_value', 0)}) — not an ideal entry point")
        if trap.get('trap'):
            risk_warnings.append(trap['detail'])
        if vol_intel.get('divergence') == 'BEARISH':
            risk_warnings.append("Price-volume divergence — rally may not sustain")
        rsi_v = float(last.get('RSI', 50))
        if rsi_v > 70:
            risk_warnings.append(f"RSI overbought ({rsi_v:.0f}) — pullback risk")
        elif rsi_v < 30:
            risk_warnings.append(f"RSI oversold ({rsi_v:.0f}) — could be falling knife")
        if momentum.get('acceleration') == 'DECELERATING':
            risk_warnings.append("Momentum decelerating — move losing steam")
        if not mtf.get('aligned') and mtf.get('weekly_trend') != 'unknown':
            risk_warnings.append("Weekly trend not aligned — reduces conviction")
        if regime_name == 'VOLATILE':
            risk_warnings.append("High volatility environment — wider stops needed")
        if regime_name == 'SIDEWAYS':
            risk_warnings.append("Range-bound market — breakout strategies underperform")
        roc_5 = float(last.get('ROC_5', 0))
        if abs(roc_5) > 7:
            risk_warnings.append(f"Overextended move (ROC={roc_5:.1f}%) — possible pullback")
        if vol_intel.get('trend') == 'falling':
            risk_warnings.append("Volume declining — conviction fading")
        # Always have at least one warning
        if not risk_warnings:
            risk_warnings.append("Standard market risk applies — always use stop loss")

        # 14. Additional Engine Mapping
        trend_phase = cls.detect_trend_phase(regime, breakout, momentum, vol_intel)
        liquidity = cls.map_liquidity(df)
        probabilities = cls.calculate_probabilities(composite, regime, mtf, market_context)
        playbook = cls.generate_playbook(trade, trend_phase, overextended)

        # 15. V5 Quant Edge Engines
        # Calculate potential risk BEFORE filters block the trade
        # If the trade is WAIT/Neutral, we construct a 'Shadow Trade' for the safety metric
        shadow_trade = trade.copy()
        if shadow_trade.get('direction') == 'WAIT':
            potential_dir = "BUY" if composite >= 50 else "SELL"
            shadow_trade = cls.generate_trade_structure(df, sr_zones, potential_dir, breakout, overextended)

        
        potential_pos = cls.calculate_position_size(shadow_trade)
        ev_data = cls.calculate_ev(probabilities, trade)
        position_size = potential_pos # Default for dashboard

        
        # 16. V5 STRICT TRADE FILTER & SEQUENTIAL CONFIRMATION

        rr_val = trade.get('rr_value', 0)
        
        # Strategy classification for Regime blocks
        is_mean_reversion = rsi_val < 35 or rsi_val > 65
        is_breakout_strat = breakout.get('status') in ['CONFIRMED', 'ATTEMPT']
        strategy_type = "MEAN_REVERSION" if is_mean_reversion else "BREAKOUT" if is_breakout_strat else "TREND_CONT"
        
        ta_direction = trade.get('direction')
        
        # V6 Regime-Strategy Mismatch Engine
        if regime_name == "SIDEWAYS" and strategy_type == "TREND_CONT":
            recommendation = "HOLD"
            trade['note'] = f"V6 REGIME FILTER: Strategy ({strategy_type}) underperforms violently in SIDEWAYS regime. Trade blocked."
            signal_quality = {"tier": "D", "label": "REGIME BLOCKED", "color": "#FF6B6B"}
            trade['direction'] = "WAIT"
            risk_warnings.append(trade['note'])
        # Sequential block: chop + flat volume = NO TRADE
        elif regime_name == "CHOPPY" and vol_intel.get('trend') == 'flat':
            recommendation = "HOLD"
            trade['note'] = "V5 FILTER: Choppy market with no volume — DO NOT TRADE."
            signal_quality = {"tier": "D", "label": "AVOID MARKET", "color": "#FF6B6B"}
            trade['direction'] = "WAIT"
            risk_warnings.append(trade['note'])
        # V5 Absolute Filter (Negative EV or bad R:R)
        # Relaxed: Only block if EV is significantly negative (< -0.1R)
        elif trade.get('direction') != 'WAIT' and (float(ev_data.get('ev', 0)) < -0.1 or rr_val < 1.3):
            recommendation = "HOLD"
            trade['note'] = f"V5 FILTER: Bad math (EV={ev_data['ev']}, R:R={rr_val}). Trade physically blocked."
            signal_quality = {"tier": "D", "label": "BLOCKED", "color": "#FF6B6B"}
            trade['direction'] = "WAIT"
            risk_warnings.append(trade['note'])

        # V7 Self-Learning Loop Block (Real World Stats)
        if strategy_stats and trade.get('direction') != 'WAIT':
            # Extract PF for this specific strategy type
            strat_info = next((s for s in strategy_stats if s['strategy'] == strategy_type), None)
            if strat_info:
                real_pf = strat_info.get('profit_factor', 1.0)
                real_wr = strat_info.get('win_rate', 0.0)
                total_t = strat_info.get('total_trades', 0)
                
                # Relaxed: Only block if PF is catastrophically low (< 0.7)
                if total_t >= 10 and real_pf < 0.7:
                    recommendation = "HOLD"
                    trade['note'] = f"V7 SELF-LEARNING BLOCK: Strategy '{strategy_type}' is UNPROFITABLE in real-world tracking (PF {real_pf}). Execution halted."
                    signal_quality = {"tier": "D", "label": "UNPROFITABLE", "color": "#FF6B6B"}
                    trade['direction'] = "WAIT"
                    risk_warnings.append(trade['note'])

                elif total_t >= 10:
                    # Dynamic Confidence Scaling
                    if real_pf > 1.5:
                        composite = min(100, composite * 1.1)
                    elif real_pf < 1.2:
                        composite *= 0.9
                    composite = round(composite, 1)

        # Merge new warnings into risk warnings
        if overextended.get('overextended'):
            risk_warnings.append(overextended['detail'])
        if liquidity.get('detected'):
            for pool in liquidity['pools']:
                risk_warnings.append(pool)

        # Base: 70. Normalized by how 'bad' the EV was.
        safety_score = float(70.0 + (abs(float(min(0.0, float(ev_data['ev'])))) * 15.0))
        if recommendation == "HOLD" and ta_direction != "WAIT":
            safety_score += 10.0
        safety_score = float(min(99.0, float(round(float(safety_score)))))
        
        cap_saved = float(position_size.get('risk_amount', 0.0))

        
        # Phase 3: Production Safety Guards
        nifty_change = market_context.get('nifty_daily_change', 0.0)
        market_regime_alert = None
        if nifty_change < -2.5:
            market_regime_alert = f"HIGH VOLATILITY ({nifty_change}%): Signals unreliable. Avoid new entries."

        near_earnings = cls._check_earnings_proximity(ticker)
        if near_earnings:
            composite = min(composite, 60.0)
            risk_warnings.append("Earnings risk: Within 5-day window. Conviction capped.")

        # V3 Production Tier Alignment
        tier_info = cls()._get_tier_info(composite)
        conviction_label = tier_info["label"]

        # Phase 4 Regime Refinement
        if rsi_val < 35:
            regime_name = "OVERSOLD"
            regime["detail"] = f"RSI {rsi_val:.0f} (Potential Bounce Window)"
        elif breakout.get('status') == 'CONFIRMED':
            regime_name = "BREAKOUT"
            regime["detail"] = f"Price clearing {breakout.get('type', 'level')}"
        
        # Standardize regime name and detail
        regime["regime"] = regime_name
        
        return {
            "bias": recommendation,
            "recommendation": recommendation,
            "currency_symbol": currency_sim,
            "verdict": cls._generate_verdict(ticker, recommendation, composite, trade, conviction_label),
            "market_regime_alert": market_regime_alert,
            "algorithm_version": cls.ALGORITHM_VERSION,
            "composite_score": composite,
            "struct_score": struct_score,
            "ind_score": ind_score,
            "ai_score": round(ai_prob_proxy * 100, 1),
            "signals": signals,
            "l1_evidence": l1_evidence,
            "l2_evidence": l2_evidence,
            "l1_generated_at": now_ts,
            "l2_generated_at": now_ts,
            "algorithm_version": "PANVI_1.2",


            "rsi": rsi_val,
            "last_price": round(float(last['Close']), 2),
            "breakdown": {k: round(v, 1) for k, v in scores.items()},
            "price_change_pct": round(float(price_change_pct), 2),
            "regime": regime,
            "breakout": breakout,
            "trap": trap,
            "volume_intel": vol_intel,
            "momentum": momentum,
            "sr_zones": sr_zones,
            "trade": trade,
            "mtf": mtf,
            "signal_quality": signal_quality,
            "risk_warnings": risk_warnings,
            "trend_phase": trend_phase,
            "liquidity": liquidity,
            "probabilities": probabilities,
            "playbook": playbook,
            "expected_value": ev_data,
            "position_size": position_size,
            "capital_safety_score": float(safety_score),
            "capital_saved_formatted": f"₹{cap_saved:,.0f}" if cap_saved > 0 else f"{float(abs(float(ev_data['ev'])) + 1.25):.2f}R"


        }
