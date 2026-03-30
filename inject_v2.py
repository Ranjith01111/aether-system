import boto3
import time
import pandas as pd
import numpy as np
import datetime

# --- CONFIGURATION ---
BUCKET_NAME = 'aether-project-data' 
FILE_KEY = 'telemetry_batch.csv'

print("--- INJECTOR V3 (BATCH MODE) STARTED ---")
print(f"Sending 50-row history to {BUCKET_NAME} every 5 seconds...")

s3 = boto3.client('s3', region_name='ap-south-2')

try:
    while True:
        # 1. GENERATE 50 DATA POINTS (History)
        # Create a time series (last 250 seconds)
        times = [datetime.datetime.now() - datetime.timedelta(seconds=x) for x in range(50, 0, -1)]
        times.reverse() # Oldest first, Newest last
        
        # Generate a temperature curve that wiggles
        base_temps = np.linspace(100, 105, 50) # Slight rise
        noise = np.random.normal(0, 2, 50)      # Random noise
        temps = base_temps + noise
        
        # Vibration
        vibes = np.random.uniform(48, 52, 50)
        
        data = {
            'Time_Stamp': times,
            'Temperature_C': temps,
            'Vibration_Hz': vibes
        }
        
        df = pd.DataFrame(data)
        
        # Convert time to string so CSV handles it easily
        df['Time_Stamp'] = df['Time_Stamp'].dt.strftime("%H:%M:%S")
        
        # 2. UPLOAD
        csv_buffer = df.to_csv(index=False)
        s3.put_object(Bucket=BUCKET_NAME, Key=FILE_KEY, Body=csv_buffer)
        
        print(f"Packet Sent. Latest Temp: {temps[-1]:.2f}°C")
        time.sleep(5)
        
except KeyboardInterrupt:
    print("\n--- INJECTOR STOPPED ---")