"""
Trends and analytics endpoints
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.logging import log
from app.models.models import Paper, GitHubRepo, SkillTrend

router = APIRouter()


@router.get("/skills/trending")
async def get_trending_skills(
    days: int = Query(7, description="Number of days to analyze"),
    limit: int = Query(20, description="Number of skills to return"),
    db: Session = Depends(get_db)
):
    """
    Get trending skills based on recent data
    """
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get recent papers
        papers = db.query(Paper).filter(
            Paper.created_at >= start_date
        ).all()
        
        # Count skill mentions
        skill_counts = {}
        for paper in papers:
            for skill in (paper.extracted_skills or []):
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
        
        # Sort and limit
        trending = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return {
            "trending_skills": [
                {"skill": skill, "mentions": count, "rank": idx + 1}
                for idx, (skill, count) in enumerate(trending)
            ],
            "period_days": days,
            "total_papers_analyzed": len(papers),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error getting trending skills: {str(e)}")
        return {
            "error": str(e),
            "trending_skills": [],
            "timestamp": datetime.now().isoformat()
        }


@router.get("/papers/recent")
async def get_recent_papers(
    limit: int = Query(10, description="Number of papers to return"),
    db: Session = Depends(get_db)
):
    """
    Get recent research papers
    """
    try:
        papers = db.query(Paper).order_by(
            desc(Paper.created_at)
        ).limit(limit).all()
        
        return {
            "papers": [
                {
                    "id": p.id,
                    "title": p.title,
                    "abstract": p.abstract[:200] + "..." if p.abstract and len(p.abstract) > 200 else p.abstract,
                    "authors": p.authors,
                    "skills": p.extracted_skills,
                    "url": p.url,
                    "published": p.published_date.isoformat() if p.published_date else None
                }
                for p in papers
            ],
            "count": len(papers),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error getting recent papers: {str(e)}")
        return {
            "error": str(e),
            "papers": [],
            "timestamp": datetime.now().isoformat()
        }


@router.get("/github/trending")
async def get_trending_repos(
    limit: int = Query(10, description="Number of repos to return"),
    db: Session = Depends(get_db)
):
    """
    Get trending GitHub repositories
    """
    try:
        repos = db.query(GitHubRepo).order_by(
            desc(GitHubRepo.stars)
        ).limit(limit).all()
        
        return {
            "repositories": [
                {
                    "name": r.name,
                    "full_name": r.full_name,
                    "description": r.description,
                    "stars": r.stars,
                    "language": r.language,
                    "topics": r.topics,
                    "url": r.url
                }
                for r in repos
            ],
            "count": len(repos),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error getting trending repos: {str(e)}")
        return {
            "error": str(e),
            "repositories": [],
            "timestamp": datetime.now().isoformat()
        }


@router.get("/summary/daily")
async def get_daily_summary(db: Session = Depends(get_db)):
    """
    Get daily summary of ML trends
    """
    try:
        today = datetime.now().date()
        
        # Count today's data
        papers_count = db.query(func.count(Paper.id)).filter(
            func.date(Paper.created_at) == today
        ).scalar() or 0
        
        repos_count = db.query(func.count(GitHubRepo.id)).filter(
            func.date(GitHubRepo.created_at) == today
        ).scalar() or 0
        
        return {
            "date": today.isoformat(),
            "statistics": {
                "papers_collected": papers_count,
                "repos_tracked": repos_count,
                "total_papers": db.query(func.count(Paper.id)).scalar() or 0,
                "total_repos": db.query(func.count(GitHubRepo.id)).scalar() or 0
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error getting daily summary: {str(e)}")
        return {
            "error": str(e),
            "statistics": {},
            "timestamp": datetime.now().isoformat()
        }