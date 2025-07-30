#!/usr/bin/env python3
"""
Setup script for Zenskar Backend development environment.
"""
import os
import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    """Run a shell command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False


def main():
    """Main setup function."""
    print("🚀 Setting up Zenskar Backend development environment")
    print("=" * 50)
    
    # Check if .env file exists
    if not Path(".env").exists():
        if Path(".env.example").exists():
            print("📋 Creating .env file from .env.example...")
            with open(".env.example", "r") as src, open(".env", "w") as dst:
                dst.write(src.read())
            print("✅ .env file created")
            print("⚠️  Please update .env with your actual credentials")
        else:
            print("❌ .env.example not found")
            return False
    
    # Check Python version
    if sys.version_info < (3, 11):
        print("❌ Python 3.11+ is required")
        return False
    
    # Install Python dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return False
    
    # Check Docker
    if not run_command("docker --version", "Checking Docker installation"):
        print("❌ Docker is required. Please install Docker Desktop")
        return False
    
    # Check Docker Compose
    if not run_command("docker-compose --version", "Checking Docker Compose"):
        print("❌ Docker Compose is required")
        return False
    
    # Start infrastructure services
    if not run_command("docker-compose up -d postgres kafka", "Starting infrastructure services"):
        return False
    
    # Wait for services to be ready
    print("⏳ Waiting for services to be ready...")
    import time
    time.sleep(10)
    
    # Check service health
    if not run_command("docker-compose ps", "Checking service status"):
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("\n📝 Next steps:")
    print("1. Update .env file with your Stripe credentials")
    print("2. Run: python run.py (to start API server)")
    print("3. Run: python -m src.workers.outbound_sync (to start worker)")
    print("4. Visit: http://localhost:8000/docs (for API documentation)")
    print("\n📚 For more information, see README.md")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
