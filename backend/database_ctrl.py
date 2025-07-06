import os
import sys
from database import create_database_api
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_events_database():
    """Populate the database with events from multiple cities."""
    
    try:
        # Initialize database
        db = create_database_api()
        logger.info("🚀 Starting database population...")
        
        # List of cities to populate
        cities_to_populate = [
            {"city": "Prague", "country": "CZ", "days": 90},
            {"city": "Berlin", "country": "DE", "days": 60},
            {"city": "Vienna", "country": "AT", "days": 60},
            {"city": "Munich", "country": "DE", "days": 45},
            {"city": "Bratislava", "country": "SK", "days": 45}
        ]
        
        total_events_loaded = 0
        
        for city_config in cities_to_populate:
            logger.info(f"🏙️ Loading events for {city_config['city']}, {city_config['country']}")
            
            success = db.load_prg_data()
            
            if success:
                logger.info(f"✅ Successfully loaded events for {city_config['city']}")
                total_events_loaded += 1
            else:
                logger.error(f"❌ Failed to load events for {city_config['city']}")
        
        logger.info(f"🎉 Database population completed! Processed {total_events_loaded}/{len(cities_to_populate)} cities")
        
        # Get final count
        events_df = db.get_table_data("events", limit=1)
        if not events_df.empty:
            total_count = db.execute_query("SELECT COUNT(*) FROM events")
            if total_count:
                logger.info(f"📊 Total events in database: {total_count[0][0]}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during database population: {e}")
        return False

def main():
    """Main function to run database population."""
    
    # Check if DATABASE_URL is set (required for Railway)
    if not os.getenv('DATABASE_URL'):
        logger.error("❌ DATABASE_URL environment variable not set")
        logger.info("💡 Make sure you're running this on Railway or set DATABASE_URL locally")
        sys.exit(1)
    
    logger.info("🗃️ Railway PostgreSQL detected")
    
    # Run population
    success = populate_events_database()
    
    if success:
        logger.info("🎊 Database population completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Database population failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()