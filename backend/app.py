from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid, shutil, os
import asyncio
from dotenv import load_dotenv
from lightweight_ingest import lightweight_ingest_document
from gemini_query import answer_query_gemini, answer_complex_query_gemini

# Load environment variables from .env file
load_dotenv()

# Production configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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
    docs_url="/docs" if ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if ENVIRONMENT == "development" else None
)

# Store processing status
processing_status = {}

# Production CORS configuration
if ENVIRONMENT == "production":
    allowed_origins = [
        FRONTEND_URL,
        "https://*.netlify.app",
        "https://*.netlify.com"
    ]
else:
    allowed_origins = [
        "http://localhost:5173", 
        "http://localhost:5174", 
        "http://127.0.0.1:5173", 
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
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
    return {
        "status": "ok",
        "environment": ENVIRONMENT,
        "processing_queue": len(processing_status),
        "gemini_api": gemini_status,
        "version": "2.0.0"
    }

# -------------------------
# Background Processing Function
# -------------------------
def process_document_background(doc_id: str, pdf_path: str):
    """Process document in background and update status"""
    try:
        processing_status[doc_id] = {"status": "processing", "progress": 10}
        print(f"Starting lightweight processing for {doc_id}")
        
        # Use lightweight ingest
        from lightweight_ingest import lightweight_ingest_document
        success = lightweight_ingest_document(pdf_path, doc_id)
        
        if success:
            # Load the saved chunks to count them
            import json
            chunks_file = f"storage/{doc_id}_chunks.json"
            if os.path.exists(chunks_file):
                with open(chunks_file, 'r', encoding='utf-8') as f:
                    chunks = json.load(f)
                num_chunks = len(chunks)
            else:
                num_chunks = 0
            
            processing_status[doc_id] = {
                "status": "completed", 
                "progress": 100,
                "num_chunks": num_chunks
            }
            print(f"Lightweight processing completed for {doc_id}: {num_chunks} chunks")
        else:
            raise Exception("Document processing failed")
        
    except Exception as e:
        processing_status[doc_id] = {
            "status": "failed", 
            "progress": 0,
            "error": str(e)
        }
        print(f"Background processing failed for {doc_id}: {e}")
        # Clean up the saved file if processing fails
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

# -------------------------
# Upload PDF Endpoint (Fast Response)
# -------------------------
@app.post("/upload")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    try:
        print(f"Received upload request for file: {file.filename}")
        print(f"Content type: {file.content_type}")
        print(f"File size: {file.size if hasattr(file, 'size') else 'Unknown'}")
        
        # Check file size limit (50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if hasattr(file, 'size') and file.size and file.size > max_size:
            raise HTTPException(status_code=413, detail=f"File too large. Maximum size is 50MB, received {file.size/1024/1024:.1f}MB")
        
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
            "message": "File uploaded successfully. Processing in background..."
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        print(f"Unexpected upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

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
        # Check if document is processed
        if request.doc_id not in processing_status:
            raise HTTPException(status_code=404, detail="Document not found")
        
        status = processing_status[request.doc_id]
        if status["status"] != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"Document is still processing. Status: {status['status']}"
            )
        
        # Use Gemini-based query
        result = answer_query_gemini(request.doc_id, request.question)
        
        # If confidence is low, try complex query approach
        if result.get("confidence", 0) < 0.4:
            try:
                alternative_result = answer_complex_query_gemini(request.doc_id, request.question)
                if alternative_result.get("confidence", 0) > result.get("confidence", 0):
                    result = alternative_result
            except Exception as e:
                print(f"Alternative query failed: {e}")
                # Continue with original result
        
        return result
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        print(f"Error in /ask endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
