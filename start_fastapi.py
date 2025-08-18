#!/usr/bin/env python3
"""
FastAPI Server Startup Script
Production-ready startup with configuration options
"""

import uvicorn
import os
import sys
from pathlib import Path
import logging

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Environment configuration
HOST = os.getenv("API_HOST", "localhost")
PORT = int(os.getenv("API_PORT", 8000))
RELOAD = os.getenv("API_RELOAD", "true").lower() == "true"
LOG_LEVEL = os.getenv("API_LOG_LEVEL", "info")
WORKERS = int(os.getenv("API_WORKERS", 1))

def main():
    """Start the FastAPI server"""
    
    # Copy global variables to local scope for potential modification
    workers = WORKERS
    
    print("🚀 Smart Notes FastAPI Server")
    print("=" * 50)
    print(f"📊 Host: {HOST}")
    print(f"📊 Port: {PORT}")
    print(f"📊 Reload: {RELOAD}")
    print(f"📊 Log Level: {LOG_LEVEL}")
    print(f"📊 Workers: {workers}")
    print()
    print("📍 Endpoints:")
    print(f"  🔧 Health Check: http://{HOST}:{PORT}/api/health")
    print(f"  📚 Interactive Docs: http://{HOST}:{PORT}/docs")
    print(f"  📖 ReDoc: http://{HOST}:{PORT}/redoc")
    print(f"  🌐 OpenAPI Schema: http://{HOST}:{PORT}/openapi.json")
    print()
    print("🔄 API Endpoints:")
    print(f"  POST http://{HOST}:{PORT}/api/notes/batch")
    print(f"  POST http://{HOST}:{PORT}/api/bake")
    print(f"  GET  http://{HOST}:{PORT}/api/notes")
    print(f"  GET  http://{HOST}:{PORT}/api/results")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    if RELOAD and workers > 1:
        print("⚠️  Warning: Reload mode enabled with multiple workers. Using single worker.")
        workers = 1
    
    # Start server
    uvicorn.run(
        "api_server_fastapi:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        log_level=LOG_LEVEL,
        workers=workers if not RELOAD else None,
        access_log=True
    )

if __name__ == "__main__":
    main()