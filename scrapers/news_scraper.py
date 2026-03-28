"""
Live Cricket News & Sentiment Scraper.

Scrapes latest IPL news from multiple sources and performs
sentiment analysis to gauge team/player confidence levels.
"""

import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from utils.logger import logger


class CricketNewsScraper:
    """Scrape and analyze live cricket news for IPL predictions."""

    SOURCES = {
        "espncricinfo": {
            "url": "https://www.espncricinfo.com/cricket-news",
            "selector": "article",
        },
        "cricbuzz": {
            "url": "https://www.cricbuzz.com/cricket-news",
            "selector": ".cb-nws-lst",
        },
    }

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    # Sentiment keywords for cricket context
    POSITIVE_KEYWORDS = [
        "dominant", "brilliant", "superb", "stunning", "magnificent",
        "record", "century", "fifer", "unbeaten", "comeback", "clinical",
        "consistent", "explosive", "match-winner", "in-form", "peak",
        "confident", "strong", "powerful", "aggressive", "fearless",
        "win", "victory", "triumph", "champion", "boost", "retain",
    ]

    NEGATIVE_KEYWORDS = [
        "injured", "injury", "ruled out", "doubtful", "struggling",
        "dropped", "poor form", "slump", "collapse", "disappointing",
        "defeat", "lost", "bowled out", "cheap dismissal", "controversy",
        "ban", "suspended", "unfit", "hamstring", "fracture", "torn",
        "miss", "absent", "unavailable", "concern", "worry", "setback",
    ]

    TEAM_KEYWORDS = {
        "Chennai Super Kings": ["CSK", "Chennai", "Super Kings", "Dhoni", "Ruturaj"],
        "Mumbai Indians": ["MI", "Mumbai", "Pandya", "Rohit"],
        "Royal Challengers Bengaluru": ["RCB", "Bengaluru", "Bangalore", "Kohli", "Virat"],
        "Kolkata Knight Riders": ["KKR", "Kolkata", "Knight Riders", "Rahane"],
        "Sunrisers Hyderabad": ["SRH", "Sunrisers", "Hyderabad", "Cummins"],
        "Rajasthan Royals": ["RR", "Rajasthan", "Royals", "Parag"],
        "Delhi Capitals": ["DC", "Delhi", "Capitals", "KL Rahul"],
        "Punjab Kings": ["PBKS", "Punjab", "Kings", "Shreyas"],
        "Lucknow Super Giants": ["LSG", "Lucknow", "Super Giants", "Pant", "Rishabh"],
        "Gujarat Titans": ["GT", "Gujarat", "Titans", "Buttler"],
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._news_cache = {}

    def get_latest_news(self, max_articles: int = 30) -> list[dict]:
        """Fetch latest cricket news from multiple sources."""
        all_news = []

        # Source 1: Cricbuzz
        all_news.extend(self._scrape_cricbuzz(max_articles))

        # Source 2: Google News RSS for IPL
        all_news.extend(self._scrape_google_news_rss(max_articles))

        logger.info(f"Scraped {len(all_news)} news articles")
        return all_news

    def _scrape_cricbuzz(self, max_articles: int) -> list[dict]:
        """Scrape news from Cricbuzz."""
        articles = []
        try:
            resp = self.session.get(
                "https://www.cricbuzz.com/cricket-news",
                timeout=15,
            )
            soup = BeautifulSoup(resp.text, "html.parser")

            for item in soup.select(".cb-nws-hdln-ancr, .cb-nws-lst a")[:max_articles]:
                title = item.get_text(strip=True)
                link = item.get("href", "")
                if title and ("ipl" in title.lower() or any(
                    kw.lower() in title.lower()
                    for team_kws in self.TEAM_KEYWORDS.values()
                    for kw in team_kws
                )):
                    articles.append({
                        "title": title,
                        "source": "cricbuzz",
                        "url": f"https://www.cricbuzz.com{link}" if link.startswith("/") else link,
                        "timestamp": datetime.now().isoformat(),
                    })
        except Exception as e:
            logger.warning(f"Cricbuzz scrape failed: {e}")

        return articles

    def _scrape_google_news_rss(self, max_articles: int) -> list[dict]:
        """Scrape IPL news from Google News RSS feed."""
        articles = []
        try:
            resp = self.session.get(
                "https://news.google.com/rss/search?q=IPL+2026+cricket&hl=en-IN&gl=IN&ceid=IN:en",
                timeout=15,
            )
            soup = BeautifulSoup(resp.text, "xml")

            for item in soup.find_all("item")[:max_articles]:
                title = item.find("title")
                pub_date = item.find("pubDate")
                link = item.find("link")

                if title:
                    articles.append({
                        "title": title.get_text(strip=True),
                        "source": "google_news",
                        "url": link.get_text(strip=True) if link else "",
                        "timestamp": pub_date.get_text(strip=True) if pub_date else datetime.now().isoformat(),
                    })
        except Exception as e:
            logger.warning(f"Google News RSS scrape failed: {e}")

        return articles

    def get_team_news(self, team: str) -> list[dict]:
        """Get news specific to a team."""
        all_news = self.get_latest_news()
        team_kws = self.TEAM_KEYWORDS.get(team, [team])

        return [
            article for article in all_news
            if any(kw.lower() in article["title"].lower() for kw in team_kws)
        ]

    def analyze_sentiment(self, team: str, news: list[dict] = None) -> dict:
        """Analyze sentiment for a team from recent news."""
        if news is None:
            news = self.get_team_news(team)

        if not news:
            return {
                "team": team,
                "sentiment_score": 0.0,  # neutral
                "sentiment_label": "neutral",
                "positive_signals": [],
                "negative_signals": [],
                "news_count": 0,
                "confidence": 0.0,
            }

        positive_signals = []
        negative_signals = []
        total_score = 0.0

        for article in news:
            title = article["title"].lower()

            pos_count = sum(1 for kw in self.POSITIVE_KEYWORDS if kw in title)
            neg_count = sum(1 for kw in self.NEGATIVE_KEYWORDS if kw in title)

            if pos_count > neg_count:
                positive_signals.append(article["title"])
                total_score += (pos_count - neg_count) * 0.15
            elif neg_count > pos_count:
                negative_signals.append(article["title"])
                total_score -= (neg_count - pos_count) * 0.15

        # Normalize score to [-1, 1]
        if news:
            avg_score = max(-1.0, min(1.0, total_score / len(news)))
        else:
            avg_score = 0.0

        # Determine label
        if avg_score > 0.2:
            label = "positive"
        elif avg_score < -0.2:
            label = "negative"
        else:
            label = "neutral"

        return {
            "team": team,
            "sentiment_score": round(avg_score, 3),
            "sentiment_label": label,
            "positive_signals": positive_signals[:5],
            "negative_signals": negative_signals[:5],
            "news_count": len(news),
            "confidence": min(1.0, len(news) / 10),  # More news = more confidence
        }

    def get_match_sentiment(self, team1: str, team2: str) -> dict:
        """Get comparative sentiment analysis for a matchup."""
        all_news = self.get_latest_news()

        t1_news = [
            a for a in all_news
            if any(kw.lower() in a["title"].lower()
                   for kw in self.TEAM_KEYWORDS.get(team1, [team1]))
        ]
        t2_news = [
            a for a in all_news
            if any(kw.lower() in a["title"].lower()
                   for kw in self.TEAM_KEYWORDS.get(team2, [team2]))
        ]

        t1_sentiment = self.analyze_sentiment(team1, t1_news)
        t2_sentiment = self.analyze_sentiment(team2, t2_news)

        # Calculate sentiment advantage
        diff = t1_sentiment["sentiment_score"] - t2_sentiment["sentiment_score"]
        if abs(diff) > 0.3:
            advantage = team1 if diff > 0 else team2
            advantage_level = "strong"
        elif abs(diff) > 0.1:
            advantage = team1 if diff > 0 else team2
            advantage_level = "slight"
        else:
            advantage = "neutral"
            advantage_level = "none"

        # Prediction adjustment based on sentiment (-0.03 to +0.03)
        sentiment_shift = round(max(-0.03, min(0.03, diff * 0.05)), 4)

        return {
            "team1": t1_sentiment,
            "team2": t2_sentiment,
            "sentiment_advantage": advantage,
            "advantage_level": advantage_level,
            "prediction_shift": sentiment_shift,
            "headlines": {
                team1: [a["title"] for a in t1_news[:3]],
                team2: [a["title"] for a in t2_news[:3]],
            },
        }

    def get_injury_news(self) -> list[dict]:
        """Get injury-specific news."""
        all_news = self.get_latest_news()
        injury_keywords = ["injury", "injured", "ruled out", "hamstring", "fracture",
                          "strain", "surgery", "miss", "doubtful", "unfit", "fitness"]

        return [
            article for article in all_news
            if any(kw in article["title"].lower() for kw in injury_keywords)
        ]

    def get_transfer_news(self) -> list[dict]:
        """Get transfer/replacement news."""
        all_news = self.get_latest_news()
        transfer_keywords = ["replacement", "replaced", "traded", "released",
                            "signed", "acquired", "draft", "retained"]

        return [
            article for article in all_news
            if any(kw in article["title"].lower() for kw in transfer_keywords)
        ]
