import os
import json
import google.generativeai as genai
from typing import Dict, Any, Optional, List
from services.news_service import NewsService

class AIService:
    """
    AI Prediction Layer with Smart Technical Fallback.
    When Gemini is unavailable, generates rich analysis from indicators alone.
    """

    def __init__(self, gemini_key: Optional[str] = None, news_key: Optional[str] = None):
        self.gemini_key = gemini_key or os.getenv("GEMINI_API_KEY")
        self.news_service = NewsService(news_key)

        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            self.model = genai.GenerativeModel('models/gemini-2.0-flash')
        else:
            self.model = None

    # ─── Smart Fallback: Generate insight from technical data alone ──
    @staticmethod
    def _generate_technical_insight(ticker: str, ta: Dict[str, Any]) -> Dict[str, Any]:
        """Generate rich, actionable analysis from technical indicators alone."""
        breakdown = ta.get("breakdown", {})
        composite = ta.get("composite_score", 50)
        rsi = ta.get("rsi", 50)
        signals = ta.get("signals", [])
        price_change = ta.get("price_change_pct", 0)

        # Count bullish vs bearish indicators
        bullish = [k for k, v in breakdown.items() if v >= 60]
        bearish = [k for k, v in breakdown.items() if v <= 40]
        neutral = [k for k, v in breakdown.items() if 40 < v < 60]

        # RSI Analysis
        if rsi < 25:
            rsi_analysis = f"RSI at {rsi} indicates extreme oversold conditions — a bounce is likely."
        elif rsi < 35:
            rsi_analysis = f"RSI at {rsi} is in oversold territory — watch for a reversal."
        elif rsi > 75:
            rsi_analysis = f"RSI at {rsi} signals extreme overbought — correction risk is high."
        elif rsi > 65:
            rsi_analysis = f"RSI at {rsi} is entering overbought zone — momentum may be fading."
        else:
            rsi_analysis = f"RSI at {rsi} is in neutral range — no extreme momentum signal."

        # Trend Analysis
        sma_score = breakdown.get("sma_cross", 50)
        ema_score = breakdown.get("ema_cross", 50)
        trend_200 = breakdown.get("trend_200", 50)

        if sma_score >= 65 and trend_200 >= 58:
            trend_analysis = "The stock is in a confirmed uptrend (above SMA 20, 50, and 200)."
        elif sma_score <= 35 and trend_200 <= 42:
            trend_analysis = "The stock is in a confirmed downtrend (below key moving averages)."
        elif sma_score >= 60:
            trend_analysis = "Short-term trend is bullish, but long-term direction is unclear."
        elif sma_score <= 40:
            trend_analysis = "Short-term trend is bearish, though the long-term trend may hold support."
        else:
            trend_analysis = "The stock is range-bound with no clear directional trend."

        # Momentum Analysis
        macd_score = breakdown.get("macd", 50)
        stoch_score = breakdown.get("stochastic", 50)

        if macd_score >= 75 and stoch_score >= 70:
            momentum = "Strong bullish momentum: both MACD and Stochastic confirm upward pressure."
        elif macd_score <= 25 and stoch_score <= 30:
            momentum = "Strong bearish momentum: MACD and Stochastic both signal downside."
        elif macd_score >= 60:
            momentum = "MACD is bullish — positive momentum building."
        elif macd_score <= 40:
            momentum = "MACD is bearish — selling pressure remains."
        else:
            momentum = "Momentum is neutral with no strong directional bias."

        # Volume Analysis
        vol_score = breakdown.get("volume", 50)
        if vol_score >= 75:
            volume_note = "Volume spike on up-day confirms buying conviction."
        elif vol_score <= 25:
            volume_note = "High volume on decline suggests institutional selling."
        else:
            volume_note = "Volume is average — no strong conviction signal."

        # Risk Assessment
        risks = []
        if rsi > 70:
            risks.append("Overbought RSI increases pullback risk")
        if sma_score <= 35:
            risks.append("Price below key moving averages (bearish structure)")
        if macd_score <= 30:
            risks.append("Negative MACD momentum")
        if vol_score <= 30:
            risks.append("Selling pressure indicated by volume")
        if breakdown.get("adx", 50) >= 70 and sma_score <= 40:
            risks.append("Strong bearish trend confirmed by ADX")

        if not risks:
            if composite >= 65:
                risk_text = "Low risk: Technical indicators are broadly aligned to the upside."
            else:
                risk_text = "Moderate risk: Mixed signals — position sizing should be conservative."
        else:
            risk_text = "; ".join(risks[:3]) + "."

        # Build the full insight
        insight = f"{rsi_analysis} {trend_analysis} {momentum}"

        # Modifier based on technical alignment
        if len(bullish) >= 7:
            modifier = 10
        elif len(bullish) >= 5:
            modifier = 5
        elif len(bearish) >= 7:
            modifier = -10
        elif len(bearish) >= 5:
            modifier = -5
        else:
            modifier = 0

        # Confidence level
        if len(bullish) >= 6 or len(bearish) >= 6:
            confidence = "high"
        elif len(bullish) >= 4 or len(bearish) >= 4:
            confidence = "medium"
        else:
            confidence = "low"

        sentiment = "bullish" if len(bullish) > len(bearish) else "bearish" if len(bearish) > len(bullish) else "neutral"

        return {
            "ai_modifier": modifier,
            "sentiment": sentiment,
            "insight": insight,
            "confidence": confidence,
            "key_risk": risk_text,
            "volume_analysis": volume_note,
            "bullish_count": len(bullish),
            "bearish_count": len(bearish),
            "neutral_count": len(neutral),
        }

    async def analyze_ticker_sentiment(self, ticker: str, technical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Try Gemini first; fall back to smart technical analysis."""

        # Always generate technical fallback
        fallback = self._generate_technical_insight(ticker, technical_data)

        articles = self.news_service.get_top_headlines(category="business")
        if not articles or not self.model:
            return fallback

        headlines = [a.get('title', '') for a in articles[:15] if a.get('title')]
        headlines_str = "\n".join(f"- {h}" for h in headlines)

        composite = technical_data.get("composite_score", 50)
        rsi = technical_data.get("rsi", 50)
        recommendation = technical_data.get("recommendation", "HOLD")
        signals = technical_data.get("signals", [])

        prompt = f"""You are a senior quantitative analyst. Analyze stock ticker "{ticker}".

TECHNICAL DATA:
- Composite Score: {composite}/100 | RSI: {rsi} | Signal: {recommendation}
- Active Signals: {', '.join(signals) if signals else 'None'}

MARKET HEADLINES:
{headlines_str}

Respond in EXACTLY this JSON (no markdown, no backticks):
{{"sentiment_modifier": <int -20 to +20>, "sentiment": "<bullish|bearish|neutral>", "insight": "<2 sentences about what headlines + technicals suggest for {ticker}>", "confidence": "<high|medium|low>", "key_risk": "<1 sentence biggest risk>"}}"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
                text = text.rsplit("```", 1)[0].strip()

            data = json.loads(text)
            modifier = max(-20, min(20, int(data.get("sentiment_modifier", 0))))

            return {
                "ai_modifier": modifier,
                "sentiment": data.get("sentiment", "neutral"),
                "insight": data.get("insight", fallback["insight"]),
                "confidence": data.get("confidence", "medium"),
                "key_risk": data.get("key_risk", fallback["key_risk"]),
                "volume_analysis": fallback["volume_analysis"],
                "bullish_count": fallback["bullish_count"],
                "bearish_count": fallback["bearish_count"],
                "neutral_count": fallback["neutral_count"],
            }

        except Exception as e:
            print(f"Gemini failed for {ticker}: {e}. Using technical fallback.")
            return fallback

    async def predict_stock_outcome(self, ticker: str, technical_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Final prediction: Technical Score + AI Modifier = Final Score."""
        composite_score = technical_summary.get("composite_score", 50)
        breakdown = technical_summary.get("breakdown", {})

        ai_data = await self.analyze_ticker_sentiment(ticker, technical_summary)
        ai_modifier = ai_data.get("ai_modifier", 0)

        final_score = max(0, min(100, composite_score + ai_modifier))

        if final_score >= 80:
            prediction = "STRONG BUY"
        elif final_score >= 65:
            prediction = "BUY"
        elif final_score >= 45:
            prediction = "HOLD"
        elif final_score >= 30:
            prediction = "SELL"
        else:
            prediction = "STRONG SELL"

        if final_score >= 50:
            probability = 50 + (final_score - 50) * 0.9
        else:
            probability = 50 - (50 - final_score) * 0.9
        probability = max(5.0, min(95.0, probability))

        if ai_modifier <= -10:
            geo_risk = "High"
        elif ai_modifier <= -5:
            geo_risk = "Medium"
        else:
            geo_risk = "Low"

        return {
            "prediction": prediction,
            "probability": f"{probability:.1f}%",
            "final_score": round(float(final_score), 1),
            "technical_score": composite_score,
            "ai_modifier": ai_modifier,
            "ai_sentiment": ai_data.get("sentiment", "neutral"),
            "ai_insight": ai_data.get("insight", ""),
            "ai_confidence": ai_data.get("confidence", "low"),
            "key_risk": ai_data.get("key_risk", ""),
            "geopolitical_risk": geo_risk,
            "volume_analysis": ai_data.get("volume_analysis", ""),
            "bullish_count": ai_data.get("bullish_count", 0),
            "bearish_count": ai_data.get("bearish_count", 0),
            "breakdown": breakdown,
        }
