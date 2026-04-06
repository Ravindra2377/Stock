import yfinance as yf
import pandas as pd
from typing import List, Dict, Any
import time

class StockService:
    _market_cache = {"data": None, "timestamp": 0}

    @classmethod
    def get_market_context(cls) -> Dict[str, Any]:
        """Fetch NIFTY 50 trend and daily change, cached for 15 mins."""
        now = time.time()
        if cls._market_cache["data"] and (now - cls._market_cache["timestamp"] < 900):
            return cls._market_cache["data"]
            
        try:
            nifty = yf.Ticker("^NSEI")
            # Get 2 days for daily change calculation
            df = nifty.history(period="5d")
            if len(df) < 2:
                result = {"trend": "UNKNOWN", "nifty_daily_change": 0.0}
            else:
                last_two = df.tail(2)
                close = float(last_two['Close'].iloc[-1])
                prev_close = float(last_two['Close'].iloc[-2])
                daily_change = ((close - prev_close) / prev_close) * 100.0
                
                sma20 = float(df['Close'].rolling(20).mean().iloc[-1]) if len(df) >= 20 else close
                result = {
                    "trend": "BULLISH" if close > sma20 else "BEARISH",
                    "nifty_daily_change": round(daily_change, 2)
                }
            cls._market_cache = {"data": result, "timestamp": now}
            return result
        except:
            return {"trend": "UNKNOWN", "nifty_daily_change": 0.0}

    @staticmethod
    def get_stock_data(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """Fetch historical stock data from Yahoo Finance."""
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        return df

    @staticmethod
    def get_live_price(ticker: str) -> float:
        """Fetch the latest price for a stock."""
        stock = yf.Ticker(ticker)
        # Use fast_info for basic data if available, or just the last close
        try:
            return stock.fast_info['lastPrice']
        except:
            df = stock.history(period="1d")
            if not df.empty:
                return df['Close'].iloc[-1]
            return 0.0

    @staticmethod
    def get_company_info(ticker: str) -> Dict[str, Any]:
        """Fetch company metadata."""
        stock = yf.Ticker(ticker)
        return stock.info

    @staticmethod
    def get_weekly_data(ticker: str, period: str = "2y") -> pd.DataFrame:
        """Fetch weekly timeframe data for multi-timeframe analysis."""
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval="1wk")
        return df
