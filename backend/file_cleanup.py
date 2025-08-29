#!/usr/bin/env python3
"""
File cleanup manager for Talk2PDF backend
Automatically removes old PDF files and associated data to prevent disk space issues
"""

import os
import time
import glob
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FileCleanupManager:
    """Manages cleanup of old PDF files and associated data"""
    
    def __init__(self, storage_dir="storage"):
        self.storage_dir = storage_dir
        # Get settings from environment variables
        self.max_age_hours = int(os.getenv("MAX_STORAGE_AGE_HOURS", "24"))
        self.max_files = int(os.getenv("MAX_STORED_DOCUMENTS", "50"))
        self.auto_cleanup_enabled = os.getenv("AUTO_CLEANUP_ENABLED", "true").lower() == "true"
        
    def get_file_age_hours(self, file_path):
        """Get age of file in hours"""
        try:
            file_time = os.path.getmtime(file_path)
            current_time = time.time()
            age_seconds = current_time - file_time
            return age_seconds / 3600  # Convert to hours
        except:
            return 0
    
    def get_document_files(self, doc_id):
        """Get all files associated with a document ID"""
        files = []
        base_patterns = [
            f"{self.storage_dir}/{doc_id}.pdf",
            f"{self.storage_dir}/{doc_id}.index", 
            f"{self.storage_dir}/{doc_id}_chunks.json"
        ]
        
        for pattern in base_patterns:
            if os.path.exists(pattern):
                files.append(pattern)
        
        return files
    
    def cleanup_old_files(self):
        """Remove old files based on age"""
        removed_count = 0
        freed_space = 0
        
        print(f"🧹 Starting cleanup of files older than {self.max_age_hours} hours...")
        
        # Find all PDF files
        pdf_files = glob.glob(f"{self.storage_dir}/*.pdf")
        
        for pdf_file in pdf_files:
            age_hours = self.get_file_age_hours(pdf_file)
            
            if age_hours > self.max_age_hours:
                # Extract doc_id from filename
                filename = os.path.basename(pdf_file)
                doc_id = filename.replace('.pdf', '')
                
                # Get all associated files
                doc_files = self.get_document_files(doc_id)
                
                # Calculate total size before deletion
                total_size = 0
                for file_path in doc_files:
                    try:
                        total_size += os.path.getsize(file_path)
                    except:
                        pass
                
                # Delete all associated files
                for file_path in doc_files:
                    try:
                        os.remove(file_path)
                        print(f"🗑️  Removed: {file_path} (age: {age_hours:.1f}h)")
                        removed_count += 1
                    except Exception as e:
                        print(f"❌ Error removing {file_path}: {e}")
                
                freed_space += total_size
        
        if removed_count > 0:
            print(f"✅ Cleanup complete: {removed_count} files removed, {freed_space/1024/1024:.1f}MB freed")
        else:
            print("✅ No old files to cleanup")
        
        return removed_count, freed_space
    
    def cleanup_excess_files(self):
        """Remove excess files if we have too many documents"""
        removed_count = 0
        freed_space = 0
        
        # Find all PDF files with their modification times
        pdf_files = glob.glob(f"{self.storage_dir}/*.pdf")
        
        if len(pdf_files) <= self.max_files:
            return removed_count, freed_space
        
        print(f"🧹 Too many documents ({len(pdf_files)}), keeping only {self.max_files} newest...")
        
        # Sort by modification time (oldest first)
        pdf_files_with_time = []
        for pdf_file in pdf_files:
            try:
                mtime = os.path.getmtime(pdf_file)
                pdf_files_with_time.append((pdf_file, mtime))
            except:
                continue
        
        pdf_files_with_time.sort(key=lambda x: x[1])  # Sort by time
        
        # Remove oldest files
        files_to_remove = len(pdf_files) - self.max_files
        for i in range(files_to_remove):
            pdf_file, _ = pdf_files_with_time[i]
            
            # Extract doc_id
            filename = os.path.basename(pdf_file)
            doc_id = filename.replace('.pdf', '')
            
            # Get all associated files
            doc_files = self.get_document_files(doc_id)
            
            # Calculate total size
            total_size = 0
            for file_path in doc_files:
                try:
                    total_size += os.path.getsize(file_path)
                except:
                    pass
            
            # Delete all associated files
            for file_path in doc_files:
                try:
                    os.remove(file_path)
                    print(f"🗑️  Removed excess: {file_path}")
                    removed_count += 1
                except Exception as e:
                    print(f"❌ Error removing {file_path}: {e}")
            
            freed_space += total_size
        
        if removed_count > 0:
            print(f"✅ Excess cleanup complete: {removed_count} files removed, {freed_space/1024/1024:.1f}MB freed")
        
        return removed_count, freed_space
    
    def cleanup_orphaned_files(self):
        """Remove orphaned chunks/index files that don't have corresponding PDFs"""
        removed_count = 0
        freed_space = 0
        
        print("🧹 Cleaning up orphaned files...")
        
        # Find all chunks and index files
        chunk_files = glob.glob(f"{self.storage_dir}/*_chunks.json")
        index_files = glob.glob(f"{self.storage_dir}/*.index")
        
        for chunk_file in chunk_files:
            # Extract doc_id from chunks filename
            filename = os.path.basename(chunk_file)
            doc_id = filename.replace('_chunks.json', '')
            
            # Check if corresponding PDF exists
            pdf_file = f"{self.storage_dir}/{doc_id}.pdf"
            if not os.path.exists(pdf_file):
                try:
                    size = os.path.getsize(chunk_file)
                    os.remove(chunk_file)
                    print(f"🗑️  Removed orphaned: {chunk_file}")
                    removed_count += 1
                    freed_space += size
                except Exception as e:
                    print(f"❌ Error removing {chunk_file}: {e}")
        
        for index_file in index_files:
            # Extract doc_id from index filename  
            filename = os.path.basename(index_file)
            doc_id = filename.replace('.index', '')
            
            # Check if corresponding PDF exists
            pdf_file = f"{self.storage_dir}/{doc_id}.pdf"
            if not os.path.exists(pdf_file):
                try:
                    size = os.path.getsize(index_file)
                    os.remove(index_file)
                    print(f"🗑️  Removed orphaned: {index_file}")
                    removed_count += 1
                    freed_space += size
                except Exception as e:
                    print(f"❌ Error removing {index_file}: {e}")
        
        if removed_count > 0:
            print(f"✅ Orphaned cleanup complete: {removed_count} files removed, {freed_space/1024/1024:.1f}MB freed")
        
        return removed_count, freed_space
    
    def get_storage_stats(self):
        """Get storage directory statistics"""
        stats = {
            'total_files': 0,
            'total_size_mb': 0,
            'pdf_count': 0,
            'chunks_count': 0,
            'index_count': 0
        }
        
        if not os.path.exists(self.storage_dir):
            return stats
        
        for file_path in glob.glob(f"{self.storage_dir}/*"):
            if os.path.isfile(file_path):
                stats['total_files'] += 1
                try:
                    stats['total_size_mb'] += os.path.getsize(file_path) / 1024 / 1024
                except:
                    pass
                
                if file_path.endswith('.pdf'):
                    stats['pdf_count'] += 1
                elif file_path.endswith('_chunks.json'):
                    stats['chunks_count'] += 1
                elif file_path.endswith('.index'):
                    stats['index_count'] += 1
        
        return stats
    
    def run_full_cleanup(self):
        """Run complete cleanup process"""
        print(f"🚀 Starting full cleanup process...")
        
        # Get initial stats
        initial_stats = self.get_storage_stats()
        print(f"📊 Initial: {initial_stats['total_files']} files, {initial_stats['total_size_mb']:.1f}MB")
        
        total_removed = 0
        total_freed = 0
        
        # 1. Remove orphaned files first
        removed, freed = self.cleanup_orphaned_files()
        total_removed += removed
        total_freed += freed
        
        # 2. Remove old files
        removed, freed = self.cleanup_old_files()
        total_removed += removed
        total_freed += freed
        
        # 3. Remove excess files if still too many
        removed, freed = self.cleanup_excess_files()
        total_removed += removed
        total_freed += freed
        
        # Get final stats
        final_stats = self.get_storage_stats()
        
        print(f"🎉 Cleanup Summary:")
        print(f"   Files removed: {total_removed}")
        print(f"   Space freed: {total_freed/1024/1024:.1f}MB")
        print(f"   Final: {final_stats['total_files']} files, {final_stats['total_size_mb']:.1f}MB")
        
        return total_removed, total_freed

def run_cleanup():
    """Main cleanup function"""
    cleanup_manager = FileCleanupManager()
    return cleanup_manager.run_full_cleanup()

if __name__ == "__main__":
    run_cleanup()
