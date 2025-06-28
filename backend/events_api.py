import requests
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
the_key = os.getenv('TM', None)


def get_events(
    # Basic search parameters
    keyword: Optional[str] = None,
    
    # Location filters
    country_code: Optional[str] = None,
    state_code: Optional[str] = None,
    city: Optional[str] = None,
    postal_code: Optional[str] = None,
    market_id: Optional[str] = None,
    dma_id: Optional[str] = None,
    
    # Geographic filters
    lat_long: Optional[str] = None,  # Format: "latitude,longitude"
    geo_point: Optional[str] = None,  # GeoHash
    radius: Optional[int] = None,
    unit: str = "miles",  # "miles" or "km"
    
    # Classification filters
    classification_name: Optional[List[str]] = None,  # e.g., ["music", "sports"]
    classification_id: Optional[List[str]] = None,
    segment_id: Optional[List[str]] = None,
    genre_id: Optional[List[str]] = None,
    subgenre_id: Optional[List[str]] = None,
    type_id: Optional[List[str]] = None,
    subtype_id: Optional[List[str]] = None,
    
    # Venue and attraction filters
    venue_id: Optional[str] = None,
    attraction_id: Optional[str] = None,
    
    # Date filters
    start_date_time: Optional[str] = None,  # ISO format: "2024-01-01T00:00:00Z"
    end_date_time: Optional[str] = None,
    local_start_date_time: Optional[str] = None,
    local_start_end_date_time: Optional[str] = None,
    
    # Sales date filters
    onsale_start_date_time: Optional[str] = None,
    onsale_end_date_time: Optional[str] = None,
    onsale_on_start_date: Optional[str] = None,
    
    # Content filters
    source: Optional[str] = None,  # "ticketmaster", "universe", "frontgate", "tmr"
    include_test: str = "no",  # "yes", "no", "only"
    include_tba: str = "no",  # Include "To Be Announced" events
    include_tbd: str = "no",  # Include "To Be Determined" events
    include_family: str = "yes",  # "yes", "no", "only"
    include_spellcheck: str = "no",
    
    # Pagination and sorting
    size: int = 20,  # Max events per page (max 200)
    page: int = 0,  # Page number
    sort: str = "relevance,desc",  # Sorting options
    
    # Localization
    locale: str = "en",
    preferred_country: str = "us",
    
    # Output options
    save_to_file: bool = False,
    filename: Optional[str] = None,
    print_response: bool = False
) -> Dict[str, Any]:
    """
    Get events from Ticketmaster Discovery API with comprehensive filtering options.
    
    Args:
        api_key: Your Ticketmaster API key
        keyword: Search keyword
        country_code: ISO country code (e.g., "US", "CZ", "GB")
        state_code: State/province code
        city: City name
        postal_code: Postal/ZIP code
        market_id: Market ID for demographic targeting
        dma_id: Designated Market Area ID
        lat_long: "latitude,longitude" for geographic search
        geo_point: GeoHash for geographic search
        radius: Search radius
        unit: Distance unit ("miles" or "km")
        classification_name: List of classification names
        classification_id: List of classification IDs
        segment_id: List of segment IDs (Music, Sports, etc.)
        genre_id: List of genre IDs
        subgenre_id: List of subgenre IDs
        type_id: List of type IDs
        subtype_id: List of subtype IDs
        venue_id: Specific venue ID
        attraction_id: Specific attraction ID
        start_date_time: Start date filter (ISO format)
        end_date_time: End date filter (ISO format)
        local_start_date_time: Local start date filter
        local_start_end_date_time: Local start/end date range
        onsale_start_date_time: On-sale start date filter
        onsale_end_date_time: On-sale end date filter
        onsale_on_start_date: On-sale on specific date
        source: Content source filter
        include_test: Include test events
        include_tba: Include "To Be Announced" events
        include_tbd: Include "To Be Determined" events
        include_family: Include family-friendly events
        include_spellcheck: Include spell check suggestions
        size: Number of events per page (1-200)
        page: Page number (0-based)
        sort: Sort order (relevance,desc | name,asc | date,asc | etc.)
        locale: Language locale
        preferred_country: Country for popularity boost
        save_to_file: Save response to JSON file
        filename: Custom filename for saved file
        print_response: Print the response data
    
    Returns:
        Dictionary containing the API response
        
    Raises:
        requests.RequestException: If API request fails
        ValueError: If invalid parameters provided
    """
    
    # Build the base URL
    base_url = "https://app.ticketmaster.com/discovery/v2/events.json"
    
    # Build parameters dictionary
    params = {
        "apikey": the_key,
        "size": min(size, 200),  # Ensure size doesn't exceed API limit
        "page": page,
        "sort": sort,
        "locale": locale,
        "preferredCountry": preferred_country,
        "includeTest": include_test,
        "includeTBA": include_tba,
        "includeTBD": include_tbd,
        "includeFamily": include_family,
        "includeSpellcheck": include_spellcheck,
        "unit": unit
    }
    
    # Add optional parameters
    optional_params = {
        "keyword": keyword,
        "countryCode": country_code,
        "stateCode": state_code,
        "city": city,
        "postalCode": postal_code,
        "marketId": market_id,
        "dmaId": dma_id,
        "latlong": lat_long,
        "geoPoint": geo_point,
        "radius": radius,
        "venueId": venue_id,
        "attractionId": attraction_id,
        "startDateTime": start_date_time,
        "endDateTime": end_date_time,
        "localStartDateTime": local_start_date_time,
        "localStartEndDateTime": local_start_end_date_time,
        "onsaleStartDateTime": onsale_start_date_time,
        "onsaleEndDateTime": onsale_end_date_time,
        "onsaleOnStartDate": onsale_on_start_date,
        "source": source
    }
    
    # Add non-None optional parameters
    for key, value in optional_params.items():
        if value is not None:
            params[key] = value
    
    # Handle list parameters
    list_params = {
        "classificationName": classification_name,
        "classificationId": classification_id,
        "segmentId": segment_id,
        "genreId": genre_id,
        "subGenreId": subgenre_id,
        "typeId": type_id,
        "subTypeId": subtype_id
    }
    
    for key, value in list_params.items():
        if value is not None and len(value) > 0:
            params[key] = value if isinstance(value, list) else [value]
    
    try:
        # Make the API request
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse JSON response
        data = response.json()
        
        # Print response if requested
        if print_response:
            print(f"API Response Status: {response.status_code}")
            print(f"Total Events Found: {data.get('page', {}).get('totalElements', 'Unknown')}")
            print(f"Events on This Page: {len(data.get('_embedded', {}).get('events', []))}")
            print("-" * 50)
        
        # Save to file if requested
        if save_to_file:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"ticketmaster_events_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
            
            if print_response:
                print(f"Response saved to: {filename}")
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        raise
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        raise
    except Exception as e:
        print(f"Unexpected Error: {e}")
        raise


def get_events_all_pages(api_key: str, max_pages: int = 5, **kwargs) -> List[Dict[str, Any]]:
    """
    Get events from multiple pages (up to max_pages).
    
    Args:
        api_key: Your Ticketmaster API key
        max_pages: Maximum number of pages to fetch
        **kwargs: All other parameters from get_events()
    
    Returns:
        List of all events from all pages
    """
    all_events = []
    page = 0
    
    while page < max_pages:
        try:
            response = get_events(page=page, **kwargs)
            events = response.get('_embedded', {}).get('events', [])
            
            if not events:  # No more events
                break
                
            all_events.extend(events)
            
            # Check if we've reached the last page
            page_info = response.get('page', {})
            if page >= page_info.get('totalPages', 1) - 1:
                break
                
            page += 1
            
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break
    
    return all_events


# Example usage functions
def search_music_events_in_czech_republic() -> Dict[str, Any]:
    """Example: Search for music events in Czech Republic"""
    return get_events(
        keyword="music",
        country_code="CZ",
        classification_name=["music"],
        size=50,
        sort="date,asc",
        save_to_file=True,
        print_response=True
    )


def search_concerts_in_prague(api_key: str) -> Dict[str, Any]:
    """Example: Search for concerts in Prague"""
    return get_events(
        city="Prague",
        country_code="CZ",
        classification_name=["music"],
        genre_id=["KnvZfZ7vAeA"],  # Rock genre ID
        start_date_time="2024-01-01T00:00:00Z",
        size=100,
        print_response=True
    )


def search_sports_events_nearby(api_key: str, latitude: float, longitude: float) -> Dict[str, Any]:
    """Example: Search for sports events near a location"""
    return get_events(
        lat_long=f"{latitude},{longitude}",
        radius=50,
        unit="km",
        classification_name=["sports"],
        size=30,
        sort="distance,asc",
        print_response=True
    )


# Helper functions
def extract_venue_info(event):
    """Extract venue information from event data"""
    venues = event.get('_embedded', {}).get('venues', [])
    if venues:
        venue = venues[0]
        return {
            'id': venue.get('id'),
            'name': venue.get('name'),
            'address': venue.get('address', {}).get('line1'),
            'city': venue.get('city', {}).get('name'),
            'state': venue.get('state', {}).get('name'),
            'country': venue.get('country', {}).get('name'),
            'postal_code': venue.get('postalCode'),
            'timezone': venue.get('timezone'),
            'location': venue.get('location', {})
        }
    return None


def extract_classifications(event):
    """Extract classification information from event data"""
    classifications = event.get('classifications', [])
    if classifications:
        classification = classifications[0]
        return {
            'segment': classification.get('segment', {}).get('name'),
            'genre': classification.get('genre', {}).get('name'),
            'subgenre': classification.get('subGenre', {}).get('name'),
            'type': classification.get('type', {}).get('name'),
            'subtype': classification.get('subType', {}).get('name'),
            'family': classification.get('family', False)
        }
    return None

def transform_event_simple(event):
    """Simple event transformation for basic endpoints"""
    return {
        'id': event.get('id'),
        'name': event.get('name'),
        'date': event.get('dates', {}).get('start', {}).get('localDate'),
        'time': event.get('dates', {}).get('start', {}).get('localTime'),
        'venue_name': extract_venue_info(event).get('name') if extract_venue_info(event) else None,
        'classification': extract_classifications(event).get('segment') if extract_classifications(event) else None,
        'url': event.get('url')
    }