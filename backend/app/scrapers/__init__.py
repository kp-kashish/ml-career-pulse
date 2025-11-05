"""
Scrapers package
"""

from app.scrapers.base_scraper import BaseScraper
from app.scrapers.arxiv_scraper import ArxivScraper
from app.scrapers.github_scraper import GitHubScraper
from app.scrapers.reddit_scraper import RedditScraper

__all__ = ['BaseScraper', 'ArxivScraper', 'GitHubScraper', 'RedditScraper']