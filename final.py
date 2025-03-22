import pandas as pd
import re

# ---------------- Configuration ----------------
ab_file = 'ab_latency.csv'    # A→B CSV file
bc_file = 'bc_latency.csv'    # B→C CSV file
output_file = 'final_latency.xlsx'  # Output Excel file

# Threshold: 30 minutes = 1800 seconds
threshold_sec = 1800

# ---------------- Helper Functions ----------------

def parse_latency_string(lat_str):
    """
    Parses a string into total number of seconds (float).
    Handles three patterns:
      - Pattern C: "HH:MM:SS(.fraction)" e.g. "22:27:25.344478"
      - Pattern B: "X day(s), HH:MM:SS(.fraction)" e.g. "1 day, 2:19:01.113712"
      - Pattern A: "0 years 0 mons 0 days 0 hours 0 mins 12.565 secs"
    Returns None if parsing fails.
    """
    if not isinstance(lat_str, str):
        return None

    # Pattern C: "HH:MM:SS(.fraction)"
    pattern_c = re.compile(r'^(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+(\.\d+)?)$')
    match_c = pattern_c.search(lat_str)
    if match_c:
        hours = float(match_c.group('hours'))
        minutes = float(match_c.group('minutes'))
        seconds = float(match_c.group('seconds'))
        total_sec = hours * 3600 + minutes * 60 + seconds
        return total_sec

    # Pattern B: "X day(s), HH:MM:SS(.fraction)"
    pattern_b = re.compile(r'^(?P<days>\d+)\s+day[s]?,\s+(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+(\.\d+)?)$')
    match_b = pattern_b.search(lat_str)
    if match_b:
        days = float(match_b.group('days'))
        hours = float(match_b.group('hours'))
        minutes = float(match_b.group('minutes'))
        seconds = float(match_b.group('seconds'))
        total_sec = days * 86400 + hours * 3600 + minutes * 60 + seconds
        return total_sec

    # Pattern A: "0 years 0 mons 0 days 0 hours 0 mins 12.565 secs"
    pattern_a = re.compile(r'^(?P<days>\d+)\s+days?\s+(?P<hours>\d+)\s+hours?\s+(?P<minutes>\d+)\s+mins?\s+(?P<secs>\d+(\.\d+)?)\s+secs$')
    match_a = pattern_a.search(lat_str)
    if match_a:
        days = float(match_a.group('days'))
        hours = float(match_a.group('hours'))
        minutes = float(match_a.group('minutes'))
        seconds = float(match_a.group('secs'))
        total_sec = days * 86400 + hours * 3600 + minutes * 60 + seconds
        return total_sec

    print(f"[DEBUG] parse_latency_string failed for: {lat_str}")
    return None

def format_seconds_as_string(total_seconds):
    """
    Converts float seconds into a string like '0 days 00:12:34'
    Rounds total_seconds to an integer so the final display doesn't show fractional seconds.
    Returns '' if total_seconds is None/NaN.
    """
    if pd.isnull(total_seconds):
        return ''
    rounded_sec = round(total_seconds)
    td = pd.to_timedelta(rounded_sec, unit='s')
    days = td.components.days
    hh = td.components.hours
    mm = td.components.minutes
    ss = td.components.seconds
    return f"{days} days {hh:02d}:{mm:02d}:{ss:02d}"

def format_breach_percentage(value):
    """
    Formats the breach percentage with two decimals plus a trailing '%'.
    (This helper is no longer used for the final display, but kept for legacy.)
    """
    if pd.isnull(value):
        return ''
    return f"{value:.2f}%"

# ---------------- New Helper Functions to Remove Fractional Seconds ----------------

def remove_fractional_seconds_from_datetime(dt_str):
    """
    Converts a datetime string like '2025-02-24T05:15:00.207' to '2025-02-24T05:15:00'
    """
    if not isinstance(dt_str, str):
        return dt_str
    try:
        dt = pd.to_datetime(dt_str, errors='raise')
        return dt.strftime('%Y-%m-%dT%H:%M:%S')
    except Exception:
        return dt_str

def remove_fractional_seconds_from_latency(lat_str):
    """
    Converts a string like '0 years 0 mons 0 days 0 hours 0 mins 54.326 secs'
    to '0 years 0 mons 0 days 0 hours 0 mins 54 secs'
    """
    if not isinstance(lat_str, str):
        return lat_str
    return re.sub(r'(\d+)\.\d+\s+secs', r'\1 secs', lat_str)

# ---------------- Main Script ----------------

def main():
    # 1) Read the A→B CSV
    df_ab = pd.read_csv(ab_file)
    print("A→B CSV columns:", df_ab.columns.tolist())

    # 2) Read the B→C CSV
    df_bc = pd.read_csv(bc_file)
    print("B→C CSV columns:", df_bc.columns.tolist())

    # 3) Rename columns to standardize if needed
    rename_ab = {}
    if 'latency_interval' in df_ab.columns:
        rename_ab['latency_interval'] = 'latency_a_to_b_str'
    if 'latency_in_seconds' in df_ab.columns:
        rename_ab['latency_in_seconds'] = 'latency_a_to_b_sec'
    df_ab.rename(columns=rename_ab, inplace=True)

    rename_bc = {}
    if 'latency_b_to_c' in df_bc.columns:
        rename_bc['latency_b_to_c'] = 'latency_b_to_c_str'
    if 'extracted_code' in df_bc.columns:
        rename_bc['extracted_code'] = 'booking_code'
    df_bc.rename(columns=rename_bc, inplace=True)

    print("A→B CSV columns after rename:", df_ab.columns.tolist())
    print("B→C CSV columns after rename:", df_bc.columns.tolist())

    # 4) Merge on 'booking_code'
    try:
        df_combined = pd.merge(df_ab, df_bc, on='booking_code', how='inner', suffixes=('_ab','_bc'))
    except KeyError as e:
        print("ERROR: KeyError when merging on 'booking_code'. Check your column names!")
        print("Exception details:", e)
        return

    # 5) Parse latencies for B→C
    if 'latency_b_to_c_str' in df_combined.columns:
        df_combined['latency_b_to_c_sec'] = df_combined['latency_b_to_c_str'].apply(parse_latency_string)
    else:
        df_combined['latency_b_to_c_sec'] = None

    # 6) Sum latencies to get total_latency_sec = latency_a_to_b_sec + latency_b_to_c_sec
    if 'latency_a_to_b_sec' not in df_combined.columns:
        print("WARNING: 'latency_a_to_b_sec' column not found. Can't sum total.")
        df_combined['total_latency_sec'] = None
    else:
        df_combined['total_latency_sec'] = df_combined['latency_a_to_b_sec'] + df_combined['latency_b_to_c_sec']

    # ---------------- New Breach/Threshold Logic ----------------
    # Create a new column 'breach_category' that incorporates both:
    #   - For bookings with total_latency_sec <= threshold_sec: label as "Within Threshold"
    #   - For bookings exceeding threshold, compute a percentile ranking among only those rows and bin them.
    within_mask = df_combined['total_latency_sec'] <= threshold_sec
    exceed_mask = df_combined['total_latency_sec'] > threshold_sec

    df_combined['breach_category'] = None
    df_combined.loc[within_mask, 'breach_category'] = "Within Threshold"

    if exceed_mask.sum() > 0:
        # For rows exceeding the threshold, rank them by total_latency_sec among themselves.
        percentiles = df_combined.loc[exceed_mask, 'total_latency_sec'].rank(pct=True)
        df_combined.loc[exceed_mask, 'breach_rank'] = percentiles
        # Now bin these percentiles into 6 categories.
        df_combined.loc[exceed_mask, 'breach_category'] = pd.cut(
            df_combined.loc[exceed_mask, 'breach_rank'],
            bins=[0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            labels=["<=50th percentile", "50-60th percentile", "60-70th percentile", "70-80th percentile", "80-90th percentile", "90-100th percentile"],
            include_lowest=True
        )

    # For final display, assign breach_category to breach_percentage column.
    df_combined['breach_percentage'] = df_combined['breach_category']

    # 7) Create total_latency string (formatted)
    df_combined['total_latency'] = df_combined['total_latency_sec'].apply(format_seconds_as_string)

    # 8) Build final DataFrame with minimal columns
    final_cols = [
        'booking_code',
        'booking_received_at',
        'booking_pushed_at',
        'invoice_created_at',
        'latency_a_to_b_str',
        'latency_b_to_c_str',
        'total_latency',
        'breach_percentage'
    ]
    for col in final_cols:
        if col not in df_combined.columns:
            print(f"WARNING: Column '{col}' not found in merged data. It will be missing in final output.")

    df_final = df_combined[final_cols].copy()

    # Rename for final clarity
    df_final.rename(columns={
        'latency_a_to_b_str': 'latency_a_to_b',
        'latency_b_to_c_str': 'latency_b_to_c'
    }, inplace=True)

    # 9) Remove fractional seconds from selected columns
    df_final['booking_received_at'] = df_final['booking_received_at'].apply(remove_fractional_seconds_from_datetime)
    df_final['booking_pushed_at']   = df_final['booking_pushed_at'].apply(remove_fractional_seconds_from_datetime)
    df_final['latency_a_to_b']      = df_final['latency_a_to_b'].apply(remove_fractional_seconds_from_latency)
    df_final['latency_b_to_c']      = df_final['latency_b_to_c'].apply(remove_fractional_seconds_from_latency)

    # 10) Save final DataFrame to Excel
    df_final.to_excel(output_file, index=False)
    print("Final merged data saved to:", output_file)
    print("Columns in final output:", df_final.columns.tolist())

if __name__ == "__main__":
    main()
