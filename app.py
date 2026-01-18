import streamlit as st
import pandas as pd
import joblib
import boto3
import io
from fpdf import FPDF
import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="AETHER Mission Control", page_icon="🚀", layout="wide")

# --- LOAD THE AI BRAIN ---
@st.cache_resource
def load_model():
    return joblib.load('aether_brain_model.pkl')

model = load_model()

# --- LOAD DATA FROM AWS S3 ---
@st.cache_data
def load_cloud_data():
    try:
        s3 = boto3.client('s3',
                  aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
                  aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"])
        bucket_name = 'aether-project-data'  # UPDATE IF NEEDED
        file_key = 'telemetry_batch_1.csv'
        
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        df = pd.read_csv(io.BytesIO(response['Body'].read()))
        return df
    except Exception as e:
        st.error(f"Error connecting to Cloud: {e}")
        return pd.DataFrame()

# --- DASHBOARD CONTENT ---
st.title("🚀 AETHER System - Real-time Telemetry")

st.sidebar.header("Live Controls")
temp = st.sidebar.slider("Engine Temp (°C)", 80.0, 130.0, 100.0)
vib = st.sidebar.slider("Vibration (Hz)", 40.0, 70.0, 50.0)
fuel = st.sidebar.slider("Fuel (%)", 0.0, 100.0, 75.0)

# --- MANUAL PREDICTION ---
input_data = pd.DataFrame({
    'Temperature': [temp],
    'Vibration': [vib],
    'Fuel': [fuel]
})

prediction = model.predict(input_data)[0]
probability = model.predict_proba(input_data)[0][1]

col1, col2, col3 = st.columns(3)

col1.metric("Temperature", f"{temp} °C")
col2.metric("Vibration", f"{vib} Hz")
col3.metric("Fuel Level", f"{fuel}%")

if prediction == 1:
    st.error(f"⛔ CRITICAL FAILURE (Confidence: {probability*100:.1f}%)")
    
    # Add a checkbox to turn the siren on/off
    enable_alarm = st.checkbox("🚨 ACTIVATE SIREN ALARM")
    
    if enable_alarm:
        st.warning("Siren Active: Playing Warning Sound...")
        # Play a 'Beep...Beep...Beep' sound
        # Frequency: 1000Hz, Duration: 500ms
        #winsound.Beep(1000, 500) 
else:
    st.success(f"✅ SYSTEM NOMINAL (Confidence: {(1-probability)*100:.1f}%)")
    
    
# --- CLOUD DATA SECTION ---
st.divider()
st.subheader("🛰️ Historical Data Feed (Direct from AWS S3)")

df_history = load_cloud_data()

if not df_history.empty:
    st.write(f"Showing last **{len(df_history)}** records retrieved from Cloud Storage:")
    st.dataframe(df_history) # This shows the actual data from Step 4
else:
    st.warning("No historical data found in the bucket.")

# Telemetry Trend Analysis Section 

st.divider()
st.subheader("📉 Telemetry Trend Analysis (Live Graph)")

# We will plot the Temperature history from the S3 data
if not df_history.empty:
    # Plotly creates interactive, zoomable charts (very professional)
    import plotly.express as px
    
    # Create a 'Time' axis just for visualization (0, 1, 2, 3...)
    df_plot = df_history.head(50).copy() # Show last 50 records
    df_plot['Time_Sequence'] = range(len(df_plot))
    
    # Draw the chart
    fig = px.line(df_plot, x='Time_Sequence', y='Temperature_C', 
                  title='Engine Temperature Trend (Last 50 Readings)',
                  labels={'Temperature_C': 'Temp (°C)', 'Time_Sequence': 'Time Sequence'},
                  markers=True)
    
    # Update look to look like NASA style (dark background)
    fig.update_layout(template="plotly_dark")
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.info("Smacky Tip: Hover over the graph to see exact values. Notice the 'spikes' - those are potential anomalies.")

else:
    st.warning("No data available to graph.")

#Cloud Auditor Section

st.divider()
st.subheader("🔍 Automated Cloud Auditor")

# Button to trigger the audit
if st.button("Run Full System Diagnostic Audit"):
    if not df_history.empty:
        st.info("Processing 1000+ records from Cloud Storage... Please wait.")
        
        # 1. PREPARE DATA FOR THE MODEL
        # The model was trained on columns named 'Temperature', 'Vibration', 'Fuel'.
        # But the S3 data has names like 'Temperature_C', 'Vibration_Hz'.
        # We must rename them so the AI understands them.
        audit_data = df_history[['Temperature_C', 'Vibration_Hz', 'Fuel_Level_%']].copy()
        audit_data.columns = ['Temperature', 'Vibration', 'Fuel'] # Renaming for the AI
        
        # 2. RUN PREDICTIONS ON ALL ROWS
        bulk_predictions = model.predict(audit_data)
        
        # 3. COUNT THE DANGERS
        danger_count = sum(bulk_predictions)
        safe_count = len(bulk_predictions) - danger_count
        risk_percentage = (danger_count / len(bulk_predictions)) * 100
        
        # 4. DISPLAY RESULTS
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total Records Analyzed", len(bulk_predictions))
        col_b.metric("Critical Anomalies Detected", danger_count)
        col_c.metric("System Risk Level", f"{risk_percentage:.1f}%")
        
        if risk_percentage > 5.0:
            st.error("Smacky Warning: High Risk detected in historical data! Investigation required.")
        else:
            st.success("Smacky Report: Historical data is mostly Nominal. System is stable.")
            
    else:
        st.warning("No data found to audit.")


def generate_report(temp, vib, fuel, prediction, confidence):
    pdf = FPDF()
    pdf.add_page()
    
    # Set Title Font
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="AETHER SYSTEM - INCIDENT REPORT", ln=True, align='C')
    
    # Set Normal Font
    pdf.set_font("Arial", '', 12)
    
    # Write Data
    date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf.cell(200, 10, txt=f"Report Generated: {date_time}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.cell(200, 10, txt="SENSOR READINGS:", ln=True)
    pdf.cell(200, 10, txt=f"Engine Temperature: {temp} °C", ln=True)
    pdf.cell(200, 10, txt=f"Vibration Freq: {vib} Hz", ln=True)
    pdf.cell(200, 10, txt=f"Fuel Level: {fuel} %", ln=True)
    pdf.ln(10)
    
    pdf.cell(200, 10, txt="AI ANALYSIS:", ln=True)
    
    if prediction == 1:
        pdf.set_text_color(255, 0, 0)
        pdf.cell(200, 10, txt="STATUS: CRITICAL FAILURE DETECTED", ln=True)
        pdf.cell(200, 10, txt="ACTION: Initiate Emergency Shutdown Protocol.", ln=True)
    else:
        pdf.set_text_color(0, 128, 0)
        pdf.cell(200, 10, txt="STATUS: SYSTEM NOMINAL", ln=True)
        pdf.cell(200, 10, txt="ACTION: Continue Monitoring.", ln=True)
        
    pdf.set_text_color(0, 0, 0)
    output_filename = "Mission_Report.pdf"
    pdf.output(output_filename)
    return output_filename

# --- REPORT GENERATION SECTION ---
st.markdown("---")
if st.button("📄 Generate Official PDF Report"):
    with st.spinner('Generating Report...'):
        pdf_file = generate_report(temp, vib, fuel, prediction, probability*100)
        with open(pdf_file, "rb") as f:
            st.download_button(
                label="Download PDF Document",
                data=f,
                file_name=pdf_file,
                mime="application/pdf"

            )

