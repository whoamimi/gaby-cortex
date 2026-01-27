"""
app/main.py
Main application file for the FastAPI SSE service.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .utils.woodlogs import setup_logger
from .utils.on_startup import get_workspace
from .src.router.exceptions import validation_exception_handler
from .src.router.schema import StreamRequiter
from .src.streamer import generate_events

workspace = get_workspace()
logger = setup_logger(__name__)

app = FastAPI(
    title="DataBy AI SSE",
    description="API service for handling Server-Sent Events (SSE) for DataBy AI.",
    version="1.0.0",
)

app.add_exception_handler(422, validation_exception_handler)
app.mount("/static", StaticFiles(directory=workspace.dir.static_path), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://databy.ai",
        "http://localhost:9002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    logger.info("Starting DataBy AI SSE Service...")
    return FileResponse(workspace.dir.static_path / "index.html")

@app.get("/health")
async def get_health():
    logger.info("Health check requested.")
    return JSONResponse(content={"status": "healthy"}, status_code=200)

@app.get("/stream/{id}", response_class=StreamingResponse)
async def stream_events(inputs: StreamRequiter):
    logger.info(f"Starting SSE stream for session ID: {inputs.id}\nReceived: {inputs}\n")

    generator = generate_events(inputs)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    )