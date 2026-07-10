#!/usr/bin/env python3
"""
Daily Historical Weather Collector - Cloud Version

Collects current weather conditions for ALL racecourses every 2 hours,
regardless of racing schedule. This builds a historical weather database
for feature engineering (e.g., "rainfall last 7 days").

This runs in GitHub Actions every 2 hours automatically.

Author: Claude Code
Date: October 2025
"""

import os
import sqlite3
from datetime import datetime
import argparse
import time

# Import weather functions (in same directory)
from weather import get_comprehensive_weather, VENUE_COORDS

DB_PATH = 'data/venue_daily_weather.db'

# Columns added after the original schema. Stored as (name, sql_type) so
# ensure_database() can add them via ALTER TABLE without losing any
# previously-collected history.
NEW_COLUMNS = [
    ('predicted_going_turf', 'TEXT'),
    ('predicted_going_dirt', 'TEXT'),
    ('turf_likely_off', 'INTEGER'),
    ('going_confidence', 'TEXT'),
    ('venue_aliases', 'TEXT'),
]


class DailyWeatherCollector:
    """Collects daily weather snapshots for all venues"""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.ensure_database()

    def ensure_database(self):
        """Create database and table if they don't exist, and migrate the
        schema forward (additive only) if it already exists."""
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else '.', exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS venue_daily_weather (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Location and time
                venue TEXT NOT NULL,
                country TEXT NOT NULL,
                collection_date TEXT NOT NULL,
                collection_hour INTEGER NOT NULL,
                collection_timestamp TEXT NOT NULL,

                -- Core weather conditions
                temperature REAL,
                apparent_temperature REAL,
                precipitation_current REAL,
                rain_current REAL,
                wind_speed REAL,
                wind_direction REAL,
                wind_gusts REAL,
                humidity REAL,
                dew_point REAL,
                pressure REAL,
                cloud_cover REAL,
                visibility REAL,
                weather_code INTEGER,
                precipitation_probability REAL,

                -- Ground conditions
                soil_moisture_0_1cm REAL,
                soil_moisture_1_3cm REAL,
                soil_moisture_3_9cm REAL,
                soil_temperature_0cm REAL,
                soil_temperature_6cm REAL,
                evapotranspiration REAL,

                -- Historical rainfall
                rainfall_1h REAL,
                rainfall_3h REAL,
                rainfall_6h REAL,
                rainfall_24h REAL,
                rainfall_7d REAL,

                -- Derived features
                ground_saturation_index REAL,
                net_moisture_24h REAL,
                hours_since_rain INTEGER,
                predicted_going TEXT,
                track_drying INTEGER,
                track_wetting INTEGER,

                -- Metadata
                weather_data_quality TEXT,
                weather_fetched_at TEXT NOT NULL,
                temperature_unit TEXT,
                wind_speed_unit TEXT,

                UNIQUE(venue, collection_date, collection_hour)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_venue_daily_weather_venue_date
            ON venue_daily_weather(venue, collection_date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_venue_daily_weather_date
            ON venue_daily_weather(collection_date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_venue_daily_weather_timestamp
            ON venue_daily_weather(collection_timestamp)
        """)

        # Additive schema migration: add any new columns that don't exist
        # yet, so previously-collected history is never lost.
        cursor.execute("PRAGMA table_info(venue_daily_weather)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        for column_name, column_type in NEW_COLUMNS:
            if column_name not in existing_columns:
                cursor.execute(f"ALTER TABLE venue_daily_weather ADD COLUMN {column_name} {column_type}")
                print(f"[MIGRATE] Added column: {column_name} ({column_type})")

        conn.commit()
        conn.close()

        print(f"[OK] Database ready: {self.db_path}")

    def collect_venue_weather(self, venue, coords):
        """Collect current weather for a single venue"""
        now = datetime.now()

        print(f"  {venue:30s}", end=' ', flush=True)

        try:
            weather = get_comprehensive_weather(venue, now)

            if not weather:
                print("[FAIL] No weather data")
                return None

            # Extract summary for display
            temp = weather.get('temperature', 'N/A')
            temp_unit = weather.get('temp_unit', '')
            rain = weather.get('rainfall_24h', 0.0)
            soil = weather.get('soil_moisture_0_1cm', 0.0)
            going_turf = weather.get('predicted_going_turf', 'N/A')
            going_dirt = weather.get('predicted_going_dirt', 'N/A')

            print(f"[OK] {temp}{temp_unit}, Rain24h:{rain:.1f}mm, Soil:{soil:.2f}, Turf:{going_turf}, Dirt:{going_dirt}")

            return {
                'venue': venue,
                'country': coords['country'],
                'weather': weather
            }

        except Exception as e:
            print(f"[ERROR] {e}")
            return None

    def save_to_database(self, venue_data):
        """Save weather data to venue_daily_weather table"""
        if not venue_data or not venue_data.get('weather'):
            return False

        venue = venue_data['venue']
        country = venue_data['country']
        weather = venue_data['weather']

        # Use the canonical venue name resolved by get_comprehensive_weather
        # (handles any old/alias name passed in from VENUE_COORDS iteration)
        canonical_venue = weather.get('venue', venue)

        now = datetime.now()
        collection_date = now.strftime('%Y-%m-%d')
        collection_hour = now.hour
        collection_timestamp = now.isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Insert or replace (in case we run twice in same hour)
            cursor.execute("""
                INSERT OR REPLACE INTO venue_daily_weather (
                    venue, country, collection_date, collection_hour, collection_timestamp,
                    temperature, apparent_temperature, precipitation_current, rain_current,
                    wind_speed, wind_direction, wind_gusts, humidity, dew_point,
                    pressure, cloud_cover, visibility, weather_code, precipitation_probability,
                    soil_moisture_0_1cm, soil_moisture_1_3cm, soil_moisture_3_9cm,
                    soil_temperature_0cm, soil_temperature_6cm, evapotranspiration,
                    rainfall_1h, rainfall_3h, rainfall_6h, rainfall_24h, rainfall_7d,
                    ground_saturation_index, net_moisture_24h, hours_since_rain,
                    predicted_going, track_drying, track_wetting,
                    weather_data_quality, weather_fetched_at, temperature_unit, wind_speed_unit,
                    predicted_going_turf, predicted_going_dirt, turf_likely_off,
                    going_confidence, venue_aliases
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?
                )
            """, (
                canonical_venue, country, collection_date, collection_hour, collection_timestamp,
                weather.get('temperature'), weather.get('apparent_temperature'),
                weather.get('precipitation_current'), weather.get('rain_current'),
                weather.get('wind_speed'), weather.get('wind_direction'),
                weather.get('wind_gusts'), weather.get('humidity'),
                weather.get('dew_point'), weather.get('pressure'),
                weather.get('cloud_cover'), weather.get('visibility'),
                weather.get('weather_code'), weather.get('precipitation_probability'),
                weather.get('soil_moisture_0_1cm'), weather.get('soil_moisture_1_3cm'),
                weather.get('soil_moisture_3_9cm'), weather.get('soil_temperature_0cm'),
                weather.get('soil_temperature_6cm'), weather.get('evapotranspiration'),
                weather.get('rainfall_1h'), weather.get('rainfall_3h'),
                weather.get('rainfall_6h'), weather.get('rainfall_24h'),
                weather.get('rainfall_7d'), weather.get('ground_saturation_index'),
                weather.get('net_moisture_24h'), weather.get('hours_since_rain'),
                weather.get('predicted_going'), weather.get('track_drying'),
                weather.get('track_wetting'), weather.get('data_quality'),
                weather.get('fetched_at'), weather.get('temp_unit'),
                weather.get('wind_unit'),
                weather.get('predicted_going_turf'), weather.get('predicted_going_dirt'),
                weather.get('turf_likely_off'), weather.get('going_confidence'),
                weather.get('venue_aliases')
            ))

            conn.commit()
            return True

        except Exception as e:
            print(f"  [DB ERROR] {venue}: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

    def run_collection(self, test_mode=False):
        """Main collection loop for all venues"""
        print("=" * 80)
        print("  DAILY HISTORICAL WEATHER COLLECTION")
        print("=" * 80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        if test_mode:
            print("[TEST MODE] Collecting for 3 venues only")
            print()
            test_venues = ['Newbury', 'Cheltenham', 'Churchill Downs']
            venues_to_collect = {k: v for k, v in VENUE_COORDS.items() if k in test_venues}
        else:
            venues_to_collect = VENUE_COORDS

        print(f"Collecting weather for {len(venues_to_collect)} venues...")
        print()

        success_count = 0
        fail_count = 0
        failed_venues = []

        # First pass: collect all venues
        for venue, coords in venues_to_collect.items():
            venue_data = self.collect_venue_weather(venue, coords)

            if venue_data and self.save_to_database(venue_data):
                success_count += 1
            else:
                failed_venues.append((venue, coords))
                fail_count += 1

            # Delay to avoid overwhelming the API and prevent timeouts
            time.sleep(0.5)

        # Retry failed venues once more with longer delay
        if failed_venues:
            print()
            print(f"Retrying {len(failed_venues)} failed venues...")
            print()

            for venue, coords in failed_venues:
                time.sleep(2.0)  # Longer delay before retry
                venue_data = self.collect_venue_weather(venue, coords)

                if venue_data and self.save_to_database(venue_data):
                    success_count += 1
                    fail_count -= 1

        # Summary
        print()
        print("=" * 80)
        print("  COLLECTION SUMMARY")
        print("=" * 80)
        print(f"Successful: {success_count}/{len(venues_to_collect)}")
        print(f"Failed: {fail_count}/{len(venues_to_collect)}")
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Show database stats
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM venue_daily_weather")
        total_records = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT venue) FROM venue_daily_weather")
        unique_venues = cursor.fetchone()[0]

        cursor.execute("""
            SELECT MIN(collection_date), MAX(collection_date)
            FROM venue_daily_weather
        """)
        date_range = cursor.fetchone()

        conn.close()

        print("Database Statistics:")
        print(f"  Total records: {total_records}")
        print(f"  Unique venues: {unique_venues}")
        print(f"  Date range: {date_range[0]} to {date_range[1]}")
        print()

        return success_count, fail_count


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(description='Collect daily historical weather for all venues')
    parser.add_argument('--test', action='store_true', help='Test mode (3 venues only)')
    args = parser.parse_args()

    collector = DailyWeatherCollector()
    success, failed = collector.run_collection(test_mode=args.test)

    # Exit with error code only if majority failed or zero succeeded
    # Allow partial failures (e.g., a few API timeouts) to still commit data
    if success == 0:
        print("CRITICAL: All venues failed!")
        exit(1)
    elif failed > success:
        print(f"WARNING: More failures ({failed}) than successes ({success})")
        exit(1)
    else:
        # Success! Even if some venues failed, we got useful data
        exit(0)


if __name__ == '__main__':
    main()
