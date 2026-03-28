import os
import json
import google.generativeai as genai
from typing import Dict, Any, Optional
from services.news_service import NewsService

class AIService:
    """
    AI Prediction Layer.
    Combines technical composite score with Gemini-powered sentiment
    analysis to produce a final investment signal.
    """

    def __init__(self, gemini_key: Optional[str] = None, news_key: Optional[str] = None):
        self.gemini_key = gemini_key or os.getenv("GEMINI_API_KEY")
        self.news_service = NewsService(news_key)

        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            self.model = genai.GenerativeModel('models/gemini-2.0-flash')
        else:
            self.model = None

    async def analyze_ticker_sentiment(self, ticker: str, technical_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get AI sentiment for a specific ticker using news headlines
        and technical context. Returns a modifier score (-20 to +20).
        """
        # Fetch news headlines
        articles = self.news_service.get_top_headlines(category="business")
        if not articles or not self.model:
            return {
                "ai_modifier": 0,
                "sentiment": "neutral",
                "insight": "AI analysis unavailable (no API key or no news data).",
                "confidence": "low"
            }

        headlines = [a.get('title', '') for a in articles[:15] if a.get('title')]
        headlines_str = "\n".join(f"- {h}" for h in headlines)

        composite = technical_data.get("composite_score", 50)
        rsi = technical_data.get("rsi", 50)
        recommendation = technical_data.get("recommendation", "HOLD")
        signals = technical_data.get("signals", [])
        price_change = technical_data.get("price_change_pct", 0)

        prompt = f"""You are a senior quantitative analyst. Analyze stock ticker "{ticker}" using the market context below.

TECHNICAL ANALYSIS DATA:
- Composite Score: {composite}/100
- Recommendation: {recommendation}
- RSI: {rsi}
- Recent Price Change: {price_change}%
- Active Signals: {', '.join(signals) if signals else 'None'}

CURRENT MARKET HEADLINES:
{headlines_str}

Based on the headlines and technical data, provide your analysis in EXACTLY this JSON format (no markdown, no backticks):
{{
  "sentiment_modifier": <integer from -20 to +20>,
  "sentiment": "<bullish|bearish|neutral>",
  "insight": "<One concise sentence about what the headlines and technicals together suggest for this stock>",
  "confidence": "<high|medium|low>",
  "key_risk": "<One sentence about the biggest risk factor>"
}}

Rules:
- sentiment_modifier should be between -20 and +20
- Positive modifier = bullish headlines support the technical signal
- Negative modifier = bearish headlines contradict the technical signal
- Be conservative: only give high modifiers (±15 to ±20) for extreme situations
- If headlines are mixed or unrelated, keep modifier near 0"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()

            # Clean markdown code block if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
                text = text.rsplit("```", 1)[0]
                text = text.strip()

            data = json.loads(text)

            modifier = max(-20, min(20, int(data.get("sentiment_modifier", 0))))

            return {
                "ai_modifier": modifier,
                "sentiment": data.get("sentiment", "neutral"),
                "insight": data.get("insight", "No insight available."),
                "confidence": data.get("confidence", "low"),
                "key_risk": data.get("key_risk", "No specific risks identified.")
            }

        except Exception as e:
            print(f"AI Analysis Error for {ticker}: {e}")
            return {
                "ai_modifier": 0,
                "sentiment": "neutral",
                "insight": f"AI analysis failed: {str(e)[:80]}",
                "confidence": "low",
                "key_risk": "Unable to assess risks."
            }

    async def predict_stock_outcome(self, ticker: str, technical_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Final prediction: Technical Score + AI Modifier = Final Score.
        """
        composite_score = technical_summary.get("composite_score", 50)
        rsi = technical_summary.get("rsi", 50)

        # Get AI sentiment analysis
        ai_data = await self.analyze_ticker_sentiment(ticker, technical_summary)
        ai_modifier = ai_data.get("ai_modifier", 0)

        # Final score = Technical (0-100) + AI Modifier (-20 to +20)
        final_score = max(0, min(100, composite_score + ai_modifier))

        # Final recommendation based on combined score
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

        # Confidence as probability
        if final_score >= 50:
            probability = 50 + (final_score - 50) * 0.9  # Scale 50-95%
        else:
            probability = 50 - (50 - final_score) * 0.9  # Scale 5-50%
        probability = max(5, min(95, probability))

        # Geopolitical risk assessment
        if ai_modifier <= -10:
            geo_risk = "High"
        elif ai_modifier <= -5:
            geo_risk = "Medium"
        else:
            geo_risk = "Low"

        return {
            "prediction": prediction,
            "probability": f"{probability:.1f}%",
            "final_score": round(final_score, 1),
            "technical_score": composite_score,
            "ai_modifier": ai_modifier,
            "ai_sentiment": ai_data.get("sentiment", "neutral"),
            "ai_insight": ai_data.get("insight", ""),
            "ai_confidence": ai_data.get("confidence", "low"),
            "key_risk": ai_data.get("key_risk", ""),
            "geopolitical_risk": geo_risk,
        }
