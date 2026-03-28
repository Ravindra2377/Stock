import yfinance as yf
import pandas as pd
from typing import List, Dict, Any

class StockService:
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
