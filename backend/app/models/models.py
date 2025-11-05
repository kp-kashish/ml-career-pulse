"""
SQLAlchemy database models
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Text, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class Paper(Base):
    """ArXiv research paper model"""
    __tablename__ = "papers"
    
    id = Column(String(50), primary_key=True, index=True)
    title = Column(Text, nullable=False)
    abstract = Column(Text, nullable=False)
    authors = Column(Text)
    published_date = Column(DateTime, nullable=False)
    source = Column(String(50), default="arxiv")
    url = Column(Text)
    categories = Column(JSON, default=list)
    extracted_skills = Column(JSON, default=list)
    detailed_skills = Column(JSON, default=dict)  # NEW FIELD
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"<Paper {self.id}: {self.title[:50]}>"


class GitHubRepo(Base):
    """GitHub repository model"""
    __tablename__ = "github_repos"
    
    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    description = Column(Text)
    stars = Column(Integer, default=0)
    forks = Column(Integer, default=0)
    language = Column(String(50))
    topics = Column(JSON, default=list)
    url = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    extracted_skills = Column(JSON, default=list)
    detailed_skills = Column(JSON, default=dict)  # NEW FIELD
    added_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"<GitHubRepo {self.full_name}: {self.stars} stars>"

class JobPosting(Base):
    """
    Job posting model
    """
    __tablename__ = "job_postings"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String)
    location = Column(String)
    description = Column(Text)
    required_skills = Column(JSON)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    remote = Column(Boolean, default=False)
    source = Column(String, index=True)
    url = Column(String)
    posted_date = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SkillTrend(Base):
    """
    Skill trend analysis model
    """
    __tablename__ = "skill_trends"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    skill = Column(String, index=True, nullable=False)
    date = Column(DateTime, index=True, nullable=False)
    mentions_papers = Column(Integer, default=0)
    mentions_github = Column(Integer, default=0)
    mentions_jobs = Column(Integer, default=0)
    mentions_reddit = Column(Integer, default=0)
    trend_score = Column(Float, default=0.0)
    growth_rate = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DailyInsight(Base):
    """
    Daily insights and recommendations model
    """
    __tablename__ = "daily_insights"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, unique=True, index=True, nullable=False)
    hot_skills = Column(JSON)
    emerging_topics = Column(JSON)
    declining_skills = Column(JSON)
    recommended_learning = Column(JSON)
    job_market_summary = Column(Text)
    research_highlights = Column(Text)
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())