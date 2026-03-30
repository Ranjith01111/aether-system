import boto3
import pandas as pd
import io

print("--- GROUND CONTROL: INITIATING DATA LINK ---")

# 1. CONFIGURATION
# UPDATE THIS TO YOUR EXACT BUCKET NAME
bucket_name = 'aether-project-data' 
file_key = 'telemetry_batch_1.csv'

try:
    # 2. CONNECT TO S3
    s3 = boto3.client('s3')
    
    print(f"Requesting data from bucket: {bucket_name}...")
    
    # 3. DOWNLOAD THE DATA INTO MEMORY (Not to hard drive)
    response = s3.get_object(Bucket=bucket_name, Key=file_key)
    
    # Convert the streaming data into a pandas dataframe
    df = pd.read_csv(io.BytesIO(response['Body'].read()))
    
    print("Data Received. Processing telemetry...")
    
    # 4. RUN ANALYSIS (The "Mission Report")
    print("\n--- MISSION TELEMETRY REPORT ---")
    print(f"Total Data Points Received: {len(df)}")
    print(f"Average Temperature: {df['Temperature_C'].mean():.2f}°C")
    print(f"Max Temperature Recorded: {df['Temperature_C'].max():.2f}°C")
    print(f"Average Fuel Level: {df['Fuel_Level_%'].mean():.2f}%")
    
    # Check for anomalies (High Temp)
    high_temp_count = len(df[df['Temperature_C'] > 110])
    if high_temp_count > 0:
        print(f"\nWARNING: {high_temp_count} critical temperature spikes detected.")
    else:
        print("\nSTATUS: System Nominal.")
        
    # Show the first few rows of data
    print("\n--- LIVE DATA FEED (First 5 Rows) ---")
    print(df.head())

except Exception as e:
    print(f"\n--- LINK FAILURE ---")
    print(f"Reason: {e}")