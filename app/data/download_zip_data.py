"""Download and prepare ZIP code geocoding data."""
import pandas as pd
import requests
from pathlib import Path

def download_zip_data():
    """Download US ZIP code data with lat/lon coordinates."""
    
    # Using a free ZIP code database
    url = "https://raw.githubusercontent.com/scpike/us-state-county-zip/master/geo-data.csv"
    
    print("Downloading ZIP code data...")
    df = pd.read_csv(url)
    
    # Filter and rename columns to match our schema
    zip_data = df[['zipcode', 'latitude', 'longitude', 'city', 'state']].copy()
    zip_data.columns = ['zip_code', 'latitude', 'longitude', 'city', 'state_code']
    
    # Ensure ZIP codes are 5 digits
    zip_data['zip_code'] = zip_data['zip_code'].astype(str).str.zfill(5)
    
    # Save to CSV
    output_path = Path(__file__).parent / "zip_codes.csv"
    zip_data.to_csv(output_path, index=False)
    print(f"ZIP code data saved to {output_path}")
    
    return output_path

if __name__ == "__main__":
    download_zip_data()