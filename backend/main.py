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

app = FastAPI(title="AI Global Stock Predictor API")

# Enable CORS for React Native / Expo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_service = AIService()

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
        df = StockService.get_stock_data(ticker)
        if df.empty:
            raise HTTPException(status_code=404, detail="Stock not found or no data")

        df_with_indicators = IndicatorService.calculate_indicators(df)
        ta_summary = IndicatorService.generate_signals(df_with_indicators)
        prediction = await ai_service.predict_stock_outcome(ticker, ta_summary)
        
        return {
            "ticker": ticker,
            "ta_summary": ta_summary,
            "ai_prediction": prediction
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scan")
async def scan_global_markets():
    """Scan all predefined global tickers and return their signals."""
    
    async def process_ticker(ticker):
        try:
            df = StockService.get_stock_data(ticker)
            if not df.empty:
                df_with_ind = IndicatorService.calculate_indicators(df)
                ta_summary = IndicatorService.generate_signals(df_with_ind)
                return {
                    "ticker": ticker,
                    "recommendation": ta_summary.get('recommendation', 'HOLD'),
                    "composite_score": ta_summary.get('composite_score', 50),
                    "rsi": ta_summary.get('rsi', 0),
                    "price": ta_summary.get('last_price', 0),
                    "price_change_pct": ta_summary.get('price_change_pct', 0),
                    "signals": ta_summary.get('signals', []),
                }
        except:
            pass
        return None

    tasks = [process_ticker(ticker) for ticker in GLOBAL_TICKERS]
    results = await asyncio.gather(*tasks)

    valid = [r for r in results if r]
    # Sort by composite score descending (best opportunities first)
    valid.sort(key=lambda x: x.get('composite_score', 50), reverse=True)
    return valid

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
