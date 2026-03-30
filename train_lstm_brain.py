import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler
import joblib

print("--- INITIALIZING DEEP LEARNING BRAIN (LSTM) ---")

# 1. GENERATE TREND DATA (Time-Series)
# We create 2000 data points. Temperature is slowly RISING, then crashing.
np.random.seed(99)
time_steps = 2000
temperature = np.linspace(100, 150, time_steps) # Rising trend
noise = np.random.normal(0, 2, time_steps)
data = temperature + noise

df = pd.DataFrame(data, columns=['Temperature'])

# 2. PREPARE DATA (The most important part)
# LSTM needs data scaled between 0 and 1
scaler = MinMaxScaler(feature_range=(0, 1))
scaled_data = scaler.fit_transform(df)

# We create sequences: Use the PAST 60 points to predict the NEXT 1 point
# This gives the AI "Memory"
sequence_length = 60
X = []
y = []

for i in range(len(scaled_data) - sequence_length):
    X.append(scaled_data[i:i+sequence_length])
    y.append(scaled_data[i+sequence_length])

X, y = np.array(X), np.array(y)

# Reshape X to 3D [Samples, Time Steps, Features]
X = np.reshape(X, (X.shape[0], X.shape[1], 1))

print(f"Training Data Shape: {X.shape}")
print("Teaching the AI to understand trends...")

# 3. BUILD THE LSTM MODEL
model = Sequential()
# 50 Neurons, return_sequences=True means we stack LSTM layers
model.add(LSTM(units=50, return_sequences=True, input_shape=(X.shape[1], 1)))
model.add(LSTM(units=50))
model.add(Dense(units=1)) # Output is the prediction

model.compile(optimizer='adam', loss='mean_squared_error')

# 4. TRAIN
print("Training the Neural Network... (This is the heavy lifting)")
model.fit(X, y, epochs=10, batch_size=32, verbose=1)

# 5. SAVE EVERYTHING
# We save the model AND the scaler (because we need to un-scale predictions later)
model.save('aether_brain_v2.h5')
joblib.dump(scaler, 'scaler.pkl')

print("\n*** SUCCESS ***")
print("Deep Learning Brain Saved as 'aether_brain_v2.h5'")
print("Scaler Saved as 'scaler.pkl'")
print("This model now understands 'History' and 'Trends'.")