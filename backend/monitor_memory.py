#!/usr/bin/env python3
"""
Memory monitoring script for Talk2PDF backend
"""

import psutil
import os
import time
import json
from datetime import datetime

def get_memory_usage():
    """Get current memory usage"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    memory_percent = process.memory_percent()
    
    return {
        'timestamp': datetime.now().isoformat(),
        'memory_rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
        'memory_vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
        'memory_percent': memory_percent,
        'available_mb': psutil.virtual_memory().available / 1024 / 1024,
        'total_mb': psutil.virtual_memory().total / 1024 / 1024
    }

def log_memory_usage():
    """Log memory usage to file"""
    usage = get_memory_usage()
    
    # Log to console
    print(f"Memory Usage: {usage['memory_rss_mb']:.1f}MB RSS, "
          f"{usage['memory_percent']:.1f}% of system, "
          f"{usage['available_mb']:.0f}MB available")
    
    # Log to file
    log_file = "storage/memory_usage.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(usage) + '\n')
    
    return usage

if __name__ == "__main__":
    print("🔍 Memory monitoring started...")
    while True:
        try:
            usage = log_memory_usage()
            
            # Alert if memory usage is high
            if usage['memory_rss_mb'] > 400:  # Alert if over 400MB
                print(f"⚠️  HIGH MEMORY USAGE: {usage['memory_rss_mb']:.1f}MB")
            
            time.sleep(30)  # Check every 30 seconds
            
        except KeyboardInterrupt:
            print("\n🛑 Memory monitoring stopped")
            break
        except Exception as e:
            print(f"Error in memory monitoring: {e}")
            time.sleep(60)
