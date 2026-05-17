# NisargHunter AI - Phase 1 Backend Setup

## Project Structure

```
backend/
├── __init__.py
├── main.py                          # FastAPI application entry point
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
│
├── core/                            # Core configuration and utilities
│   ├── __init__.py
│   ├── config.py                    # Pydantic Settings configuration
│   └── redis.py                     # Redis client management
│
├── database/                        # Database layer
│   ├── __init__.py
│   ├── base.py                      # SQLAlchemy base and mixins
│   └── session.py                   # SQLAlchemy async session factory
│
├── schemas/                         # Pydantic models
│   ├── __init__.py
│   └── base.py                      # Base response schemas
│
├── models/                          # SQLAlchemy ORM models
│   └── __init__.py
│
└── api/                             # API routes
    ├── __init__.py
    └── routes/
        ├── __init__.py
        └── health.py                # Health check endpoint
```

## Architecture Overview

### Design Principles
- **Async-First**: All database and Redis operations are fully asynchronous
- **Dependency Injection**: FastAPI dependencies for clean, testable code
- **Modular**: Separated concerns across core, database, and API layers
- **Type-Safe**: Full Pydantic v2 and type hints
- **Production-Ready**: Environment-based configuration, logging, error handling

### Key Components

1. **Configuration** (`core/config.py`)
   - Pydantic v2 BaseSettings
   - Singleton pattern for settings
   - Environment variable loading via .env

2. **Database** (`database/`)
   - SQLAlchemy 2.0 async engine with asyncpg async driver
   - AsyncSessionLocal factory
   - Automatic schema initialization
   - UUID + timestamp mixins for all models

3. **Redis** (`core/redis.py`)
   - Singleton Redis client
   - Async connect/close lifecycle management
   - Dependency injection for routes

4. **Lifespan Management** (`main.py`)
   - Startup: DB schema init + Redis connection
   - Shutdown: Clean Redis + DB disconnection
   - Async context manager pattern

5. **Health Check** (`api/routes/health.py`)
   - Simple endpoint for load balancer probes
   - Returns app name and version

## Installation & Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Redis 6+

### Local Development

1. **Clone and setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Database setup**
   - Ensure PostgreSQL is running
   - Update DATABASE_URL in .env
   - Tables auto-initialize on app startup

5. **Run development server**
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access application**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs (Swagger UI)
   - Health: http://localhost:8000/health

### Docker Deployment

**Start all services:**
```bash
docker-compose up -d
```

**Services:**
- Backend API: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

**Stop services:**
```bash
docker-compose down
```

**View logs:**
```bash
docker-compose logs -f backend
```

## API Documentation

### Health Check
```http
GET /health

Response:
{
  "status": "ok",
  "version": "1.0.0"
}
```

## Database Models

Models should inherit from `BaseModel` in `backend/database/base.py`:

```python
from sqlalchemy.orm import Mapped
from backend.database.base import BaseModel

class Project(BaseModel):
    """Project model."""
    __tablename__ = "projects"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Automatically includes: id, created_at, updated_at
```

## Adding New Routes

1. Create route file in `backend/api/routes/`
2. Define APIRouter and endpoints
3. Import in `backend/main.py`
4. Register with `app.include_router()`

Example:
```python
# backend/api/routes/projects.py
from fastapi import APIRouter

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/")
async def list_projects():
    return []
```

Then in `main.py`:
```python
from backend.api.routes import projects
app.include_router(projects.router)
```

## Environment Variables

Required (.env):
- `APP_NAME`: Application name
- `APP_VERSION`: Application version
- `DEBUG`: Debug mode (true/false)
- `SECRET_KEY`: JWT/encryption secret
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `ANTHROPIC_API_KEY`: Claude API key
- `HACKERONE_USERNAME`: HackerOne username
- `HACKERONE_API_TOKEN`: HackerOne API token

## Dependency Injection Examples

### Database Session
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.session import get_db

@router.get("/items")
async def list_items(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Item))
    return result.scalars().all()
```

### Redis
```python
from fastapi import Depends
from redis.asyncio import Redis
from backend.core.redis import get_redis

@router.get("/cache")
async def get_cache(redis: Redis = Depends(get_redis)):
    value = await redis.get("key")
    return {"value": value}
```

### Settings
```python
from backend.core.config import settings

@router.get("/config")
async def get_config():
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug
    }
```

## Production Deployment

### Security Checklist
- [ ] Set `DEBUG=false` in production
- [ ] Use strong `SECRET_KEY` (generate with `openssl rand -hex 32`)
- [ ] Configure CORS properly (not `allow_origins=*`)
- [ ] Use environment-specific connection strings
- [ ] Enable HTTPS with proper certificates
- [ ] Set up monitoring and logging
- [ ] Configure database backups
- [ ] Use Redis persistence

### Scaling Considerations
- Async architecture supports high concurrency
- Use connection pooling (configured in `session.py`)
- Implement Redis caching for frequently accessed data
- Use load balancer with health checks
- Consider message queue for long-running tasks

## Testing

```bash
# Run tests (when available)
pytest

# With coverage
pytest --cov=backend
```

## Troubleshooting

**"Redis client not initialized"**
- Ensure Redis is running
- Check REDIS_URL in .env
- Verify startup hooks are executing

**"Database connection failed"**
- Verify PostgreSQL is running
- Check DATABASE_URL format
- Ensure asyncpg driver is installed

**"Import errors"**
- Verify all `__init__.py` files exist
- Check Python path includes project root
- Reinstall dependencies: `pip install -r requirements.txt`

## Next Phase Features (Phase 2+)

- [ ] User authentication (JWT)
- [ ] Role-based access control (RBAC)
- [ ] Database models for vulnerability tracking
- [ ] API endpoints for CRUD operations
- [ ] Background job processing (Celery/AIO)
- [ ] WebSocket support for real-time updates
- [ ] Comprehensive API documentation
- [ ] Integration with HackerOne API
- [ ] Claude AI integration for analysis
- [ ] Logging and monitoring
- [ ] API rate limiting
- [ ] Request validation middleware

## Contributing

Follow these patterns for consistency:
1. Use async/await everywhere
2. Add type hints to all functions
3. Use dependency injection for external dependencies
4. Add docstrings to public functions
5. Keep route handlers thin (use service layer for logic)
6. Add comments for complex logic only

## License

Proprietary - NisargHunter AI
