"""
GitHub trending repositories scraper with LLM extraction
"""

import httpx
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.scrapers.base_scraper import BaseScraper
from app.core.config import settings
from app.core.logging import log


class GitHubScraper(BaseScraper):
    """
    Scraper for GitHub trending ML repositories with intelligent skill extraction
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
            log.info("GitHub scraper initialized with authentication token")
        else:
            log.warning("GitHub scraper initialized without token - rate limits will be lower")
    
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
            log.info(f"Fetching GitHub repos: query='{query}', stars_min={stars_min}")
            
            # Calculate date for trending (last 7 days)
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Build search query
            search_query = f"{query} stars:>={stars_min} created:>{week_ago}"
            log.debug(f"GitHub search query: {search_query}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/search/repositories",
                    headers=self.headers,
                    params={
                        'q': search_query,
                        'sort': 'stars',
                        'order': 'desc',
                        'per_page': 50
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    repos = data.get('items', [])
                    log.info(f"Fetched {len(repos)} repositories from GitHub")
                elif response.status_code == 403:
                    log.error("GitHub API rate limit exceeded - add GITHUB_TOKEN to .env")
                else:
                    log.error(f"GitHub API error: {response.status_code}")
        
        except Exception as e:
            log.error(f"Error fetching GitHub data: {str(e)}")
            import traceback
            log.error(traceback.format_exc())
        
        return repos
    
    async def process_data(self, raw_data: List[Dict]) -> List[Dict]:
        """
        Process raw repository data with LLM extraction
        """
        from app.services.skill_extractor import SkillExtractor
        
        if not raw_data:
            log.warning("No repos to process")
            return []
        
        log.info(f"Processing {len(raw_data)} repos with LLM extraction")
        
        extractor = SkillExtractor()
        processed = []
        
        # Estimate processing time
        if extractor.model:
            estimated_time = len(raw_data) * extractor.request_delay
            log.info(f"Estimated processing time: {estimated_time:.0f}s (~{estimated_time/60:.1f} minutes)")
        
        for i, repo in enumerate(raw_data, 1):
            try:
                # Basic keyword extraction
                text = f"{repo.get('name', '')} {repo.get('description', '')} {' '.join(repo.get('topics', []))}"
                basic_skills = self.extract_skills(text)
                
                # LLM-based detailed extraction
                detailed_skills = await extractor.extract_from_repo(
                    repo['name'],
                    repo.get('description', ''),
                    repo.get('topics', [])
                )
                
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
                    'extracted_skills': basic_skills,
                    'detailed_skills': detailed_skills
                })
                
                # Progress logging
                if i % 10 == 0 or i == len(raw_data):
                    log.info(f"Processed {i}/{len(raw_data)} repos ({i*100//len(raw_data)}%)")
                
            except Exception as e:
                log.error(f"Error processing repo {i}: {str(e)}")
                continue
        
        log.info(f"Successfully processed {len(processed)} repos with detailed extraction")
        return processed