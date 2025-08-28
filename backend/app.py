from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid, shutil, os
import asyncio
from ingest import ingest_document
from query import answer_query, answer_complex_query

app = FastAPI()

# Store processing status
processing_status = {}

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:5174", 
        "http://127.0.0.1:5173", 
        "http://127.0.0.1:5174",
        "http://localhost:3000",  # Additional common ports
        "http://127.0.0.1:3000"
    ],  # React/Vite frontend
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# -------------------------
# Health Check Endpoint
# -------------------------
@app.get("/")
def health_check():
    return {"message": "Talk2PDF Backend is running!", "status": "healthy"}

@app.get("/health")
def health():
    return {"status": "ok"}

# -------------------------
# Background Processing Function
# -------------------------
def process_document_background(doc_id: str, pdf_path: str):
    """Process document in background and update status"""
    try:
        processing_status[doc_id] = {"status": "processing", "progress": 0}
        print(f"Starting background processing for {doc_id}")
        
        result = ingest_document(doc_id, pdf_path)
        
        processing_status[doc_id] = {
            "status": "completed", 
            "progress": 100,
            "num_chunks": result.get('num_chunks', 0)
        }
        print(f"Background processing completed for {doc_id}")
        
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
    try:
        result = answer_query(request.doc_id, request.question)
        
        # If the first attempt gives low confidence, try alternative approach
        if result.get("score", 0) < 0.3 and result.get("answer") and len(result["answer"]) < 50:
            try:
                # Try with broader search for complex questions
                alternative_result = answer_complex_query(request.doc_id, request.question)
                if alternative_result.get("score", 0) > result.get("score", 0):
                    result = alternative_result
            except:
                pass  # Fall back to original result
        
        return result  # Return the result directly, not wrapped in another "answer" key
    except Exception as e:
        print(f"Error in /ask endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
