"""
GitHub trending repositories scraper
"""

import httpx
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.scrapers.base_scraper import BaseScraper
from app.core.config import settings
from app.core.logging import log


class GitHubScraper(BaseScraper):
    """
    Scraper for GitHub trending ML repositories
    """
    
    def __init__(self):
        super().__init__("GitHub")
        self.base_url = "https://api.github.com"
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'ML-Career-Pulse'
        }
        if settings.GITHUB_TOKEN:
            self.headers['Authorization'] = f'token {settings.GITHUB_TOKEN}'
    
    async def fetch_data(self, query: str = "machine learning", stars_min: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch trending ML repositories from GitHub
        
        Args:
            query: Search query
            stars_min: Minimum stars threshold
            
        Returns:
            List of repository data
        """
        repos = []
        
        try:
            # Calculate date for trending (last 7 days)
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Build search query
            search_query = f"{query} stars:>={stars_min} created:>{week_ago}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/search/repositories",
                    headers=self.headers,
                    params={
                        'q': search_query,
                        'sort': 'stars',
                        'order': 'desc',
                        'per_page': 50
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    repos = data.get('items', [])
                    log.info(f"Fetched {len(repos)} repositories from GitHub")
                else:
                    log.error(f"GitHub API error: {response.status_code}")
        
        except Exception as e:
            log.error(f"Error fetching GitHub data: {str(e)}")
        
        return repos
    
    async def process_data(self, raw_data: List[Dict]) -> List[Dict]:
        """
        Process raw repository data
        
        Args:
            raw_data: Raw repository data
            
        Returns:
            Processed repository data
        """
        processed = []
        
        for repo in raw_data:
            # Extract description and topics for skill detection
            text = f"{repo.get('name', '')} {repo.get('description', '')} {' '.join(repo.get('topics', []))}"
            skills = self.extract_skills(text)
            
            processed.append({
                'id': str(repo['id']),
                'name': repo['name'],
                'full_name': repo['full_name'],
                'description': repo.get('description', ''),
                'stars': repo['stargazers_count'],
                'forks': repo['forks_count'],
                'language': repo.get('language', 'Unknown'),
                'topics': repo.get('topics', []),
                'url': repo['html_url'],
                'created_at': repo['created_at'],
                'updated_at': repo['updated_at'],
                'extracted_skills': skills
            })
        
        return processed