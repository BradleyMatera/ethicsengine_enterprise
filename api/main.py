import logging
import sys
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request

# Add project root to path to allow absolute imports
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import routers and other necessary components
from api.routers import pipelines, server, results
from batch_api.main_api import router as batch_router
from utils.logging_config import setup_logging
from utils.concurrency_monitor import ConcurrencyMonitor
from core.engine import EthicsEngine
from config.settings import settings

# Setup logging based on config
setup_logging()
logger = logging.getLogger(__name__)

# --- Application Setup ---
app = FastAPI(
    title="Ethics Engine Enterprise API",
    description="API for managing and executing Ethics Engine pipelines.",
    version="0.1.0"
)

# --- Initialize and Store Shared State ---
llm_limit = settings.max_concurrent_llm_calls
llm_semaphore = asyncio.Semaphore(llm_limit)
concurrency_monitor = ConcurrencyMonitor(semaphore=llm_semaphore, limit=llm_limit)
ethics_engine = EthicsEngine()

app.state.concurrency_monitor = concurrency_monitor
app.state.ethics_engine = ethics_engine
app.state.llm_semaphore = llm_semaphore
logger.info(f"Concurrency monitor initialized with limit: {llm_limit}")
logger.info("EthicsEngine instance created and configurations loaded.")

# --- Middleware ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response

# --- Include Routers ---
app.include_router(pipelines.router)
app.include_router(server.router)
app.include_router(results.router)
app.include_router(batch_router, prefix="/batch", tags=["Batch API"])

# --- Root Endpoint ---
@app.get("/", tags=["General"])
async def read_root():
    return {"message": "Welcome to the Ethics Engine Enterprise API"}

@app.get("/health", tags=["General"])
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}

# --- Application Startup/Shutdown Events ---
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Ethics Engine Enterprise API...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Ethics Engine Enterprise API...")
