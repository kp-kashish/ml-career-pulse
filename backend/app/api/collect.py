"""
Data collection endpoints with LLM-powered skill extraction
"""

from fastapi import APIRouter, BackgroundTasks, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import hashlib

from app.core.database import get_db
from app.core.logging import log
from app.models.models import Paper, GitHubRepo
from app.scrapers.arxiv_scraper import ArxivScraper
from app.scrapers.github_scraper import GitHubScraper
from app.scrapers.reddit_scraper import RedditScraper

router = APIRouter()


@router.post("/arxiv")
async def collect_arxiv_papers(
    background_tasks: BackgroundTasks,
    max_results: int = Query(50, description="Maximum papers to fetch", ge=1, le=100),
    days_back: int = Query(7, description="Days to look back", ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Collect papers from ArXiv with LLM-powered detailed skill extraction
    
    Note: LLM extraction respects rate limits (~15 requests/minute).
    For 50 papers, expect ~3-4 minutes processing time.
    
    Args:
        max_results: Maximum number of papers to collect (1-100)
        days_back: Number of days to look back (1-30)
    
    Returns:
        Collection status with counts, timing info, and success rate
    """
    try:
        start_time = datetime.now()
        log.info(f"ArXiv collection request: max_results={max_results}, days_back={days_back}")
        
        # Initialize and run scraper
        scraper = ArxivScraper()
        result = await scraper.run(max_results=max_results, days_back=days_back)
        
        # Check for errors
        if result.get('error'):
            log.error(f"Scraper returned error: {result['error']}")
            return {
                "status": "error",
                "error": result['error'],
                "timestamp": datetime.now().isoformat()
            }
        
        papers_data = result['data']
        log.info(f"Processing {len(papers_data)} papers for database storage")
        
        papers_added = 0
        papers_updated = 0
        
        for paper_data in papers_data:
            paper_id = paper_data['id']
            
            # Check if paper already exists
            existing = db.query(Paper).filter_by(id=paper_id).first()
            
            if not existing:
                # Create new paper
                paper = Paper(
                    id=paper_id,
                    title=paper_data['title'],
                    abstract=paper_data['abstract'],
                    authors=paper_data['authors'],
                    published_date=datetime.fromisoformat(paper_data['published_date']),
                    source=paper_data['source'],
                    url=paper_data['url'],
                    categories=paper_data['categories'],
                    extracted_skills=paper_data['extracted_skills'],
                    detailed_skills=paper_data['detailed_skills']
                )
                db.add(paper)
                papers_added += 1
                log.debug(f"Added new paper: {paper_data['title'][:50]}")
            else:
                # Update existing paper with new skills
                new_basic = set(paper_data['extracted_skills'])
                existing_basic = set(existing.extracted_skills)
                combined_basic = list(existing_basic.union(new_basic))
                
                if len(combined_basic) > len(existing_basic):
                    existing.extracted_skills = combined_basic
                    existing.detailed_skills = paper_data['detailed_skills']
                    papers_updated += 1
                    log.debug(f"Updated skills for paper: {paper_data['title'][:50]}")
        
        db.commit()
        
        # Calculate success rate for LLM extraction
        successful_extractions = sum(
            1 for p in papers_data 
            if p.get('detailed_skills') and any(v for v in p['detailed_skills'].values() if v)
        )
        success_rate = (successful_extractions / len(papers_data) * 100) if papers_data else 0
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        log.info(f"ArXiv collection complete: {papers_added} added, {papers_updated} updated in {processing_time:.1f}s")
        log.info(f"LLM extraction success rate: {success_rate:.1f}% ({successful_extractions}/{len(papers_data)})")
        
        return {
            "status": "success",
            "papers_added": papers_added,
            "papers_updated": papers_updated,
            "total_fetched": len(papers_data),
            "llm_success_rate": f"{success_rate:.1f}%",
            "successful_extractions": successful_extractions,
            "processing_time_seconds": round(processing_time, 1),
            "message": f"Added {papers_added} new papers, updated {papers_updated} existing papers",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error collecting ArXiv papers: {str(e)}")
        import traceback
        log.error(traceback.format_exc())
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/github")
async def collect_github_repos(
    query: str = Query("machine learning", description="Search query"),
    stars_min: int = Query(100, description="Minimum stars", ge=10),
    db: Session = Depends(get_db)
):
    """
    Collect trending GitHub repositories with LLM-powered skill extraction
    
    Note: LLM extraction respects rate limits (~15 requests/minute).
    
    Args:
        query: Search query for repositories
        stars_min: Minimum number of stars required
    
    Returns:
        Collection status with counts and success rate
    """
    try:
        start_time = datetime.now()
        log.info(f"GitHub collection request: query='{query}', stars_min={stars_min}")
        
        # Initialize and run scraper
        scraper = GitHubScraper()
        result = await scraper.run(query=query, stars_min=stars_min)
        
        # Check for errors
        if result.get('error'):
            log.error(f"Scraper returned error: {result['error']}")
            return {
                "status": "error",
                "error": result['error'],
                "timestamp": datetime.now().isoformat()
            }
        
        repos_data = result['data']
        log.info(f"Processing {len(repos_data)} repos for database storage")
        
        repos_added = 0
        repos_updated = 0
        
        for repo_data in repos_data:
            repo_id = repo_data['id']
            
            # Check if repo already exists
            existing = db.query(GitHubRepo).filter_by(id=repo_id).first()
            
            if not existing:
                # Create new repo
                repo = GitHubRepo(
                    id=repo_id,
                    name=repo_data['name'],
                    full_name=repo_data['full_name'],
                    description=repo_data['description'],
                    stars=repo_data['stars'],
                    forks=repo_data['forks'],
                    language=repo_data['language'],
                    topics=repo_data['topics'],
                    url=repo_data['url'],
                    created_at=datetime.fromisoformat(repo_data['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(repo_data['updated_at'].replace('Z', '+00:00')),
                    extracted_skills=repo_data['extracted_skills'],
                    detailed_skills=repo_data['detailed_skills']
                )
                db.add(repo)
                repos_added += 1
                log.debug(f"Added new repo: {repo_data['full_name']}")
            else:
                # Update stars, forks, and skills
                existing.stars = repo_data['stars']
                existing.forks = repo_data['forks']
                
                new_skills = set(repo_data['extracted_skills'])
                existing_skills = set(existing.extracted_skills)
                combined = list(existing_skills.union(new_skills))
                
                if len(combined) > len(existing_skills):
                    existing.extracted_skills = combined
                    existing.detailed_skills = repo_data['detailed_skills']
                
                repos_updated += 1
                log.debug(f"Updated repo: {repo_data['full_name']}")
        
        db.commit()
        
        # Calculate success rate
        successful_extractions = sum(
            1 for r in repos_data 
            if r.get('detailed_skills') and any(v for v in r['detailed_skills'].values() if v)
        )
        success_rate = (successful_extractions / len(repos_data) * 100) if repos_data else 0
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        log.info(f"GitHub collection complete: {repos_added} added, {repos_updated} updated in {processing_time:.1f}s")
        log.info(f"LLM extraction success rate: {success_rate:.1f}% ({successful_extractions}/{len(repos_data)})")
        
        return {
            "status": "success",
            "repos_added": repos_added,
            "repos_updated": repos_updated,
            "total_fetched": len(repos_data),
            "llm_success_rate": f"{success_rate:.1f}%",
            "successful_extractions": successful_extractions,
            "processing_time_seconds": round(processing_time, 1),
            "message": f"Added {repos_added} new repos, updated {repos_updated} existing repos",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error collecting GitHub repos: {str(e)}")
        import traceback
        log.error(traceback.format_exc())
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/reddit")
async def collect_reddit_posts(
    limit: int = Query(50, description="Posts per subreddit", ge=10, le=100),
    db: Session = Depends(get_db)
):
    """
    Collect hot posts from ML subreddits with LLM-powered analysis
    
    Note: Reddit posts are analyzed but not stored in database yet.
    Returns trending skills extracted from discussions.
    
    Args:
        limit: Number of posts to fetch per subreddit (10-100)
    
    Returns:
        Analysis of trending skills from Reddit discussions
    """
    try:
        start_time = datetime.now()
        log.info(f"Reddit collection request: limit={limit}")
        
        # Initialize and run scraper
        scraper = RedditScraper()
        result = await scraper.run(limit=limit)
        
        # Check for errors
        if result.get('error'):
            log.error(f"Scraper returned error: {result['error']}")
            return {
                "status": "error",
                "error": result['error'],
                "timestamp": datetime.now().isoformat()
            }
        
        posts_data = result['data']
        
        # Extract trending skills from posts
        all_skills = []
        for post in posts_data:
            all_skills.extend(post['extracted_skills'])
        
        from collections import Counter
        skill_counts = Counter(all_skills)
        trending_skills = [
            {"skill": skill, "mentions": count} 
            for skill, count in skill_counts.most_common(10)
        ]
        
        # Calculate success rate
        successful_extractions = sum(
            1 for p in posts_data 
            if p.get('detailed_skills') and any(v for v in p['detailed_skills'].values() if v)
        )
        success_rate = (successful_extractions / len(posts_data) * 100) if posts_data else 0
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        log.info(f"Reddit collection complete: {len(posts_data)} posts analyzed in {processing_time:.1f}s")
        log.info(f"LLM extraction success rate: {success_rate:.1f}% ({successful_extractions}/{len(posts_data)})")
        
        return {
            "status": "success",
            "posts_fetched": len(posts_data),
            "trending_skills": trending_skills,
            "llm_success_rate": f"{success_rate:.1f}%",
            "successful_extractions": successful_extractions,
            "processing_time_seconds": round(processing_time, 1),
            "message": f"Analyzed {len(posts_data)} posts from Reddit",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error collecting Reddit posts: {str(e)}")
        import traceback
        log.error(traceback.format_exc())
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/status")
async def collection_status(db: Session = Depends(get_db)):
    """
    Get current collection statistics
    
    Returns:
        Database statistics and collection status
    """
    try:
        total_papers = db.query(Paper).count()
        total_repos = db.query(GitHubRepo).count()
        
        # Get recent additions (last 24 hours)
        from datetime import timedelta
        yesterday = datetime.now() - timedelta(days=1)
        
        recent_papers = db.query(Paper).filter(
            Paper.published_date >= yesterday
        ).count()
        
        recent_repos = db.query(GitHubRepo).filter(
            GitHubRepo.created_at >= yesterday
        ).count()
        
        # Calculate papers with detailed skills
        papers_with_details = db.query(Paper).filter(
            Paper.detailed_skills != None,
            Paper.detailed_skills != {}
        ).count()
        
        repos_with_details = db.query(GitHubRepo).filter(
            GitHubRepo.detailed_skills != None,
            GitHubRepo.detailed_skills != {}
        ).count()
        
        return {
            "status": "healthy",
            "total_papers": total_papers,
            "total_repos": total_repos,
            "papers_last_24h": recent_papers,
            "repos_last_24h": recent_repos,
            "papers_with_detailed_skills": papers_with_details,
            "repos_with_detailed_skills": repos_with_details,
            "detailed_extraction_rate": {
                "papers": f"{(papers_with_details/total_papers*100):.1f}%" if total_papers > 0 else "0%",
                "repos": f"{(repos_with_details/total_repos*100):.1f}%" if total_repos > 0 else "0%"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error getting collection status: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/llm-status")
async def get_llm_status():
    """
    Get LLM extraction status and rate limit info
    
    Returns:
        LLM configuration and rate limit information
    """
    from app.services.skill_extractor import SkillExtractor
    
    try:
        extractor = SkillExtractor()
        
        if not extractor.model:
            return {
                "status": "unavailable",
                "message": "LLM extraction is not configured. Add GEMINI_API_KEY to .env",
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "status": "available",
            "model": "gemini-2.5-flash",
            "rate_limit": f"{extractor.requests_per_minute} requests/minute",
            "delay_between_requests": f"{extractor.request_delay:.1f} seconds",
            "estimated_time": {
                "10_papers": f"{10 * extractor.request_delay / 60:.1f} minutes",
                "50_papers": f"{50 * extractor.request_delay / 60:.1f} minutes",
                "100_papers": f"{100 * extractor.request_delay / 60:.1f} minutes"
            },
            "monitoring_url": "https://ai.dev/usage?tab=rate-limit",
            "recommendations": [
                "Start with 5-10 papers to test",
                "Use max_results=20-30 for regular collection",
                "Schedule larger collections (50+) during off-hours",
                "Monitor rate limits at ai.dev/usage"
            ],
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        log.error(f"Error getting LLM status: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/run-all")
async def run_all_scrapers(
    background_tasks: BackgroundTasks,
    max_papers: int = Query(20, description="Max papers to collect", ge=5, le=50),
    db: Session = Depends(get_db)
):
    """
    Run all scrapers (ArXiv, GitHub, Reddit)
    
    Warning: This will take several minutes due to rate limiting.
    For max_papers=20, expect ~5-7 minutes total.
    
    Args:
        max_papers: Maximum papers to collect from ArXiv
    
    Returns:
        Combined results from all scrapers
    """
    try:
        start_time = datetime.now()
        log.info(f"Running all scrapers with max_papers={max_papers}")
        
        # Run all scrapers sequentially
        arxiv_result = await collect_arxiv_papers(background_tasks, max_papers, 7, db)
        github_result = await collect_github_repos("machine learning", 100, db)
        reddit_result = await collect_reddit_posts(30, db)
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        return {
            "status": "success",
            "message": "All scrapers executed",
            "total_processing_time_seconds": round(total_time, 1),
            "total_processing_time_minutes": round(total_time / 60, 1),
            "results": {
                "arxiv": arxiv_result,
                "github": github_result,
                "reddit": reddit_result
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error running all scrapers: {str(e)}")
        import traceback
        log.error(traceback.format_exc())
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }