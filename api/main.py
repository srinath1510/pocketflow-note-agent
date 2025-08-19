"""
FastAPI main application with middleware and routing
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import logging
import sys
import traceback
import time

from .routers import capture, threads, legacy, session_continuity
from .models.responses import HealthResponse
from .utils.storage import notes_storage, batches_storage, processing_results

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app with metadata for automatic documentation
app = FastAPI(
    title="Smart Notes API",
    description="""
    AI-powered research continuity assistant that transforms multi-modal captures 
    into organized knowledge with intelligent thread management.
    
    ## Features
    - Multi-modal capture support (web, chat, PDF, YouTube, notes)
    - Research thread detection and management  
    - Session continuity across time
    - Batch LLM processing with optimization
    - Neo4j knowledge graph integration
    - Notion note generation
    
    ## Quick Start
    1. Capture content using POST /api/v1/capture
    2. Trigger AI processing with POST /api/bake
    3. Get results with GET /api/results
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "chrome-extension://*",
        "http://localhost:*",
        "https://localhost:*",
        "http://127.0.0.1:*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(capture.router, prefix="/api/v1/capture", tags=["capture"])
app.include_router(threads.router, prefix="/api/v1/threads", tags=["threads"])
app.include_router(legacy.router, prefix="/api", tags=["legacy"])
app.include_router(session_continuity.router, prefix="/api/v1/sessions", tags=["session-continuity"])

# Initialize pipeline orchestrator
try:
    from pipeline_orchestrator import PipelineOrchestrator
    pipeline_orchestrator = PipelineOrchestrator()
    logger.info("Pipeline orchestrator initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize pipeline orchestrator: {str(e)}")
    pipeline_orchestrator = None


# Exception handlers

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with detailed information"""
    logger.error(f"HTTP {exc.status_code} error: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "error_type": type(exc).__name__,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "debug": str(traceback.format_exc()) if app.debug else None
        }
    )


# Add middleware to include rate limit headers in all responses
@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    """Add rate limit headers to responses"""
    response = await call_next(request)
    
    # Add rate limit headers if available
    if hasattr(request.state, 'rate_limit_info'):
        rate_info = request.state.rate_limit_info
        response.headers["X-RateLimit-Limit"] = str(rate_info.get('limit', 30))
        response.headers["X-RateLimit-Remaining"] = str(rate_info.get('remaining', 0))
        response.headers["X-RateLimit-Reset"] = str(int(rate_info.get('reset_time', time.time())))
    
    return response


# Root endpoints

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Smart Notes FastAPI Server",
        "version": "2.0.0",
        "server_type": "FastAPI ASGI",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_status": "available" if pipeline_orchestrator else "unavailable",
        "documentation": {
            "interactive_docs": "/docs",
            "redoc": "/redoc",
            "openapi_schema": "/openapi.json"
        },
        "endpoints": {
            "health": "/api/health",
            "status": "/api/status",
            "notes_batch": "/api/notes/batch",
            "bake": "/api/bake",
            "notes": "/api/notes",
            "batches": "/api/batches",
            "results": "/api/results"
        }
    }


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for extension connectivity"""
    try:
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="2.0.0",
            service="smart-notes-api",
            server_type="FastAPI ASGI",
            debug_mode=app.debug,
            endpoints={
                "health": "/api/health",
                "notes_batch": "/api/notes/batch",
                "bake": "/api/bake",
                "notes": "/api/notes",
                "batches": "/api/batches",
                "results": "/api/results",
                "docs": "/docs"
            }
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


@app.get("/api/status")
async def get_status():
    """Get detailed server status"""
    try:
        return {
            "server": "Smart Notes FastAPI API",
            "status": "running",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "debug_mode": app.debug,
            "python_version": sys.version,
            "fastapi_version": "2.0.0+",
            "stats": {
                "notes_in_memory": len(notes_storage),
                "batches_processed": len(batches_storage),
                "processing_results": len(processing_results)
            },
            "pipeline_orchestrator": {
                "available": pipeline_orchestrator is not None,
                "status": "operational" if pipeline_orchestrator else "unavailable"
            }
        }
    except Exception as e:
        logger.error(f"Status endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Application startup
@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("🚀 FastAPI Smart Notes API Server starting up...")
    logger.info("📊 Server will run on: http://localhost:8000")
    logger.info("🔧 Health check: http://localhost:8000/api/health")
    logger.info("📚 Interactive docs: http://localhost:8000/docs")
    logger.info("📖 ReDoc: http://localhost:8000/redoc")


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Smart Notes FastAPI Server...")
    print("📊 Server will run on: http://localhost:8000")
    print("🔧 Health check: http://localhost:8000/api/health")
    print("📚 Interactive docs: http://localhost:8000/docs")
    print("📖 ReDoc: http://localhost:8000/redoc")
    print("📍 Available endpoints:")
    print("  - GET  /              (Root)")
    print("  - GET  /api/health    (Health check)")
    print("  - GET  /api/status    (Status)")
    print("  - POST /api/notes/batch (Process notes)")
    print("  - POST /api/bake      (Bake notes)")
    print("  - GET  /api/notes     (Get notes)")
    print("  - GET  /api/batches   (Get batches)")
    print("  - GET  /api/results   (Get results)")
    print("  - DELETE /api/notes   (Clear notes)")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    uvicorn.run(
        "api.main:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info"
    )