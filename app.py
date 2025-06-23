"""
FastAPI web application for PriorAuthAutomation.
Production-ready REST API for prior authorization document processing.
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import our services
from src.services.data_store import save_document_metadata, get_document_metadata, list_documents
from src.services.ocr_service import get_ocr_service_info, perform_tesseract_ocr
from src.services.parsing_service import perform_llamaparse, get_parsing_service_info
from src.services.llm_service import extract_entities_with_gemini, get_llm_service_info
from src.services.pdf_utils import check_pdf_is_native, get_pdf_info
from src.orchestrator import PipelineOrchestrator, get_pipeline_info
import uuid
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
pipeline_orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global pipeline_orchestrator
    
    # Startup
    logger.info("🚀 Starting PriorAuthAutomation API Server...")
    pipeline_orchestrator = PipelineOrchestrator()
    logger.info("✅ Pipeline orchestrator initialized")
    
    yield
    
    # Shutdown
    logger.info("🔄 Shutting down PriorAuthAutomation API Server...")

# Create FastAPI application
app = FastAPI(
    title="PriorAuthAutomation API",
    description="AI-powered REST API for prior authorization document processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend application."""
    try:
        import os
        frontend_path = os.path.join(os.path.dirname(__file__), "frontend.html")
        logger.info(f"Attempting to load frontend from: {frontend_path}")
        with open(frontend_path, "r", encoding="utf-8") as f:
            content = f.read()
            logger.info("Successfully loaded frontend content")
            return content
    except Exception as e:
        logger.error(f"Error loading frontend: {e}")
        logger.info("Falling back to API documentation")
        # Fallback to API documentation if frontend file is not found
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>PriorAuthAutomation API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #2c5282; text-align: center; }
                .feature { background: #e6f3ff; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .endpoint { background: #f0f8f0; padding: 10px; margin: 5px 0; border-radius: 5px; font-family: monospace; }
                .button { display: inline-block; padding: 10px 20px; background: #4299e1; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }
                .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
                .working { background: #c6f6d5; color: #22543d; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🏥 PriorAuthAutomation API</h1>
                
                <div class="status working">
                    <strong>✅ API Status: Online and Ready</strong><br>
                    AI-powered prior authorization document processing
                </div>
                
                <h2>🚀 Key Features</h2>
                <div class="feature">
                    <strong>🤖 AI Entity Extraction:</strong> Google Gemini API extracts patient, medication, and diagnosis information
                </div>
                <div class="feature">
                    <strong>📄 Smart OCR:</strong> Tesseract OCR for scanned documents with image preprocessing
                </div>
                <div class="feature">
                    <strong>🔀 Hybrid Parsing:</strong> LlamaParse + pdfplumber for comprehensive document analysis
                </div>
                <div class="feature">
                    <strong>💾 Complete Audit Trail:</strong> Full document processing history and metadata
                </div>
                
                <h2>📚 API Documentation</h2>
                <a href="/docs" class="button">Interactive API Docs (Swagger)</a>
                <a href="/redoc" class="button">API Documentation (ReDoc)</a>
                
                <h2>🔗 Quick API Endpoints</h2>
                <div class="endpoint">GET /health - System health check</div>
                <div class="endpoint">GET /status - Service status and capabilities</div>
                <div class="endpoint">POST /process-document - Upload and process a PDF</div>
                <div class="endpoint">GET /documents - List all processed documents</div>
                <div class="endpoint">GET /documents/{doc_id} - Get document details</div>
                
                <h2>🧪 Try It Out</h2>
                <p>1. Visit <a href="/docs">/docs</a> for interactive testing</p>
                <p>2. Upload a PDF to <code>/process-document</code></p>
                <p>3. Check processing status with <code>/documents/{doc_id}</code></p>
                
                <p style="text-align: center; margin-top: 30px; color: #666;">
                    Built with FastAPI • Powered by AI • Ready for Production
                </p>
            </div>
        </body>
        </html>
        """

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "PriorAuthAutomation API",
        "version": "1.0.0"
    }

@app.get("/status")
async def get_system_status():
    """Get comprehensive system status and service information."""
    try:
        # Get pipeline info
        pipeline_info = get_pipeline_info()
        
        # Get individual service info
        services = {
            "ocr": get_ocr_service_info(),
            "parsing": get_parsing_service_info(),
            "llm": get_llm_service_info()
        }
        
        return {
            "status": "operational",
            "pipeline": pipeline_info,
            "services": services,
            "capabilities": {
                "ocr": "Tesseract OCR for scanned documents",
                "parsing": "LlamaParse + pdfplumber hybrid extraction",
                "ai_extraction": "Google Gemini entity extraction",
                "storage": "JSON-based document storage with audit trail",
                "formats": ["PDF"]
            }
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-document")
async def process_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    form_template: UploadFile = File(None),
    extract_entities: bool = True,
    use_ocr: bool = True
):
    """
    Process a prior authorization document with optional form template.
    
    - **file**: Source PDF file containing patient information to extract
    - **form_template**: Optional blank form PDF to be filled (uses default if not provided)
    - **extract_entities**: Whether to perform AI entity extraction
    - **use_ocr**: Whether to use OCR for scanned documents
    """
    
    # Validate source file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Source file must be a PDF")
    
    # Validate form template if provided
    if form_template and not form_template.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Form template must be a PDF file")
    
    # Generate document ID
    doc_id = str(uuid.uuid4())
    
    # Save uploaded files temporarily
    temp_source_path = None
    temp_form_path = None
    
    try:
        # Create temporary file for source document
        with tempfile.NamedTemporaryFile(delete=False, suffix='_source.pdf') as temp_file:
            temp_source_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
        
        # Create temporary file for form template if provided
        if form_template:
            with tempfile.NamedTemporaryFile(delete=False, suffix='_form.pdf') as temp_file:
                temp_form_path = temp_file.name
                form_content = await form_template.read()
                temp_file.write(form_content)
        
        # Process documents in background
        background_tasks.add_task(
            process_document_background,
            doc_id,
            temp_source_path,
            temp_form_path,
            file.filename,
            form_template.filename if form_template else None,
            extract_entities,
            use_ocr
        )
        
        return {
            "document_id": doc_id,
            "filename": file.filename,
            "form_template": form_template.filename if form_template else "Default Template",
            "status": "processing",
            "message": "Documents uploaded successfully and processing started",
            "endpoints": {
                "status": f"/documents/{doc_id}",
                "all_documents": "/documents"
            }
        }
        
    except Exception as e:
        # Clean up temp files on error
        if temp_source_path and os.path.exists(temp_source_path):
            os.unlink(temp_source_path)
        if temp_form_path and os.path.exists(temp_form_path):
            os.unlink(temp_form_path)
        logger.error(f"Error processing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_document_background(
    doc_id: str,
    source_path: str,
    form_path: str,
    source_filename: str,
    form_filename: str,
    extract_entities: bool,
    use_ocr: bool
):
    """Background task to process documents."""
    try:
        logger.info(f"Starting background processing for document {doc_id}")
        
        # Save initial metadata
        metadata = {
            "document_id": doc_id,
            "filename": source_filename,
            "form_template": form_filename,
            "status": "processing",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "stages_completed": [],
            "processing_options": {
                "extract_entities": extract_entities,
                "use_ocr": use_ocr,
                "has_form_template": form_path is not None
            }
        }
        save_document_metadata(doc_id, metadata)
        
        # If form template is provided, copy it to the output directory BEFORE processing
        if form_path and form_filename:
            try:
                import shutil
                from pathlib import Path
                
                # Create output directory path for the form template
                output_dir = Path("data")
                template_output_path = output_dir / f"{doc_id}_form_template.pdf"
                
                # Copy the form template to the expected location
                shutil.copy2(form_path, template_output_path)
                
                logger.info(f"Form template saved to: {template_output_path}")
            except Exception as e:
                logger.warning(f"Failed to save form template: {e}")
        
        # Use orchestrator for processing with the specific document ID
        global pipeline_orchestrator
        
        result = pipeline_orchestrator.run_pipeline(
            source_path,
            schema_name="InsureCo_Ozempic",
            document_id=doc_id  # Pass the document ID so it uses the correct template
        )
        
        # Add form template info to results if it was used
        if form_path and form_filename:
            if "summary" not in result:
                result["summary"] = {}
            result["summary"]["form_template_used"] = form_filename
            result["summary"]["form_template_saved"] = f"data/{doc_id}_form_template.pdf"
        
        # Update metadata with completion
        metadata["status"] = "completed"
        metadata["updated_at"] = datetime.now().isoformat()
        metadata["stages_completed"] = result.get("stages_completed", [])
        metadata["processing_summary"] = result.get("summary", {})
        save_document_metadata(doc_id, metadata)
        
        logger.info(f"Completed background processing for document {doc_id}")
        
    except Exception as e:
        logger.error(f"Error in background processing for {doc_id}: {e}")
        # Update metadata with error
        metadata = get_document_metadata(doc_id) or {}
        metadata["status"] = "error"
        metadata["updated_at"] = datetime.now().isoformat()
        metadata["error"] = str(e)
        save_document_metadata(doc_id, metadata)
        
    finally:
        # Clean up temporary files
        if source_path and os.path.exists(source_path):
            os.unlink(source_path)
        if form_path and os.path.exists(form_path):
            os.unlink(form_path)

@app.get("/documents")
async def list_all_documents():
    """List all processed documents."""
    try:
        documents = list_documents()
        return {
            "documents": documents,
            "total_count": len(documents)
        }
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/{doc_id}")
async def get_document_details(doc_id: str):
    """Get detailed information about a specific document."""
    try:
        metadata = get_document_metadata(doc_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "document": metadata,
            "document_id": doc_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/{doc_id}/download")
async def download_processed_data(doc_id: str):
    """Download processed data as JSON."""
    try:
        metadata = get_document_metadata(doc_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            json.dump(metadata, temp_file, indent=2)
            temp_file_path = temp_file.name
        
        return FileResponse(
            temp_file_path,
            media_type='application/json',
            filename=f"{doc_id}_processed.json",
            background=BackgroundTasks().add_task(os.unlink, temp_file_path)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading data for {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/{doc_id}/download-pdf")
async def download_filled_pdf(doc_id: str):
    """Download the filled PDF form."""
    try:
        metadata = get_document_metadata(doc_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check if document processing is completed
        if metadata.get("status") != "completed":
            raise HTTPException(status_code=400, detail="Document processing not completed yet")
        
        # Look for the generated PDF in processing summary
        processing_summary = metadata.get("processing_summary", {})
        output_files = processing_summary.get("output_files", [])
        
        pdf_file = None
        for file_info in output_files:
            if file_info.get("type") == "filled_pdf":
                pdf_file = file_info.get("path")
                break
        
        if not pdf_file:
            raise HTTPException(status_code=404, detail="No filled PDF found for this document")
        
        pdf_path = Path(pdf_file)
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="Filled PDF file not found on disk")
        
        # Get source filename for better naming
        source_filename = metadata.get("filename", "document")
        base_name = Path(source_filename).stem
        
        return FileResponse(
            str(pdf_path),
            media_type='application/pdf',
            filename=f"{base_name}_filled_form.pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading PDF for {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("WORKERS", "1"))
    
    print("🚀 Starting PriorAuthAutomation API Server...")
    print(f"📡 Server will be available at: http://{host}:{port}")
    print(f"📚 API Documentation: http://{host}:{port}/docs")
    print(f"🔧 System Status: http://{host}:{port}/status")
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        workers=workers,
        reload=False,
        log_level="info"
    ) 