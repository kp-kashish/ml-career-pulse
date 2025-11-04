"""
ArXiv research papers scraper
"""

import arxiv
from typing import List, Dict, Any
from datetime import datetime, timedelta
import hashlib
from app.scrapers.base_scraper import BaseScraper
from app.core.logging import log


class ArxivScraper(BaseScraper):
    """
    Scraper for fetching ML/AI papers from ArXiv
    """
    
    def __init__(self):
        super().__init__("ArXiv")
        self.client = arxiv.Client()
        self.categories = ['cs.LG', 'cs.AI', 'stat.ML', 'cs.CV', 'cs.CL', 'cs.NE']
    
    async def fetch_data(self, max_results: int = 50, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Fetch recent papers from ArXiv
        
        Args:
            max_results: Maximum number of papers to fetch
            days_back: Number of days to look back
            
        Returns:
            List of paper data
        """
        papers = []
        
        try:
            # Build query for multiple categories
            query = ' OR '.join([f'cat:{cat}' for cat in self.categories])
            
            # Create search
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            # Fetch papers
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for result in self.client.results(search):
                if result.published < cutoff_date:
                    break
                    
                papers.append({
                    'id': result.entry_id,
                    'title': result.title,
                    'abstract': result.summary,
                    'authors': [author.name for author in result.authors],
                    'published_date': result.published,
                    'categories': result.categories,
                    'pdf_url': result.pdf_url,
                    'comment': result.comment
                })
            
            log.info(f"Fetched {len(papers)} papers from ArXiv")
            
        except Exception as e:
            log.error(f"Error fetching ArXiv papers: {str(e)}")
        
        return papers
    
    async def process_data(self, raw_data: List[Dict]) -> List[Dict]:
        """
        Process raw paper data
        
        Args:
            raw_data: Raw paper data
            
        Returns:
            Processed paper data
        """
        processed = []
        
        for paper in raw_data:
            # Generate unique ID
            paper_id = hashlib.md5(paper['id'].encode()).hexdigest()
            
            # Extract skills from title and abstract
            text = f"{paper['title']} {paper['abstract']}"
            skills = self.extract_skills(text)
            
            processed.append({
                'id': paper_id,
                'title': paper['title'],
                'abstract': paper['abstract'][:500],  # Truncate for storage
                'authors': ', '.join(paper['authors'][:5]),  # First 5 authors
                'published_date': paper['published_date'].isoformat(),
                'categories': paper['categories'],
                'url': paper['pdf_url'],
                'source': 'arxiv',
                'extracted_skills': skills,
                'skill_count': len(skills)
            })
        
        return processed
    
    async def get_trending_topics(self, papers: List[Dict]) -> Dict[str, Any]:
        """
        Analyze papers to find trending topics
        
        Args:
            papers: Processed paper data
            
        Returns:
            Trending topics analysis
        """
        skill_counts = {}
        category_counts = {}
        
        for paper in papers:
            # Count skills
            for skill in paper.get('extracted_skills', []):
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
            
            # Count categories
            for category in paper.get('categories', []):
                category_counts[category] = category_counts.get(category, 0) + 1
        
        # Sort by frequency
        trending_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
        trending_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'trending_skills': trending_skills[:10],
            'trending_categories': trending_categories[:5],
            'total_papers': len(papers),
            'analysis_date': datetime.now().isoformat()
        }