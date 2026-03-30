import pandas as pd
import numpy as np
import boto3
import os

print("--- Starting AETHER Data Uplink ---")

# 1. GENERATE SIMULATED DATA
# Creating 1000 rows of sensor data
np.random.seed(42)
data = {
    'Sensor_ID': np.arange(1, 1001),
    'Temperature_C': np.random.normal(100, 15, 1000), # Avg 100 deg
    'Vibration_Hz': np.random.normal(50, 5, 1000),     # Avg 50 Hz
    'Fuel_Level_%': np.random.uniform(100, 0, 1000),   # Draining fuel
    'Status': np.random.choice(['OK', 'WARNING'], 1000, p=[0.95, 0.05])
}

df = pd.DataFrame(data)

# Save locally to D drive
local_filename = 'telemetry_batch_1.csv'
df.to_csv(local_filename, index=False)
print(f"Data generated and saved locally as {local_filename}")

# 2. UPLOAD TO AWS S3
# Replace with your ACTUAL bucket name
bucket_name = 'aether-project-data' 

try:
    s3 = boto3.client('s3')
    object_name = local_filename
    
    print(f"Connecting to AWS Region: {s3.meta.region_name}...")
    
    s3.upload_file(local_filename, bucket_name, object_name)
    
    print("\n*** SUCCESS ***")
    print(f"File '{local_filename}' has been uploaded to bucket '{bucket_name}'.")
    print("The data is now in the cloud!")
    
except Exception as e:
    print("\n*** ERROR ***")
    print(f"Could not upload file. Reason: {e}")
    print("Check if your bucket name is correct.")