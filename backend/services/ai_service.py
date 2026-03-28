import os
import json
import google.generativeai as genai
from typing import Dict, Any, Optional
from services.news_service import NewsService

class AIService:
    """
    AI Prediction Layer v2.0 — Pro Trading Engine Integration.
    Smart technical fallback + optional Gemini enhancement.
    """

    def __init__(self, gemini_key: Optional[str] = None, news_key: Optional[str] = None):
        self.gemini_key = gemini_key or os.getenv("GEMINI_API_KEY")
        self.news_service = NewsService(news_key)
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            self.model = genai.GenerativeModel('models/gemini-2.0-flash')
        else:
            self.model = None

    @staticmethod
    def _generate_technical_insight(ticker: str, ta: Dict[str, Any]) -> Dict[str, Any]:
        """Generate rich, context-aware analysis from the pro engine data."""
        breakdown = ta.get("breakdown", {})
        composite = ta.get("composite_score", 50)
        rsi = ta.get("rsi", 50)
        regime = ta.get("regime", {})
        breakout = ta.get("breakout", {})
        vol_intel = ta.get("volume_intel", {})
        momentum = ta.get("momentum", {})
        trade = ta.get("trade", {})
        mtf = ta.get("mtf", {})
        quality = ta.get("signal_quality", {})

        # Count indicators
        bullish = [k for k, v in breakdown.items() if v >= 60]
        bearish = [k for k, v in breakdown.items() if v <= 40]

        parts = []

        # 1. Regime context
        regime_name = regime.get('regime', 'SIDEWAYS')
        parts.append(f"Market is {regime_name} ({regime.get('detail', '')}).")

        # 2. Breakout status
        bo_status = breakout.get('status', 'NONE')
        if bo_status == "CONFIRMED":
            parts.append(f"🔥 {breakout.get('detail', 'Confirmed breakout detected')}.")
        elif bo_status == "ATTEMPT":
            parts.append(f"⚠️ {breakout.get('detail', 'Breakout attempt')}.")
        elif bo_status == "WEAK":
            parts.append(f"❌ {breakout.get('detail', 'Weak breakout — possible fake-out')}.")

        # 3. Volume intelligence
        smart = vol_intel.get('smart_money')
        if smart:
            parts.append(f"🧠 {smart}.")
        if vol_intel.get('divergence') == "BEARISH":
            parts.append("⚠️ Price-volume divergence: rally on declining volume — caution.")
        elif vol_intel.get('divergence') == "BULLISH":
            parts.append("Selling pressure fading — volume declining on pullback.")

        # 4. Momentum
        accel = momentum.get('acceleration', 'STEADY')
        if 'ACCELERATING UP' in accel:
            parts.append("Momentum accelerating upward — strength building.")
        elif 'ACCELERATING DOWN' in accel:
            parts.append("Momentum accelerating to the downside.")
        elif accel == 'DECELERATING':
            parts.append("Momentum decelerating — move losing power.")

        # 5. Multi-timeframe
        wt = mtf.get('weekly_trend', 'unknown')
        if mtf.get('aligned'):
            parts.append(f"Weekly trend confirms: {wt}.")
        elif wt != "unknown":
            parts.append(f"Weekly trend mixed ({wt}) — reduces confidence.")

        # 6. Trade context
        if trade.get('direction') in ('LONG', 'SHORT'):
            rr = trade.get('risk_reward', 'N/A')
            rr_ok = trade.get('rr_acceptable', False)
            parts.append(f"Risk:Reward = {rr}.")
            if not rr_ok:
                parts.append("⚠️ R:R below 1.5 — not an ideal entry.")
            if trade.get('pullback_entry'):
                parts.append(f"Better entry on pullback to {trade['pullback_entry']}.")
        if trade.get('note'):
            parts.append(trade['note'])

        # 6b. Trap warning
        trap = ta.get("trap", {})
        if trap.get('trap'):
            parts.insert(0, f"🚨 {trap.get('detail', 'Trap detected')}.")

        insight = " ".join(parts)

        # Risk assessment — use engine's always-on warnings
        risk_list = ta.get('risk_warnings', [])
        risk_text = "; ".join(risk_list[:4]) + "." if risk_list else "Standard market risk applies."

        # Modifier
        modifier = 0
        if len(bullish) >= 7: modifier = 8
        elif len(bullish) >= 5: modifier = 4
        elif len(bearish) >= 7: modifier = -8
        elif len(bearish) >= 5: modifier = -4
        if bo_status == "CONFIRMED":
            modifier += 5 if breakout.get('type') == "BULLISH" else -5
        if smart and 'BUYING' in smart: modifier += 3
        elif smart and 'SELLING' in smart: modifier -= 3

        sentiment = "bullish" if len(bullish) > len(bearish) else "bearish" if len(bearish) > len(bullish) else "neutral"
        confidence = "high" if abs(modifier) >= 10 else "medium" if abs(modifier) >= 5 else "low"

        return {
            "ai_modifier": max(-20, min(20, modifier)),
            "sentiment": sentiment,
            "insight": insight,
            "confidence": confidence,
            "key_risk": risk_text,
            "bullish_count": len(bullish),
            "bearish_count": len(bearish),
            "neutral_count": len(breakdown) - len(bullish) - len(bearish),
        }

    async def analyze_ticker_sentiment(self, ticker: str, technical_data: Dict[str, Any]) -> Dict[str, Any]:
        fallback = self._generate_technical_insight(ticker, technical_data)
        articles = self.news_service.get_top_headlines(category="business")
        if not articles or not self.model:
            return fallback

        headlines = [a.get('title', '') for a in articles[:15] if a.get('title')]
        headlines_str = "\n".join(f"- {h}" for h in headlines)
        regime = technical_data.get("regime", {}).get("regime", "UNKNOWN")
        composite = technical_data.get("composite_score", 50)

        prompt = f"""You are a senior quant. Analyze "{ticker}" (Market: {regime}, Score: {composite}/100).
HEADLINES:
{headlines_str}
Respond in JSON only (no markdown): {{"sentiment_modifier": <int -20 to +20>, "sentiment": "<bullish|bearish|neutral>", "insight": "<2 sentences>", "confidence": "<high|medium|low>", "key_risk": "<1 sentence>"}}"""

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
                "bullish_count": fallback["bullish_count"],
                "bearish_count": fallback["bearish_count"],
                "neutral_count": fallback["neutral_count"],
            }
        except Exception as e:
            print(f"Gemini failed for {ticker}: {e}. Using technical fallback.")
            return fallback

    async def predict_stock_outcome(self, ticker: str, technical_summary: Dict[str, Any]) -> Dict[str, Any]:
        composite_score = technical_summary.get("composite_score", 50)
        breakdown = technical_summary.get("breakdown", {})

        ai_data = await self.analyze_ticker_sentiment(ticker, technical_summary)
        ai_modifier = ai_data.get("ai_modifier", 0)
        final_score = max(0, min(100, composite_score + ai_modifier))

        if final_score >= 80: prediction = "STRONG BUY"
        elif final_score >= 65: prediction = "BUY"
        elif final_score >= 45: prediction = "HOLD"
        elif final_score >= 30: prediction = "SELL"
        else: prediction = "STRONG SELL"

        if final_score >= 50:
            probability = 50 + (final_score - 50) * 0.9
        else:
            probability = 50 - (50 - final_score) * 0.9
        probability = max(5.0, min(95.0, probability))

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
            "geopolitical_risk": "High" if ai_modifier <= -10 else "Medium" if ai_modifier <= -5 else "Low",
            "bullish_count": ai_data.get("bullish_count", 0),
            "bearish_count": ai_data.get("bearish_count", 0),
            "neutral_count": ai_data.get("neutral_count", 0),
            "breakdown": breakdown,
        }
