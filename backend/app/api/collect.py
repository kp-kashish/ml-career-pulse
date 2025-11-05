"""
Data collection endpoints
"""

from fastapi import APIRouter, BackgroundTasks, Query
from sqlalchemy.orm import Session
from fastapi import Depends
from typing import Optional
from datetime import datetime
import hashlib

from app.core.database import get_db
from app.core.logging import log
from app.models.models import Paper, GitHubRepo

router = APIRouter()


@router.post("/arxiv")
async def collect_arxiv_papers(
    background_tasks: BackgroundTasks,
    max_results: int = Query(20, description="Maximum papers to fetch"),
    db: Session = Depends(get_db)
):
    """
    Collect papers from ArXiv
    """
    try:
        log.info(f"Starting ArXiv collection for {max_results} papers")
        
        # For now, let's add some sample data
        sample_papers = [
            {
                "title": "Attention Is All You Need",
                "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
                "authors": "Vaswani et al.",
                "skills": ["transformer", "attention", "nlp"]
            },
            {
                "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                "abstract": "We introduce a new language representation model called BERT...",
                "authors": "Devlin et al.",
                "skills": ["bert", "nlp", "transformer", "fine-tuning"]
            },
            {
                "title": "Retrieval-Augmented Generation for Large Language Models",
                "abstract": "Large language models (LLMs) have demonstrated impressive capabilities...",
                "authors": "Lewis et al.",
                "skills": ["rag", "llm", "retrieval", "langchain"]
            }
        ]
        
        papers_added = 0
        for paper_data in sample_papers:
            paper_id = hashlib.md5(paper_data["title"].encode()).hexdigest()
            
            existing = db.query(Paper).filter_by(id=paper_id).first()
            if not existing:
                paper = Paper(
                    id=paper_id,
                    title=paper_data["title"],
                    abstract=paper_data["abstract"],
                    authors=paper_data["authors"],
                    published_date=datetime.now(),
                    source="arxiv",
                    url=f"https://arxiv.org/abs/{paper_id}",
                    categories=["cs.LG", "cs.AI"],
                    extracted_skills=paper_data["skills"]
                )
                db.add(paper)
                papers_added += 1
        
        db.commit()
        
        return {
            "status": "success",
            "papers_added": papers_added,
            "message": f"Added {papers_added} new papers",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error collecting ArXiv papers: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/github")
async def collect_github_repos(
    query: str = Query("machine learning", description="Search query"),
    db: Session = Depends(get_db)
):
    """
    Collect trending GitHub repositories
    """
    try:
        log.info(f"Starting GitHub collection for query: {query}")
        
        # Sample data for testing
        sample_repos = [
            {
                "name": "transformers",
                "full_name": "huggingface/transformers",
                "description": "Transformers: State-of-the-art Machine Learning for PyTorch, TensorFlow, and JAX.",
                "stars": 120000,
                "language": "Python",
                "topics": ["pytorch", "tensorflow", "transformer", "bert", "gpt"]
            },
            {
                "name": "langchain",
                "full_name": "langchain-ai/langchain",
                "description": "Building applications with LLMs through composability",
                "stars": 85000,
                "language": "Python",
                "topics": ["llm", "langchain", "rag", "agents"]
            },
            {
                "name": "pytorch",
                "full_name": "pytorch/pytorch",
                "description": "Tensors and Dynamic neural networks in Python",
                "stars": 75000,
                "language": "Python",
                "topics": ["pytorch", "deep-learning", "neural-network"]
            }
        ]
        
        repos_added = 0
        for repo_data in sample_repos:
            repo_id = hashlib.md5(repo_data["full_name"].encode()).hexdigest()
            
            existing = db.query(GitHubRepo).filter_by(id=repo_id).first()
            if not existing:
                repo = GitHubRepo(
                    id=repo_id,
                    name=repo_data["name"],
                    full_name=repo_data["full_name"],
                    description=repo_data["description"],
                    stars=repo_data["stars"],
                    forks=repo_data["stars"] // 5,
                    language=repo_data["language"],
                    topics=repo_data["topics"],
                    url=f"https://github.com/{repo_data['full_name']}"
                )
                db.add(repo)
                repos_added += 1
        
        db.commit()
        
        return {
            "status": "success",
            "repos_added": repos_added,
            "message": f"Added {repos_added} new repositories",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log.error(f"Error collecting GitHub repos: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }