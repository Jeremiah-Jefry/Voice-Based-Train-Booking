"""
Simple startup script for Voice Train Booking Platform
"""

import os
import sys
from pathlib import Path

def main():
    """Main function to start the app"""
    print("Starting Voice Train Booking Platform...")
    
    # Change to project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Start the Flask app
    print("Starting development server...")
    print("Server will be available at: http://localhost:5000")
    print("Voice interface: http://localhost:5000/voice/interface")
    print("Demo login: Username 'demo_user' / Password 'password123'")
    print("Press Ctrl+C to stop")
    
    try:
        from app import create_app
        app = create_app()
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Error starting server: {e}")
        print("Try running: python run.py")

if __name__ == "__main__":
    main()