"""
API endpoints for data scraping
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.logging import log
from app.scrapers.arxiv_scraper import ArxivScraper
from app.scrapers.github_scraper import GitHubScraper
from app.scrapers.reddit_scraper import RedditScraper
from app.models.models import Paper, GitHubRepo, SkillTrend

router = APIRouter()


@router.get("/status")
async def get_scraper_status():
    """Get status of all scrapers"""
    return {
        "scrapers": {
            "arxiv": {"status": "ready", "description": "ArXiv ML papers scraper"},
            "github": {"status": "ready", "description": "GitHub trending repos scraper"},
            "reddit": {"status": "ready", "description": "Reddit ML communities scraper"}
        },
        "last_run": None,
        "next_scheduled": None
    }


@router.post("/arxiv/run")
async def run_arxiv_scraper(
    background_tasks: BackgroundTasks,
    max_results: Optional[int] = 20,
    db: Session = Depends(get_db)
):
    """Run ArXiv scraper"""
    try:
        log.info("Starting ArXiv scraper via API")
        
        scraper = ArxivScraper()
        result = await scraper.run(max_results=max_results)
        
        papers_saved = 0
        for paper_data in result.get('data', []):
            existing = db.query(Paper).filter_by(id=paper_data['id']).first()
            if not existing:
                paper = Paper(
                    id=paper_data['id'],
                    title=paper_data['title'],
                    abstract=paper_data['abstract'],
                    authors=paper_data['authors'],
                    published_date=datetime.fromisoformat(paper_data['published_date']),
                    source=paper_data['source'],
                    url=paper_data['url'],
                    categories=paper_data['categories'],
                    extracted_skills=paper_data['extracted_skills']
                )
                db.add(paper)
                papers_saved += 1
        
        db.commit()
        
        return {
            "status": "success",
            "papers_fetched": result.get('item_count', 0),
            "papers_saved": papers_saved,
            "timestamp": result.get('timestamp')
        }
        
    except Exception as e:
        log.error(f"Error in ArXiv scraper endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))