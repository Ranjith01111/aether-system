import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

print("--- INITIALIZING AETHER CORE (AI BRAIN) ---")

# 1. GENERATE "SMART DATA" WITH A HIDDEN DANGER PATTERN
np.random.seed(101)
n_samples = 5000

data = {
    'Temperature': np.random.normal(100, 10, n_samples),
    'Vibration': np.random.normal(50, 5, n_samples),
    'Fuel': np.random.uniform(0, 100, n_samples)
}

df = pd.DataFrame(data)

# THE HIDDEN PATTERN (The Logic we want the AI to learn)
# If Temp is HIGH (>110) AND Vibration is HIGH (>55) -> It is DANGEROUS
# Otherwise -> It is SAFE
target = []

for i in range(n_samples):
    if df.at[i, 'Temperature'] > 110 and df.at[i, 'Vibration'] > 55:
        target.append(1) # 1 = Danger / Failure
    else:
        target.append(0) # 0 = Safe / Nominal

df['Target_Label'] = target

print(f"Data created. Hidden danger cases: {sum(target)} out of {n_samples}")

# 2. PREPARE DATA FOR TRAINING
X = df[['Temperature', 'Vibration', 'Fuel']]  # The Inputs
y = df['Target_Label']                         # The Answers

# Split: 80% to learn, 20% to test how smart it is
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. TRAIN THE AI
# Using Random Forest: An algorithm that uses many "decision trees" to decide
model = RandomForestClassifier(n_estimators=100, random_state=42)

print("Training the AETHER Brain... (This might take 10-20 seconds)")
model.fit(X_train, y_train)
print("Training Complete.")

# 4. EVALUATE
predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)

print(f"\n--- SYSTEM CHECK ---")
print(f"AI Accuracy Score: {accuracy * 100:.2f}%")

if accuracy > 0.95:
    print("Smacky: The AI has learned the pattern perfectly!")
else:
    print("Smacky: The AI needs more training.")

# 5. SCENARIO: PREDICT A NEW EMERGENCY
print("\n--- LIVE SIMULATION ---")
# Let's create a scenario: High Temp + High Vibration (DANGER!)
live_scenario = pd.DataFrame({
    'Temperature': [112],   # Over 110
    'Vibration': [56],      # Over 55
    'Fuel': [45]
})

prediction = model.predict(live_scenario)
probability = model.predict_proba(live_scenario)

if prediction[0] == 1:
    print(f"ALERT: AI predicts CRITICAL FAILURE!")
    print(f"Confidence: {probability[0][1] * 100:.2f}%")
else:
    print("System Status: Normal.")

# Save the model to use later
import joblib
joblib.dump(model, 'aether_brain_model.pkl')
print("\nBrain saved to file: aether_brain_model.pkl")