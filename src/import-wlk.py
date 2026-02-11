"""Import WLK data, then export as CSV files

According to the WeatherLink "readme" file, the following describes the structure of a .WLK file

//   Data is stored in monthly files.  Each file has the following header.
struct DayIndex
{
   short recordsInDay;  // includes any daily summary records
   long startPos;    // The index (starting at 0) of the first daily summary record
};

// Header for each monthly file.
// The first 16 bytes are used to identify a weather database file and to identify
//   different file formats. (Used for converting older database files.)
class HeaderBlock
{
   char idCode [16]; // = {'W', 'D', 'A', 'T', '5', '.', '0', 0, 0, 0, 0, 0, 0, 0, 5, 0}
   long totalRecords;
   DayIndex dayIndex [32]; // index records for each day. Index 0 is not used
                           // (i.e. the 1'st is at index 1, not index 0)
};

// After the Header are a series of 88 byte data records with one of the following
//   formats.  Note that each day will begin with 2 daily summary records

// Daily Summary Record 1
struct DailySummary1
{
   BYTE dataType = 2;
   BYTE reserved;    // this will cause the rest of the fields to start on an even address

   short dataSpan;   // total # of minutes accounted for by physical records for this day
   short hiOutTemp, lowOutTemp; // tenths of a degree F
   short hiInTemp, lowInTemp;   // tenths of a degree F
   short avgOutTemp, avgInTemp; // tenths of a degree F (integrated over the day)
   short hiChill, lowChill;     // tenths of a degree F
   short hiDew, lowDew;         // tenths of a degree F
   short avgChill, avgDew;      // tenths of a degree F
   short hiOutHum, lowOutHum;   // tenths of a percent
   short hiInHum, lowInHum;     // tenths of a percent
   short avgOutHum;             // tenths of a percent
   short hiBar, lowBar;         // thousandths of an inch Hg
   short avgBar;                // thousandths of an inch Hg
   short hiSpeed, avgSpeed;     // tenths of an MPH
   short dailyWindRunTotal;     // 1/10'th of an mile
   short hi10MinSpeed;          // the highest average wind speed record
   BYTE  dirHiSpeed, hi10MinDir; // direction code (0-15, 255)
   short dailyRainTotal;        // 1/1000'th of an inch
   short hiRainRate;            // 1/100'th inch/hr ???
   short dailyUVDose;           // 1/10'th of a standard MED
   BYTE  hiUV;                  // tenth of a UV Index
   BYTE timeValues[27];         // space for 18 time values (see below)
};

// Daily Summary Record 2
struct DailySummary2
{
   BYTE dataType = 3;
   BYTE  reserved;   // this will cause the rest of the fields to start on an even address

   // this field is not used now.
   unsigned short todaysWeather; // bitmapped weather conditions (Fog, T-Storm, hurricane, etc)

   short numWindPackets;      // # of valid packets containing wind data,
                              // this is used to indicate reception quality
   short hiSolar;             // Watts per meter squared
   short dailySolarEnergy;    // 1/10'th Ly
   short minSunlight;         // number of accumulated minutes where the avg solar rad > 150
   short dailyETTotal;        // 1/1000'th of an inch
   short hiHeat, lowHeat;     // tenths of a degree F
   short avgHeat;             // tenths of a degree F
   short hiTHSW, lowTHSW;     // tenths of a degree F
   short hiTHW, lowTHW;       // tenths of a degree F

   short integratedHeatDD65;  // integrated Heating Degree Days (65F threshold)
                              // tenths of a degree F - Day

   // Wet bulb values are not calculated
   short hiWetBulb, lowWetBulb; // tenths of a degree F
   short avgWetBulb;          // tenths of a degree F

   BYTE dirBins[24];          // space for 16 direction bins
                              // (Used to calculate monthly dominant Dir)

   BYTE timeValues[15];       // space for 10 time values (see below)

   short integratedCoolDD65;  // integrated Cooling Degree Days (65F threshold)
                              // tenths of a degree F - Day
   BYTE  reserved2[11];
};

struct WeatherDataRecord
{
   BYTE dataType = 1;
   BYTE archiveInterval;      // number of minutes in the archive
   // see below for more details about these next two fields)
   BYTE iconFlags;            // Icon associated with this record, plus Edit flags
   BYTE moreFlags;            // Tx Id, etc.

   short packedTime;          // minutes past midnight of the end of the archive period
   short outsideTemp;         // tenths of a degree F
   short hiOutsideTemp;       // tenths of a degree F
   short lowOutsideTemp;      // tenths of a degree F
   short insideTemp;          // tenths of a degree F
   short barometer;           // thousandths of an inch Hg
   short outsideHum;          // tenths of a percent
   short insideHum;           // tenths of a percent
   unsigned short rain;       // number of clicks + rain collector type code
   short hiRainRate;          // clicks per hour
   short windSpeed;           // tenths of an MPH
   short hiWindSpeed;         // tenths of an MPH
   BYTE windDirection;        // direction code (0-15, 255)
   BYTE hiWindDirection;      // direction code (0-15, 255)
   short numWindSamples;      // number of valid ISS packets containing wind data
                              // this is a good indication of reception
   short solarRad, hisolarRad;// Watts per meter squared
   BYTE  UV, hiUV;            // tenth of a UV Index

   BYTE leafTemp[4];          // (whole degrees F) + 90

   short extraRad;            // used to calculate extra heating effects of the sun in THSW index

   short newSensors[6];       // reserved for future use
   BYTE  forecast;            // forecast code during the archive interval

   BYTE  ET;                  // in thousandths of an inch

   BYTE soilTemp[6];          // (whole degrees F) + 90
   BYTE soilMoisture[6];      // centibars of dryness
   BYTE leafWetness[4];       // Leaf Wetness code (0-15, 255)
   BYTE extraTemp[7];         // (whole degrees F) + 90
   BYTE extraHum[7];          // whole percent
};

The rain collector type is encoded in the most significant nibble of the rain field.
rainCollectorType = (rainCode & 0xF000);
rainClicks = (rainCode & 0x0FFF);

Type		rainCollectorType
0.1 inch	0x0000
0.01 inch	0x1000
0.2 mm		0x2000
1.0 mm		0x3000
0.1 mm		0x6000 (not fully supported)

Use the rainCollectorType to interpret the hiRainRate field. For example, if you have
a 0.01 in rain collector, a rain rate value of 19 = 0.19 in/hr = 4.8 mm/hr, but if you have
a 0.2 mm rain collector, a rain rate value of 19 = 3.8 mm/hr = 0.15 in/hr.

"""
from __future__ import annotations

import argparse
import datetime
import struct
from pathlib import Path

import weewx
import weewx.drivers.vantage


class DayIndex:
    """Represents a day index in the header block of a .WLK file."""

    def __init__(self, byte_values: bytes, day_in_month: int):
        records_in_day, start_pos = struct.unpack('<hi', byte_values)
        self.records_in_day = records_in_day
        self.start_pos = start_pos
        self.day_in_month = day_in_month

    def __str__(self):
        return (f"Day {self.day_in_month}: Starting position {self.start_pos}; "
                f"# of records {self.records_in_day}")


header_block = [
    ('16s', 'idCode'),  # = {'W', 'D', 'A', 'T', '5', '.', '0', 0, 0, 0, 0, 0, 0, 0, 5, 0}
    ('I', 'totalRecords'),
    ('6s' * 32, 'dayIndex')  # The 32 day indexes
]

# Needs to be 88 bytes long:
daily_summary1 = [
    ('B', 'dataType'),  # = 2
    ('87s', 'unused'),
]

# Needs to be 88 bytes long:
daily_summary2 = [
    ('B', 'dataType'),  # = 3
    ('87s', 'unused')
]

# This should be 88 bytes long:
weather_data_record = [
    ('B', 'dataType'),  # = 1
    ('B', 'interval'),  # In minutes
    ('B', 'iconFlags'),
    ('B', 'moreFlags'),
    ('h', 'packed_time'),  # Minutes past midnight
    ('h', 'outTemp'),  # tenths of a degree F
    ('h', 'highOutTemp'),  # tenths of a degree F
    ('h', 'lowOutTemp'),  # tenths of a degree F
    ('h', 'inTemp'),  # tenths of a degree F
    ('h', 'barometer'),  # thousandths of an inch Hg
    ('h', 'outHumidity'),  # tenths of a percent
    ('h', 'inHumidity'),  # tenths of a percent
    ('H', 'rain'),  # number of clicks + rain collector type code
    ('h', 'hiRainRate'),  # clicks per hour
    ('h', 'windSpeed'),  # tenths of an MPH
    ('h', 'windGust'),  # tenths of an MPH
    ('B', 'windDir'),  # direction code (0-15, 255)
    ('B', 'windGustDir'),  # direction code (0-15, 255)
    ('h', 'wind_samples'),  # number of valid ISS packets containing wind data
    ('H', 'radiation'),  # Watts per meter squared
    ('H', 'highRadiation'),  # Watts per meter squared
    ('B', 'UV'),  # tenth of a UV Index
    ('B', 'highUV'),  # tenth of a UV Index
    ('B', 'leafTemp1'),  # (whole degrees F) + 90
    ('B', 'leafTemp2'),  # (whole degrees F) + 90
    ('B', 'leafTemp3'),  # (whole degrees F) + 90
    ('B', 'leafTemp4'),  # (whole degrees F) + 90
    ('h', 'extraRad'),  # used to calculate extra heating effects of the sun in THSW index
    ('h', 'newSensors1'),  # reserved for future use
    ('h', 'newSensors2'),
    ('h', 'newSensors3'),
    ('h', 'newSensors4'),
    ('h', 'newSensors5'),
    ('h', 'newSensors6'),
    ('B', 'forecastRule'),
    ('B', 'ET'),  # in thousandths of an inch
    ('B', 'soilTemp1'),  # (whole degrees F) + 90
    ('B', 'soilTemp2'),
    ('B', 'soilTemp3'),
    ('B', 'soilTemp4'),
    ('B', 'soilTemp5'),
    ('B', 'soilTemp6'),
    ('B', 'soilMoist1'),  # centibars of dryness
    ('B', 'soilMoist2'),
    ('B', 'soilMoist3'),
    ('B', 'soilMoist4'),
    ('B', 'soilMoist5'),
    ('B', 'soilMoist6'),
    ('B', 'leafWet1'),  # Leaf Wetness code (0-15, 255)
    ('B', 'leafWet2'),
    ('B', 'leafWet3'),
    ('B', 'leafWet4'),
    ('B', 'extraTemp1'),  # (whole degrees F) + 90
    ('B', 'extraTemp2'),
    ('B', 'extraTemp3'),
    ('B', 'extraTemp4'),
    ('B', 'extraTemp5'),
    ('B', 'extraTemp6'),
    ('B', 'extraTemp7'),
    ('B', 'extraHumid1'),  # whole percent
    ('B', 'extraHumid2'),
    ('B', 'extraHumid3'),
    ('B', 'extraHumid4'),
    ('B', 'extraHumid5'),
    ('B', 'extraHumid6'),
    ('B', 'extraHumid7'),
]

weather_data_formats, weather_data_names = zip(*weather_data_record)
weather_data_struct = struct.Struct('<' + ''.join(weather_data_formats))
assert weather_data_struct.size == 88

header_formats, header_names = zip(*header_block)
header_struct = struct.Struct('<' + ''.join(header_formats))

VANTAGE_MODEL_TYPE = 2
VANTAGE_ISS_ID = 1


def decode_rain(raw_archive_record: dict, key: str) -> float | None:
    rain_collector_type = (raw_archive_record[key] & 0xF000)
    rain_clicks = (raw_archive_record[key] & 0x0FFF)
    if rain_collector_type == 0x0000:
        bucket_size = 0.1
    elif rain_collector_type == 0x1000:
        bucket_size = 0.01
    elif rain_collector_type == 0x2000:
        bucket_size = 0.007874  # = 0.2 mm
    elif rain_collector_type == 0x3000:
        bucket_size = 0.0393701  # = 1.0 mm
    else:
        raise ValueError(f"Unknown rain collector type: {rain_collector_type}")
    return rain_clicks * bucket_size


# Make a copy of the archive map, so we can modify it without affecting the original. Then add
# any specialized mappings.
archive_map = weewx.drivers.vantage._archive_map.copy()
archive_map['inHumidity'] = lambda p, k: float(p[k]) / 10.0 if p[k] != 0xff else None
archive_map['outHumidity'] = lambda p, k: float(p[k]) / 10.0 if p[k] != 0xff else None
archive_map['windSpeed'] = lambda p, k: float(p[k]) / 10.0 if p[k] != 0xff else None
archive_map['windGust'] = lambda p, k: float(p[k]) / 10.0 if p[k] != 0xff else None
archive_map['rain'] = decode_rain
archive_map['hiRainRate'] = decode_rain


# TODO: radiation is not right. Is the 'dash' value 0x8000?

def wlk_generator(path: Path):
    # Figure out year and month from filename:
    year_str, month_str = path.stem.split('-')
    year, month = int(year_str), int(month_str)

    with open(path, 'rb') as fd:
        # Read the header block
        header_data = fd.read(header_struct.size)
        if len(header_data) < header_struct.size:
            return

        # Unpack the header values.
        header_values = header_struct.unpack(header_data)

        #  Element 0 is the idCode. Check it.
        if not header_values[0].startswith(b'WDAT5.'):
            raise ValueError("Not a WeatherLink .WLK file")

        # Element 1 is the total number of records in the file.
        # We don't use it, but it might be useful later.
        total_records = header_values[1]

        # Element 2 through 33 are day indexes. There will be 32 of them, but the first one is not
        # actually used. The rest represent information about each day of the month (up to 31 of them).
        day_indexes = []
        for i in range(32):
            day_indexes.append(DayIndex(header_values[2 + i], i))
        for day_index in day_indexes:
            print(day_index)

        # Now march through each day of the month.
        for day in range(1, 31):
            assert day_indexes[day].day_in_month == day
            if day_indexes[day].records_in_day == 0:
                continue

            # The starting position is the number of *records* (not bytes) in. So, multiply
            # by the record size, which is 88. We also have to add in the size of the header.
            fd.seek(88 * day_indexes[day].start_pos + header_struct.size)

            # Now read each record in the day. Stop when we reach the number of records in the day.
            n = 0
            while True:
                if n >= day_indexes[day].records_in_day:
                    break
                record_buffer = fd.read(88)
                if len(record_buffer) < 88:
                    break

                # The first byte identifies the record type
                record_type = record_buffer[0]

                if record_type == 1:
                    # Weather data record. Unpack the buffer.
                    data_tuple = weather_data_struct.unpack(record_buffer)
                    raw_value_dict = dict(zip(weather_data_names, data_tuple))
                    # Decode and convert to physical units
                    archive_record = decode_record(raw_value_dict)
                    # Add the time stamp
                    archive_record['dateTime'] = decode_time(year, month, day,
                                                             raw_value_dict['packed_time'])
                    yield archive_record
                    n += 1
                elif record_type in [2, 3]:
                    # Daily summary record, ignore
                    continue
                else:
                    # Unknown record type
                    raise ValueError(f"Unknown record type {record_type}")


def decode_time(year: int, month: int, day: int, packed_time: int) -> int:
    """Convert a packed time into unix epoch time."""
    if not 0 <= packed_time <= 1440:
        raise ValueError(f"Invalid packed time: {packed_time}")
    dt = datetime.datetime(year, month, day, 0, 0, 0) + datetime.timedelta(minutes=packed_time)
    return int(dt.timestamp())


def decode_record(raw_archive_record: dict) -> dict:
    archive_record = {
        'usUnits': weewx.US,
        # Divide archive interval by 60 to keep consistent with wview
        'interval': int(raw_archive_record['interval']),

    }
    archive_record['rxCheckPercent'] = \
        weewx.drivers.vantage._rxcheck(VANTAGE_MODEL_TYPE,
                                       archive_record['interval'],
                                       VANTAGE_ISS_ID,
                                       raw_archive_record['wind_samples'])
    for obs_type in raw_archive_record:
        # Get the mapping function for this type. If there is no such
        # function, supply a lambda function that will just return None
        func = archive_map.get(obs_type, lambda p, k: None)
        # Call the function:
        val = func(raw_archive_record, obs_type)
        # Skip all null values
        if val is not None:
            archive_record[obs_type] = val

    return archive_record


def main():
    from weeutil.weeutil import timestamp_to_string
    parser = argparse.ArgumentParser(
        description="Read .WLK weather files and print weather data records.")
    parser.version = "1.0"
    parser.add_argument("wlk_files", nargs='+', help="Input .WLK files")
    args = parser.parse_args()

    for filename in args.wlk_files:
        path = Path(filename)
        for record in wlk_generator(path):
            print(timestamp_to_string(record['dateTime']), record)


if __name__ == "__main__":
    main()
