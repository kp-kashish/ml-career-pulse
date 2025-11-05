"""Test endpoints"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/time")
async def get_time():
    """Get current time"""
    return {
        "current_time": datetime.now().isoformat(),
        "message": "API is working!"
    }


@router.get("/skills")
async def get_skills_list():
    """Get list of tracked skills"""
    skills = [
        "pytorch", "tensorflow", "keras", "scikit-learn",
        "langchain", "huggingface", "docker", "kubernetes"
    ]
    return {
        "skills": skills,
        "count": len(skills)
    }