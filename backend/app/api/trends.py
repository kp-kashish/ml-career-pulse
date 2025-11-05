"""
Trends analysis endpoints
"""

from fastapi import APIRouter, Query, Depends
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Paper, GitHubRepo
from sqlalchemy import func, desc
from collections import Counter

router = APIRouter()


@router.get("/skills/trending")
async def get_trending_skills(
    days: int = Query(default=7, description="Number of days to analyze"),
    limit: int = Query(default=20, description="Number of skills to return"),
    db: Session = Depends(get_db)
):
    """
    Get trending skills based on recent data
    
    Args:
        days: Number of days to look back
        limit: Maximum number of skills to return
    
    Returns:
        Trending skills with mention counts
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Get skills from papers
    papers = db.query(Paper).filter(
        Paper.published_date >= cutoff_date
    ).all()
    
    # Get skills from repos
    repos = db.query(GitHubRepo).filter(
        GitHubRepo.created_at >= cutoff_date
    ).all()
    
    # Count skill mentions
    all_skills = []
    for paper in papers:
        all_skills.extend(paper.extracted_skills or [])
    for repo in repos:
        all_skills.extend(repo.extracted_skills or [])
    
    skill_counts = Counter(all_skills)
    
    # Format response
    trending_skills = [
        {"skill": skill, "mentions": count, "rank": i+1}
        for i, (skill, count) in enumerate(skill_counts.most_common(limit))
    ]
    
    return {
        "trending_skills": trending_skills,
        "period_days": days,
        "total_papers_analyzed": len(papers),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/skills/detailed")
async def get_detailed_skills(
    days: int = Query(default=7, description="Number of days to analyze"),
    limit: int = Query(default=10, description="Number of items per category"),
    db: Session = Depends(get_db)
):
    """
    Get detailed skills breakdown from LLM extraction
    
    Shows specific frameworks, models, techniques extracted by LLM
    instead of just basic keyword matching.
    
    Args:
        days: Number of days to look back
        limit: Number of items to return per category
    
    Returns:
        Aggregated detailed skills: frameworks, models, techniques, domains, datasets
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    
    papers = db.query(Paper).filter(
        Paper.published_date >= cutoff_date
    ).all()
    
    # Aggregate all detailed skills from papers
    all_frameworks = []
    all_models = []
    all_techniques = []
    all_domains = []
    all_datasets = []
    all_metrics = []
    all_innovations = []
    
    papers_with_details = 0
    
    for paper in papers:
        detailed = paper.detailed_skills
        if detailed and isinstance(detailed, dict):
            if any(v for v in detailed.values() if v):
                papers_with_details += 1
                
            all_frameworks.extend(detailed.get('frameworks', []))
            all_models.extend(detailed.get('models', []))
            all_techniques.extend(detailed.get('techniques', []))
            all_domains.extend(detailed.get('domains', []))
            all_datasets.extend(detailed.get('datasets', []))
            all_metrics.extend(detailed.get('metrics', []))
            all_innovations.extend(detailed.get('key_innovations', []))
    
    # Count and format
    frameworks_count = Counter(all_frameworks)
    models_count = Counter(all_models)
    techniques_count = Counter(all_techniques)
    domains_count = Counter(all_domains)
    datasets_count = Counter(all_datasets)
    metrics_count = Counter(all_metrics)
    
    return {
        "period_days": days,
        "papers_analyzed": len(papers),
        "papers_with_detailed_extraction": papers_with_details,
        "extraction_success_rate": f"{(papers_with_details/len(papers)*100):.1f}%" if papers else "0%",
        "top_frameworks": [
            {"name": name, "mentions": count, "rank": i+1}
            for i, (name, count) in enumerate(frameworks_count.most_common(limit))
        ],
        "top_models": [
            {"name": name, "mentions": count, "rank": i+1}
            for i, (name, count) in enumerate(models_count.most_common(limit))
        ],
        "top_techniques": [
            {"name": name, "mentions": count, "rank": i+1}
            for i, (name, count) in enumerate(techniques_count.most_common(limit))
        ],
        "top_domains": [
            {"name": name, "mentions": count, "rank": i+1}
            for i, (name, count) in enumerate(domains_count.most_common(limit))
        ],
        "top_datasets": [
            {"name": name, "mentions": count, "rank": i+1}
            for i, (name, count) in enumerate(datasets_count.most_common(limit))
        ],
        "top_metrics": [
            {"name": name, "mentions": count, "rank": i+1}
            for i, (name, count) in enumerate(metrics_count.most_common(limit))
        ],
        "innovations_sample": all_innovations[:5] if all_innovations else [],
        "timestamp": datetime.now().isoformat()
    }


@router.get("/papers/recent")
async def get_recent_papers(
    limit: int = Query(default=10, description="Number of papers to return"),
    db: Session = Depends(get_db)
):
    """
    Get recently collected papers
    
    Args:
        limit: Maximum number of papers to return
    
    Returns:
        List of recent papers with skills
    """
    papers = db.query(Paper).order_by(
        desc(Paper.created_at)
    ).limit(limit).all()
    
    papers_data = [
        {
            "arxiv_id": p.id,
            "title": p.title,
            "abstract": p.abstract[:200] + "..." if len(p.abstract) > 200 else p.abstract,
            "url": p.url,
            "published_date": p.published_date.isoformat() if p.published_date else None,
            "basic_skills": p.extracted_skills,
            "has_detailed_skills": bool(p.detailed_skills and any(v for v in p.detailed_skills.values() if v)),
            "categories": p.categories
        }
        for p in papers
    ]
    
    return {
        "count": len(papers_data),
        "papers": papers_data
    }


@router.get("/github/trending")
async def get_trending_repos(
    limit: int = Query(default=10, description="Number of repos to return"),
    db: Session = Depends(get_db)
):
    """
    Get trending GitHub repositories
    
    Args:
        limit: Maximum number of repositories to return
    
    Returns:
        List of trending repos sorted by stars
    """
    repos = db.query(GitHubRepo).order_by(
        desc(GitHubRepo.stars)
    ).limit(limit).all()
    
    repos_data = [
        {
            "full_name": r.full_name,
            "description": r.description,
            "url": r.url,
            "stars": r.stars,
            "forks": r.forks,
            "language": r.language,
            "topics": r.topics,
            "basic_skills": r.extracted_skills,
            "has_detailed_skills": bool(r.detailed_skills and any(v for v in r.detailed_skills.values() if v))
        }
        for r in repos
    ]
    
    return {
        "count": len(repos_data),
        "repositories": repos_data
    }


@router.get("/summary/daily")
async def get_daily_summary(db: Session = Depends(get_db)):
    """
    Get daily summary of trends and activity
    
    Returns:
        Summary of today's collection activity and trending skills
    """
    # Get today's data
    today = datetime.now().date()
    
    # Count papers added today
    papers_today = db.query(func.count(Paper.id)).filter(
        func.date(Paper.created_at) == today
    ).scalar()
    
    # Count repos added today
    repos_today = db.query(func.count(GitHubRepo.id)).filter(
        func.date(GitHubRepo.added_at) == today
    ).scalar()
    
    # Get total counts
    total_papers = db.query(func.count(Paper.id)).scalar()
    total_repos = db.query(func.count(GitHubRepo.id)).scalar()
    
    # Get top skills from last 24 hours
    cutoff = datetime.now() - timedelta(hours=24)
    recent_papers = db.query(Paper).filter(Paper.created_at >= cutoff).all()
    recent_repos = db.query(GitHubRepo).filter(GitHubRepo.added_at >= cutoff).all()
    
    all_skills = []
    for p in recent_papers:
        all_skills.extend(p.extracted_skills or [])
    for r in recent_repos:
        all_skills.extend(r.extracted_skills or [])
    
    skill_counts = Counter(all_skills)
    top_skills = [
        {"skill": skill, "mentions": count}
        for skill, count in skill_counts.most_common(5)
    ]
    
    return {
        "date": today.isoformat(),
        "papers_added_today": papers_today,
        "repos_added_today": repos_today,
        "total_papers": total_papers,
        "total_repositories": total_repos,
        "top_skills_24h": top_skills,
        "summary": f"Collected {papers_today} papers and {repos_today} repos today. " +
                  f"Database now has {total_papers} papers and {total_repos} repositories.",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/comparison")
async def get_comparison(
    days: int = Query(default=7, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Compare basic keyword extraction vs detailed LLM extraction
    
    Shows the difference between simple keyword matching and LLM-powered analysis
    
    Args:
        days: Number of days to look back
    
    Returns:
        Comparison of basic vs detailed skill extraction
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    
    papers = db.query(Paper).filter(
        Paper.published_date >= cutoff_date
    ).all()
    
    # Basic skills (keyword matching)
    basic_skills = []
    for p in papers:
        basic_skills.extend(p.extracted_skills or [])
    
    basic_unique = len(set(basic_skills))
    basic_top = Counter(basic_skills).most_common(5)
    
    # Detailed skills (LLM extraction)
    detailed_frameworks = []
    detailed_models = []
    detailed_techniques = []
    
    for p in papers:
        if p.detailed_skills and isinstance(p.detailed_skills, dict):
            detailed_frameworks.extend(p.detailed_skills.get('frameworks', []))
            detailed_models.extend(p.detailed_skills.get('models', []))
            detailed_techniques.extend(p.detailed_skills.get('techniques', []))
    
    detailed_all = detailed_frameworks + detailed_models + detailed_techniques
    detailed_unique = len(set(detailed_all))
    
    return {
        "period_days": days,
        "papers_analyzed": len(papers),
        "basic_extraction": {
            "total_mentions": len(basic_skills),
            "unique_skills": basic_unique,
            "top_5": [{"skill": s, "count": c} for s, c in basic_top],
            "example": "llm, transformer, pytorch"
        },
        "detailed_extraction": {
            "total_mentions": len(detailed_all),
            "unique_items": detailed_unique,
            "frameworks_found": len(set(detailed_frameworks)),
            "models_found": len(set(detailed_models)),
            "techniques_found": len(set(detailed_techniques)),
            "example": "Llama 3 70B, LoRA fine-tuning, PyTorch 2.0"
        },
        "improvement": {
            "more_specific": f"{detailed_unique - basic_unique} more specific items identified",
            "detail_level": "Detailed extraction provides version numbers, specific models, and precise techniques"
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/skills/market-ready")
async def get_market_ready_skills(
    days: int = Query(default=30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get skills that are actually relevant to job market with normalized names
    """
    from app.services.skill_extractor import SkillExtractor
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    papers = db.query(Paper).filter(
        Paper.published_date >= cutoff_date
    ).all()
    
    # Aggregate by category
    all_frameworks = []
    all_techniques = []
    all_areas = []
    all_programming = []
    all_emerging = []
    
    for paper in papers:
        detailed = paper.detailed_skills
        if detailed and isinstance(detailed, dict):
            all_frameworks.extend(detailed.get('core_frameworks', []))
            all_techniques.extend(detailed.get('ml_techniques', []))
            all_areas.extend(detailed.get('application_areas', []))
            all_programming.extend(detailed.get('programming_skills', []))
            all_emerging.extend(detailed.get('emerging_trends', []))
    
    # Normalize all skills
    def normalize_list(skills):
        normalized = []
        for skill in skills:
            norm = SkillExtractor.normalize_skill_name(skill)
            if norm:
                normalized.append(norm)
        return normalized
    
    all_frameworks = normalize_list(all_frameworks)
    all_techniques = normalize_list(all_techniques)
    all_areas = normalize_list(all_areas)
    all_programming = normalize_list(all_programming)
    all_emerging = normalize_list(all_emerging)
    
    # Count
    frameworks_count = Counter(all_frameworks)
    techniques_count = Counter(all_techniques)
    areas_count = Counter(all_areas)
    programming_count = Counter(all_programming)
    emerging_count = Counter(all_emerging)
    
    # Calculate percentage
    total_papers = len(papers)
    
    def format_skills(counter, total):
        return [
            {
                "skill": skill,
                "mentions": count,
                "prevalence": f"{(count/total*100):.1f}%",
                "rank": i+1
            }
            for i, (skill, count) in enumerate(counter.most_common(15))
        ]
    
    return {
        "period_days": days,
        "papers_analyzed": total_papers,
        "in_demand_frameworks": format_skills(frameworks_count, total_papers),
        "trending_techniques": format_skills(techniques_count, total_papers),
        "hot_application_areas": format_skills(areas_count, total_papers),
        "required_programming_skills": format_skills(programming_count, total_papers),
        "emerging_trends": format_skills(emerging_count, total_papers),
        "recommendation": {
            "learn_now": [s for s, _ in frameworks_count.most_common(3)],
            "watch": [s for s, _ in emerging_count.most_common(3)],
            "stable_demand": [s for s, _ in techniques_count.most_common(3)]
        },
        "timestamp": datetime.now().isoformat()
    }