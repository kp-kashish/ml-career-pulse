"""
Adzuna Job API Scraper for ML Career Pulse
Uses official Adzuna API for reliable job posting collection
"""

import asyncio
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from .base_scraper import BaseScraper


class AdzunaJobScraper(BaseScraper):
    """Scraper for ML job postings using Adzuna API"""
    
    def __init__(self, app_id: str, app_key: str):
        super().__init__("Adzuna Jobs")
        self.app_id = app_id
        self.app_key = app_key
        self.base_url = "https://api.adzuna.com/v1/api/jobs"
    
    async def fetch_data(self, **kwargs) -> List[Dict]:
        """Fetch job postings from Adzuna API"""
        query = kwargs.get('query', 'machine learning engineer')
        country = kwargs.get('country', 'us')  # us, gb, ca, au, etc.
        max_results = kwargs.get('max_results', 50)
        
        return await self.collect_jobs(query, country, max_results)
    
    async def process_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Process raw job data into standardized format"""
        processed_jobs = []
        
        for job in raw_data:
            try:
                processed_job = {
                    'id': job.get('id', ''),
                    'title': job.get('title', ''),
                    'company': job.get('company', {}).get('display_name', 'Unknown'),
                    'location': job.get('location', {}).get('display_name', 'Remote'),
                    'description': job.get('description', ''),
                    'salary': self._format_salary(job),
                    'url': job.get('redirect_url', ''),
                    'date_posted': job.get('created', 'Recently'),
                    'source': 'Adzuna',
                    'collected_at': datetime.utcnow().isoformat(),
                    'extracted_skills': self.extract_skills(
                        f"{job.get('title', '')} {job.get('description', '')}"
                    )
                }
                processed_jobs.append(processed_job)
            except Exception as e:
                logger.warning(f"Error processing Adzuna job: {e}")
                continue
        
        return processed_jobs
    
    def _format_salary(self, job: Dict) -> Optional[str]:
        """Format salary information"""
        salary_min = job.get('salary_min')
        salary_max = job.get('salary_max')
        
        if salary_min and salary_max:
            return f"${salary_min:,.0f} - ${salary_max:,.0f}"
        elif salary_min:
            return f"${salary_min:,.0f}+"
        elif salary_max:
            return f"Up to ${salary_max:,.0f}"
        return None
    
    async def collect_jobs(
        self,
        query: str = "machine learning engineer",
        country: str = "us",
        max_results: int = 50
    ) -> List[Dict]:
        """
        Collect job postings from Adzuna API
        
        Args:
            query: Job search query
            country: Country code (us, gb, ca, au, de, fr, etc.)
            max_results: Maximum number of jobs to collect
            
        Returns:
            List of job posting dictionaries
        """
        logger.info(f"Starting Adzuna API collection: query='{query}', country='{country}', max={max_results}")
        
        jobs = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # Calculate number of pages needed (Adzuna returns 50 results per page max)
                results_per_page = min(50, max_results)
                num_pages = (max_results // results_per_page) + (1 if max_results % results_per_page else 0)
                num_pages = min(num_pages, 5)  # Limit to 5 pages (250 jobs max)
                
                for page in range(1, num_pages + 1):
                    if len(jobs) >= max_results:
                        break
                    
                    url = f"{self.base_url}/{country}/search/{page}"
                    
                    params = {
                        'app_id': self.app_id,
                        'app_key': self.app_key,
                        'what': query,
                        'results_per_page': results_per_page,
                        'content-type': 'application/json',
                        'sort_by': 'date',  # Sort by most recent
                        'category': 'it-jobs'  # Focus on IT/tech jobs
                    }
                    
                    logger.info(f"Requesting: {url}")
                    logger.info(f"With params: what={query}, results_per_page={results_per_page}, app_id={self.app_id[:4]}...")
                    
                    try:
                        async with session.get(url, params=params) as response:
                            response_text = await response.text()
                            
                            if response.status != 200:
                                logger.error(f"Adzuna API error - Status: {response.status}")
                                logger.error(f"URL: {url}")
                                logger.error(f"Response: {response_text[:500]}")
                                continue
                            
                            data = await response.json()
                            logger.info(f"API Response keys: {data.keys()}")
                            
                            # Extract job results
                            results = data.get('results', [])
                            
                            if not results:
                                logger.warning(f"No results found at page {page}")
                                logger.info(f"Response data: {data}")
                                break
                            
                            jobs.extend(results)
                            logger.info(f"Collected {len(results)} jobs from page {page}")
                            
                            if len(jobs) >= max_results:
                                jobs = jobs[:max_results]
                                break
                            
                        # Be respectful with rate limiting
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error fetching Adzuna page {page}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error in Adzuna API collection: {e}")
            
        logger.info(f"Collected {len(jobs)} total jobs from Adzuna")
        return jobs
    
    async def get_job_details(self, job_id: str, country: str = "us") -> Optional[Dict]:
        """
        Get detailed information about a specific job
        
        Args:
            job_id: Adzuna job ID
            country: Country code
            
        Returns:
            Detailed job information
        """
        url = f"{self.base_url}/{country}/details/{job_id}"
        
        params = {
            'app_id': self.app_id,
            'app_key': self.app_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"Failed to get job details for {job_id}: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting job details: {e}")
            return None


# Example usage
async def main():
    # Initialize with your credentials
    app_id = "9024125b"
    app_key = "13497e520dff5cffd5155166f7c761209"
    
    scraper = AdzunaJobScraper(app_id, app_key)
    
    # Collect jobs
    result = await scraper.run(
        query="machine learning engineer",
        country="us",
        max_results=20
    )
    
    print(f"\nCollected {result['item_count']} jobs from Adzuna")
    
    if result['data']:
        print(f"\nSample job:")
        sample = result['data'][0]
        print(f"Title: {sample['title']}")
        print(f"Company: {sample['company']}")
        print(f"Location: {sample['location']}")
        print(f"Salary: {sample['salary']}")
        print(f"Skills: {', '.join(sample['extracted_skills'][:5])}")


if __name__ == "__main__":
    asyncio.run(main())