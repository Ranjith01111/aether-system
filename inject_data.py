import time
import pandas as pd
import numpy as np
import boto3
import random

print("--- AETHER: SPACECRAFT EMULATOR STARTED ---")
print("Sending Telemetry to AWS S3... (Press Ctrl+C to Stop)")

# Initialize S3 Client
s3 = boto3.client('s3', region_name='ap-south-2')
bucket_name = 'aether-project-data' # VERIFY NAME
file_key = 'telemetry_batch_1.csv'

counter = 0

try:
    while True:
        # 1. GENERATE LIVING DATA
        # We create a baseline temp that drifts slightly (Sine wave)
        current_time = time.time()
        base_temp = 100 + np.sin(current_time * 0.1) * 10 # Drifts between 90 and 110
        
        # Add random spikes to make it look "Noisy"
        temp_spike = random.uniform(-2, 2)
        final_temp = 999.99
        
        data = {
            'Time_Stamp': [time.time()],
            'Temperature_C': [final_temp],
            'Vibration_Hz': [random.uniform(48, 52)],
            'Fuel_Level_%': [max(0, 100 - (counter * 0.05))] # Fuel slowly draining
        }
        
        df = pd.DataFrame(data)
        
        # 2. UPLOAD TO S3
        csv_buffer = df.to_csv(index=False)
        s3.put_object(Bucket=bucket_name, Key=file_key, Body=csv_buffer)
        
        print(f"[{counter}] Packet Sent: Temp {final_temp:.1f}°C | Fuel {max(0, 100 - (counter * 0.05)):.1f}%")
        
        counter += 1
        time.sleep(5) # Wait 5 seconds before sending next packet
        
except KeyboardInterrupt:
    print("\n--- EMULATOR STOPPED ---")