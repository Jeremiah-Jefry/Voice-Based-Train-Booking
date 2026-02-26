from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # Run in debug mode for development
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)