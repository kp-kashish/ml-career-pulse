# ML Career Pulse

> Real-time intelligence platform for tracking ML/AI skills demand, emerging trends, and career opportunities.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

## Overview

ML Career Pulse aggregates data from research papers, GitHub repositories, and community discussions to provide actionable insights on in-demand ML skills and emerging trends. Built for ML engineers, researchers, and students who want data-driven career guidance.

## Key Features

- **Trend Analysis**: Track skill popularity across 50+ sources with daily updates
- **Market Intelligence**: Identify high-demand frameworks, techniques, and application areas
- **Skill Normalization**: Intelligent deduplication and categorization of ML technologies
- **LLM-Powered Extraction**: Automated skill extraction from papers and repositories
- **API Access**: RESTful API for programmatic access to trend data

## Architecture

```
┌─────────────┐
│   FastAPI   │ ← API Layer
├─────────────┤
│  Scrapers   │ ← Data Collection (ArXiv, GitHub, Reddit)
├─────────────┤
│ LLM Service │ ← Skill Extraction (Gemini)
├─────────────┤
│  Database   │ ← PostgreSQL + Redis
└─────────────┘
```

## Tech Stack

**Backend**

- FastAPI (async Python web framework)
- SQLAlchemy (ORM with Alembic migrations)
- Pydantic (data validation)
- Google Gemini API (LLM-powered extraction)

**Data Sources**

- ArXiv API (research papers)
- GitHub REST API (trending repositories)
- Reddit API via PRAW (community discussions)

**Infrastructure**

- Docker & Docker Compose
- PostgreSQL (primary database)
- Redis (caching layer)

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional)
- API Keys: [Google Gemini](https://makersuite.google.com/app/apikey), [GitHub](https://github.com/settings/tokens), [Reddit](https://www.reddit.com/prefs/apps)

### Local Development

```bash
# Clone repository
git clone https://github.com/kp-kashish/ml-career-pulse.git
cd ml-career-pulse/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

### Docker Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Access the API at `http://localhost:8000/docs`

## API Documentation

### Collect Data

```bash
# Collect ArXiv papers
POST /api/v1/collect/arxiv?max_results=50&days_back=7

# Collect GitHub repositories
POST /api/v1/collect/github?query=machine+learning&stars_min=100

# Check collection status
GET /api/v1/collect/status
```

### Analyze Trends

```bash
# Get market-ready skills
GET /api/v1/trends/skills/market-ready?days=30

# Get trending skills
GET /api/v1/trends/skills/trending?days=7&limit=20

# Get detailed skill breakdown
GET /api/v1/trends/skills/detailed?days=7&limit=10
```

Interactive API documentation available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

## Configuration

Environment variables (`.env`):

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/ml_pulse

# API Keys
GEMINI_API_KEY=your_gemini_key
GITHUB_TOKEN=your_github_token
REDDIT_CLIENT_ID=your_reddit_id
REDDIT_CLIENT_SECRET=your_reddit_secret

# App Config
LOG_LEVEL=INFO
RATE_LIMIT_PER_MINUTE=15
```

## Project Structure

```
ml-career-pulse/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Config, database, logging
│   │   ├── models/       # SQLAlchemy models
│   │   ├── scrapers/     # Data collection modules
│   │   └── services/     # Business logic (LLM extraction)
│   ├── alembic/          # Database migrations
│   ├── tests/            # Unit and integration tests
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```

## Performance

- **Extraction Success Rate**: 100% (50 papers tested)
- **Processing Time**: ~3.3 minutes per 50 papers
- **Rate Limit**: 15 LLM requests/minute (configurable)
- **Data Freshness**: Updated daily via scheduled jobs

## Sample Results

From 50 recent ArXiv papers (7-day window):

| Category   | Top Skills               | Prevalence |
| ---------- | ------------------------ | ---------- |
| Frameworks | PyTorch                  | 92%        |
|            | TensorFlow               | 84%        |
| Techniques | Transformer Architecture | 58%        |
|            | Fine-tuning              | 56%        |
| Emerging   | Foundation Models        | 14%        |
|            | Diffusion Models         | 8%         |

## Roadmap

- [ ] Frontend dashboard (Next.js)
- [ ] Job posting scraper (LinkedIn, Indeed)
- [ ] Historical trend tracking
- [ ] Personalized skill recommendations
- [ ] Email digest subscriptions
- [ ] Public API with rate limiting

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- [ArXiv API](https://arxiv.org/help/api) for research paper access
- [GitHub REST API](https://docs.github.com/en/rest) for repository data
- [Google Gemini](https://ai.google.dev/) for LLM capabilities

## Contact

**Kashish Patel** - [@kp-kashish](https://github.com/kp-kashish)

Project Link: [https://github.com/kp-kashish/ml-career-pulse](https://github.com/kp-kashish/ml-career-pulse)

---

<p align="center">Made with ❤️ for the ML community</p>
