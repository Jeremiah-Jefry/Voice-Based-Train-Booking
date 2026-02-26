#!/usr/bin/env python3
"""
Startup script for Voice Train Booking Platform
Initializes database, installs dependencies, and starts the development server
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Main startup function"""
    print("🚂 Voice Train Booking Platform Setup")
    print("=" * 50)
    
    # Change to project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install dependencies
    print("\n📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        print("Please install dependencies manually: pip install -r requirements.txt")
    
    # Initialize database
    print("\n🗄️  Initializing database...")
    try:
        from app import create_app, db
        
        app = create_app()
        with app.app_context():
            db.create_all()
            print("✅ Database tables created")
            
        # Seed database with sample data
        print("\n🌱 Seeding database with sample data...")
        subprocess.run([sys.executable, "seed_db.py"], check=True)
        print("✅ Sample data added successfully")
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        print("Please run manually: python seed_db.py")
    
    # Display startup information
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\n📋 Quick Start Guide:")
    print("1. Start the server: python run.py")
    print("2. Open: http://localhost:5000")
    print("3. Demo login:")
    print("   - Username: demo_user")
    print("   - Password: password123")
    
    print("\n🎤 Voice Commands to try:")
    print("- 'Search trains from Mumbai to Delhi'")
    print("- 'Check PNR status 1234567890'")
    print("- 'Show my booking history'")
    
    print("\n💻 Development URLs:")
    print("- Home: http://localhost:5000")
    print("- Login: http://localhost:5000/auth/login")
    print("- Voice Interface: http://localhost:5000/voice/interface")
    
    # Ask if user wants to start the server
    start_server = input("\n🚀 Start the development server now? (y/n): ").lower().strip()
    
    if start_server == 'y':
        print("\n🚀 Starting development server...")
        print("Server will be available at: http://localhost:5000")
        print("Press Ctrl+C to stop the server")
        
        try:
            os.system("python run.py")
        except KeyboardInterrupt:
            print("\n👋 Server stopped. Thanks for using Voice Train Booking!")
    else:
        print("\n👋 Setup complete! Run 'python run.py' when ready to start.")

if __name__ == "__main__":
    main()