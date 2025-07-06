import pandas as pd
import json
import logging
from typing import Optional, List, Union
from datetime import datetime, timedelta
import pytz
import os
from pathlib import Path
from events_api import get_events as get_events_api, extract_venue_info, extract_classifications
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PostgreSQLDatabaseAPI:
    """
    Database API for Railway PostgreSQL with all the same functionality as SQLite version.
    Uses Railway's managed PostgreSQL service for reliable persistence.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize PostgreSQL connection using Railway database URL."""
        if database_url is None:
            database_url = os.getenv('DATABASE_URL')
            
        if not database_url:
            raise ValueError("DATABASE_URL environment variable must be set for PostgreSQL connection")
        
        # Parse DATABASE_URL for psycopg2 if needed
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self._init_database()
        logger.info("✅ PostgreSQL database initialized successfully")
    
    def _init_database(self):
        """Initialize database and create essential tables if they don't exist."""
        try:
            with self.engine.connect() as conn:
                # Create events table schema if it doesn't exist
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS events (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        url TEXT,
                        date DATE,
                        time TIME,
                        datetime TIMESTAMP WITH TIME ZONE,
                        timezone TEXT,
                        status TEXT,
                        venue_id TEXT,
                        venue_name TEXT,
                        venue_address TEXT,
                        venue_city TEXT,
                        venue_state TEXT,
                        venue_country TEXT,
                        venue_postal_code TEXT,
                        venue_timezone TEXT,
                        venue_location JSONB,
                        classification_segment TEXT,
                        classification_genre TEXT,
                        classification_subgenre TEXT,
                        classification_type TEXT,
                        classification_subtype TEXT,
                        classification_family BOOLEAN DEFAULT FALSE,
                        price_ranges JSONB,
                        images JSONB,
                        info TEXT,
                        please_note TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create users table if it doesn't exist
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        telegram_id TEXT UNIQUE,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        preferences JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create user_events table for user-event relationships
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS user_events (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        event_id TEXT REFERENCES events(id),
                        status TEXT DEFAULT 'interested',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, event_id)
                    )
                """))
                
                # Create indexes for better performance
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_events_date ON events(date)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_events_city ON events(venue_city)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_events_classification ON events(classification_segment)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)"))
                
                # Create trigger for updated_at
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION update_updated_at_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ language 'plpgsql'
                """))
                
                conn.execute(text("""
                    DROP TRIGGER IF EXISTS update_events_updated_at ON events;
                    CREATE TRIGGER update_events_updated_at
                        BEFORE UPDATE ON events
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column()
                """))
                
                conn.commit()
                logger.info("📊 PostgreSQL schema initialized successfully")
                
        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}")
            raise
    
    def save_table(self, table_name: str, data: pd.DataFrame) -> bool:
        """
        Creates a new table if it doesn't exist, updates if table exists.
        Uses PostgreSQL's ON CONFLICT for efficient upserts.
        
        Args:
            table_name: Name of the table to create/update
            data: Pandas DataFrame containing the data
            
        Returns:
            bool: True if operation successful, False otherwise
        """
        try:
            if data.empty:
                logger.warning(f"⚠️ DataFrame is empty for table '{table_name}'")
                return False
            
            # Special handling for events table with proper JSON serialization
            if table_name == 'events':
                # Convert complex fields to JSON strings for PostgreSQL JSONB
                if 'venue_location' in data.columns:
                    data['venue_location'] = data['venue_location'].apply(
                        lambda x: json.dumps(x) if isinstance(x, dict) else x
                    )
                if 'price_ranges' in data.columns:
                    data['price_ranges'] = data['price_ranges'].apply(
                        lambda x: json.dumps(x) if isinstance(x, list) else x
                    )
                if 'images' in data.columns:
                    data['images'] = data['images'].apply(
                        lambda x: json.dumps(x) if isinstance(x, list) else x
                    )
            
            # Use pandas to_sql with PostgreSQL engine
            data.to_sql(
                table_name, 
                self.engine, 
                if_exists='append', 
                index=False,
                method='multi'  # Faster batch inserts
            )
            
            # Handle conflicts for events table specifically
            if table_name == 'events':
                with self.engine.connect() as conn:
                    # Use ON CONFLICT for upsert behavior
                    conn.execute(text(f"""
                        INSERT INTO {table_name} 
                        SELECT * FROM {table_name}_temp
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            url = EXCLUDED.url,
                            date = EXCLUDED.date,
                            time = EXCLUDED.time,
                            datetime = EXCLUDED.datetime,
                            timezone = EXCLUDED.timezone,
                            status = EXCLUDED.status,
                            venue_name = EXCLUDED.venue_name,
                            venue_city = EXCLUDED.venue_city,
                            venue_country = EXCLUDED.venue_country,
                            classification_segment = EXCLUDED.classification_segment,
                            classification_genre = EXCLUDED.classification_genre,
                            updated_at = CURRENT_TIMESTAMP
                    """))
                    conn.commit()
            
            logger.info(f"✅ Successfully saved {len(data)} records to table '{table_name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving table '{table_name}': {e}")
            return False
    
    def delete_table(self, table_name: str) -> bool:
        """
        Delete a table from the database.
        
        Args:
            table_name: Name of the table to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                # Check if table exists
                result = conn.execute(text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = :table_name
                """), {"table_name": table_name})
                
                if not result.fetchone():
                    logger.warning(f"⚠️ Table '{table_name}' does not exist")
                    return False
                
                # Drop the table
                conn.execute(text(f"DROP TABLE {table_name} CASCADE"))
                conn.commit()
                
                logger.info(f"🗑️ Successfully deleted table '{table_name}'")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error deleting table '{table_name}': {e}")
            return False
    
    def load_prg_data(
        self,
    ) -> bool:
        """
        Load event data from Ticketmaster API and save to PostgreSQL database.
        
        Args:
            table_name: Name of the table to save events to
            city: City to search events in
            country_code: Country code (e.g., "CZ", "US")
            days_ahead: Number of days ahead to search
            classification: Event classifications (comma-separated)
            size: Maximum number of events to fetch
            keyword: Optional keyword to search for
            
        Returns:
            bool: True if data loaded successfully, False otherwise
        """
        try:
            logger.info(f"🎫 Loading event data for Prague, CZ")
            
            # Calculate date range
            now = datetime.now(pytz.UTC)
            future_date = now + timedelta(days=90)
            
            start_date_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            end_date_time = future_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Call Ticketmaster API
            api_response = get_events_api(
                lat_long='50.0755,14.4378',  # Prague center coordinates
                radius=25,  # 25km radius
                start_date_time=start_date_time,
                end_date_time=end_date_time,
                size=min(200, 200),
                sort="date,asc",
                include_tba="no",
                include_tbd="no",
                save_to_file=False
            )
            
            # Extract events data
            events_data = api_response.get('_embedded', {}).get('events', [])
            
            if not events_data:
                logger.warning(f"⚠️ No events found for Prague, CZ")
                return False
            
            logger.info(f"🎭 Processing {len(events_data)} events from Ticketmaster API")
            
            # Transform events data (same logic as SQLite version)
            transformed_events = []
            for event in events_data:
                venue_info = extract_venue_info(event)
                classification_info = extract_classifications(event)
                
                transformed_event = {
                    'id': event.get('id'),
                    'name': event.get('name'),
                    'url': event.get('url'),
                    'date': event.get('dates', {}).get('start', {}).get('localDate'),
                    'time': event.get('dates', {}).get('start', {}).get('localTime'),
                    'datetime': event.get('dates', {}).get('start', {}).get('dateTime'),
                    'timezone': event.get('dates', {}).get('timezone'),
                    'status': event.get('dates', {}).get('status', {}).get('code'),
                    'venue_id': venue_info.get('id') if venue_info else None,
                    'venue_name': venue_info.get('name') if venue_info else None,
                    'venue_address': venue_info.get('address') if venue_info else None,
                    'venue_city': venue_info.get('city') if venue_info else None,
                    'venue_state': venue_info.get('state') if venue_info else None,
                    'venue_country': venue_info.get('country') if venue_info else None,
                    'venue_postal_code': venue_info.get('postal_code') if venue_info else None,
                    'venue_timezone': venue_info.get('timezone') if venue_info else None,
                    'venue_location': venue_info.get('location', {}) if venue_info else {},
                    'classification_segment': classification_info.get('segment') if classification_info else None,
                    'classification_genre': classification_info.get('genre') if classification_info else None,
                    'classification_subgenre': classification_info.get('subgenre') if classification_info else None,
                    'classification_type': classification_info.get('type') if classification_info else None,
                    'classification_subtype': classification_info.get('subtype') if classification_info else None,
                    'classification_family': classification_info.get('family', False) if classification_info else False,
                    'price_ranges': event.get('priceRanges', []),
                    'images': event.get('images', []),
                    'info': event.get('info'),
                    'please_note': event.get('pleaseNote')
                }
                transformed_events.append(transformed_event)
            
            # Convert to DataFrame
            events_df = pd.DataFrame(transformed_events)
            
            # Use PostgreSQL UPSERT for efficient updates
            success = self._upsert_events(events_df)
            
            if success:
                logger.info(f"✅ Successfully loaded {len(events_df)} events to PostgreSQL")
            else:
                logger.error(f"❌ Failed to save events to PostgreSQL")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error loading event data: {e}")
            return False
    
    def _upsert_events(self, events_df: pd.DataFrame) -> bool:
        """Perform efficient UPSERT for events data using PostgreSQL."""
        try:
            with self.engine.connect() as conn:
                # Use PostgreSQL's efficient UPSERT
                for _, event in events_df.iterrows():
                    conn.execute(text("""
                        INSERT INTO events (
                            id, name, url, date, time, datetime, timezone, status,
                            venue_id, venue_name, venue_address, venue_city, venue_state, 
                            venue_country, venue_postal_code, venue_timezone, venue_location,
                            classification_segment, classification_genre, classification_subgenre,
                            classification_type, classification_subtype, classification_family,
                            price_ranges, images, info, please_note
                        ) VALUES (
                            :id, :name, :url, :date, :time, :datetime, :timezone, :status,
                            :venue_id, :venue_name, :venue_address, :venue_city, :venue_state,
                            :venue_country, :venue_postal_code, :venue_timezone, :venue_location,
                            :classification_segment, :classification_genre, :classification_subgenre,
                            :classification_type, :classification_subtype, :classification_family,
                            :price_ranges, :images, :info, :please_note
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            url = EXCLUDED.url,
                            date = EXCLUDED.date,
                            time = EXCLUDED.time,
                            datetime = EXCLUDED.datetime,
                            status = EXCLUDED.status,
                            venue_name = EXCLUDED.venue_name,
                            venue_city = EXCLUDED.venue_city,
                            updated_at = CURRENT_TIMESTAMP
                    """), {
                        'id': event['id'],
                        'name': event['name'],
                        'url': event['url'],
                        'date': event['date'],
                        'time': event['time'],
                        'datetime': event['datetime'],
                        'timezone': event['timezone'],
                        'status': event['status'],
                        'venue_id': event['venue_id'],
                        'venue_name': event['venue_name'],
                        'venue_address': event['venue_address'],
                        'venue_city': event['venue_city'],
                        'venue_state': event['venue_state'],
                        'venue_country': event['venue_country'],
                        'venue_postal_code': event['venue_postal_code'],
                        'venue_timezone': event['venue_timezone'],
                        'venue_location': json.dumps(event['venue_location']),
                        'classification_segment': event['classification_segment'],
                        'classification_genre': event['classification_genre'],
                        'classification_subgenre': event['classification_subgenre'],
                        'classification_type': event['classification_type'],
                        'classification_subtype': event['classification_subtype'],
                        'classification_family': event['classification_family'],
                        'price_ranges': json.dumps(event['price_ranges']),
                        'images': json.dumps(event['images']),
                        'info': event['info'],
                        'please_note': event['please_note']
                    })
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"❌ Error during events upsert: {e}")
            return False
    
    def get_table_data(self, table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
        """Get data from a table as pandas DataFrame."""
        try:
            query = f"SELECT * FROM {table_name}"
            if limit:
                query += f" LIMIT {limit}"
            
            df = pd.read_sql_query(query, self.engine)
            logger.info(f"📊 Retrieved {len(df)} records from table '{table_name}'")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error getting data from table '{table_name}': {e}")
            return pd.DataFrame()
    
    def execute_query(self, query: str, params: Optional[dict] = None) -> List[tuple]:
        """Execute a custom SQL query."""
        try:
            with self.engine.connect() as conn:
                if params:
                    result = conn.execute(text(query), params)
                else:
                    result = conn.execute(text(query))
                
                results = result.fetchall()
                logger.info(f"🔍 Query executed successfully, returned {len(results)} rows")
                return results
                
        except Exception as e:
            logger.error(f"❌ Error executing query: {e}")
            return []


# Factory function to create the appropriate database API
def create_database_api() -> Union[PostgreSQLDatabaseAPI, 'DatabaseAPI']:
    """Create database API based on environment (PostgreSQL for Railway, SQLite for local)."""
    database_url = os.getenv('DATABASE_URL')
    
    if database_url and 'postgresql' in database_url:
        logger.info("🐘 Using PostgreSQL database (Railway)")
        return PostgreSQLDatabaseAPI(database_url)
    