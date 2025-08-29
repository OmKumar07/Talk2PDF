from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid, shutil, os
import asyncio
import gc  # Memory management
import threading
import time
from dotenv import load_dotenv
from lightweight_ingest import lightweight_ingest_document
from gemini_query import answer_query_gemini, answer_complex_query_gemini
from file_cleanup import FileCleanupManager

# Load environment variables from .env file
load_dotenv()

# Production configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Memory optimization settings
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "20971520"))  # Reduced to 20MB from 50MB
MAX_CONCURRENT_UPLOADS = 2  # Limit concurrent processing
PROCESSING_TIMEOUT_MINUTES = 10  # Timeout after 10 minutesort FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid, shutil, os
import asyncio
from dotenv import load_dotenv
from lightweight_ingest import lightweight_ingest_document
from gemini_query import answer_query_gemini, answer_complex_query_gemini

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
DOCS_ENABLED = os.getenv("DOCS_ENABLED", "true").lower() == "true"
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "52428800"))  # 50MB default
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Parse custom allowed origins if provided
CUSTOM_ORIGINS = os.getenv("ALLOWED_ORIGINS", "")
if CUSTOM_ORIGINS:
    custom_origins_list = [origin.strip() for origin in CUSTOM_ORIGINS.split(",")]
else:
    custom_origins_list = []

# Validate required environment variables
if not GEMINI_API_KEY:
    if ENVIRONMENT == "production":
        raise ValueError("GEMINI_API_KEY environment variable is required for production")
    else:
        print("Warning: GEMINI_API_KEY not set. Some features may not work.")
        print("💡 Create a .env file with GEMINI_API_KEY=your_key_here")

app = FastAPI(
    title="Talk2PDF API (Gemini-Powered)",
    description="Lightweight AI-powered PDF document chat interface using Google Gemini",
    version="2.0.0",
    docs_url="/docs" if (ENVIRONMENT == "development" and DOCS_ENABLED) else None,
    redoc_url="/redoc" if (ENVIRONMENT == "development" and DOCS_ENABLED) else None
)

# Store processing status
processing_status = {}

# Initialize cleanup manager
cleanup_manager = FileCleanupManager()

# Background cleanup thread
def periodic_cleanup():
    """Run periodic cleanup in background"""
    while True:
        try:
            # Wait 1 hour between cleanups
            time.sleep(3600)  # 1 hour = 3600 seconds
            print("🧹 Running periodic cleanup...")
            cleanup_manager.run_full_cleanup()
        except Exception as e:
            print(f"❌ Error in periodic cleanup: {e}")
            time.sleep(600)  # Wait 10 minutes on error

# Start cleanup thread
cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()

# CORS configuration with custom origins support
base_origins = []

if ENVIRONMENT == "production":
    base_origins = [
        FRONTEND_URL,
        "https://talkpdf.netlify.app"
    ]
else:
    base_origins = [
        "http://localhost:5173", 
        "http://localhost:5174", 
        "http://127.0.0.1:5173", 
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

# Combine with custom origins
allowed_origins = base_origins + custom_origins_list

# Remove duplicates while preserving order
allowed_origins = list(dict.fromkeys(allowed_origins))

# Debug logging for CORS configuration
print(f"CORS Configuration:")
print(f"Environment: {ENVIRONMENT}")
print(f"Frontend URL: {FRONTEND_URL}")
print(f"Custom Origins: {custom_origins_list}")
print(f"Final Allowed Origins: {allowed_origins}")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Global OPTIONS handler for CORS preflight
@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    return JSONResponse(
        content="OK",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

# -------------------------
# Health Check Endpoint
# -------------------------
@app.get("/")
def health_check():
    return {
        "message": "Talk2PDF Backend (Gemini-Powered) is running!", 
        "status": "healthy",
        "environment": ENVIRONMENT,
        "version": "2.0.0",
        "ai_provider": "Google Gemini",
        "features": ["lightweight", "fast", "accurate"]
    }

@app.get("/health")
def health():
    gemini_status = "configured" if GEMINI_API_KEY else "missing_api_key"
    storage_stats = cleanup_manager.get_storage_stats()
    return {
        "status": "ok",
        "environment": ENVIRONMENT,
        "processing_queue": len(processing_status),
        "gemini_api": gemini_status,
        "version": "2.0.0",
        "storage": {
            "total_files": storage_stats['total_files'],
            "total_size_mb": round(storage_stats['total_size_mb'], 1),
            "pdf_count": storage_stats['pdf_count']
        }
    }

# -------------------------
# Storage Management Endpoints
# -------------------------
@app.post("/cleanup")
def manual_cleanup():
    """Manually trigger storage cleanup"""
    try:
        removed, freed_bytes = cleanup_manager.run_full_cleanup()
        return {
            "status": "success",
            "files_removed": removed,
            "space_freed_mb": round(freed_bytes / 1024 / 1024, 1),
            "message": f"Cleanup completed: {removed} files removed, {freed_bytes/1024/1024:.1f}MB freed"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/storage/stats")
def get_storage_stats():
    """Get storage statistics"""
    stats = cleanup_manager.get_storage_stats()
    return {
        "total_files": stats['total_files'],
        "total_size_mb": round(stats['total_size_mb'], 1),
        "pdf_count": stats['pdf_count'],
        "chunks_count": stats['chunks_count'],
        "index_count": stats['index_count']
    }

# -------------------------
# Background Processing Function
# -------------------------
def process_document_background(doc_id: str, pdf_path: str):
    """Process document in background and update status with memory management"""
    start_time = time.time()
    timeout_seconds = PROCESSING_TIMEOUT_MINUTES * 60
    
    try:
        processing_status[doc_id] = {
            "status": "processing", 
            "progress": 10,
            "start_time": start_time,
            "timeout_minutes": PROCESSING_TIMEOUT_MINUTES
        }
        print(f"Starting lightweight processing for {doc_id}")
        
        # Force garbage collection before processing
        gc.collect()
        
        # Check timeout before processing
        if time.time() - start_time > timeout_seconds:
            raise Exception(f"Processing timeout after {PROCESSING_TIMEOUT_MINUTES} minutes")
        
        # Use lightweight ingest with timeout check
        success = lightweight_ingest_document(pdf_path, doc_id)
        
        # Check timeout after processing
        if time.time() - start_time > timeout_seconds:
            raise Exception(f"Processing timeout after {PROCESSING_TIMEOUT_MINUTES} minutes")
        
        if success:
            # Load the saved chunks to count them
            import json
            chunks_file = f"storage/{doc_id}_chunks.json"
            if os.path.exists(chunks_file):
                # Read file size instead of loading all chunks to save memory
                file_size = os.path.getsize(chunks_file)
                # Estimate chunk count from file size (rough estimate)
                estimated_chunks = max(1, file_size // 200)  # Rough estimate
                num_chunks = estimated_chunks
            else:
                num_chunks = 0
            
            processing_time = time.time() - start_time
            processing_status[doc_id] = {
                "status": "completed", 
                "progress": 100,
                "num_chunks": num_chunks,
                "processing_time_seconds": round(processing_time, 1)
            }
            print(f"Lightweight processing completed for {doc_id}: ~{num_chunks} chunks in {processing_time:.1f}s")
        else:
            raise Exception("Document processing failed")
        
        # Force cleanup after processing
        gc.collect()
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = str(e)
        
        # Check if it's a timeout error
        if "timeout" in error_msg.lower() or processing_time > timeout_seconds:
            error_msg = f"Processing timeout after {PROCESSING_TIMEOUT_MINUTES} minutes. Please try a smaller document with fewer pages."
        
        processing_status[doc_id] = {
            "status": "failed", 
            "progress": 0,
            "error": error_msg,
            "processing_time_seconds": round(processing_time, 1)
        }
        print(f"Background processing failed for {doc_id}: {error_msg}")
        
        # Clean up ALL files associated with failed processing
        try:
            files_to_cleanup = cleanup_manager.get_document_files(doc_id)
            for file_path in files_to_cleanup:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🗑️ Cleaned up failed processing file: {file_path}")
        except Exception as cleanup_error:
            print(f"Error during cleanup: {cleanup_error}")
        
        # Force cleanup on error
        gc.collect()

# -------------------------
# Upload PDF Endpoint (Fast Response)
# -------------------------
@app.post("/upload")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    try:
        # Check if too many documents are being processed
        active_processing = sum(1 for status in processing_status.values() 
                              if status.get("status") == "processing")
        
        if active_processing >= MAX_CONCURRENT_UPLOADS:
            raise HTTPException(
                status_code=429, 
                detail="Too many documents being processed. Please wait and try again."
            )
        
        print(f"Received upload request for file: {file.filename}")
        print(f"Content type: {file.content_type}")
        print(f"File size: {file.size if hasattr(file, 'size') else 'Unknown'}")
        
        # Check file size limit (configurable via environment)
        max_size = MAX_FILE_SIZE
        if hasattr(file, 'size') and file.size and file.size > max_size:
            max_mb = max_size / 1024 / 1024
            current_mb = file.size / 1024 / 1024
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size is {max_mb:.0f}MB, received {current_mb:.1f}MB. Please try a smaller PDF with fewer pages."
            )
        
        if file.content_type != "application/pdf":
            print(f"Invalid content type: {file.content_type}")
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        doc_id = str(uuid.uuid4())
        path = f"storage/{doc_id}.pdf"
        os.makedirs("storage", exist_ok=True)
        
        print(f"Saving file to: {path}")

        # Save file with error handling
        try:
            with open(path, "wb") as f:
                shutil.copyfileobj(file.file, f)
        except Exception as e:
            print(f"Error saving file: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
        print(f"File saved successfully, starting background processing...")

        # Start background processing
        processing_status[doc_id] = {"status": "uploaded", "progress": 0}
        background_tasks.add_task(process_document_background, doc_id, path)

        return {
            "doc_id": doc_id,
            "status": "uploaded",
            "message": f"File uploaded successfully. Processing in background... (timeout: {PROCESSING_TIMEOUT_MINUTES} minutes)",
            "processing_info": {
                "timeout_minutes": PROCESSING_TIMEOUT_MINUTES,
                "file_size_mb": round((file.size / 1024 / 1024), 1) if hasattr(file, 'size') and file.size else None,
                "recommendation": "For faster processing, use PDFs with fewer pages (under 50 pages recommended)"
            }
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        print(f"Unexpected upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        # Force cleanup after each upload
        gc.collect()

# -------------------------
# Check Processing Status Endpoint
# -------------------------
@app.get("/status/{doc_id}")
def get_processing_status(doc_id: str):
    """Check the processing status of a document"""
    if doc_id not in processing_status:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return processing_status[doc_id]


# -------------------------
# Ask Question Endpoint
# -------------------------
class AskRequest(BaseModel):
    doc_id: str
    question: str

@app.post("/ask")
def ask(request: AskRequest):
    """Ask a question about the document using Gemini API"""
    try:
        print(f"Received ask request for doc_id: {request.doc_id}, question: {request.question[:100]}...")
        
        # Check if document is processed
        if request.doc_id not in processing_status:
            print(f"Document {request.doc_id} not found in processing_status")
            raise HTTPException(status_code=404, detail="Document not found. Please upload a document first.")
        
        status = processing_status[request.doc_id]
        print(f"Document {request.doc_id} status: {status}")
        
        if status["status"] == "processing":
            raise HTTPException(
                status_code=202, 
                detail="Document is still being processed. Please wait and try again."
            )
        elif status["status"] == "failed":
            error_msg = status.get("error", "Unknown error")
            raise HTTPException(
                status_code=400, 
                detail=f"Document processing failed: {error_msg}"
            )
        elif status["status"] != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"Document is not ready. Current status: {status['status']}"
            )
        
        # Check if document files actually exist
        chunks_file = f"storage/{request.doc_id}_chunks.json"
        if not os.path.exists(chunks_file):
            print(f"Chunks file not found: {chunks_file}")
            raise HTTPException(
                status_code=404, 
                detail="Document data not found. Please re-upload the document."
            )
        
        print(f"Using Gemini-based query for doc_id: {request.doc_id}")
        
        # Use Gemini-based query with error handling
        try:
            result = answer_query_gemini(request.doc_id, request.question)
            print(f"Gemini query result confidence: {result.get('confidence', 0)}")
        except Exception as e:
            print(f"Error in answer_query_gemini: {e}")
            raise HTTPException(
                status_code=500, 
                detail="Failed to process your question. Please try again with a different question."
            )
        
        # If confidence is low, try complex query approach
        if result.get("confidence", 0) < 0.4:
            try:
                print("Trying alternative complex query approach...")
                alternative_result = answer_complex_query_gemini(request.doc_id, request.question)
                if alternative_result.get("confidence", 0) > result.get("confidence", 0):
                    result = alternative_result
                    print("Using alternative result with higher confidence")
            except Exception as e:
                print(f"Alternative query failed: {e}")
                # Continue with original result
        
        return result
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        print(f"Unexpected error in /ask endpoint: {e}")
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred while processing your question. Please try again."
        )
