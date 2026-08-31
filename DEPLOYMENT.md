# CivicSight — Deployment Guide

## Architecture

CivicSight consists of 5 services:

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| Frontend | Static HTML/JS (nginx) | 3000 | User interface |
| Node API | Express.js | 5000 | Auth, project CRUD, mutations |
| Data Backend | FastAPI + PostgreSQL/PostGIS | 8000 | Read-only data/analytics |
| AI Service | FastAPI + PyTorch/Groq | 8001 | Image analysis, progress assessment |
| MongoDB | MongoDB 7 | 27017 | User data, project metadata |
| PostGIS | PostgreSQL 16 + PostGIS 3.4 | 5433 | Infrastructure data |

## Local Development

### Prerequisites
- Docker Desktop
- Node.js 20+ (for local frontend dev)
- Python 3.12+ (for local backend dev)

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/niksxox/CivicSight.git
cd CivicSight

# 2. Create environment file
cp .env.example .env
# Edit .env with your values

# 3. Start all services
docker compose up --build -d

# 4. Initialize the data backend (first time only)
docker compose exec data-backend python scripts/init_db.py
docker compose exec data-backend python scripts/run_etl.py

# 5. Access the application
# Frontend:    http://localhost:3000
# Node API:    http://localhost:5000/api/health
# Data API:    http://localhost:8000/docs
# AI Service:  http://localhost:8001/health
```

## Cloud Deployment

### Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | API key for Groq LLM service |
| `JWT_SECRET` | Yes | Secret for JWT signing (min 32 chars) |
| `MONGO_USER` | Yes | MongoDB username |
| `MONGO_PASSWORD` | Yes | MongoDB password |
| `POSTGRES_USER` | Yes | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `FRONTEND_URL` | Yes | Public frontend URL for CORS |
| `ENVIRONMENT` | No | `production` or `development` |

### Deployment Options

#### Option 1: Single Server (Docker Compose)
```bash
# On your cloud VM
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

#### Option 2: Managed Services
1. **Database**: Use MongoDB Atlas and a managed PostgreSQL with PostGIS (e.g., Supabase, Neon, or AWS RDS)
2. **Frontend**: Deploy static files to Vercel, Netlify, or S3+CloudFront
3. **APIs**: Deploy to Railway, Render, Fly.io, or AWS ECS

### Health Endpoints

| Service | Endpoint |
|---------|----------|
| Frontend | `GET /` |
| Node API | `GET /api/health` |
| Data Backend | `GET /health` |
| AI Service | `GET /health` |

## Production Checklist

- [ ] All environment variables set
- [ ] `ENVIRONMENT=production`
- [ ] `JWT_SECRET` is a strong random string
- [ ] `GROQ_API_KEY` is valid
- [ ] CORS origins configured correctly
- [ ] Database connections use TLS
- [ ] No localhost URLs in production config
- [ ] Health endpoints accessible
- [ ] Persistent volumes for databases

## Troubleshooting

### Frontend shows "Unable to connect to the data backend"
- Check that the data-backend service is running: `docker compose ps`
- Verify `DATABASE_URL` is correct
- Check logs: `docker compose logs data-backend`

### Authentication fails
- Verify MongoDB is running and accessible
- Check `MONGO_URI` in Node API environment
- Ensure `JWT_SECRET` is set

### AI analysis fails
- Verify `GROQ_API_KEY` is set
- Check AI service logs: `docker compose logs ai-service`
