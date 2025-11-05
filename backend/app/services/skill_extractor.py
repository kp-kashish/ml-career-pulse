"""
Intelligent skill extraction using LLM for all data sources
Handles rate limiting, retries, and multiple source types
"""

import google.generativeai as genai
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging import log
import json
import asyncio


class SkillExtractor:
    """
    Uses LLM to intelligently extract skills, technologies, and techniques
    from ANY text source (papers, repos, job posts, discussions)
    
    Features:
    - Automatic rate limiting
    - Retry logic for transient failures
    - Multiple source type support
    - Graceful fallback on errors
    """
    
    def __init__(self, model_name: str = 'gemini-2.5-flash'):
        """
        Initialize Gemini API with rate limiting
        
        Args:
            model_name: Model to use (default: gemini-2.5-flash for better rate limits)
        """
        if not settings.GEMINI_API_KEY:
            log.warning("GEMINI_API_KEY not found - skill extraction will be limited to basic keywords")
            self.model = None
            self.requests_per_minute = 0
            self.request_delay = 0
            return
            
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(model_name)
            
            # Rate limiting configuration
            # gemini-2.5-flash: 15 req/min free tier
            # gemini-2.0-flash-exp: 10 req/min free tier
            self.requests_per_minute = 15 if 'flash' in model_name and '2.5' in model_name else 10
            self.request_delay = 60 / self.requests_per_minute
            
            log.info(f"SkillExtractor initialized with {model_name}")
            log.info(f"Rate limit: {self.requests_per_minute} requests/minute ({self.request_delay:.1f}s between requests)")
            
        except Exception as e:
            log.error(f"Failed to initialize SkillExtractor: {str(e)}")
            self.model = None
            self.requests_per_minute = 0
            self.request_delay = 0
    
    def _clean_json_response(self, text: str) -> str:
        """
        Remove markdown code blocks and fix common JSON issues
        
        Args:
            text: Raw LLM response text
            
        Returns:
            Cleaned JSON string
        """
        text = text.strip()
        
        # Remove markdown code blocks
        if text.startswith('```'):
            lines = text.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].startswith('```'):
                lines = lines[:-1]
            text = '\n'.join(lines)
        
        # Remove 'json' language identifier
        if text.startswith('json'):
            text = text[4:].strip()
        
        # Extract JSON object if there's extra text
        if '{' in text and '}' in text:
            start = text.index('{')
            end = text.rindex('}') + 1
            text = text[start:end]
        
        # Fix trailing commas (common LLM error)
        import re
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        
        return text
    
    async def extract_from_paper(self, title: str, abstract: str, retry_count: int = 3) -> Dict[str, Any]:
        """
        Extract MARKETABLE skills from research paper
        Focus on skills that are learnable and relevant to job market
        """
        if not self.model:
            return self._empty_paper_result()
        
        await asyncio.sleep(self.request_delay)
        
        prompt = f"""Analyze this ML/AI research paper and extract ONLY marketable, learnable skills.

    Title: {title}
    Abstract: {abstract}

    Focus on skills that:
    - Can be learned by ML engineers/researchers
    - Are relevant to job market
    - Are transferable across projects
    - Represent real tools, frameworks, or techniques

    Extract and return ONLY a JSON object:

    {{
    "core_frameworks": ["PyTorch", "TensorFlow", "JAX"],
    "ml_techniques": ["Transformer architecture", "Reinforcement Learning", "Fine-tuning"],
    "application_areas": ["Computer Vision", "NLP", "Time Series"],
    "programming_skills": ["Python", "CUDA", "Distributed Training"],
    "emerging_trends": ["Mixture of Experts", "Diffusion Models"]
    }}

    Rules:
    - Use STANDARD names (e.g., "PyTorch" not "PyTorch 2.0")
    - Focus on GENERAL techniques (e.g., "Knowledge Distillation" not "GRACE score")
    - Include WIDELY-USED tools only
    - Skip paper-specific datasets/models unless they're industry-standard
    - Emerging trends = techniques gaining traction but not yet mainstream

    Return ONLY valid JSON. No explanations.
    """
        
        for attempt in range(retry_count):
            try:
                response = self.model.generate_content(prompt)
                result_text = self._clean_json_response(response.text)
                
                try:
                    extracted = json.loads(result_text)
                    
                    if not isinstance(extracted, dict):
                        raise ValueError("Response is not a dictionary")
                    
                    # Ensure all expected keys exist
                    expected_keys = ['core_frameworks', 'ml_techniques', 'application_areas', 
                                'programming_skills', 'emerging_trends']
                    for key in expected_keys:
                        if key not in extracted:
                            extracted[key] = []
                    
                    # Normalize skill names (standardize capitalization)
                    for key in extracted:
                        if isinstance(extracted[key], list):
                            extracted[key] = [str(item).strip() for item in extracted[key] if item]
                    
                    log.debug(f"LLM extraction successful for paper: {title[:50]}...")
                    return extracted
                    
                except (json.JSONDecodeError, ValueError) as je:
                    log.warning(f"JSON parsing attempt {attempt + 1} failed")
                    if attempt < retry_count - 1:
                        await asyncio.sleep(2)
                        continue
                    return self._empty_paper_result()
                    
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower():
                    if attempt < retry_count - 1:
                        wait_time = 60
                        log.warning(f"Rate limit hit, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    return self._empty_paper_result()
                else:
                    log.error(f"LLM extraction failed: {error_str}")
                    if attempt < retry_count - 1:
                        await asyncio.sleep(2)
                        continue
                    return self._empty_paper_result()
        
        return self._empty_paper_result()

    def _empty_paper_result(self) -> Dict[str, Any]:
        """Return empty result structure for papers"""
        return {
            "core_frameworks": [],
            "ml_techniques": [],
            "application_areas": [],
            "programming_skills": [],
            "emerging_trends": []
        }
    
    async def extract_from_repo(self, name: str, description: str, topics: List[str] = None, retry_count: int = 3) -> Dict[str, Any]:
        """
        Extract detailed skills from GitHub repository
        
        Args:
            name: Repository name
            description: Repository description
            topics: Repository topics/tags
            retry_count: Number of retries on rate limit errors
            
        Returns:
            Dictionary with structured skill information
        """
        if not self.model:
            log.debug("LLM not available, returning empty result")
            return self._empty_repo_result()
        
        # Rate limiting delay
        await asyncio.sleep(self.request_delay)
        
        topics_str = ', '.join(topics) if topics else 'None'
        
        prompt = f"""Analyze this GitHub repository and extract detailed information.

Repository Name: {name}
Description: {description}
Topics: {topics_str}

Extract and return a JSON object with these fields:
1. "tech_stack": Technologies and languages (e.g., ["Python 3.11", "FastAPI", "PostgreSQL"])
2. "ml_frameworks": ML frameworks (e.g., ["PyTorch", "TensorFlow", "scikit-learn"])
3. "tools": Development tools (e.g., ["Docker", "Kubernetes", "MLflow"])
4. "use_cases": What the project does (e.g., ["text generation", "image classification"])
5. "target_audience": Who would use this (e.g., ["ML researchers", "data scientists"])
6. "key_features": Notable features (max 3 items)

Return ONLY valid JSON with arrays for each field. If nothing found, use empty array [].
"""
        
        for attempt in range(retry_count):
            try:
                response = self.model.generate_content(prompt)
                result_text = self._clean_json_response(response.text)
                extracted = json.loads(result_text)
                
                log.debug(f"LLM extraction successful for repo: {name}")
                return extracted
                
            except Exception as e:
                error_str = str(e)
                
                if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                    if attempt < retry_count - 1:
                        wait_time = 60
                        log.warning(f"Rate limit hit for repo '{name}', waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        log.error(f"Rate limit exceeded for repo: {name}")
                        return self._empty_repo_result()
                else:
                    log.error(f"LLM extraction failed for repo '{name}': {error_str}")
                    if attempt < retry_count - 1:
                        await asyncio.sleep(2)
                        continue
                    return self._empty_repo_result()
        
        return self._empty_repo_result()
    
    async def extract_from_discussion(self, title: str, content: str, source: str = "reddit", retry_count: int = 3) -> Dict[str, Any]:
        """
        Extract skills from online discussions (Reddit, forums, etc.)
        
        Args:
            title: Discussion title
            content: Discussion content
            source: Source platform (reddit, hackernews, etc.)
            retry_count: Number of retries on rate limit errors
            
        Returns:
            Dictionary with structured skill information
        """
        if not self.model:
            log.debug("LLM not available, returning empty result")
            return self._empty_discussion_result()
        
        # Rate limiting delay
        await asyncio.sleep(self.request_delay)
        
        prompt = f"""Analyze this {source} discussion about ML/AI and extract information.

Title: {title}

Content: {content[:1000]}

Extract and return a JSON object with these fields:
1. "mentioned_tools": Tools/frameworks people are discussing (e.g., ["LangChain", "Ollama"])
2. "problems_discussed": Problems or challenges mentioned (e.g., ["GPU memory issues", "fine-tuning cost"])
3. "solutions_suggested": Solutions or approaches suggested (e.g., ["use quantization", "try LoRA"])
4. "trending_topics": Hot topics in this discussion (e.g., ["local LLMs", "open source models"])
5. "sentiment": Overall sentiment ("positive", "negative", "neutral", "mixed")

Return ONLY valid JSON with arrays for each field. If nothing found, use empty array [].
"""
        
        for attempt in range(retry_count):
            try:
                response = self.model.generate_content(prompt)
                result_text = self._clean_json_response(response.text)
                extracted = json.loads(result_text)
                
                log.debug(f"LLM extraction successful for discussion: {title[:50]}...")
                return extracted
                
            except Exception as e:
                error_str = str(e)
                
                if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                    if attempt < retry_count - 1:
                        wait_time = 60
                        log.warning(f"Rate limit hit for discussion, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        log.error(f"Rate limit exceeded for discussion: {title[:50]}...")
                        return self._empty_discussion_result()
                else:
                    log.error(f"LLM extraction failed for discussion: {error_str}")
                    if attempt < retry_count - 1:
                        await asyncio.sleep(2)
                        continue
                    return self._empty_discussion_result()
        
        return self._empty_discussion_result()
    
    async def extract_from_job_post(self, title: str, description: str, company: str = "", retry_count: int = 3) -> Dict[str, Any]:
        """
        Extract skills from job postings (LinkedIn, Indeed, etc.)
        
        Args:
            title: Job title
            description: Job description
            company: Company name
            retry_count: Number of retries on rate limit errors
            
        Returns:
            Dictionary with structured skill information
        """
        if not self.model:
            log.debug("LLM not available, returning empty result")
            return self._empty_job_result()
        
        # Rate limiting delay
        await asyncio.sleep(self.request_delay)
        
        prompt = f"""Analyze this ML/AI job posting and extract detailed requirements.

Job Title: {title}
Company: {company}
Description: {description[:1500]}

Extract and return a JSON object with these fields:
1. "required_skills": Must-have skills (e.g., ["Python", "PyTorch", "5+ years ML experience"])
2. "preferred_skills": Nice-to-have skills (e.g., ["AWS", "MLflow", "PhD"])
3. "tools": Specific tools mentioned (e.g., ["Docker", "Kubernetes", "Git"])
4. "role_type": Type of role (e.g., "ML Engineer", "Research Scientist", "Data Scientist")
5. "seniority": Level (e.g., "Senior", "Mid-level", "Junior", "Lead")
6. "focus_areas": Main focus (e.g., ["NLP", "Computer Vision", "MLOps"])

Return ONLY valid JSON with arrays for each field. If nothing found, use empty array [].
"""
        
        for attempt in range(retry_count):
            try:
                response = self.model.generate_content(prompt)
                result_text = self._clean_json_response(response.text)
                extracted = json.loads(result_text)
                
                log.debug(f"LLM extraction successful for job: {title}")
                return extracted
                
            except Exception as e:
                error_str = str(e)
                
                if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                    if attempt < retry_count - 1:
                        wait_time = 60
                        log.warning(f"Rate limit hit for job post, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        log.error(f"Rate limit exceeded for job: {title}")
                        return self._empty_job_result()
                else:
                    log.error(f"LLM extraction failed for job: {error_str}")
                    if attempt < retry_count - 1:
                        await asyncio.sleep(2)
                        continue
                    return self._empty_job_result()
        
        return self._empty_job_result()
    
    # Fallback empty results - used when LLM is unavailable or fails
    def _empty_paper_result(self) -> Dict[str, Any]:
        """Return empty result structure for papers"""
        return {
            "frameworks": [],
            "models": [],
            "techniques": [],
            "domains": [],
            "datasets": [],
            "metrics": [],
            "key_innovations": []
        }
    
    def _empty_repo_result(self) -> Dict[str, Any]:
        """Return empty result structure for repositories"""
        return {
            "tech_stack": [],
            "ml_frameworks": [],
            "tools": [],
            "use_cases": [],
            "target_audience": [],
            "key_features": []
        }
    
    def _empty_discussion_result(self) -> Dict[str, Any]:
        """Return empty result structure for discussions"""
        return {
            "mentioned_tools": [],
            "problems_discussed": [],
            "solutions_suggested": [],
            "trending_topics": [],
            "sentiment": "neutral"
        }
    
    def _empty_job_result(self) -> Dict[str, Any]:
        """Return empty result structure for job postings"""
        return {
            "required_skills": [],
            "preferred_skills": [],
            "tools": [],
            "role_type": "Unknown",
            "seniority": "Unknown",
            "focus_areas": []
        }
    
    @staticmethod
    def normalize_skill_name(skill: str) -> str:
        """
        Normalize skill names to avoid duplicates
        
        Args:
            skill: Raw skill name
            
        Returns:
            Normalized skill name
        """
        if not skill:
            return ""
        
        skill = skill.strip()
        
        # Standardization map - maps variations to canonical names
        standardization_map = {
            # NLP variations
            "natural language processing": "NLP",
            "natural language processing (nlp)": "NLP",
            "nlp": "NLP",
            
            # LLM variations
            "large language models": "Large Language Models",
            "large language models (llms)": "Large Language Models",
            "llms": "Large Language Models",
            
            # Computer Vision
            "computer vision": "Computer Vision",
            "cv": "Computer Vision",
            
            # Reinforcement Learning
            "reinforcement learning": "Reinforcement Learning",
            "rl": "Reinforcement Learning",
            
            # Machine Learning
            "machine learning": "Machine Learning",
            "ml": "Machine Learning",
            
            # Deep Learning
            "deep learning": "Deep Learning",
            "dl": "Deep Learning",
            
            # Architecture names
            "transformer architecture": "Transformer Architecture",
            "transformers": "Transformer Architecture",
            
            # Remove generic suffixes
            " models": "",
            " (nlp)": "",
            " (llms)": "",
            " (cv)": "",
            " (rl)": "",
            " (ml)": "",
        }
        
        skill_lower = skill.lower()
        
        # Check for direct matches first
        if skill_lower in standardization_map:
            result = standardization_map[skill_lower]
            return result if result else skill
        
        # Remove suffixes
        for suffix, replacement in standardization_map.items():
            if suffix.startswith(" ") and skill_lower.endswith(suffix):
                return skill[:len(skill)-len(suffix)].strip()
        
        # Title case for consistency
        return skill.title()
    
    async def batch_process(self, items: List[Dict], item_type: str) -> List[Dict]:
        """
        Batch process multiple items with rate limiting and progress tracking
        
        Args:
            items: List of items to process
            item_type: Type of items ("paper", "repo", "discussion", "job")
            
        Returns:
            Items with added detailed_skills field
        """
        if not items:
            return []
        
        total = len(items)
        estimated_time = total * self.request_delay if self.model else 0
        
        log.info(f"Starting batch LLM extraction for {total} {item_type}s")
        if self.model:
            log.info(f"Estimated processing time: {estimated_time:.0f} seconds (~{estimated_time/60:.1f} minutes)")
        else:
            log.warning("LLM not available - skipping detailed extraction")
        
        enriched_items = []
        
        for i, item in enumerate(items, 1):
            try:
                # Progress logging every 10 items
                if i % 10 == 0 or i == 1:
                    log.info(f"Processing item {i}/{total} ({i*100//total}%)")
                
                # Extract based on type
                if item_type == "paper":
                    detailed = await self.extract_from_paper(
                        item.get('title', ''),
                        item.get('abstract', '')
                    )
                elif item_type == "repo":
                    detailed = await self.extract_from_repo(
                        item.get('name', ''),
                        item.get('description', ''),
                        item.get('topics', [])
                    )
                elif item_type == "discussion":
                    detailed = await self.extract_from_discussion(
                        item.get('title', ''),
                        item.get('content', ''),
                        item.get('source', 'reddit')
                    )
                elif item_type == "job":
                    detailed = await self.extract_from_job_post(
                        item.get('title', ''),
                        item.get('description', ''),
                        item.get('company', '')
                    )
                else:
                    log.warning(f"Unknown item type: {item_type}")
                    detailed = {}
                
                item['detailed_skills'] = detailed
                enriched_items.append(item)
                
            except Exception as e:
                log.error(f"Error processing item {i}: {str(e)}")
                item['detailed_skills'] = {}
                enriched_items.append(item)
        
        log.info(f"Completed batch extraction for {len(enriched_items)} items")
        return enriched_items