from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from core.context import context
import io
import os

app = FastAPI()

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

class ExecRequest(BaseModel):
    code: str

@app.get("/")
async def read_root():
    # Serve debug.html
    debug_html_path = os.path.join(static_dir, "debug.html")
    if os.path.exists(debug_html_path):
        with open(debug_html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return {"message": "Debug UI not found. Please create server/static/debug.html"}

@app.get("/api/screenshot")
async def get_screenshot():
    page = context.page
    if not page:
        raise HTTPException(status_code=503, detail="Browser not initialized or page not available")
    
    try:
        # Take screenshot in memory
        screenshot_bytes = page.screenshot(type="jpeg", quality=80)
        return StreamingResponse(io.BytesIO(screenshot_bytes), media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screenshot failed: {str(e)}")

@app.get("/api/status")
async def get_status():
    page = context.page
    if not page:
        return {"status": "not_ready", "url": None, "title": None}
    
    try:
        return {
            "status": "running",
            "url": page.url,
            "title": page.title()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/exec")
async def exec_code(request: ExecRequest):
    page = context.page
    if not page:
        raise HTTPException(status_code=503, detail="Browser not initialized")
    
    try:
        # Execute JS code
        result = page.evaluate(request.code)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def start_server(host="0.0.0.0", port=8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")
