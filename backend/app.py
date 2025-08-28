from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid, shutil, os
from ingest import ingest_document
from query import answer_query

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],  # React/Vite frontend
    allow_credentials=True,
    allow_methods=["*"],
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
# Upload PDF Endpoint
# -------------------------
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    doc_id = str(uuid.uuid4())
    path = f"storage/{doc_id}.pdf"
    os.makedirs("storage", exist_ok=True)

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Process and store embeddings
    ingest_document(doc_id, path)

    return {"doc_id": doc_id}


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
        return result  # Return the result directly, not wrapped in another "answer" key
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
