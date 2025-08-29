import pdfplumber
import json
import uuid
import os
from sklearn.feature_extraction.text import TfidfVectorizer
import re
import gc  # Garbage collection for memory management

def clean_text(text):
    """Clean and normalize text with memory efficiency"""
    if not text:
        return ""
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

def smart_chunk_text(text, max_chunk_size=600, overlap=50):
    """Create intelligent chunks with sentence awareness and memory optimization"""
    
    if not text or len(text.strip()) < 20:
        return []
    
    # Split into sentences with memory-efficient regex
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
                
                # Start new chunk with smaller overlap to save memory
                words = current_chunk.split()
                if len(words) > 15:
                    overlap_text = ' '.join(words[-8:])  # Reduced overlap
                    current_chunk = overlap_text + " " + sentence
                else:
                    current_chunk = sentence
            else:
                # Single sentence is too long, split it more aggressively
                if len(sentence) > max_chunk_size:
                    words = sentence.split()
                    chunk_size = max_chunk_size // 12  # Smaller chunks
                    for i in range(0, len(words), chunk_size):
                        chunk_words = words[i:i + chunk_size]
                        if chunk_words:
                            chunks.append(' '.join(chunk_words))
                else:
                    current_chunk = sentence
        else:
            current_chunk += " " + sentence if current_chunk else sentence
    
    # Add the last chunk
    if current_chunk:
        chunks.append(clean_text(current_chunk))
    
    # Clear temporary variables
    del sentences
    gc.collect()
    
    return chunks

def lightweight_ingest_document(file_path, doc_id):
    """Process PDF document for lightweight retrieval system with memory optimization"""
    
    try:
        chunks = []
        page_num = 0
        max_pages = 200  # Limit pages to prevent memory issues
        
        # Extract text from PDF with memory management
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            
            # Process pages in batches to manage memory
            batch_size = 10
            for batch_start in range(0, min(total_pages, max_pages), batch_size):
                batch_end = min(batch_start + batch_size, total_pages, max_pages)
                
                for page_idx in range(batch_start, batch_end):
                    page = pdf.pages[page_idx]
                    page_num = page_idx + 1
                    
                    try:
                        text = page.extract_text()
                        
                        if text and len(text.strip()) > 30:  # Only process pages with substantial text
                            # Create smart chunks for this page with smaller chunks
                            page_chunks = smart_chunk_text(text, max_chunk_size=500, overlap=30)
                            
                            for chunk_idx, chunk_text in enumerate(page_chunks):
                                if len(chunk_text.strip()) > 20:  # Filter out very short chunks
                                    chunk_data = {
                                        'id': f"{doc_id}_p{page_num}_c{chunk_idx}",
                                        'text': chunk_text,
                                        'page': page_num,
                                        'chunk_index': chunk_idx
                                    }
                                    chunks.append(chunk_data)
                        
                        # Clear page text to free memory
                        del text
                        
                    except Exception as e:
                        print(f"Error processing page {page_num}: {str(e)}")
                        continue
                
                # Force garbage collection after each batch
                gc.collect()
                
                # Limit total chunks to prevent memory issues
                if len(chunks) > 1000:
                    print(f"Limiting chunks to 1000 for memory efficiency")
                    break
        
        if not chunks:
            raise Exception("No text content could be extracted from the PDF")
        
        # Save chunks to storage with memory-efficient writing
        chunks_file = f"storage/{doc_id}_chunks.json"
        os.makedirs(os.path.dirname(chunks_file), exist_ok=True)
        
        # Write in smaller batches to manage memory
        with open(chunks_file, 'w', encoding='utf-8') as f:
            f.write('[\n')
            for i, chunk in enumerate(chunks):
                if i > 0:
                    f.write(',\n')
                json.dump(chunk, f, ensure_ascii=False)
            f.write('\n]')
        
        # Create a simple index file with metadata
        index_data = {
            'doc_id': doc_id,
            'total_chunks': len(chunks),
            'total_pages': page_num,
            'processing_method': 'lightweight_tfidf_optimized',
            'chunk_file': chunks_file
        }
        
        index_file = f"storage/{doc_id}.index"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        # Clear chunks from memory
        del chunks
        gc.collect()
        
        print(f"Successfully processed document: {index_data['total_chunks']} chunks from {page_num} pages")
        return True
        
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        # Force cleanup on error
        gc.collect()
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
