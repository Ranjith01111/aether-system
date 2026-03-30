import boto3
import time
import pandas as pd
import numpy as np
import datetime

# CONFIG
BUCKET_NAME = 'aether-project-data' 
FILE_KEY = 'telemetry_data.csv'

print("--- INJECTOR FINAL STARTED ---")
s3 = boto3.client('s3', region_name='ap-south-2')

try:
    while True:
        times = [datetime.datetime.now() - datetime.timedelta(seconds=x) for x in range(50, 0, -1)]
        times.reverse()
        
        base_temps = np.linspace(100, 105, 50) 
        noise = np.random.normal(0, 2, 50)
        temps = base_temps + noise
        vibes = np.random.uniform(48, 52, 50)
        
        # STANDARD COLUMNS
        data = {
            'Time': times,
            'Temperature': temps,
            'Vibration': vibes
        }
        
        df = pd.DataFrame(data)
        df['Time'] = df['Time'].dt.strftime("%H:%M:%S")
        
        csv_buffer = df.to_csv(index=False)
        s3.put_object(Bucket=BUCKET_NAME, Key=FILE_KEY, Body=csv_buffer)
        
        print(f"Sent 50 rows. Latest: {temps[-1]:.2f}°C")
        time.sleep(5)
except KeyboardInterrupt:
    print("\nSTOPPED")