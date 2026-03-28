import os
from newsapi import NewsApiClient
from typing import List, Dict, Any, Optional

class NewsService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("NEWS_API_KEY")
        if self.api_key:
            self.newsapi = NewsApiClient(api_key=self.api_key)
        else:
            self.newsapi = None

    def get_top_headlines(self, category: str = "business", country: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch top headlines for a specific category or country."""
        if not self.newsapi:
            return []
        
        try:
            headlines = self.newsapi.get_top_headlines(category=category, country=country, language='en')
            return headlines.get('articles', [])
        except Exception as e:
            print(f"Error fetching news: {e}")
            return []

    def get_everything(self, query: str) -> List[Dict[str, Any]]:
        """Search for news related to a specific query (e.g. 'Federal Reserve', 'Crude Oil')."""
        if not self.newsapi:
            return []
            
        try:
            articles = self.newsapi.get_everything(q=query, language='en', sort_by='relevancy')
            return articles.get('articles', [])[:10] # Return top 10
        except Exception as e:
            print(f"Error fetching news for query {query}: {e}")
            return []
