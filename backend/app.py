from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import pytz
import logging
from backend.database import create_database_api
import json
from database import create_database_api
db = create_database_api()

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
    """Get upcoming events with flexible filtering from database"""
    
    # Get query parameters with defaults
    city = request.args.get('city', 'Berlin')
    country_code = request.args.get('country', 'CZ')
    days_ahead = int(request.args.get('days_ahead', 90))
    classification = request.args.get('classification', 'music,sports')
    size = int(request.args.get('size', 50))
    keyword = request.args.get('keyword', None)
    
    # Log request parameters
    logger.info(f"📍 Events request received - City: {city}, Country: {country_code}, Days ahead: {days_ahead}")
    
    # Calculate current date and future date for filtering
    now = datetime.now(pytz.UTC)
    future_date = now + timedelta(days=days_ahead)
    
    # Format dates for database filtering
    start_date = now.strftime("%Y-%m-%d")
    end_date = future_date.strftime("%Y-%m-%d")
    
    # Parse classification parameter
    classification_list = [c.strip() for c in classification.split(',') if c.strip()]
    
    try:
        db = create_database_api()
        
        # Build SQL query with filters
        base_query = """
            SELECT * FROM events 
            WHERE date >= ? AND date <= ?
        """
        # params = [start_date, end_date]
        
        # # Add city filter
        # if city and city.lower() != 'all':
        #     base_query += " AND LOWER(venue_city) = LOWER(?)"
        #     params.append(city)
        
        # # Add country filter
        # if country_code and country_code.lower() != 'all':
        #     base_query += " AND LOWER(venue_country) = LOWER(?)"
        #     params.append(country_code)
        
        # # Add keyword filter
        # if keyword:
        #     base_query += " AND LOWER(name) LIKE LOWER(?)"
        #     params.append(f"%{keyword}%")
        
        # # Add classification filter
        # if classification_list and classification_list != ['all']:
        #     classification_conditions = []
        #     for cls in classification_list:
        #         classification_conditions.append("LOWER(classification_segment) = LOWER(?)")
        #         params.append(cls)
        #     if classification_conditions:
        #         base_query += f" AND ({' OR '.join(classification_conditions)})"
        
        # # Add ordering and limit
        # base_query += " ORDER BY date ASC, time ASC LIMIT ?"
        # params.append(str(min(size, 200)))
        
        # Execute query
        # logger.info(f"🔍 Executing database query with {len(params)} parameters")
        events_data = db.execute_query(base_query)
        
        # Get column names for proper data mapping
        columns_query = "PRAGMA table_info(events)"
        column_info = db.execute_query(columns_query)
        column_names = [col[1] for col in column_info]  # col[1] is column name
        
        # Convert query results to list of dictionaries
        events_list = []
        for row in events_data:
            event_dict = dict(zip(column_names, row))
            events_list.append(event_dict)
        
        logger.info(f"🎫 Retrieved {len(events_list)} events from database")
        
        # Transform database data to frontend format
        transformed_events = []
        for idx, event in enumerate(events_list):
            # Parse JSON fields
            try:
                price_ranges = json.loads(event.get('price_ranges', '[]')) if event.get('price_ranges') else []
            except:
                price_ranges = []
            
            try:
                images = json.loads(event.get('images', '[]')) if event.get('images') else []
            except:
                images = []
            
            try:
                venue_location = json.loads(event.get('venue_location', '{}')) if event.get('venue_location') else {}
            except:
                venue_location = {}
            
            # Reconstruct venue info object
            venue_info = None
            if event.get('venue_name'):
                venue_info = {
                    'id': event.get('venue_id'),
                    'name': event.get('venue_name'),
                    'address': event.get('venue_address'),
                    'city': event.get('venue_city'),
                    'state': event.get('venue_state'),
                    'country': event.get('venue_country'),
                    'postal_code': event.get('venue_postal_code'),
                    'timezone': event.get('venue_timezone'),
                    'location': venue_location
                }
            
            # Reconstruct classifications object
            classifications_info = None
            if event.get('classification_segment'):
                classifications_info = {
                    'segment': event.get('classification_segment'),
                    'genre': event.get('classification_genre'),
                    'subgenre': event.get('classification_subgenre'),
                    'type': event.get('classification_type'),
                    'subtype': event.get('classification_subtype'),
                    'family': bool(event.get('classification_family', 0))
                }
            
            # Build transformed event matching frontend expectations
            transformed_event = {
                'id': event.get('id'),
                'name': event.get('name'),
                'url': event.get('url'),
                'date': event.get('date'),
                'time': event.get('time'),
                'datetime': event.get('datetime'),
                'timezone': event.get('timezone'),
                'status': event.get('status'),
                'venue': venue_info,
                'classifications': classifications_info,
                'price_ranges': price_ranges,
                'images': images,
                'info': event.get('info'),
                'please_note': event.get('please_note')
            }
            transformed_events.append(transformed_event)
            
            # Log each event details
            venue_name = venue_info.get('name', 'Unknown venue') if venue_info else 'No venue'
            venue_city = venue_info.get('city', 'Unknown city') if venue_info else 'No city'
            
            logger.info(f"  Event {idx + 1}: '{transformed_event['name']}' at {venue_name}, {venue_city} on {transformed_event['date']}")
        
        # Calculate pagination info (simulated since we're using LIMIT)
        total_events_query = base_query.replace("LIMIT ?", "").replace("ORDER BY date ASC, time ASC ", "")
        total_count_query = f"SELECT COUNT(*) FROM ({total_events_query})"
        # total_params = params[:-1]  # Remove the LIMIT parameter
        
        total_result = db.execute_query(total_count_query)
        total_events = total_result[0][0] if total_result else 0
        
        # Calculate pagination
        events_per_page = min(size, 200)
        total_pages = (total_events + events_per_page - 1) // events_per_page
        current_page = 0
        
        # Summary logging
        logger.info(f"✅ Successfully transformed {len(transformed_events)} events")
        logger.info(f"📊 Total events available: {total_events} across {total_pages} pages")
        
        # Log first 5 event names for quick reference
        if transformed_events:
            logger.info("🎭 First few events:")
            for i, event in enumerate(transformed_events[:5]):
                logger.info(f"   {i+1}. {event['name']}")
        
        # Return response in same format as before
        return jsonify({
            "events": transformed_events,
            "pagination": {
                "total_events": total_events,
                "total_pages": total_pages,
                "current_page": current_page,
                "events_per_page": events_per_page,
                "events_on_page": len(transformed_events)
            },
            "filters_applied": {
                "city": city,
                "country": country_code,
                "classifications": classification_list,
                "keyword": keyword,
                "date_range": {
                    "from": start_date,
                    "to": end_date,
                    "days_ahead": days_ahead
                }
            },
            "status": "success"
        })
        
    except Exception as e:
        logger.error(f"❌ Error fetching events from database: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "error",
            "message": "Failed to fetch upcoming events from database"
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)