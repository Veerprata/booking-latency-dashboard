import pandas as pd
import json

INPUT_FILE = 'sync_master.xlsx'       # The Excel file with the "Dumps" column
OUTPUT_FILE = 'cleaned_codes.csv'     # Output CSV
DUMPS_COLUMN = 'Dumps'                # The column name in your Excel file

def extract_ota_booking_code(dumps_str):
    """
    Attempt to parse the 'Dumps' JSON and extract 'ota_booking_code' from
    insertedBookingDetails -> [0].
    
    We'll try two approaches:
    1) Single json.loads(dumps_str)
    2) Double json.loads(json.loads(dumps_str)) if the first fails
    """
    # Debug: Print the raw Dumps string (truncated for brevity)
    print("Raw Dumps value:", repr(dumps_str)[:150])
    
    def parse_and_extract(s):
        """Parse JSON string s and extract 'ota_booking_code' if present."""
        try:
            data = json.loads(s)
            print("Parsed JSON keys:", list(data.keys()))
            if "insertedBookingDetails" in data:
                details_list = data["insertedBookingDetails"]
                print("Found insertedBookingDetails:", details_list)
                if isinstance(details_list, list) and len(details_list) > 0:
                    code = details_list[0].get("ota_booking_code")
                    print("Extracted ota_booking_code:", code)
                    return code
            return None
        except Exception as e:
            print("Error in parse_and_extract:", e)
            return None

    # 1) Try single json.loads
    try:
        code = parse_and_extract(dumps_str)
        if code:
            print("Parsed with single json.loads ->", code)
            return code
    except Exception as e:
        print("Single json.loads failed:", e)

    # 2) If single failed or returned None, try double parse
    try:
        intermediate = json.loads(dumps_str)
        print("First-level parse result:", intermediate)
        code = parse_and_extract(intermediate)
        if code:
            print("Parsed with double json.loads ->", code)
            return code
    except Exception as e:
        print("Double json.loads failed:", e)

    # If all attempts fail, return None
    return None

def main():
    # 1. Read the Excel file
    df = pd.read_excel(INPUT_FILE)
    
    # 2. Verify we have the 'Dumps' column
    if DUMPS_COLUMN not in df.columns:
        raise ValueError(f"Expected column '{DUMPS_COLUMN}' not found in the Excel file.")
    
    # 3. Extract codes with debug output
    df["ota_booking_code"] = df[DUMPS_COLUMN].apply(
        lambda x: extract_ota_booking_code(x) if pd.notnull(x) else None
    )
    
    # 4. Filter rows where a code was found
    df_clean = df[df["ota_booking_code"].notnull()].copy()
    
    # 5. Keep only the extracted code column
    df_clean = df_clean[["ota_booking_code"]]
    
    # 6. Save to CSV
    df_clean.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    
    print("-" * 50)
    print(f"Extracted {len(df_clean)} booking codes.")
    print(f"Clean data saved to '{OUTPUT_FILE}'.")

if __name__ == "__main__":
    main()
