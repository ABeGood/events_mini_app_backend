from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)

# Configure CORS for Telegram domains
CORS(app, origins=[
    "https://web.telegram.org",
    "https://*.telegram.org",
    "https://tg.dev",
    "http://localhost:3000",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:4173",
    "https://abegood.github.io"
])

@app.route('/')
def health_check():
    """Health check endpoint for Railway"""
    return jsonify({
        "status": "healthy",
        "message": "Flask backend is running on Railway!"
    })

@app.route('/api/message', methods=['GET', 'OPTIONS'])  # ✅ Explicitly handle OPTIONS
def get_message():
    """Main endpoint that returns a simple message"""
    if request.method == 'OPTIONS':
        # Handle preflight request
        print("🔍 Handling OPTIONS preflight request")
        return '', 200
    
    print("✅ Handling GET request")
    return jsonify({
        "message": "Hello from Flask backend on Railway! 🚀",
        "status": "success",
        "timestamp": "2025-06-21",
        "service": "telegram-mini-app-backend",
        "request_origin": request.headers.get('Origin')
    })

@app.route('/api/events', methods=['GET'])
def get_events():
    """Additional endpoint for your map events"""
    sample_events = [
        {
            "id": 1,
            "title": "Prague Music Festival",
            "category": "Music",
            "location": [14.4378, 50.0755],
            "description": "Amazing indie rock concert in the heart of Prague"
        },
        {
            "id": 2,
            "title": "Art Gallery Opening",
            "category": "Arts & Theatre",
            "location": [14.4405, 50.0848],
            "description": "Contemporary art exhibition opening night"
        }
    ]
    
    return jsonify({
        "events": sample_events,
        "total": len(sample_events),
        "status": "success"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)