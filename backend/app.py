from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import pytz
from events_api import get_events as get_events_api
from events_api import transform_event_simple, extract_venue_info, extract_classifications

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
def get_events_upcoming():
    """Get upcoming events with flexible filtering"""
    
    # Get query parameters with defaults
    city = request.args.get('city', 'Prague')
    country_code = request.args.get('country', 'CZ')
    days_ahead = int(request.args.get('days_ahead', 90))  # Default 3 months ahead
    classification = request.args.get('classification', 'music,sports')  # Can be comma-separated
    size = int(request.args.get('size', 50))
    keyword = request.args.get('keyword', None)
    
    # Calculate current date and future date
    now = datetime.now(pytz.UTC)
    future_date = now + timedelta(days=days_ahead)
    
    # Format dates for API (ISO format)
    start_date_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_date_time = future_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Parse classification parameter
    classification_list = [c.strip() for c in classification.split(',') if c.strip()]
    
    try:
        # Call your Ticketmaster API function
        api_response = get_events_api(
            country_code=country_code,
            city=city,
            classification_name=classification_list,
            keyword=keyword,
            start_date_time=start_date_time,  # From now
            end_date_time=end_date_time,      # Until future date
            size=min(size, 200),              # Max per page
            sort="date,asc",                  # Sort by date ascending
            locale="cs",                      # Czech language
            include_tba="no",                 # Exclude "To Be Announced"
            include_tbd="no",                 # Exclude "To Be Determined"
            save_to_file=False                # Don't save to file for API calls
        )
        
        # Extract events from API response
        events_data = api_response.get('_embedded', {}).get('events', [])
        page_info = api_response.get('page', {})
        
        # Transform events data for frontend (optional - customize as needed)
        transformed_events = []
        for event in events_data:
            transformed_event = {
                'id': event.get('id'),
                'name': event.get('name'),
                'url': event.get('url'),
                'date': event.get('dates', {}).get('start', {}).get('localDate'),
                'time': event.get('dates', {}).get('start', {}).get('localTime'),
                'datetime': event.get('dates', {}).get('start', {}).get('dateTime'),
                'timezone': event.get('dates', {}).get('timezone'),
                'status': event.get('dates', {}).get('status', {}).get('code'),
                'venue': extract_venue_info(event),
                'classifications': extract_classifications(event),
                'price_ranges': event.get('priceRanges', []),
                'images': event.get('images', []),
                'info': event.get('info'),
                'please_note': event.get('pleaseNote')
            }
            transformed_events.append(transformed_event)
        
        return jsonify({
            "events": transformed_events,
            "pagination": {
                "total_events": page_info.get('totalElements', 0),
                "total_pages": page_info.get('totalPages', 0),
                "current_page": page_info.get('number', 0),
                "events_per_page": page_info.get('size', 0),
                "events_on_page": len(events_data)
            },
            "filters_applied": {
                "city": city,
                "country": country_code,
                "classifications": classification_list,
                "keyword": keyword,
                "date_range": {
                    "from": start_date_time,
                    "to": end_date_time,
                    "days_ahead": days_ahead
                }
            },
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error",
            "message": "Failed to fetch upcoming events"
        }), 500


@app.route('/api/events/today', methods=['GET'])
def get_events_today():
    """Get events happening today"""
    
    city = request.args.get('city', 'Prague')
    country_code = request.args.get('country', 'CZ')
    classification = request.args.get('classification', 'music,sports')
    
    # Get today's date range
    today = datetime.now(pytz.UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    start_date_time = today.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_date_time = tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    classification_list = [c.strip() for c in classification.split(',') if c.strip()]
    
    try:
        api_response = get_events_api(
            country_code=country_code,
            city=city,
            classification_name=classification_list,
            start_date_time=start_date_time,
            end_date_time=end_date_time,
            size=100,
            sort="date,asc",
            locale="cs",
            save_to_file=False
        )
        
        events_data = api_response.get('_embedded', {}).get('events', [])
        
        return jsonify({
            "events": [transform_event_simple(event) for event in events_data],
            "total": len(events_data),
            "date": today.strftime("%Y-%m-%d"),
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500


@app.route('/api/events/this-week', methods=['GET'])
def get_events_this_week():
    """Get events happening this week"""
    
    city = request.args.get('city', 'Prague')
    country_code = request.args.get('country', 'CZ')
    classification = request.args.get('classification', 'music,sports')
    
    # Get this week's date range
    now = datetime.now(pytz.UTC)
    week_start = now - timedelta(days=now.weekday())  # Monday
    week_end = week_start + timedelta(days=7)
    
    start_date_time = week_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_date_time = week_end.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    classification_list = [c.strip() for c in classification.split(',') if c.strip()]
    
    try:
        api_response = get_events_api(
            country_code=country_code,
            city=city,
            classification_name=classification_list,
            start_date_time=start_date_time,
            end_date_time=end_date_time,
            size=200,
            sort="date,asc",
            locale="cs",
            save_to_file=False
        )
        
        events_data = api_response.get('_embedded', {}).get('events', [])
        
        return jsonify({
            "events": [transform_event_simple(event) for event in events_data],
            "total": len(events_data),
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)