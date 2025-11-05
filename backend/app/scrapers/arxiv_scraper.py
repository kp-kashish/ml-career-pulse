"""
ArXiv research papers scraper with LLM extraction
"""

import arxiv
from typing import List, Dict, Any
from datetime import datetime, timedelta
import hashlib
from app.scrapers.base_scraper import BaseScraper
from app.core.logging import log


class ArxivScraper(BaseScraper):
    """
    Scraper for fetching ML/AI papers from ArXiv with intelligent skill extraction
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
            log.info(f"Starting ArXiv fetch: max_results={max_results}, days_back={days_back}")
            
            # Build query for multiple categories
            query = ' OR '.join([f'cat:{cat}' for cat in self.categories])
            log.debug(f"ArXiv query string: {query}")
            
            # Create search - fetch more than needed to account for date filtering
            search = arxiv.Search(
                query=query,
                max_results=max_results * 2,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days_back)
            log.info(f"Filtering papers published after: {cutoff_date.isoformat()}")
            
            # Fetch and filter papers
            count = 0
            for result in self.client.results(search):
                # Handle timezone-aware datetime comparison
                result_date = result.published
                compare_cutoff = cutoff_date
                
                if result_date.tzinfo is not None:
                    compare_cutoff = cutoff_date.replace(tzinfo=result_date.tzinfo)
                
                # Check if paper is within date range
                if result_date < compare_cutoff:
                    log.debug(f"Paper outside date range: {result.title[:50]} ({result_date})")
                    continue
                
                # Stop if we have enough papers
                if count >= max_results:
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
                count += 1
                log.debug(f"Added paper {count}/{max_results}: {result.title[:50]}")
            
            log.info(f"ArXiv fetch complete: {len(papers)} papers retrieved")
            
        except Exception as e:
            log.error(f"Error fetching ArXiv papers: {str(e)}")
            import traceback
            log.error(traceback.format_exc())
        
        return papers
    
    async def process_data(self, raw_data: List[Dict]) -> List[Dict]:
        """
        Process raw paper data with LLM-based skill extraction
        Includes rate limiting and progress tracking
        """
        from app.services.skill_extractor import SkillExtractor
        import asyncio
        
        if not raw_data:
            log.warning("No papers to process")
            return []
        
        log.info(f"Processing {len(raw_data)} papers with LLM extraction")
        
        extractor = SkillExtractor()
        processed = []
        
        # Estimate processing time
        if extractor.model:
            estimated_time = len(raw_data) * extractor.request_delay
            log.info(f"Estimated processing time: {estimated_time:.0f}s (~{estimated_time/60:.1f} minutes)")
        else:
            log.warning("LLM not available - using basic keyword extraction only")
        
        for i, paper in enumerate(raw_data, 1):
            try:
                paper_id = hashlib.md5(paper['id'].encode()).hexdigest()
                
                # Basic keyword extraction (fast, always available)
                text = f"{paper['title']} {paper['abstract']}"
                basic_skills = self.extract_skills(text)
                
                # LLM-based detailed extraction (slower, more accurate)
                detailed_skills = await extractor.extract_from_paper(
                    paper['title'],
                    paper['abstract']
                )
                
                # Format publication date
                pub_date = paper['published_date']
                if hasattr(pub_date, 'isoformat'):
                    pub_date_str = pub_date.isoformat()
                else:
                    pub_date_str = str(pub_date)
                
                processed.append({
                    'id': paper_id,
                    'title': paper['title'],
                    'abstract': paper['abstract'][:500],
                    'authors': ', '.join(paper['authors'][:5]),
                    'published_date': pub_date_str,
                    'categories': paper['categories'],
                    'url': paper['pdf_url'],
                    'source': 'arxiv',
                    'extracted_skills': basic_skills,
                    'detailed_skills': detailed_skills
                })
                
                # Progress logging every 10 items
                if i % 10 == 0 or i == len(raw_data):
                    log.info(f"Processed {i}/{len(raw_data)} papers ({i*100//len(raw_data)}%)")
                
            except Exception as e:
                log.error(f"Error processing paper {i}: {str(e)}")
                continue
        
        log.info(f"Successfully processed {len(processed)} papers with detailed extraction")
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
            # Count basic skills
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