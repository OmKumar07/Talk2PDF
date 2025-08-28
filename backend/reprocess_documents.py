#!/usr/bin/env python3
"""
Script to reprocess existing documents with improved chunking and indexing
"""

import os
import glob
from ingest import ingest_document

def reprocess_all_documents():
    """
    Find all PDFs in storage and reprocess them with improved chunking
    """
    storage_dir = "storage"
    if not os.path.exists(storage_dir):
        print("No storage directory found")
        return
    
    # Find all PDF files in storage
    pdf_files = glob.glob(os.path.join(storage_dir, "*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in storage")
        return
    
    print(f"Found {len(pdf_files)} PDF(s) to reprocess...")
    
    for pdf_path in pdf_files:
        # Extract doc_id from filename (remove .pdf extension)
        filename = os.path.basename(pdf_path)
        doc_id = os.path.splitext(filename)[0]
        
        print(f"\n🔄 Reprocessing: {filename}")
        print(f"   Doc ID: {doc_id}")
        
        try:
            # Reprocess with improved chunking
            result = ingest_document(doc_id, pdf_path)
            print(f"   ✅ Success: {result['num_chunks']} chunks created")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 Reprocessing documents with improved chunking...")
    reprocess_all_documents()
    print("\n✅ Reprocessing complete!")
