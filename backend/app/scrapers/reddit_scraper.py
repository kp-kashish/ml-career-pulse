"""
Reddit ML community scraper
"""

import praw
from typing import List, Dict, Any
from datetime import datetime
from app.scrapers.base_scraper import BaseScraper
from app.core.config import settings
from app.core.logging import log


class RedditScraper(BaseScraper):
    """
    Scraper for Reddit ML communities
    """
    
    def __init__(self):
        super().__init__("Reddit")
        self.subreddits = ['MachineLearning', 'deeplearning', 'artificial', 'LocalLLaMA']
        self.reddit = None
        
        if settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET:
            self.reddit = praw.Reddit(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent='ML-Career-Pulse/1.0'
            )
    
    async def fetch_data(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch hot posts from ML subreddits
        
        Args:
            limit: Number of posts per subreddit
            
        Returns:
            List of post data
        """
        posts = []
        
        if not self.reddit:
            log.warning("Reddit API not configured")
            return posts
        
        try:
            for subreddit_name in self.subreddits:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Get hot posts
                for post in subreddit.hot(limit=limit):
                    posts.append({
                        'id': post.id,
                        'title': post.title,
                        'selftext': post.selftext,
                        'subreddit': subreddit_name,
                        'score': post.score,
                        'num_comments': post.num_comments,
                        'created_utc': post.created_utc,
                        'url': f"https://reddit.com{post.permalink}"
                    })
            
            log.info(f"Fetched {len(posts)} posts from Reddit")
            
        except Exception as e:
            log.error(f"Error fetching Reddit data: {str(e)}")
        
        return posts
    
    async def process_data(self, raw_data: List[Dict]) -> List[Dict]:
        """
        Process raw Reddit post data
        
        Args:
            raw_data: Raw post data
            
        Returns:
            Processed post data
        """
        processed = []
        
        for post in raw_data:
            # Extract skills from title and content
            text = f"{post['title']} {post.get('selftext', '')}"
            skills = self.extract_skills(text)
            
            processed.append({
                'id': post['id'],
                'title': post['title'],
                'content': post.get('selftext', '')[:500],  # Truncate
                'subreddit': post['subreddit'],
                'score': post['score'],
                'comments': post['num_comments'],
                'url': post['url'],
                'created_at': datetime.fromtimestamp(post['created_utc']).isoformat(),
                'extracted_skills': skills,
                'engagement_score': post['score'] + (post['num_comments'] * 2)
            })
        
        return processed