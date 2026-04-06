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

        # V4: Probabilities and Playbook
        probs = ta.get('probabilities', {})
        if probs:
            parts.append(f"Math: Up {probs.get('bullish', 0)}% | Sideways {probs.get('sideways', 0)}% | Down {probs.get('bearish', 0)}%.")

            
        playbook = ta.get('playbook', {})
        if playbook and playbook.get('plan'):
            plan_str = " | ".join(playbook.get('plan'))
            parts.append(f"Playbook: {plan_str}")

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

        sentiment = "positive" if len(bullish) > len(bearish) else "negative" if len(bearish) > len(bullish) else "neutral"
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


    FALLBACK_AI_RESPONSE = {
        "score": 50,
        "sentiment": "Neutral",
        "insight": "AI analysis temporarily unavailable. Market structure remains the primary signal.",
        "confidence": "Low",
        "key_risk": "Technical data only; news sentiment not factored.",
        "sources": [],
        "negative_factors": ["AI Layer Timeout/Failure"],
        "invalidation": "Restore AI connectivity to verify geopolitical factors."
    }

    async def analyze_ticker_sentiment(self, ticker: str, technical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 3: AI Brain with strict JSON contract and fallback."""
        fallback_insight = self._generate_technical_insight(ticker, technical_data)
        
        # Hydrate fallback with full contract structure
        local_fallback = self.FALLBACK_AI_RESPONSE.copy()
        local_fallback["score"] = technical_data.get("probabilities", {}).get("bullish", 50)
        local_fallback["insight"] = fallback_insight["insight"]
        local_fallback["key_risk"] = fallback_insight["key_risk"]

        if not self.model:
            return local_fallback

        articles = self.news_service.get_top_headlines(category="business")
        headlines_str = "No recent news found."
        if articles:
            headlines = [a.get('title', '') for a in articles[:15] if a.get('title')]
            headlines_str = "\n".join(f"- {h}" for h in headlines)

        regime = technical_data.get("regime", {}).get("regime", "UNKNOWN")
        probs = technical_data.get("probabilities", {})
        probs_text = f"Up {probs.get('bullish')}% / Sideways {probs.get('sideways')}% / Down {probs.get('bearish')}%" if probs else ""

        prompt = f"""You are a professional trading analyst. Analyze "{ticker}" for the {regime} regime.
GROWTH PROBABILITIES: {probs_text}
HEADLINES:
{headlines_str}
TECHNICAL CONTEXT:
"{fallback_insight.get('insight', '')}"

INSTRUCTIONS:
1. Use simple English. NEVER use 'bullish', 'bearish', 'stochastic', 'bollinger', 'macd', or 'rsi'. 
2. Use 'Expanding/Rising' for up and 'Falling/Contracting' for down.
3. Identify exactly 3 real sources/events from headlines.
4. List the #1 reason this trade might fail (Invalidation).

Respond in JSON only:
{{
  "score": <int 0-100 derived from sentiment + technicals>,
  "sentiment": "<Positive|Negative|Neutral>",
  "insight": "<2 sentences simple English>",
  "confidence": "<High|Medium|Low>",
  "key_risk": "<1 sentence simple English>",
  "sources": ["<source 1>", "<source 2>", "<source 3>"],
  "negative_factors": ["<factor 1>", "<factor 2>"],
  "invalidation": "<The exact price or event that makes this analysis wrong>"
}}"""

        try:
            response = self.model.generate_content(prompt)
            data = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
            
            # Validation & Sanitization
            return {
                "ai_score": max(0, min(100, int(data.get("score", 50)))),
                "sentiment": data.get("sentiment", "Neutral"),
                "insight": data.get("insight", local_fallback["insight"]),
                "confidence": data.get("confidence", "Medium"),
                "key_risk": data.get("key_risk", local_fallback["key_risk"]),
                "sources": data.get("sources", []),
                "negative_factors": data.get("negative_factors", []),
                "invalidation": data.get("invalidation", "Breach of primary support/resistance level"),
                "bullish_count": fallback_insight["bullish_count"],
                "bearish_count": fallback_insight["bearish_count"],
                "neutral_count": fallback_insight["neutral_count"],
            }
        except Exception as e:
            print(f"Gemini Contract Violation: {e}. Triggering institutional fallback.")
            return local_fallback

    async def predict_stock_outcome(self, ticker: str, technical_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Final Fusion: Orchestrates L1-L3 into a deterministic verdict."""
        ind_score = technical_summary.get("ind_score", 50)
        struct_score = technical_summary.get("struct_score", 50)
        breakdown = technical_summary.get("breakdown", {})
        probs = technical_summary.get("probabilities", {}) or {}

        ai_data = await self.analyze_ticker_sentiment(ticker, technical_summary)
        
        # New Fusion Logic: AI Score is now integrated by the model itself
        ai_score = float(ai_data.get("ai_score", 50))

        # Unified Fusion: 0.4 AI + 0.3 Indicators + 0.3 Structure
        final_score = (0.4 * ai_score) + (0.3 * ind_score) + (0.3 * struct_score)
        final_p = round(float(final_score), 1)

        # Institutional Position Sizing Tier
        if final_p > 85: conviction = "EXTREME"
        elif final_p > 72: conviction = "HIGH"
        elif final_p > 65: conviction = "MEDIUM"
        else: conviction = "LOW"

        # Directional Engine
        if final_p > 65: 
            prediction = "Expanding (Buy)"
        elif final_p < 35: 
            prediction = "Contracting (Sell)"
        else: 
            prediction = "Stability (Hold)"
            
        return {
            "prediction": prediction,
            "probability": f"{final_p:.1f}%",
            "final_score": final_p,
            "conviction": conviction,
            "ind_score": ind_score,
            "struct_score": struct_score,
            "ai_score": ai_score,
            "ai_sentiment": ai_data.get("sentiment", "Neutral"),
            "ai_insight": ai_data.get("insight", ""),
            "ai_confidence": ai_data.get("confidence", "Low"),
            "key_risk": ai_data.get("key_risk", ""),
            "sources": ai_data.get("sources", []),
            "negative_factors": ai_data.get("negative_factors", []),
            "invalidation": ai_data.get("invalidation", "Default support breach"),
            "geopolitical_risk": "High" if ai_score < 40 else "Medium" if ai_score < 60 else "Low",
            "bullish_count": ai_data.get("bullish_count", 0),
            "bearish_count": ai_data.get("bearish_count", 0),
            "neutral_count": ai_data.get("neutral_count", 0),
            "breakdown": breakdown,
        }
