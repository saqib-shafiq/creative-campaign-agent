"""
FastAPI Application for Creative Campaign Agent
Provides web interface and API endpoints for campaign generation.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import asyncio
import os

from app.services.ai_service import run_campaign
from app.services.memory import load_memory

app = FastAPI()

# Static file serving setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

static_dir = os.path.join(BASE_DIR, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


class CampaignRequest(BaseModel):
    """
    Request model for campaign generation endpoint.
    
    Attributes:
        product_name: Name of the product/service
        product_desc: Description of the product
        target_audience: Who the campaign targets
        brand_voice: Brand tone/style (default: "Authentic, Refreshing")
        output_language: Language for output (default: "English")
    """
    product_name: str
    product_desc: str
    target_audience: str
    brand_voice: str = "Authentic, Refreshing"
    output_language: str = "English"


@app.get("/", response_class=HTMLResponse)
async def index():
    """
    Serve the main web interface.
    
    Returns:
        HTML content from templates/index.html or error message if file not found
    """
    template_path = os.path.join(BASE_DIR, "templates", "index.html")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Error: templates/index.html not found</h1>",
            status_code=404,
        )


@app.post("/generate")
async def generate(req: CampaignRequest):
    """
    Generate marketing campaign via Server-Sent Events (SSE) streaming.
    
    Args:
        req: CampaignRequest with campaign parameters
        
    Returns:
        StreamingResponse that yields JSON events as campaign generates
        
    Event types:
        - step: Progress update
        - narrative: Final campaign content
        - error: Error message
        - [DONE]: End of stream marker
    """
    async def event_stream():
        # Load previous campaign memory for context
        memory = load_memory()
        yield f"data: {json.dumps({'type': 'step', 'content': f'Loaded memory: {len(memory)} campaigns'})}\n\n"
        await asyncio.sleep(0.1)

        # Generate campaign and stream results
        try:
            async for chunk in run_campaign(req):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        # Signal completion
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")