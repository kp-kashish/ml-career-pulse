"""
Base scraper class with common functionality
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime
from app.core.logging import log


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers
    """
    
    # Common ML/AI skills to track across all sources
    SKILLS_TO_TRACK = [
        # Frameworks
        'pytorch', 'tensorflow', 'keras', 'jax', 'scikit-learn', 'xgboost', 'lightgbm',
        # LLM related
        'transformer', 'bert', 'gpt', 'llm', 'llama', 'mistral', 'claude', 'gemini',
        'fine-tuning', 'rag', 'retrieval augmented generation', 'prompt engineering',
        # Tools
        'langchain', 'llamaindex', 'huggingface', 'wandb', 'mlflow', 'gradio', 'streamlit',
        # Cloud & MLOps
        'aws', 'azure', 'gcp', 'kubernetes', 'docker', 'airflow', 'kubeflow',
        # Languages
        'python', 'rust', 'cuda', 'sql', 'spark',
        # Techniques
        'deep learning', 'machine learning', 'reinforcement learning', 'computer vision',
        'nlp', 'natural language processing', 'gan', 'diffusion', 'vae'
    ]
    
    def __init__(self, source_name: str):
        """
        Initialize base scraper
        
        Args:
            source_name: Name of the data source
        """
        self.source_name = source_name
        log.info(f"Initializing {source_name} scraper")
    
    @abstractmethod
    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch data from the source
        
        Returns:
            List of data items
        """
        pass
    
    @abstractmethod
    async def process_data(self, raw_data: List[Dict]) -> List[Dict]:
        """
        Process raw data into standardized format
        
        Args:
            raw_data: Raw data from source
            
        Returns:
            Processed data
        """
        pass
    
    def extract_skills(self, text: str) -> List[str]:
        """
        Extract skills mentioned in text
        
        Args:
            text: Text to analyze
            
        Returns:
            List of found skills
        """
        if not text:
            return []
        
        text_lower = text.lower()
        found_skills = []
        
        for skill in self.SKILLS_TO_TRACK:
            if skill.lower() in text_lower:
                found_skills.append(skill)
        
        return list(set(found_skills))
    
    def calculate_trend_score(self, mentions: Dict[str, int]) -> float:
        """
        Calculate trend score based on mentions
        
        Args:
            mentions: Dictionary of mention counts
            
        Returns:
            Calculated trend score
        """
        total_mentions = sum(mentions.values())
        if total_mentions == 0:
            return 0.0
        
        # Weighted score based on source importance
        weights = {
            'papers': 0.3,
            'github': 0.25,
            'jobs': 0.35,
            'reddit': 0.1
        }
        
        score = sum(mentions.get(k, 0) * v for k, v in weights.items())
        return round(score, 2)
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Run the scraper
        
        Returns:
            Scraping results
        """
        try:
            log.info(f"Starting {self.source_name} scraping")
            
            # Fetch raw data
            raw_data = await self.fetch_data(**kwargs)
            log.info(f"Fetched {len(raw_data)} items from {self.source_name}")
            
            # Process data
            processed_data = await self.process_data(raw_data)
            log.info(f"Processed {len(processed_data)} items from {self.source_name}")
            
            return {
                'source': self.source_name,
                'timestamp': datetime.now().isoformat(),
                'item_count': len(processed_data),
                'data': processed_data
            }
            
        except Exception as e:
            log.error(f"Error in {self.source_name} scraper: {str(e)}")
            return {
                'source': self.source_name,
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'data': []
            }