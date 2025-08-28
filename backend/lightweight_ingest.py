import pdfplumber
import json
import uuid
import os
from sklearn.feature_extraction.text import TfidfVectorizer
import re

def clean_text(text):
    """Clean and normalize text"""
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

def smart_chunk_text(text, max_chunk_size=800, overlap=100):
    """Create intelligent chunks with sentence awareness"""
    
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # If adding this sentence would exceed max size
        if len(current_chunk) + len(sentence) > max_chunk_size:
            if current_chunk:
                chunks.append(clean_text(current_chunk))
                
                # Start new chunk with overlap (last few words)
                words = current_chunk.split()
                if len(words) > 20:
                    overlap_text = ' '.join(words[-15:])  # Last 15 words
                    current_chunk = overlap_text + " " + sentence
                else:
                    current_chunk = sentence
            else:
                # Single sentence is too long, split it
                if len(sentence) > max_chunk_size:
                    words = sentence.split()
                    for i in range(0, len(words), max_chunk_size//10):
                        chunk_words = words[i:i + max_chunk_size//10]
                        chunks.append(' '.join(chunk_words))
                else:
                    current_chunk = sentence
        else:
            current_chunk += " " + sentence if current_chunk else sentence
    
    # Add the last chunk
    if current_chunk:
        chunks.append(clean_text(current_chunk))
    
    return chunks

def lightweight_ingest_document(file_path, doc_id):
    """Process PDF document for lightweight retrieval system"""
    
    try:
        chunks = []
        page_num = 0
        
        # Extract text from PDF
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_num += 1
                text = page.extract_text()
                
                if text and len(text.strip()) > 50:  # Only process pages with substantial text
                    # Create smart chunks for this page
                    page_chunks = smart_chunk_text(text, max_chunk_size=700, overlap=80)
                    
                    for chunk_idx, chunk_text in enumerate(page_chunks):
                        if len(chunk_text.strip()) > 30:  # Filter out very short chunks
                            chunk_data = {
                                'id': f"{doc_id}_page_{page_num}_chunk_{chunk_idx}",
                                'text': chunk_text,
                                'page': page_num,
                                'chunk_index': chunk_idx,
                                'length': len(chunk_text)
                            }
                            chunks.append(chunk_data)
        
        if not chunks:
            raise Exception("No text content could be extracted from the PDF")
        
        # Save chunks to storage
        chunks_file = f"storage/{doc_id}_chunks.json"
        os.makedirs(os.path.dirname(chunks_file), exist_ok=True)
        
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        
        # Create a simple index file with metadata
        index_data = {
            'doc_id': doc_id,
            'total_chunks': len(chunks),
            'total_pages': page_num,
            'processing_method': 'lightweight_tfidf',
            'chunk_file': chunks_file
        }
        
        index_file = f"storage/{doc_id}.index"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        print(f"Successfully processed document: {len(chunks)} chunks from {page_num} pages")
        return True
        
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        return False

def ingest_document(file_path):
    """Main function to ingest a document (for compatibility)"""
    doc_id = str(uuid.uuid4())
    
    try:
        success = lightweight_ingest_document(file_path, doc_id)
        if success:
            return doc_id
        else:
            return None
    except Exception as e:
        print(f"Document ingestion failed: {str(e)}")
        return None
