import json
import folium
from datetime import datetime

def load_events_from_json(json_file_path):
    """
    Load events data from JSON file and extract relevant information
    """
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    events_list = []
    
    # Extract events from the JSON structure
    if '_embedded' in data and 'events' in data['_embedded']:
        events = data['_embedded']['events']
        
        for event in events:
            event_info = extract_event_data(event)
            if event_info:
                events_list.append(event_info)
    
    return events_list

def extract_event_data(event):
    """
    Extract relevant data from a single event
    """
    try:
        # Get event name
        event_name = event.get('name', 'Unknown Event')
        
        # Get event date
        event_date = 'TBD'
        if 'dates' in event and 'start' in event['dates']:
            local_date = event['dates']['start'].get('localDate', 'TBD')
            if local_date != 'TBD':
                # Format the date nicely
                date_obj = datetime.strptime(local_date, '%Y-%m-%d')
                event_date = date_obj.strftime('%B %d, %Y')
        
        # Get venue information and coordinates
        venue_name = 'Unknown Venue'
        latitude = None
        longitude = None
        city = ''
        country = ''
        
        if '_embedded' in event and 'venues' in event['_embedded']:
            venues = event['_embedded']['venues']
            if venues:
                venue = venues[0]
                venue_name = venue.get('name', 'Unknown Venue')
                
                # Get location coordinates
                if 'location' in venue:
                    latitude = float(venue['location'].get('latitude', 0))
                    longitude = float(venue['location'].get('longitude', 0))
                
                # Get city and country
                if 'city' in venue:
                    city = venue['city'].get('name', '')
                if 'country' in venue:
                    country = venue['country'].get('name', '')
        
        # Only return event if we have valid coordinates
        if latitude and longitude:
            return {
                'name': event_name,
                'date': event_date,
                'venue': venue_name,
                'city': city,
                'country': country,
                'latitude': latitude,
                'longitude': longitude,
                'url': event.get('url', '')
            }
    
    except Exception as e:
        print(f"Error processing event: {e}")
        return None

def create_events_map(events_list, map_center=None):
    """
    Create interactive Folium map with event markers
    """
    if not events_list:
        print("No events to display")
        return None
    
    # Calculate map center if not provided
    if map_center is None:
        avg_lat = sum(event['latitude'] for event in events_list) / len(events_list)
        avg_lon = sum(event['longitude'] for event in events_list) / len(events_list)
        map_center = [avg_lat, avg_lon]
    
    # Create the map
    event_map = folium.Map(
        location=map_center,
        zoom_start=8,
        tiles='OpenStreetMap'
    )
    
    # Add markers for each event
    for event in events_list:
        # Create popup content with HTML formatting
        popup_html = f"""
        <div style="width: 300px;">
            <h4 style="color: #2E86C1; margin-bottom: 10px;">{event['name']}</h4>
            <p><strong>📅 Date:</strong> {event['date']}</p>
            <p><strong>📍 Venue:</strong> {event['venue']}</p>
            <p><strong>🏙️ Location:</strong> {event['city']}, {event['country']}</p>
            {f'<p><a href="{event["url"]}" target="_blank">🎫 Buy Tickets</a></p>' if event['url'] else ''}
        </div>
        """
        
        # Create marker
        folium.Marker(
            location=[event['latitude'], event['longitude']],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=f"{event['name']} - {event['date']}",
            icon=folium.Icon(
                color='red',
                icon='music',
                prefix='fa'
            )
        ).add_to(event_map)
    
    return event_map

def create_advanced_events_map(events_list):
    """
    Create advanced map with additional features - FIXED VERSION
    """
    if not events_list:
        return None
    
    # Calculate map center
    avg_lat = sum(event['latitude'] for event in events_list) / len(events_list)
    avg_lon = sum(event['longitude'] for event in events_list) / len(events_list)
    
    # Create map with custom styling
    event_map = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=8,
        tiles=None
    )
    
    # Add multiple tile layers with proper attributions
    folium.TileLayer('OpenStreetMap').add_to(event_map)
    
    # Fixed tile layers with proper attributions
    folium.TileLayer(
        tiles='https://stamen-tiles-{s}.a.ssl.fastly.net/terrain/{z}/{x}/{y}{r}.png',
        attr='Map tiles by <a href="http://stamen.com">Stamen Design</a>, <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a> &mdash; Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        name='Stamen Terrain',
        overlay=False,
        control=True
    ).add_to(event_map)
    
    folium.TileLayer(
        tiles='CartoDB positron',
        name='CartoDB Positron'
    ).add_to(event_map)
    
    # Alternative: Use only built-in tile layers (simpler approach)
    # folium.TileLayer('CartoDB positron').add_to(event_map)
    # folium.TileLayer('CartoDB dark_matter').add_to(event_map)
    
    # Create marker cluster for better performance with many events
    from folium import plugins
    marker_cluster = plugins.MarkerCluster().add_to(event_map)
    
    # Add markers to cluster
    for i, event in enumerate(events_list):
        # Enhanced popup with more styling
        popup_html = f"""
        <div style="width: 320px; font-family: Arial, sans-serif;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 15px; margin: -10px -10px 10px -10px; 
                        border-radius: 8px 8px 0 0;">
                <h3 style="margin: 0; font-size: 18px;">{event['name']}</h3>
            </div>
            <div style="padding: 10px;">
                <p style="margin: 8px 0;"><strong>📅 Date:</strong> <span style="color: #2E86C1;">{event['date']}</span></p>
                <p style="margin: 8px 0;"><strong>📍 Venue:</strong> {event['venue']}</p>
                <p style="margin: 8px 0;"><strong>🏙️ Location:</strong> {event['city']}, {event['country']}</p>
                <p style="margin: 8px 0;"><strong>🌍 Coordinates:</strong> {event['latitude']:.4f}, {event['longitude']:.4f}</p>
                {f'<div style="text-align: center; margin-top: 15px;"><a href="{event["url"]}" target="_blank" style="background: #E74C3C; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; font-weight: bold;">🎫 Buy Tickets</a></div>' if event['url'] else ''}
            </div>
        </div>
        """
        
        folium.Marker(
            location=[event['latitude'], event['longitude']],
            popup=folium.Popup(popup_html, max_width=400),
            tooltip=f"Click for details: {event['name']}",
            icon=folium.Icon(
                color='darkred',
                icon='calendar',
                prefix='fa'
            )
        ).add_to(marker_cluster)
    
    # Add layer control
    folium.LayerControl().add_to(event_map)
    
    # Add fullscreen button
    plugins.Fullscreen().add_to(event_map)
    
    return event_map

# Main execution
def main():
    """
    Main function to create the map from JSON file
    """
    # Load events from your JSON file
    json_file_path = 'ticketmaster_events.json'  # Your JSON file name
    events = load_events_from_json(json_file_path)
    
    if not events:
        print("No events found in the JSON file")
        return
    
    print(f"Found {len(events)} events:")
    for event in events:
        print(f"- {event['name']} at {event['venue']} on {event['date']}")
    
    # Create basic map
    basic_map = create_events_map(events)
    if basic_map:
        basic_map.save('events_map_basic.html')
        print("Basic map saved as 'events_map_basic.html'")
    
    # Create advanced map
    advanced_map = create_advanced_events_map(events)
    if advanced_map:
        advanced_map.save('events_map_advanced.html')
        print("Advanced map saved as 'events_map_advanced.html'")

if __name__ == "__main__":
    main()