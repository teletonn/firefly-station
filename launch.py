#!/usr/bin/env python3
"""
Unified launch script for Светлячок LLM Radio System
Launches both the bot and web server simultaneously.
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path

def check_requirements():
    """Check if required files exist."""
    required_files = [
        'main.py',
        'backend/main.py',
        'config.yaml',
        'requirements.txt'
    ]

    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)

    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False

    # Check if React build exists
    if not Path('frontend/build').exists():
        print("⚠️  React frontend not built. Run 'cd frontend && npm install && npm run build' first.")
        print("   The system will still work but admin interface won't be available.")

    return True

def install_dependencies():
    """Install Python dependencies if needed."""
    print("📦 Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def build_frontend():
    """Build React frontend if not already built."""
    if Path('frontend/build').exists():
        print("✅ React frontend already built")
        return True

    if not Path('frontend/package.json').exists():
        print("⚠️  Frontend directory not found, skipping build")
        return True

    print("🔨 Building React frontend...")
    try:
        os.chdir('frontend')
        subprocess.check_call(['npm', 'install'])
        subprocess.check_call(['npm', 'run', 'build'])
        os.chdir('..')
        print("✅ React frontend built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to build frontend: {e}")
        return False
    except FileNotFoundError:
        print("❌ npm not found. Please install Node.js and npm first.")
        return False

def launch_system():
    """Launch the complete system."""
    print("🚀 Launching Светлячок LLM Radio System...")
    print("=" * 50)

    try:
        # Launch the main application
        print("Starting bot and web server...")
        process = subprocess.Popen([sys.executable, 'main.py'])

        print("✅ System launched successfully!")
        print("\n🌐 Web Interface:")
        print("   Admin Panel: http://localhost:8000")
        print("   API Docs: http://localhost:8000/docs")
        print("\n🤖 Bot Status: Running in background")
        print("\n📡 Светлячок Interface: Connected to 192.168.1.135")
        print("\nPress Ctrl+C to stop the system")

        # Wait for the process
        process.wait()

    except KeyboardInterrupt:
        print("\n🛑 Shutting down system...")
        if 'process' in locals():
            process.terminate()
            process.wait()
        print("✅ System shutdown complete")
    except Exception as e:
        print(f"❌ Error launching system: {e}")
        return False

    return True

def main():
    """Main function."""
    print("Светлячок LLM Radio System Launcher")
    print("=" * 40)

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    # Install dependencies
    if not install_dependencies():
        sys.exit(1)

    # Build frontend
    if not build_frontend():
        print("⚠️  Continuing without frontend build...")

    # Launch system
    success = launch_system()

    if success:
        print("\n🎉 System launched successfully!")
    else:
        print("\n💥 Failed to launch system!")
        sys.exit(1)

if __name__ == "__main__":
    main()