"""
Data scrapers module
"""

from app.scrapers.arxiv_scraper import ArxivScraper
from app.scrapers.github_scraper import GitHubScraper
from app.scrapers.reddit_scraper import RedditScraper

__all__ = ['ArxivScraper', 'GitHubScraper', 'RedditScraper']