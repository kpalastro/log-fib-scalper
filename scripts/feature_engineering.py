import csv
import os

def run_feature_engineering(csv_path):
    print(f"--- Starting Feature Engineering for: {csv_path} ---")
    
    if not os.path.exists(csv_path):
        print(f"ERROR: File {csv_path} not found.")
        return

    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames
            print(f"Detected Columns: {columns}")
            
            # Read first 5 rows to verify data
            rows = []
            for i, row in enumerate(reader):
                rows.append(row)
                if i >= 4:
                    break
            
            if not rows:
                print("ERROR: CSV is empty.")
                return

            print("--- Data Preview ---")
            for row in rows:
                print(row)
            
            # Placeholder for logic: Logarithmic transformations will happen here
            print("\n[TASK] Data Engineer: Validated structure. Ready for geometric feature extraction.")
            
    except Exception as e:
        print(f"CRITICAL ERROR during extraction: {e}")

if __name__ == '__main__':
    # This path points to the XAGUSD file identified earlier
    data_file = "/Users/kpal/projects/hermese/data/OANDA_XAGUSD1.csv"
    run_feature_engineering(data_file)
