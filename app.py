import streamlit as st
import pandas as pd
import numpy as np
import boto3
import io
import datetime
from fpdf import FPDF
import joblib
from tensorflow.keras.models import load_model
import plotly.express as px

# --- CONFIGURATION ---
# UPDATE THIS TO YOUR WORKING BUCKET NAME
BUCKET_NAME = 'aether-project-data' 
FILE_KEY = 'live_data.csv'

# --- PAGE SETUP ---
st.set_page_config(page_title="AETHER MASTER", page_icon="🚀", layout="wide")
st.title("🚀 AETHER SYSTEM - MISSION CONTROL")
st.markdown("### Integrated: Live Cloud Telemetry & Deep Learning AI")

# --- SECTION 1: LIVE DATA FEED (CLOUD) ---
@st.cache_data(ttl=10)  # Refreshes every 10 seconds automatically
def load_live_data():
    try:
        s3 = boto3.client('s3', region_name='ap-south-2')
        response = s3.get_object(Bucket=BUCKET_NAME, Key=FILE_KEY)
        df = pd.read_csv(response['Body'])
        return df
    except Exception as e:
        return pd.DataFrame()

# --- SECTION 2: AI BRAIN (LSTM) ---
@st.cache_resource
def load_ai_brain():
    try:
        model = load_model('aether_brain_v2.h5')
        scaler = joblib.load('scaler.pkl')
        return model, scaler
    except:
        return None, None

# --- SECTION 3: REPORTING ---
def generate_report(live_temp, prediction):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="AETHER MISSION REPORT", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, txt=f"Timestamp: {datetime.datetime.now()}", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Live Temperature: {live_temp} °C", ln=True)
    pdf.cell(200, 10, txt=f"AI Predicted Next Step: {prediction:.2f} °C", ln=True)
    filename = "Mission_Report.pdf"
    pdf.output(filename)
    return filename

# --- DASHBOARD LAYOUT ---

# 1. SIDEBAR (CONTROLS)
st.sidebar.header("Control Center")

# SIMULATOR CONTROLS (For AI)
st.sidebar.subheader("AI Simulator Inputs")
sim_temp = st.sidebar.slider("Simulate Engine Temp (°C)", 80.0, 150.0, 100.0)

# 2. COLUMNS FOR METRICS
col1, col2, col3 = st.columns(3)

# COLUMN 1: LIVE CLOUD DATA
df_live = load_live_data()
if not df_live.empty:
    live_temp_val = df_live['Temperature'][0]
    col1.metric("Live Cloud Temp", f"{live_temp_val} °C")
else:
    col1.metric("Live Cloud Temp", "No Signal")

# COLUMN 2: AI PREDICTION (SENTINEL MODE)
model, scaler = load_ai_brain()

# DECISION: Use Live Data if available, otherwise use Slider
target_temp = 0.0
source_name = ""

if not df_live.empty and 'Temperature' in df_live.columns:
    target_temp = df_live['Temperature'][0]
    source_name = "LIVE CLOUD"
else:
    target_temp = sim_temp
    source_name = "MANUAL SLIDER"

col2.metric("Prediction Source", source_name)

if model and scaler:
    # Create a sequence ending at the TARGET_TEMP
    # We simulate a "Recent History" so the AI has context
    seq = np.linspace(target_temp - 5, target_temp, 60) 
    
    seq_scaled = scaler.transform(seq.reshape(-1, 1))
    seq_input = seq_scaled.reshape(1, 60, 1)
    
    # Predict the future
    pred_scaled = model.predict(seq_input, verbose=0)
    pred_val = scaler.inverse_transform(pred_scaled)[0][0]
    
    # Calculate Risk
    if pred_val > target_temp:
        trend_emoji = "🔺 RISING"
        color = "normal"
    else:
        trend_emoji = "🔻 STABLE"
        color = "off"
        
    col2.metric(f"AI Predicted (Next 5s)", f"{pred_val:.2f} °C", f"{trend_emoji}")
    
    # AUTOMATED ALERT
    if pred_val > 120.0: # DANGER THRESHOLD
        st.error(f"🚨 SENTINEL ALERT: AI Predicts CRITICAL FAILURE ({pred_val:.1f}°C)")
        # Winsound only works on Windows, won't crash cloud
        import winsound
        if source_name == "LIVE CLOUD":
            try:
                winsound.Beep(1000, 500) # Beep if running locally
            except:
                pass 

# 3. VISUALIZATION
st.divider()
c1, c2 = st.columns(2)

# CHART 1: LIVE TELEMETRY TREND (SYNCHRONIZED)
if not df_live.empty:
    c1.subheader("📈 Telemetry Trend Analysis (Live Graph)")
    
    # Ensure we are using the simple names
    # df_live MUST have columns: 'Time', 'Temperature', 'Vibration'
    
    fig = px.line(df_live, x='Time', y='Temperature', 
                  title='Engine Temperature Trend (Last 50 Readings)',
                  labels={'Temperature': 'Temp (°C)'},
                  markers=True)
    
    fig.update_layout(
        template="plotly_dark",
        xaxis_title="Time Sequence",
        yaxis_title="Temp (°C)"
    )
    
    c1.plotly_chart(fig, use_container_width=True)
    
    with st.expander("View Raw Data"):
        st.dataframe(df_live)
else:
    c1.warning("Waiting for Batch Data Packets...")

# CHART 2: AI SIMULATION
if model and scaler:
    c2.subheader("🧠 AI Trend Simulation")
    df_sim = pd.DataFrame({'Sequence': np.arange(1, 61), 'Temp': seq})
    fig = px.line(df_sim, x='Sequence', y='Temp', 
                  title=f'Input Trend (Ending at {sim_temp}°C)',
                  markers=True)
    fig.update_layout(template="plotly_dark")
    c2.plotly_chart(fig, use_container_width=True)

# 4. REPORTS
st.divider()
if st.button("📄 Generate Mission Report"):
    if model:
        pdf_file = generate_report(live_temp_val if not df_live.empty else 0, pred_val)
        with open(pdf_file, "rb") as f:
            st.download_button(label="Download PDF", data=f, file_name=pdf_file, mime="application/pdf")
    else:
        st.warning("Brain must be online to generate report.")

# --- FUTURE HORIZON GRAPH ---
if model and scaler and (not df_live.empty):
    st.subheader("🔮 Future Horizon (Next 5 Seconds)")
    
    # Create time axis
    past_time = np.arange(-60, 0) # -60 to 0 seconds
    future_time = np.array([5])   # +5 seconds
    
    # Combine for graph
    df_horizon = pd.DataFrame({
        'Time_Seconds': list(past_time) + list(future_time),
        'Temperature_C': list(seq) + [pred_val],
        'Type': ['History'] * 60 + ['Prediction']
    })
    
    fig = px.line(df_horizon, x='Time_Seconds', y='Temperature_C',
                  color='Type', line_dash='Type',
                  title=f'Visualizing Past -> Future (Live: {target_temp:.1f}°C -> Pred: {pred_val:.1f}°C)',
                  markers=True)
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
