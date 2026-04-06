import uvicorn
import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to sys.path for robust imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import List, Dict, Any
import asyncio

from services.stock_service import StockService
from services.indicator_service import IndicatorService
from services.ai_service import AIService
from services.feedback_service import FeedbackService
from services.backtest_service import BacktestService
from services.trade_tracker_service import TradeTrackerService

app = FastAPI(title="AI Global Stock Predictor API")

# Enable CORS for React Native / Expo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_service = AIService()


async def _build_analysis_payload(ticker: str) -> Dict[str, Any]:
    """Build a frontend-friendly analysis payload for one ticker."""
    df = StockService.get_stock_data(ticker)
    if df.empty:
        raise HTTPException(status_code=404, detail="Stock not found or no data")

    try:
        weekly_df = StockService.get_weekly_data(ticker)
    except Exception:
        weekly_df = None

    market_context = StockService.get_market_context()
    portfolio = TradeTrackerService.get_portfolio()
    strategy_stats = portfolio.get('strategy_stats', []) if isinstance(portfolio, dict) else []

    df_with_indicators = IndicatorService.calculate_indicators(df)
    ta_summary = IndicatorService.generate_signals(
        ticker,
        df_with_indicators,
        weekly_df,
        market_context,
        strategy_stats=strategy_stats
    )
    ai_prediction = await ai_service.predict_stock_outcome(ticker, ta_summary)

    confidence_map = {"LOW": 0.35, "MEDIUM": 0.6, "HIGH": 0.8, "EXTREME": 0.95}
    conviction = ai_prediction.get("conviction", "LOW")

    risk_warnings = ta_summary.get("risk_warnings", [])
    risk_level = "MEDIUM"
    if len(risk_warnings) >= 5:
        risk_level = "HIGH"
    elif len(risk_warnings) <= 1:
        risk_level = "LOW"

    return {
        "ticker": ticker,
        "price": ta_summary.get("last_price", 0),
        "currency_symbol": ta_summary.get("currency_symbol", "$"),
        "recommendation": ta_summary.get("recommendation", "WAIT"),
        "verdict": ai_prediction.get("prediction", "Stability (Hold)"),
        "final_score": ai_prediction.get("final_score", ta_summary.get("composite_score", 50)),
        "confidence": round(confidence_map.get(conviction, 0.35), 2),
        "conviction": conviction,
        "probability": ai_prediction.get("probability", "50.0%"),
        "regime": ta_summary.get("regime", {}),
        "breakout": ta_summary.get("breakout", {}),
        "trade": ta_summary.get("trade", {}),
        "signals": ta_summary.get("signals", []),
        "probabilities": ta_summary.get("probabilities", {}),
        "risk": {
            "level": risk_level,
            "warnings": risk_warnings,
            "capital_safety_score": ta_summary.get("capital_safety_score", 0),
            "position_size": ta_summary.get("position_size", {}),
            "expected_value": ta_summary.get("expected_value", {}),
        },
        "ai": {
            "sentiment": ai_prediction.get("ai_sentiment", "Neutral"),
            "insight": ai_prediction.get("ai_insight", ""),
            "confidence": ai_prediction.get("ai_confidence", "Low"),
            "key_risk": ai_prediction.get("key_risk", ""),
            "sources": ai_prediction.get("sources", []),
            "invalidation": ai_prediction.get("invalidation", ""),
        },
        "ta_summary": ta_summary,
        "ai_prediction": ai_prediction,
    }

# Predefined Global Tickers for Scanner
GLOBAL_TICKERS = [
    # ──── USA (Top 30) ────
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "JPM", "V", "UNH", "MA", "HD", "PG", "JNJ", "COST", "ABBV",
    "CRM", "MRK", "NFLX", "AMD", "PEP", "KO", "ADBE", "CSCO",
    "DIS", "INTC", "BA", "NKE", "PYPL",
    # ──── India: Nifty 50 (Complete) ────
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BAJFINANCE.NS", "BHARTIARTL.NS",
    "LT.NS", "KOTAKBANK.NS", "HCLTECH.NS", "ASIANPAINT.NS", "AXISBANK.NS",
    "MARUTI.NS", "TITAN.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "WIPRO.NS",
    "TATAMOTORS.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "TATASTEEL.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "BAJAJ-AUTO.NS",
    "BAJAJFINSV.NS", "BEL.NS", "BPCL.NS", "BRITANNIA.NS", "CIPLA.NS",
    "COALINDIA.NS", "DIVISLAB.NS", "DRREDDY.NS", "EICHERMOT.NS",
    "GRASIM.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS",
    "INDUSINDBK.NS", "JSWSTEEL.NS", "M&M.NS", "NESTLEIND.NS",
    "SBILIFE.NS", "SHRIRAMFIN.NS", "TATACONSUM.NS", "TECHM.NS", "TRENT.NS",
    # ──── India: Popular Mid & Small Caps ────
    "ZOMATO.NS", "PAYTM.NS", "NYKAA.NS", "POLICYBZR.NS", "DMART.NS",
    "PIDILITIND.NS", "HAVELLS.NS", "GODREJCP.NS", "DABUR.NS", "BERGEPAINT.NS",
    "IDFCFIRSTB.NS", "BANKBARODA.NS", "PNB.NS", "CANBK.NS", "UNIONBANK.NS",
    "IRCTC.NS", "IRFC.NS", "RECLTD.NS", "PFC.NS", "NHPC.NS",
    "ADANIGREEN.NS", "ADANIPOWER.NS", "TATAPOWER.NS", "TORNTPOWER.NS",
    "HDFCAMC.NS", "ICICIPRULI.NS", "MUTHOOTFIN.NS", "CHOLAFIN.NS",
    "LTIM.NS", "PERSISTENT.NS", "COFORGE.NS", "MPHASIS.NS",
    "INDIGO.NS", "TATAELXSI.NS", "DIXON.NS", "VOLTAS.NS",
    "VEDL.NS", "HINDZINC.NS", "JINDALSTEL.NS", "SAIL.NS",
    "MANKIND.NS", "IPCALAB.NS", "LAURUSLABS.NS", "BIOCON.NS",
    "DLF.NS", "OBEROIRLTY.NS", "GODREJPROP.NS", "PRESTIGE.NS",
    # ──── UK (Top 10) ────
    "AZN.L", "SHEL.L", "HSBA.L", "ULVR.L", "BP.L",
    "GSK.L", "RIO.L", "DGE.L", "BATS.L", "LSEG.L",
    # ──── Japan (Top 10) ────
    "7203.T", "6758.T", "9984.T", "8306.T", "6861.T",
    "7267.T", "4063.T", "9432.T", "6501.T", "6902.T",
    # ──── Germany (Top 5) ────
    "SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "BAS.DE",
    # ──── Hong Kong (Top 5) ────
    "9988.HK", "0700.HK", "1299.HK", "0005.HK", "2318.HK",
    # ──── Australia (Top 5) ────
    "BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX",
]

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/stock/{ticker}")
async def get_stock_prediction(ticker: str):
    try:
        payload = await _build_analysis_payload(ticker)
        ta_summary = payload["ta_summary"]
        
        # Log prediction for legacy systems
        FeedbackService.log_prediction(ticker, ta_summary.get('last_price', 0), ta_summary)

        return {
            "ticker": ticker,
            "ta_summary": ta_summary,
            "ai_prediction": payload["ai_prediction"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analysis/{ticker}")
async def get_analysis(ticker: str):
    """Frontend-friendly analysis endpoint with normalized risk/confidence fields."""
    try:
        return await _build_analysis_payload(ticker)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scan")
async def scan_global_markets():
    """Scan all predefined global tickers and return their signals."""
    
    # Phase 24: Pre-fetch stats for efficient scanning
    portfolio = TradeTrackerService.get_portfolio()
    strategy_stats = portfolio.get('strategy_stats', [])

    async def process_ticker(ticker):
        try:
            df = StockService.get_stock_data(ticker)
            if not df.empty:
                df_with_ind = IndicatorService.calculate_indicators(df)
                ta_summary = IndicatorService.generate_signals(ticker, df_with_ind, strategy_stats=strategy_stats)
                regime = ta_summary.get('regime', {})
                breakout = ta_summary.get('breakout', {})
                quality = ta_summary.get('signal_quality', {})
                momentum = ta_summary.get('momentum', {})
                vol = ta_summary.get('volume_intel', {})
                
                return {
                    "ticker": ticker,
                    "recommendation": ta_summary.get('recommendation', 'HOLD'),
                    "composite_score": ta_summary.get('composite_score', 50),
                    "rsi": ta_summary.get('rsi', 0),
                    "price": ta_summary.get('last_price', 0),
                    "price_change_pct": ta_summary.get('price_change_pct', 0),
                    "signals": ta_summary.get('signals', []),
                    "regime": regime.get('regime', 'SIDEWAYS'),
                    "capital_safety_score": ta_summary.get('capital_safety_score', 0.0),
                    "capital_saved_formatted": ta_summary.get('capital_saved_formatted', '0.00R'),
                    "final_score": ta_summary.get('composite_score', 50),

                    "breakout_status": breakout.get('status', 'NONE'),
                    "signal_tier": quality.get('tier', 'C'),
                    "signal_label": quality.get('label', ''),
                    "momentum_accel": momentum.get('acceleration', 'STEADY'),
                    "smart_money": vol.get('smart_money'),
                }
        except Exception as e:
            print(f"Error processing {ticker} in /scan: {e}")
        return None

    tasks = [process_ticker(ticker) for ticker in GLOBAL_TICKERS]
    results = await asyncio.gather(*tasks)

    valid = [r for r in results if r]
    valid.sort(key=lambda x: x.get('composite_score', 50), reverse=True)
    return valid

@app.post("/trade/create")
async def create_trade(trade_data: Dict[str, Any]):
    """Phase 24: Execute a physical trade and track capital allocation."""
    res = TradeTrackerService.create_physical_trade(
        ticker=trade_data.get('ticker'),
        strategy=trade_data.get('strategy'),
        entry=trade_data.get('entry'),
        stop=trade_data.get('stop_loss'),
        target=trade_data.get('target')
    )
    if not res:
        raise HTTPException(status_code=400, detail="Invalid trade parameters or insufficient capital/risk")
    return res

@app.post("/update_trades")
def trigger_trade_tracker():
    """Scans and updates PENDING sqlite trades based on live outcome price action."""
    # Run legacy reconciler for predictions table
    TradeTrackerService.reconcile_pending_trades()
    # Run institutional settlement for trades table
    return TradeTrackerService.settle_physical_trades()

@app.get("/portfolio")
def get_portfolio():
    """Returns structured SQLite trades and live price-mark-to-market."""
    return TradeTrackerService.get_portfolio()


@app.get("/backtest/{ticker}")
def get_backtest(ticker: str):
    """Run historical strategy backtest for a ticker."""
    result = BacktestService.run_backtest(ticker)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/performance")
def get_performance():
    """Portfolio-level performance summary for dashboard KPI cards."""
    portfolio = TradeTrackerService.get_portfolio()
    if not isinstance(portfolio, dict) or portfolio.get("error"):
        raise HTTPException(status_code=500, detail=portfolio.get("error", "Unable to load portfolio"))

    summary = portfolio.get("summary", {})
    strategy_stats = portfolio.get("strategy_stats", [])
    closed = portfolio.get("closed_trades", [])

    best_strategy = None
    if strategy_stats:
        best_strategy = max(strategy_stats, key=lambda s: float(s.get("win_rate", 0)))

    return {
        "summary": {
            "total_equity_r": summary.get("total_equity_r", 0),
            "active_risk_r": summary.get("active_risk_r", 0),
            "win_rate": summary.get("win_rate", 0),
            "closed_trades": len(closed),
            "active_trades": len(portfolio.get("active_trades", [])),
        },
        "best_strategy": best_strategy,
        "strategy_stats": strategy_stats,
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
