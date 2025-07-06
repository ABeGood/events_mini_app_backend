from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import pytz
from events_api import get_events as get_events_api
from events_api import transform_event_simple, extract_venue_info, extract_classifications
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    city = request.args.get('city', 'Singapore')
    country_code = request.args.get('country', 'CZ')
    days_ahead = int(request.args.get('days_ahead', 90))
    classification = request.args.get('classification', 'music,sports')
    size = int(request.args.get('size', 50))
    keyword = request.args.get('keyword', None)
    
    # Log request parameters
    logger.info(f"📍 Events request received - City: {city}, Country: {country_code}, Days ahead: {days_ahead}")
    
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
            # lat_long='50.0755,14.4378',  # Prague center coordinates
            # radius=25,  # 25km radius
            # country_code=country_code,
            city=city,
            # classification_name=classification_list,
            keyword=keyword,
            start_date_time=start_date_time,
            end_date_time=end_date_time,
            size=min(size, 200),
            sort="date,asc",
            locale="cs",
            include_tba="no",
            include_tbd="no",
            save_to_file=False
        )
        
        # Extract events from API response
        events_data = api_response.get('_embedded', {}).get('events', [])
        page_info = api_response.get('page', {})
        
        # Log raw events count
        logger.info(f"🎫 Received {len(events_data)} events from Ticketmaster API")
        
        # Transform events data for frontend
        transformed_events = []
        for idx, event in enumerate(events_data):
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
            
            # Log each event details
            venue_name = transformed_event['venue'].get('name', 'Unknown venue') if transformed_event['venue'] else 'No venue'
            venue_city = transformed_event['venue'].get('city', 'Unknown city') if transformed_event['venue'] else 'No city'
            
            logger.info(f"  Event {idx + 1}: '{transformed_event['name']}' at {venue_name}, {venue_city} on {transformed_event['date']}")
        
        # Summary logging
        logger.info(f"✅ Successfully transformed {len(transformed_events)} events")
        logger.info(f"📊 Total events available: {page_info.get('totalElements', 0)} across {page_info.get('totalPages', 0)} pages")
        
        # Log first 5 event names for quick reference
        if transformed_events:
            logger.info("🎭 First few events:")
            for i, event in enumerate(transformed_events[:5]):
                logger.info(f"   {i+1}. {event['name']}")
        
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
        logger.error(f"❌ Error fetching events: {str(e)}")
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
            lat_long='50.0755,14.4378',  # Prague center coordinates
            radius=25,  # 25km radius
            # country_code=country_code,
            # city=city,
            # classification_name=classification_list,
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