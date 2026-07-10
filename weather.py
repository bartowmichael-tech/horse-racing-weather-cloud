#!/usr/bin/env python3
"""
Weather data collection using Open-Meteo API

This is a standalone copy of the weather module for cloud deployment.
Does not require any other project dependencies.
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Racecourse/Racetrack Coordinates - canonical (Equibase-style) names.
# Old / alternate names used previously are resolved via VENUE_ALIASES below,
# so lookups by a previously-used name still work without breaking anything.
# ============================================================================
VENUE_COORDS = {
    # UK Racecourses (36 venues)
    "Aintree": {"lat": 53.4748, "lon": -2.9499, "country": "UK", "tz": "Europe/London"},
    "Ascot": {"lat": 51.4088, "lon": -0.6764, "country": "UK", "tz": "Europe/London"},
    "Ayr": {"lat": 55.4598, "lon": -4.6286, "country": "UK", "tz": "Europe/London"},
    "Bangor-on-Dee": {"lat": 52.9910, "lon": -2.9235, "country": "UK", "tz": "Europe/London"},
    "Bath": {"lat": 51.4183, "lon": -2.4094, "country": "UK", "tz": "Europe/London"},
    "Brighton": {"lat": 50.8248, "lon": -0.1072, "country": "UK", "tz": "Europe/London"},
    "Cheltenham": {"lat": 51.9250, "lon": -2.0500, "country": "UK", "tz": "Europe/London"},
    "Chepstow": {"lat": 51.6431, "lon": -2.6764, "country": "UK", "tz": "Europe/London"},
    "Chester": {"lat": 53.1852, "lon": -2.8932, "country": "UK", "tz": "Europe/London"},
    "Doncaster": {"lat": 53.5229, "lon": -1.0958, "country": "UK", "tz": "Europe/London"},
    "Epsom": {"lat": 51.3146, "lon": -0.2440, "country": "UK", "tz": "Europe/London"},
    "Ffos Las": {"lat": 51.7311, "lon": -4.2400, "country": "UK", "tz": "Europe/London"},
    "Fontwell": {"lat": 50.8667, "lon": -0.6167, "country": "UK", "tz": "Europe/London"},
    "Goodwood": {"lat": 50.8787, "lon": -0.7477, "country": "UK", "tz": "Europe/London"},
    "Haydock": {"lat": 53.4833, "lon": -2.6500, "country": "UK", "tz": "Europe/London"},
    "Hereford": {"lat": 52.073, "lon": -2.729, "country": "UK", "tz": "Europe/London"},
    "Hexham": {"lat": 54.9522, "lon": -2.1245, "country": "UK", "tz": "Europe/London"},
    "Kempton Park": {"lat": 51.4167, "lon": -0.4000, "country": "UK", "tz": "Europe/London"},
    "Lingfield": {"lat": 51.1817, "lon": -0.0100, "country": "UK", "tz": "Europe/London"},
    "Ludlow": {"lat": 52.3667, "lon": -2.7167, "country": "UK", "tz": "Europe/London"},
    "Market Rasen": {"lat": 53.4500, "lon": -0.3333, "country": "UK", "tz": "Europe/London"},
    "Newbury": {"lat": 51.4008, "lon": -1.3267, "country": "UK", "tz": "Europe/London"},
    "Newcastle": {"lat": 54.9783, "lon": -1.6178, "country": "UK", "tz": "Europe/London"},
    "Newmarket": {"lat": 52.2458, "lon": 0.3822, "country": "UK", "tz": "Europe/London"},
    "Newton Abbot": {"lat": 50.5365, "lon": -3.5920, "country": "UK", "tz": "Europe/London"},
    "Plumpton": {"lat": 50.9216, "lon": -0.0570, "country": "UK", "tz": "Europe/London"},
    "Ripon": {"lat": 54.1207, "lon": -1.4923, "country": "UK", "tz": "Europe/London"},
    "Sandown": {"lat": 51.3333, "lon": -0.5667, "country": "UK", "tz": "Europe/London"},
    "Sedgefield": {"lat": 54.6667, "lon": -1.4667, "country": "UK", "tz": "Europe/London"},
    "Southwell": {"lat": 53.0833, "lon": -0.9500, "country": "UK", "tz": "Europe/London"},
    "Uttoxeter": {"lat": 52.9000, "lon": -1.8667, "country": "UK", "tz": "Europe/London"},
    "Wetherby": {"lat": 53.9333, "lon": -1.3833, "country": "UK", "tz": "Europe/London"},
    "Wolverhampton": {"lat": 52.5833, "lon": -2.1333, "country": "UK", "tz": "Europe/London"},
    "Worcester": {"lat": 52.1886, "lon": -2.2274, "country": "UK", "tz": "Europe/London"},
    "Yarmouth": {"lat": 52.6263, "lon": 1.7338, "country": "UK", "tz": "Europe/London"},
    "York": {"lat": 53.9500, "lon": -1.0833, "country": "UK", "tz": "Europe/London"},

    # USA Racetracks (30 venues)
    "Aqueduct": {"lat": 40.6733, "lon": -73.8348, "country": "USA", "tz": "America/New_York"},
    "Belmont Park": {"lat": 40.6723, "lon": -73.8308, "country": "USA", "tz": "America/New_York"},
    "Belmont At The Big A": {"lat": 40.6733, "lon": -73.8348, "country": "USA", "tz": "America/New_York"},
    "Canterbury Park": {"lat": 44.7907, "lon": -93.4828, "country": "USA", "tz": "America/Chicago"},
    "Charles Town": {"lat": 39.2887, "lon": -77.8347, "country": "USA", "tz": "America/New_York"},
    "Churchill Downs": {"lat": 38.2048, "lon": -85.7702, "country": "USA", "tz": "America/New_York"},
    "Colonial Downs": {"lat": 37.5228, "lon": -76.9964, "country": "USA", "tz": "America/New_York"},
    "Del Mar": {"lat": 32.9803, "lon": -117.2577, "country": "USA", "tz": "America/Los_Angeles"},
    "Delaware Park": {"lat": 39.7248, "lon": -75.6538, "country": "USA", "tz": "America/New_York"},
    "Ellis Park": {"lat": 37.8562, "lon": -87.5905, "country": "USA", "tz": "America/Chicago"},
    "Fair Grounds Race Course": {"lat": 29.9953, "lon": -90.0989, "country": "USA", "tz": "America/Chicago"},
    "Finger Lakes": {"lat": 42.9739, "lon": -77.3252, "country": "USA", "tz": "America/New_York"},
    "Gulfstream Park": {"lat": 25.9898, "lon": -80.1373, "country": "USA", "tz": "America/New_York"},
    "Horseshoe Indianapolis": {"lat": 39.5893, "lon": -85.8245, "country": "USA", "tz": "America/Indiana/Indianapolis"},
    "Keeneland": {"lat": 38.0403, "lon": -84.5909, "country": "USA", "tz": "America/New_York"},
    "Kentucky Downs": {"lat": 36.6739, "lon": -86.5477, "country": "USA", "tz": "America/Chicago"},
    "Laurel Park": {"lat": 39.1043, "lon": -76.8303, "country": "USA", "tz": "America/New_York"},
    "Monmouth Park": {"lat": 40.3140, "lon": -74.0086, "country": "USA", "tz": "America/New_York"},
    "Mountaineer": {"lat": 40.5262, "lon": -80.6081, "country": "USA", "tz": "America/New_York"},
    "Oaklawn Park": {"lat": 34.5101, "lon": -93.0586, "country": "USA", "tz": "America/Chicago"},
    "Parx Racing": {"lat": 40.1204, "lon": -74.9535, "country": "USA", "tz": "America/New_York"},
    "Penn National": {"lat": 40.3226, "lon": -76.6636, "country": "USA", "tz": "America/New_York"},
    "Pimlico": {"lat": 39.3719, "lon": -76.6659, "country": "USA", "tz": "America/New_York"},
    "Prairie Meadows": {"lat": 41.6545, "lon": -93.4649, "country": "USA", "tz": "America/Chicago"},
    "Presque Isle Downs": {"lat": 42.0839, "lon": -80.1067, "country": "USA", "tz": "America/New_York"},
    "Santa Anita Park": {"lat": 34.1395, "lon": -118.0377, "country": "USA", "tz": "America/Los_Angeles"},
    "Saratoga Race Course": {"lat": 43.0751, "lon": -73.7840, "country": "USA", "tz": "America/New_York"},
    "Tampa Bay Downs": {"lat": 28.0435, "lon": -82.6699, "country": "USA", "tz": "America/New_York"},
    "Thistledown": {"lat": 41.4362, "lon": -81.5379, "country": "USA", "tz": "America/New_York"},
    "Turfway Park": {"lat": 39.0334, "lon": -84.6266, "country": "USA", "tz": "America/New_York"},

    # Canada Racetracks (2 venues)
    "Assiniboia Downs": {"lat": 49.8951, "lon": -97.2867, "country": "CAN", "tz": "America/Winnipeg"},
    "Woodbine": {"lat": 43.7075, "lon": -79.6012, "country": "CAN", "tz": "America/Toronto"},
}

# ============================================================================
# Venue name aliases: old/alternate name -> canonical VENUE_COORDS key.
# Anything still matching on a previous name (e.g. "Churchill", "Tampa",
# "Horseshoe") keeps working without needing changes elsewhere.
# ============================================================================
VENUE_ALIASES = {
    "Ffos": "Ffos Las",
    "Newton": "Newton Abbot",
    "Belmont": "Belmont Park",
    "Canterbury": "Canterbury Park",
    "Churchill": "Churchill Downs",
    "Del Mar (US)": "Del Mar",
    "Fair Grounds": "Fair Grounds Race Course",
    "Gulfstream": "Gulfstream Park",
    "Horseshoe": "Horseshoe Indianapolis",
    "Laurel": "Laurel Park",
    "Oaklawn": "Oaklawn Park",
    "Santa": "Santa Anita Park",
    "Saratoga": "Saratoga Race Course",
    "Tampa": "Tampa Bay Downs",
}


def resolve_venue(name: str) -> Optional[str]:
    """Resolve a venue name (possibly an old/alternate name) to its canonical
    VENUE_COORDS key. Returns None if the venue is unknown."""
    if name in VENUE_COORDS:
        return name
    return VENUE_ALIASES.get(name)


def get_venue_aliases(canonical_name: str) -> str:
    """Return a comma-separated string of known alternate names for a
    canonical venue (empty string if none)."""
    aliases = [old for old, new in VENUE_ALIASES.items() if new == canonical_name]
    return ", ".join(aliases)


# ============================================================================
# Going prediction thresholds. These are named constants so they can be
# calibrated later against known real-world conditions without touching
# the calculation logic itself.
# ============================================================================

# --- Turf going (European/UK scale), based on surface soil moisture ---
TURF_FIRM_MAX = 0.15
TURF_GOOD_MAX = 0.25
TURF_SOFT_MAX = 0.35
# soil_moisture_surface > TURF_SOFT_MAX => Heavy

# --- US dirt going scale (Fast / Good / Muddy / Sloppy) ---
# rainfall figures are normalized to millimeters before being compared here,
# regardless of the unit system used for display (see rainfall_24h_mm below).
DIRT_SLOPPY_SATURATION = 0.40
DIRT_SLOPPY_RAIN_24H_MM = 15.0
DIRT_MUDDY_SATURATION = 0.30
DIRT_MUDDY_RAIN_24H_MM = 5.0
DIRT_GOOD_HOURS_SINCE_RAIN_MAX = 12
DIRT_FAST_HOURS_SINCE_RAIN_MIN = 24
DIRT_FAST_SATURATION_MAX = 0.20

# --- Off-the-turf likelihood (turf races moved to main/dirt track) ---
TURF_OFF_RAIN_24H_MM = 10.0
TURF_OFF_PRECIP_PROBABILITY_PCT = 70


def compute_predicted_going_turf(soil_moisture_surface: float) -> str:
    """European/UK-style turf going scale, based on surface soil moisture."""
    if soil_moisture_surface < TURF_FIRM_MAX:
        return "Firm"
    elif soil_moisture_surface < TURF_GOOD_MAX:
        return "Good"
    elif soil_moisture_surface < TURF_SOFT_MAX:
        return "Soft"
    else:
        return "Heavy"


def compute_predicted_going_dirt(ground_saturation_index: float, rainfall_24h_mm: float,
                                  hours_since_rain: int, soil_moisture_surface: float) -> str:
    """US dirt-track going scale (Fast / Good / Muddy / Sloppy). Starting
    logic only - tune the constants above once you have known conditions
    to calibrate against."""
    if ground_saturation_index >= DIRT_SLOPPY_SATURATION or rainfall_24h_mm >= DIRT_SLOPPY_RAIN_24H_MM:
        return "Sloppy"
    elif ground_saturation_index >= DIRT_MUDDY_SATURATION or rainfall_24h_mm >= DIRT_MUDDY_RAIN_24H_MM:
        return "Muddy"
    elif hours_since_rain <= DIRT_GOOD_HOURS_SINCE_RAIN_MAX or soil_moisture_surface > DIRT_FAST_SATURATION_MAX:
        return "Good"
    elif hours_since_rain >= DIRT_FAST_HOURS_SINCE_RAIN_MIN and soil_moisture_surface <= DIRT_FAST_SATURATION_MAX:
        return "Fast"
    else:
        return "Good"


def compute_turf_likely_off(rainfall_24h_mm: float, track_wetting: bool, precipitation_probability: float) -> bool:
    """Flags a heightened chance that turf races get moved to the main
    (dirt) track because of recent/forecast rain."""
    heavy_recent_rain = rainfall_24h_mm >= TURF_OFF_RAIN_24H_MM
    trending_wetter = track_wetting or (precipitation_probability or 0) >= TURF_OFF_PRECIP_PROBABILITY_PCT
    return bool(heavy_recent_rain and trending_wetter)


def get_comprehensive_weather(venue: str, race_datetime: datetime) -> Optional[Dict]:
    """
    Get comprehensive weather data using Open-Meteo API.

    Args:
        venue: Racecourse name (e.g., "Newbury", "Churchill Downs"). Old/alias
            names (e.g., "Churchill", "Tampa") are also accepted.
        race_datetime: datetime object of race start time

    Returns:
        Dictionary with comprehensive weather data, or None if error
    """
    canonical_venue = resolve_venue(venue)
    if not canonical_venue:
        logger.warning(f"No coordinates for venue: {venue}")
        return None

    coords = VENUE_COORDS[canonical_venue]
    country = coords.get('country', 'UK')
    venue_aliases = get_venue_aliases(canonical_venue)

    # Date range: 7 days before race for historical context
    end_date = race_datetime.date()
    start_date = end_date - timedelta(days=7)

    url = "https://api.open-meteo.com/v1/forecast"

    # Auto-detect units based on country
    if country == 'USA':
        temp_unit = 'fahrenheit'
        wind_unit = 'mph'
        precip_unit = 'inch'
    else:
        temp_unit = 'celsius'
        wind_unit = 'ms'
        precip_unit = 'mm'

    params = {
        'latitude': coords['lat'],
        'longitude': coords['lon'],

        'hourly': ','.join([
            'temperature_2m',
            'apparent_temperature',
            'precipitation',
            'rain',
            'wind_speed_10m',
            'wind_direction_10m',
            'wind_gusts_10m',
            'relative_humidity_2m',
            'dew_point_2m',
            'soil_moisture_0_to_1cm',
            'soil_moisture_1_to_3cm',
            'soil_moisture_3_to_9cm',
            'soil_temperature_0cm',
            'soil_temperature_6cm',
            'et0_fao_evapotranspiration',
            'pressure_msl',
            'cloud_cover',
            'visibility',
            'weather_code',
            'precipitation_probability'
        ]),

        'temperature_unit': temp_unit,
        'wind_speed_unit': wind_unit,
        'precipitation_unit': precip_unit,
        'timezone': coords.get('tz', 'Europe/London'),
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    }

    try:
        logger.info(f"Fetching weather for {canonical_venue} at {race_datetime.isoformat()}")
        response = requests.get(url, params=params, timeout=30)

        if response.status_code != 200:
            logger.error(f"HTTP {response.status_code}")
            return None

        data = response.json()
        hourly = data.get('hourly', {})
        times = hourly.get('time', [])

        # Find race time
        race_time_str = race_datetime.strftime('%Y-%m-%dT%H:00')

        if race_time_str in times:
            idx = times.index(race_time_str)

            # Calculate historical accumulations
            rainfall_1h = hourly['precipitation'][idx] if idx > 0 else 0
            rainfall_3h = sum(hourly['precipitation'][max(0, idx-3):idx]) if idx >= 3 else 0
            rainfall_6h = sum(hourly['precipitation'][max(0, idx-6):idx]) if idx >= 6 else 0
            rainfall_24h = sum(hourly['precipitation'][max(0, idx-24):idx]) if idx >= 24 else 0
            rainfall_7d = sum(hourly['precipitation'][:idx]) if idx > 0 else 0

            # Normalize rainfall_24h to millimeters for unit-independent going
            # calculations (precip_unit can be 'inch' for USA venues)
            rainfall_24h_mm = rainfall_24h * 25.4 if precip_unit == 'inch' else rainfall_24h

            # Calculate hours since last rain
            hours_since_rain = 0
            for i in range(idx-1, -1, -1):
                if hourly['precipitation'][i] > 0.1:
                    break
                hours_since_rain += 1

            # Calculate ground saturation index
            ground_saturation = (
                hourly['soil_moisture_0_to_1cm'][idx] * 0.5 +
                hourly['soil_moisture_1_to_3cm'][idx] * 0.3 +
                hourly['soil_moisture_3_to_9cm'][idx] * 0.2
            )

            # Net moisture (rain - evaporation)
            et_24h = hourly['et0_fao_evapotranspiration'][idx] * 24
            net_moisture_24h = rainfall_24h - et_24h

            # Predict going - both surfaces
            soil_moisture_surface = hourly['soil_moisture_0_to_1cm'][idx]
            precipitation_probability = hourly['precipitation_probability'][idx]

            predicted_going_turf = compute_predicted_going_turf(soil_moisture_surface)

            # Track condition trend
            if idx >= 3:
                moisture_3h_ago = hourly['soil_moisture_0_to_1cm'][idx-3]
                track_drying = soil_moisture_surface < moisture_3h_ago
                track_wetting = soil_moisture_surface > moisture_3h_ago
            else:
                track_drying = False
                track_wetting = False

            predicted_going_dirt = compute_predicted_going_dirt(
                ground_saturation, rainfall_24h_mm, hours_since_rain, soil_moisture_surface
            )
            turf_likely_off = compute_turf_likely_off(
                rainfall_24h_mm, track_wetting, precipitation_probability
            )

            result = {
                'venue': canonical_venue,
                'venue_aliases': venue_aliases,
                'country': country,
                'race_datetime': race_datetime.isoformat(),

                # Basic conditions
                'temperature': hourly['temperature_2m'][idx],
                'apparent_temperature': hourly['apparent_temperature'][idx],
                'precipitation_current': hourly['precipitation'][idx],
                'rain_current': hourly['rain'][idx],
                'wind_speed': hourly['wind_speed_10m'][idx],
                'wind_direction': hourly['wind_direction_10m'][idx],
                'wind_gusts': hourly['wind_gusts_10m'][idx],
                'humidity': hourly['relative_humidity_2m'][idx],
                'dew_point': hourly['dew_point_2m'][idx],
                'pressure': hourly['pressure_msl'][idx],
                'cloud_cover': hourly['cloud_cover'][idx],
                'visibility': hourly['visibility'][idx],
                'weather_code': hourly['weather_code'][idx],
                'precipitation_probability': precipitation_probability,

                # Ground conditions
                'soil_moisture_0_1cm': hourly['soil_moisture_0_to_1cm'][idx],
                'soil_moisture_1_3cm': hourly['soil_moisture_1_to_3cm'][idx],
                'soil_moisture_3_9cm': hourly['soil_moisture_3_to_9cm'][idx],
                'soil_temperature_0cm': hourly['soil_temperature_0cm'][idx],
                'soil_temperature_6cm': hourly['soil_temperature_6cm'][idx],
                'evapotranspiration': hourly['et0_fao_evapotranspiration'][idx],

                # Historical accumulations
                'rainfall_1h': rainfall_1h,
                'rainfall_3h': rainfall_3h,
                'rainfall_6h': rainfall_6h,
                'rainfall_24h': rainfall_24h,
                'rainfall_7d': rainfall_7d,

                # Derived features
                'ground_saturation_index': ground_saturation,
                'net_moisture_24h': net_moisture_24h,
                'hours_since_rain': hours_since_rain,
                'predicted_going': predicted_going_turf,
                'predicted_going_turf': predicted_going_turf,
                'predicted_going_dirt': predicted_going_dirt,
                'turf_likely_off': turf_likely_off,
                'track_drying': track_drying,
                'track_wetting': track_wetting,
                'going_confidence': 'comprehensive',

                # Units & metadata
                'temp_unit': '°F' if country == 'USA' else '°C',
                'wind_unit': 'mph' if country == 'USA' else 'm/s',
                'precip_unit': 'in' if country == 'USA' else 'mm',
                'data_quality': 'comprehensive',
                'fetched_at': datetime.now().isoformat()
            }

            logger.info(f"[OK] Weather data retrieved for {canonical_venue}")
            return result

        else:
            logger.error(f"Race time {race_time_str} not in response")
            return None

    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        return None
