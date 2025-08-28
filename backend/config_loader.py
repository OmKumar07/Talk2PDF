#!/usr/bin/env python3
"""
Environment Configuration Loader for Talk2PDF Backend
Allows easy switching between different environment configurations
"""

import os
import shutil
import sys
from pathlib import Path

def load_environment(env_type):
    """Load specific environment configuration"""
    
    env_files = {
        "dev": ".env.development",
        "development": ".env.development", 
        "prod": ".env.production",
        "production": ".env.production",
        "manual": ".env.manual",
        "custom": ".env.manual"
    }
    
    if env_type not in env_files:
        print(f"❌ Invalid environment type: {env_type}")
        print(f"Available options: {', '.join(env_files.keys())}")
        return False
    
    source_file = env_files[env_type]
    target_file = ".env"
    
    if not os.path.exists(source_file):
        print(f"❌ Environment file {source_file} not found!")
        return False
    
    try:
        # Backup existing .env if it exists
        if os.path.exists(target_file):
            backup_file = f".env.backup.{int(os.path.getmtime(target_file))}"
            shutil.copy2(target_file, backup_file)
            print(f"📋 Backed up existing .env to {backup_file}")
        
        # Copy the new environment file
        shutil.copy2(source_file, target_file)
        print(f"✅ Loaded {source_file} as .env")
        
        # Show configuration summary
        print(f"\n📝 Configuration Summary ({env_type}):")
        with open(target_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Hide sensitive values
                    if 'KEY' in key or 'SECRET' in key or 'TOKEN' in key:
                        value = '***HIDDEN***' if value else 'NOT_SET'
                    print(f"   {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
        return False

def show_available_environments():
    """Show all available environment configurations"""
    print("🌍 Available Environment Configurations:")
    print()
    
    configs = [
        (".env.development", "dev/development", "Local development with debugging"),
        (".env.production", "prod/production", "Production deployment (Render/cloud)"),
        (".env.manual", "manual/custom", "Manual deployment with custom settings")
    ]
    
    for file, alias, description in configs:
        if os.path.exists(file):
            print(f"✅ {alias:<15} - {description}")
        else:
            print(f"❌ {alias:<15} - {description} (file missing)")
    
    print("\nUsage:")
    print("  python config_loader.py <environment>")
    print("  python config_loader.py dev")
    print("  python config_loader.py production")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        show_available_environments()
        sys.exit(1)
    
    env_type = sys.argv[1].lower()
    
    if env_type in ["help", "-h", "--help"]:
        show_available_environments()
        sys.exit(0)
    
    if load_environment(env_type):
        print(f"\n🚀 Environment '{env_type}' loaded successfully!")
        print("You can now start the server with: uvicorn app:app --reload")
    else:
        sys.exit(1)
