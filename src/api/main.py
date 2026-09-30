from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.core.exceptions import RepoEvolutionError
from src.api.routes.repo import router as repo_router
from src.api.routes.diff import router as diff_router
from src.api.routes.drift import router as drift_router

from src.core.logging_config import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Software Evolution Intelligence Engine REST API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Conservative CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.exception_handler(RepoEvolutionError)
def repo_evolution_exception_handler(request: Request, exc: RepoEvolutionError):
    logger.warning(f"Domain exception on {request.url.path}: [{exc.error_code}] {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "status_code": exc.status_code
        }
    )

app.include_router(repo_router)
app.include_router(diff_router)
app.include_router(drift_router)


@app.get("/")
def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs": "/docs"
    }
