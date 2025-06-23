#!/usr/bin/env python3
"""
Simple FastAPI server to serve just the frontend.
This will help us test the frontend without the complexity of the main app.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend."""
    try:
        with open("frontend.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"<h1>Error loading frontend: {e}</h1><p>Current directory: {os.getcwd()}</p><p>Files: {os.listdir('.')}</p>"

if __name__ == "__main__":
    import uvicorn
    print("Starting simple frontend server on http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080) 