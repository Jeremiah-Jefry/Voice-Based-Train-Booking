# Voice Train Booking Platform

A revolutionary train ticket booking platform that enables users to search for trains, check PNR status, and make bookings using voice commands. Built with Flask, Web Speech API, and integrated with secure authentication.

##  Features

###  Voice Interface
- **Voice Search**: "Search trains from Mumbai to Delhi tomorrow"
- **PNR Status**: "Check PNR status 1234567890" 
- **Booking History**: "Show my booking history"
- **Multi-language Support**: English (Indian), Hindi support planned

###  Authentication & Security
- Secure username-based authentication system
- Secure password handling with bcrypt
- Session management with timeouts
- CSRF protection for all forms

###  Train Booking Features
- Real-time train search between stations
- Multiple class options (AC 1/2/3, Sleeper, Chair Car)
- Seat availability with cached inventory updates
- PNR generation and booking confirmation
- Booking history and management

###  Responsive Design
- Mobile-friendly voice interface
- Bootstrap 5 responsive design
- Accessibility features (ARIA labels, keyboard navigation)
- Visual feedback for voice recognition states

##  Technology Stack

### Backend
- **Flask** 2.3.3 - Web framework
- **SQLAlchemy** - ORM for database operations
- **Flask-Login** - User session management
- **Flask-Migrate** - Database migrations
- **Werkzeug** - Password hashing and utilities

### Frontend
- **Bootstrap 5** - Responsive CSS framework
- **Web Speech API** - Browser voice recognition
- **Font Awesome** - Icons and visual elements
- **Custom JavaScript** - Voice interface logic

### Database
- **SQLite** (Development) / **PostgreSQL** (Production)
- Comprehensive schema for trains, stations, routes, bookings
- Enum support for booking/seat status

##  Quick Start

### Prerequisites
- Python 3.8+
- Modern browser with Web Speech API support (Chrome, Edge, Safari)
- Microphone access for voice features

### Installation

1. **Clone and setup**:
```bash
git clone <repository-url>
cd train
python start.py
```

2. **Manual setup** (if automated setup fails):
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python seed_db.py

# Start development server
python run.py
```

3. **Access the application**:
   - Open: http://localhost:5000
   - Demo login: Username `demo_user`, Password `password123`

### Voice Features Setup
1. Allow microphone access when prompted
2. Navigate to Voice Interface from the menu
3. Try voice commands like:
   - "Search trains from Mumbai to Delhi"
   - "Check PNR status 1234567890"
   - "Show my booking history"

##  Project Structure

```
train/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── models.py             # Database models
│   ├── auth/                 # Authentication blueprintauth
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── main/                 # Main app blueprint
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── voice/                # Voice interface blueprint
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── api/                  # API endpoints blueprint
│   ├── templates/            # Jinja2 templates
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── main/
│   │   └── voice/
│   └── static/               # CSS, JS, assets
│       ├── css/
│       │   ├── style.css
│       │   └── voice.css
│       └── js/
│           ├── app.js
│           └── voice.js
├── config.py                 # Configuration settings
├── run.py                    # Application entry point  
├── requirements.txt          # Python dependencies
├── seed_db.py               # Database seeder
├── start.py                 # Setup and startup script
└── README.md
```

##  Database Schema

### Core Models
- **User**: User authentication, voice preferences
- **Station**: Railway stations with codes and locations  
- **Train**: Train details with class availability
- **Route**: Source-destination pairs with distances
- **Schedule**: Train timings and pricing for routes
- **Booking**: Reservation records with PNR numbers
- **Seat**: Individual seat allocation and status

### Key Features
- Enum support for booking status, seat status, train classes
- Foreign key relationships for data integrity
- Cached inventory with reservation timeouts
- Voice session tracking for booking workflows

##  Voice Interface Details

### Web Speech API Integration
- **SpeechRecognition**: Continuous listening with interim results
- **SpeechSynthesis**: Text-to-speech responses
- **Error Handling**: Graceful fallbacks for recognition failures
- **Session Management**: Stateful voice conversations

### Voice Command Processing
1. **Speech Recognition**: Convert speech to text using Web Speech API
2. **Command Parsing**: Extract intent and entities using regex patterns
3. **Action Execution**: Process booking requests, searches, status checks
4. **Response Generation**: Provide both text and speech responses

### Supported Commands
```javascript
// Train Search
"Search trains from [source] to [destination]"
"Find trains Mumbai to Delhi tomorrow"
"Book train from Chennai to Bangalore"

// PNR Status
"Check PNR status [10-digit-number]"
"What is the status of PNR 1234567890"

// Booking Management
"Show my bookings"
"Booking history"
"My tickets"

// Help and Navigation
"Help"
"What can you do"
```

##  Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=sqlite:///train_booking.db

# Security
SECRET_KEY=your-secret-key-here
FLASK_DEBUG=True

# Payment (Optional)
STRIPE_PUBLISHABLE_KEY=pk_test_...
RAZORPAY_KEY_ID=rzp_test_...

# External Booking API Integration (Mock)
EXTERNAL_API_BASE=https://api-mock.booking.internal
```

### Voice Settings
```python
# Voice API Configuration
SPEECH_API_TIMEOUT = 10  # seconds
VOICE_LANGUAGE = 'en-IN'

# Booking Configuration  
SEAT_RESERVATION_TIMEOUT = 600   # 10 minutes
INVENTORY_CACHE_TIMEOUT = 900    # 15 minutes
```

##  Development Guide

### Adding New Voice Commands
1. Update regex patterns in `app/voice/routes.py`
2. Create handler function for the new command
3. Add response templates for text and speech
4. Update help documentation in templates

### Database Migrations
```bash
# Create migration
flask db migrate -m "Description of changes"

# Apply migration  
flask db upgrade
```

### Testing Voice Features
1. Use Chrome DevTools for microphone simulation
2. Test with various accents and speaking speeds
3. Verify fallback behavior for recognition failures
4. Test accessibility with screen readers

##  Deployment

### Production Setup
1. **Environment**: Set `FLASK_ENV=production`
2. **Database**: Use PostgreSQL instead of SQLite
3. **Security**: Generate secure `SECRET_KEY`
4. **HTTPS**: Required for Web Speech API in production
5. **Caching**: Configure Redis for session storage

### Recommended Stack
- **Server**: Gunicorn + Nginx
- **Database**: PostgreSQL with connection pooling
- **Caching**: Redis for sessions and inventory
- **CDN**: For static assets and improved performance

##  Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and test thoroughly
4. Commit: `git commit -m "Add feature description"`
5. Push: `git push origin feature-name`
6. Create a Pull Request

##  License

This project is licensed under the MIT License - see the LICENSE file for details.

##  Acknowledgments

- Web Speech API for enabling voice recognition in browsers
- Bootstrap team for the responsive design framework
- Flask community for the excellent documentation and ecosystem
- Indian Railways for inspiration on the booking workflow

---

**🎤 Ready to book your next train journey with just your voice? Start the server and try it out!**
