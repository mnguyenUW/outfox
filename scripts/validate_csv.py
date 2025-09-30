"""Validate the healthcare CSV data before loading."""
import pandas as pd
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Expected columns from the CSV
EXPECTED_COLUMNS = [
    'Rndrng_Prvdr_CCN',
    'Rndrng_Prvdr_Org_Name',
    'Rndrng_Prvdr_City',
    'Rndrng_Prvdr_St',
    'Rndrng_Prvdr_State_FIPS',
    'Rndrng_Prvdr_Zip5',
    'Rndrng_Prvdr_State_Abrvtn',
    'Rndrng_Prvdr_RUCA',
    'Rndrng_Prvdr_RUCA_Desc',
    'DRG_Cd',
    'DRG_Desc',
    'Tot_Dschrgs',
    'Avg_Submtd_Cvrd_Chrg',
    'Avg_Tot_Pymt_Amt',
    'Avg_Mdcr_Pymt_Amt'
]

def validate_csv(file_path: str) -> Tuple[bool, List[str]]:
    """
    Validate CSV structure and data types.
    Returns (is_valid, list_of_issues)
    """
    issues = []
    
    try:
        # Read CSV
        df = pd.read_csv(file_path)
        print(f"✅ Successfully read CSV with {len(df)} rows")
        
        # Check columns
        missing_cols = set(EXPECTED_COLUMNS) - set(df.columns)
        extra_cols = set(df.columns) - set(EXPECTED_COLUMNS)
        
        if missing_cols:
            issues.append(f"Missing columns: {missing_cols}")
        if extra_cols:
            print(f"⚠️  Extra columns found (will be ignored): {extra_cols}")
        
        # Check data types and nulls
        print("\n📊 Column Analysis:")
        for col in EXPECTED_COLUMNS:
            if col in df.columns:
                null_count = df[col].isna().sum()
                dtype = df[col].dtype
                unique_count = df[col].nunique()
                
                print(f"  {col}:")
                print(f"    - Type: {dtype}")
                print(f"    - Nulls: {null_count}/{len(df)} ({null_count/len(df)*100:.1f}%)")
                print(f"    - Unique values: {unique_count}")
                
                # Validate numeric columns
                if col in ['Tot_Dschrgs', 'Avg_Submtd_Cvrd_Chrg', 'Avg_Tot_Pymt_Amt', 'Avg_Mdcr_Pymt_Amt']:
                    if not pd.api.types.is_numeric_dtype(df[col]):
                        # Try to convert
                        try:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            issues.append(f"Column {col} needed conversion to numeric")
                        except:
                            issues.append(f"Column {col} cannot be converted to numeric")
                    
                    # Check for negative values
                    if (df[col] < 0).any():
                        issues.append(f"Column {col} has negative values")
        
        # Check for duplicate provider-DRG combinations
        dup_check = df[['Rndrng_Prvdr_CCN', 'DRG_Cd']].duplicated()
        if dup_check.any():
            issues.append(f"Found {dup_check.sum()} duplicate provider-DRG combinations")
        
        # Sample data preview
        print("\n📝 Sample Data (first 3 rows):")
        print(df[['Rndrng_Prvdr_CCN', 'Rndrng_Prvdr_Org_Name', 'DRG_Cd']].head(3))
        
        return len(issues) == 0, issues
        
    except Exception as e:
        issues.append(f"Failed to read CSV: {str(e)}")
        return False, issues


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_csv.py <path_to_csv>")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    is_valid, issues = validate_csv(csv_path)
    
    if is_valid:
        print("\n✅ CSV validation successful!")
    else:
        print("\n❌ CSV validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)