import os
import sys
import sqlite3
import struct
import math
import time
from datetime import datetime, timedelta

# --- Constants & Configuration ---
WLK_RECORD_SIZE = 88  # Davis WLK records are 88 bytes
DB_NAME = "wview-archive.sdb"


# --- Meteorological Calculations ---

def calculate_dewpoint(temp_f, humidity):
    if temp_f is None or humidity is None or humidity <= 0:
        return None
    # Convert to Celsius
    temp_c = (temp_f - 32) * 5.0 / 9.0
    a, b = 17.27, 237.7
    alpha = ((a * temp_c) / (b + temp_c)) + math.log(humidity / 100.0)
    dewpoint_c = (b * alpha) / (a - alpha)
    # Convert back to Fahrenheit
    return (dewpoint_c * 9.0 / 5.0) + 32


def calculate_wind_chill(temp_f, wind_speed_mph):
    if temp_f is None or wind_speed_mph is None:
        return None
    if temp_f > 50 or wind_speed_mph < 3:
        return temp_f
    return 35.74 + (0.6215 * temp_f) - (35.75 * (wind_speed_mph ** 0.16)) + (
                0.4275 * temp_f * (wind_speed_mph ** 0.16))


def calculate_heat_index(temp_f, humidity):
    if temp_f is None or humidity is None or temp_f < 80:
        return temp_f
    hi = 0.5 * (temp_f + 61.0 + ((temp_f - 68.0) * 1.2) + (humidity * 0.094))
    if hi >= 80:
        hi = -42.379 + 2.04901523 * temp_f + 10.14333127 * humidity - 0.22475541 * temp_f * humidity \
             - 0.00683783 * temp_f ** 2 - 0.05481717 * humidity ** 2 + 0.00122874 * temp_f ** 2 * humidity \
             + 0.00085282 * temp_f * humidity ** 2 - 0.00000199 * temp_f ** 2 * humidity ** 2
    return hi


# --- Database Logic ---

def init_db(dest_dir):
    db_path = os.path.join(dest_dir, DB_NAME)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Create table based on wview schema if it doesn't exist
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS archive
                   (
                       dateTime INTEGER PRIMARY KEY,
                       usUnits INTEGER,
                       interval INTEGER,
                       barometer REAL,
                       outTemp REAL,
                       outHumidity REAL,
                       rain REAL,
                       rainRate REAL,
                       windSpeed REAL,
                       windDir REAL,
                       windGust REAL,
                       windGustDir REAL,
                       inTemp REAL,
                       inHumidity REAL,
                       dewpoint REAL,
                       windchill REAL,
                       heatindex REAL,
                       ET REAL,
                       radiation REAL,
                       UV REAL,
                       extraTemp1 REAL,
                       extraTemp2 REAL,
                       extraTemp3 REAL,
                       soilTemp1 REAL,
                       soilTemp2 REAL,
                       soilTemp3 REAL,
                       soilTemp4 REAL,
                       leafTemp1 REAL,
                       leafTemp2 REAL,
                       extraHumid1 REAL,
                       extraHumid2 REAL,
                       soilMoist1 REAL,
                       soilMoist2 REAL,
                       soilMoist3 REAL,
                       soilMoist4 REAL,
                       leafWet1 REAL,
                       leafWet2 REAL
                   )
                   ''')
    # Performance optimizations from C code
    cursor.execute("PRAGMA synchronous = OFF")
    cursor.execute("PRAGMA journal_mode = OFF")
    return conn


# --- WLK Parsing ---

def parse_wlk_file(filepath):
    """Parses a .wlk file and yields dictionaries of data."""
    if not os.path.exists(filepath):
        return

    with open(filepath, 'rb') as f:
        # Skip header (Davis WLK files have a header, usually skip to first record)
        # Note: Actual header size can vary; standard is usually skipping to offset 0x0
        # and checking for valid data.
        while True:
            data = f.read(WLK_RECORD_SIZE)
            if len(data) < WLK_RECORD_SIZE:
                break

            # Unpack Davis binary record (Simplified for standard fields)
            # Format: H=uint16, h=int16, b=int8, B=uint8
            # This follows the Davis Rev B Archive Record structure
            rec = struct.unpack('<H H h h h h H B B B B B B B 4s 4s 2s 4s 2s H B 7B', data[:52])

            # Basic Date/Time Mapping
            packed_date = rec[0]
            packed_time = rec[1]

            day = packed_date & 0x1F
            month = (packed_date >> 5) & 0x0F
            year = (packed_date >> 9) + 2000

            hour = packed_time // 100
            minute = packed_time % 100

            try:
                dt = datetime(year, month, day, hour, minute)
                ts = int(dt.timestamp())
            except ValueError:
                continue

            # Unit Conversion Logic (similar to C code)
            out_temp = rec[2] / 10.0
            barometer = rec[7] / 1000.0 if rec[7] != 0 else rec[4] / 1000.0  # simplified
            in_temp = rec[3] / 10.0
            in_hum = rec[9]
            out_hum = rec[10]
            wind_speed = rec[11] / 10.0
            wind_dir = rec[12] * 22.5 if rec[12] < 16 else None
            wind_gust = rec[13] / 10.0

            # Rain handling
            rain_raw = rec[19]  # Simplified
            click = 100.0  # Default
            rain = (rain_raw & 0xFFF) / click

            # Calculate derived
            dew = calculate_dewpoint(out_temp, out_hum)
            chill = calculate_wind_chill(out_temp, wind_speed)
            heat = calculate_heat_index(out_temp, out_hum)

            yield (ts, 1, 30, barometer, out_temp, out_hum, rain, 0.0,
                   wind_speed, wind_dir, wind_gust, None, in_temp, in_hum,
                   dew, chill, heat)


# --- Main Application ---

def main():
    if len(sys.argv) < 2:
        print("Usage: python wlk2sqlite.py <source_dir> [dest_dir]")
        sys.exit(1)

    src_dir = sys.argv[1]
    dest_dir = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()

    if not os.path.isdir(src_dir):
        print(f"Error: Source {src_dir} is not a directory.")
        sys.exit(1)

    conn = init_db(dest_dir)
    cursor = conn.cursor()

    inserts, dups, errors = 0, 0, 0
    start_time = time.time()

    print(f"Converting WLK files in {src_dir}...")

    for filename in sorted(os.listdir(src_dir)):
        if filename.endswith(".wlk"):
            filepath = os.path.join(src_dir, filename)
            for record in parse_wlk_file(filepath):
                try:
                    # The record[0] is the timestamp (Primary Key)
                    cursor.execute(
                        "INSERT INTO archive (dateTime, usUnits, interval, barometer, outTemp, outHumidity, rain, rainRate, windSpeed, windDir, windGust, windGustDir, inTemp, inHumidity, dewpoint, windchill, heatindex) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        record)
                    inserts += 1
                except sqlite3.IntegrityError:
                    dups += 1
                except Exception as e:
                    errors += 1

            # Commit per file to balance speed and safety
            conn.commit()

            elapsed = time.time() - start_time
            if elapsed > 0:
                print(
                    f"Processed {filename}: Inserts: {inserts}, Duplicates: {dups}, Speed: {int((inserts + dups) / elapsed)} recs/sec")

    conn.close()
    print("\nConversion Complete.")
    print(f"Final Stats - Inserts: {inserts}, Dups: {dups}, Errors: {errors}")


if __name__ == "__main__":
    main()