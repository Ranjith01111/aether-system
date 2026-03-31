import datetime

import boto3
import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from botocore.config import Config
from fpdf import FPDF
from tensorflow.keras.models import load_model

BUCKET_NAME = "aether-project-data"
FILE_KEYS = [
    "live_data.csv",
    "telemetry_data.csv",
    "telemetry_batch.csv",
    "telemetry_batch_1.csv",
]
LOCAL_FALLBACK_FILES = [
    "telemetry_batch_1.csv",
]
PLOT_CONFIG = {
    "displaylogo": False,
    "displayModeBar": True,
    "responsive": True,
    "scrollZoom": True,
    "staticPlot": False,
    "doubleClick": "reset",
}


def normalize_live_data(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.rename(
        columns={
            "Time_Stamp": "Time",
            "Temperature_C": "Temperature",
            "Vibration_Hz": "Vibration",
        }
    ).copy()

    if "Temperature" not in df.columns:
        return pd.DataFrame()

    if "Time" not in df.columns:
        df["Time"] = [f"T-{idx}" for idx in range(len(df), 0, -1)]

    if "Vibration" not in df.columns:
        df["Vibration"] = np.nan

    df["Temperature"] = pd.to_numeric(df["Temperature"], errors="coerce")
    df["Vibration"] = pd.to_numeric(df["Vibration"], errors="coerce")
    df = df.dropna(subset=["Temperature"]).reset_index(drop=True)
    return df[["Time", "Temperature", "Vibration"]]


def build_simulated_data(target_temp: float, points: int = 50) -> pd.DataFrame:
    end_time = pd.Timestamp.now().floor("s")
    times = pd.date_range(end=end_time, periods=points, freq="s")
    normalized_temp = np.clip((target_temp - 80.0) / 70.0, 0.0, 1.0)
    phase = np.linspace(0, 1, points)

    if target_temp < 95:
        base_trend = np.linspace(target_temp - 4.0, target_temp, points)
        wave = np.sin(phase * 2.2 * np.pi) * 0.9
    elif target_temp < 120:
        base_trend = np.linspace(target_temp - 7.0, target_temp, points)
        wave = (
            np.sin(phase * 3.5 * np.pi) * (1.4 + normalized_temp * 1.2)
            + np.sin(phase * 8.0 * np.pi) * 0.35
        )
    else:
        base_trend = np.linspace(target_temp - 11.0, target_temp + 2.0, points)
        spike = np.exp(-((phase - 0.72) ** 2) / 0.003) * (3.0 + normalized_temp * 2.5)
        wave = np.sin(phase * 5.5 * np.pi) * (2.0 + normalized_temp * 1.5) + spike

    temperature_values = np.round(base_trend + wave, 2).astype(float).tolist()
    temperature_values[-1] = round(target_temp, 2)
    vibration_values = 44 + normalized_temp * 18 + np.gradient(temperature_values) * 3.4 + np.cos(phase * 4 * np.pi) * 1.2

    return pd.DataFrame(
        {
            "Time": times.strftime("%H:%M:%S"),
            "Temperature": temperature_values,
            "Vibration": np.round(np.clip(vibration_values, 35, 75), 2),
        }
    )


def append_history(history_key: str, incoming: pd.DataFrame, limit: int = 50) -> pd.DataFrame:
    if incoming.empty:
        return pd.DataFrame(columns=["Time", "Temperature", "Vibration"])

    history = st.session_state.get(history_key)
    if history is None or history.empty:
        history = incoming.copy()
    else:
        history = pd.concat([history, incoming], ignore_index=True)

    history["Temperature"] = pd.to_numeric(history["Temperature"], errors="coerce")
    history["Vibration"] = pd.to_numeric(history["Vibration"], errors="coerce")
    history = history.dropna(subset=["Temperature"]).tail(limit).reset_index(drop=True)
    st.session_state[history_key] = history
    return history


def prepare_manual_history(target_temp: float) -> pd.DataFrame:
    previous_temp = st.session_state.get("manual_target_temp")
    if previous_temp is None or abs(previous_temp - target_temp) >= 0.25:
        history = build_simulated_data(target_temp)
    else:
        history = st.session_state.get("manual_history")
        if history is None or history.empty:
            history = build_simulated_data(target_temp)

    st.session_state["manual_target_temp"] = target_temp
    st.session_state["manual_history"] = history
    return history


def prepare_live_history(df_cloud: pd.DataFrame) -> pd.DataFrame:
    if df_cloud.empty:
        return pd.DataFrame(columns=["Time", "Temperature", "Vibration"])

    latest = df_cloud.tail(min(len(df_cloud), 5)).copy().reset_index(drop=True)
    current_times = pd.date_range(end=pd.Timestamp.now().floor("s"), periods=len(latest), freq="s")
    latest["Time"] = current_times.strftime("%H:%M:%S")
    return append_history("live_history", latest, limit=50)


def build_prediction_sequence(df_live: pd.DataFrame, target_temp: float, length: int = 60) -> np.ndarray:
    if df_live.empty:
        return np.linspace(target_temp - 5, target_temp, length)

    source = df_live["Temperature"].astype(float).to_numpy()
    if len(source) == 1:
        return np.full(length, source[0], dtype=float)

    source_x = np.linspace(0, 1, len(source))
    target_x = np.linspace(0, 1, length)
    seq = np.interp(target_x, source_x, source)
    seq[-1] = target_temp
    return seq


def inject_auto_refresh(enabled: bool, seconds: int) -> None:
    if not enabled:
        return

    refresh_ms = max(seconds, 2) * 1000
    st.markdown(
        f"""
        <script>
        setTimeout(function() {{
            window.location.reload();
        }}, {refresh_ms});
        </script>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=5)
def load_live_data() -> pd.DataFrame:
    aws_access_key = st.secrets.get("AWS_ACCESS_KEY_ID")
    aws_secret_key = st.secrets.get("AWS_SECRET_ACCESS_KEY")
    client_kwargs = {
        "region_name": "ap-south-2",
        "config": Config(connect_timeout=2, read_timeout=2, retries={"max_attempts": 1}),
    }
    if aws_access_key and aws_secret_key:
        client_kwargs["aws_access_key_id"] = aws_access_key
        client_kwargs["aws_secret_access_key"] = aws_secret_key

    s3 = boto3.client("s3", **client_kwargs)
    for file_key in FILE_KEYS:
        try:
            response = s3.get_object(Bucket=BUCKET_NAME, Key=file_key)
            df = pd.read_csv(response["Body"])
            normalized = normalize_live_data(df)
            if not normalized.empty:
                return normalized.tail(50).reset_index(drop=True)
        except Exception:
            continue

    for file_path in LOCAL_FALLBACK_FILES:
        try:
            df = pd.read_csv(file_path)
            normalized = normalize_live_data(df)
            if not normalized.empty:
                return normalized.tail(50).reset_index(drop=True)
        except Exception:
            continue

    return pd.DataFrame()


@st.cache_resource
def load_ai_brain():
    try:
        model = load_model("aether_brain_v2.h5")
        scaler = joblib.load("scaler.pkl")
        return model, scaler
    except Exception:
        return None, None


def generate_report(live_temp: float, prediction: float) -> str:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="AETHER MISSION REPORT", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, txt=f"Timestamp: {datetime.datetime.now()}", ln=True, align="C")
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Live Temperature: {live_temp:.2f} C", ln=True)
    pdf.cell(200, 10, txt=f"AI Predicted Next Step: {prediction:.2f} C", ln=True)
    filename = "Mission_Report.pdf"
    pdf.output(filename)
    return filename


st.set_page_config(page_title="AETHER MASTER", page_icon="rocket", layout="wide")
st.title("AETHER SYSTEM - MISSION CONTROL")
st.markdown("### Integrated: Live Cloud Telemetry and Deep Learning AI")

st.sidebar.header("Control Center")
st.sidebar.subheader("Telemetry Inputs")
sim_temp = st.sidebar.slider("Simulate Engine Temp (C)", 80.0, 150.0, 100.0, 0.5)
enable_ai = st.sidebar.checkbox("Enable AI Brain", value=False)
use_live_data = st.sidebar.checkbox("Use Live Cloud Data", value=False)
auto_refresh = st.sidebar.checkbox("Auto Refresh", value=use_live_data)
refresh_seconds = st.sidebar.slider("Refresh Every (s)", 2, 15, 5)
manual_refresh = st.sidebar.button("Refresh Now")

if manual_refresh:
    st.cache_data.clear()

inject_auto_refresh(auto_refresh, refresh_seconds)

col1, col2, col3 = st.columns(3)

df_cloud = load_live_data() if use_live_data else pd.DataFrame()
if use_live_data and not df_cloud.empty:
    df_live = prepare_live_history(df_cloud)
    source_name = "LIVE CLOUD"
elif use_live_data:
    df_live = pd.DataFrame(columns=["Time", "Temperature", "Vibration"])
    source_name = "LIVE CLOUD (NO SIGNAL)"
else:
    df_live = prepare_manual_history(sim_temp)
    source_name = "MANUAL SIMULATION"

live_temp_val = 0.0
if not df_live.empty:
    live_temp_val = float(df_live["Temperature"].iloc[-1])
    delta_val = 0.0 if len(df_live) < 2 else live_temp_val - float(df_live["Temperature"].iloc[-2])
    col1.metric("Current Temp", f"{live_temp_val:.2f} C", f"{delta_val:+.2f} C")
else:
    col1.metric("Current Temp", "No Signal")

model = None
scaler = None
if enable_ai:
    ai_status = st.empty()
    ai_status.info("Loading AI brain...")
    model, scaler = load_ai_brain()
    ai_status.empty()

target_temp = live_temp_val if not df_live.empty else sim_temp
col2.metric("Prediction Source", source_name)

pred_val = None
seq = build_prediction_sequence(df_live, target_temp, 60)
if model is not None and scaler is not None:
    seq_scaled = scaler.transform(pd.DataFrame({"Temperature": seq}))
    seq_input = seq_scaled.reshape(1, 60, 1)
    pred_scaled = model.predict(seq_input, verbose=0)
    pred_val = float(scaler.inverse_transform(pred_scaled)[0][0])
    trend_label = "RISING" if pred_val > target_temp else "STABLE"
    col3.metric("AI Predicted (Next 5s)", f"{pred_val:.2f} C", trend_label)

    if pred_val > 120.0:
        st.error(f"SENTINEL ALERT: AI predicts critical failure ({pred_val:.1f} C)")
else:
    col3.metric("AI Predicted (Next 5s)", "Brain Offline")

st.divider()
c1, c2 = st.columns(2)

if not df_live.empty:
    telemetry_plot_df = df_live.copy()
    telemetry_plot_df["Sample"] = np.arange(1, len(telemetry_plot_df) + 1)
    c1.subheader("Telemetry Trend Analysis")
    telemetry_fig = px.line(
        telemetry_plot_df,
        x="Sample",
        y="Temperature",
        title="Engine Temperature Trend (Last 50 Samples)",
        labels={"Temperature": "Temp (C)", "Sample": "Sample"},
        markers=True,
        hover_data={"Time": True, "Vibration": True, "Sample": False},
    )
    telemetry_fig.update_layout(
        template="plotly_dark",
        dragmode="zoom",
        xaxis_title="Sample",
        yaxis_title="Temp (C)",
    )
    telemetry_fig.update_xaxes(fixedrange=False)
    telemetry_fig.update_yaxes(fixedrange=False)
    c1.plotly_chart(telemetry_fig, width="stretch", config=PLOT_CONFIG)

    with st.expander("View Raw Data"):
        st.dataframe(df_live, width="stretch")
else:
    c1.warning("Waiting for telemetry data...")

if model is not None and scaler is not None:
    c2.subheader("AI Trend Simulation")
    df_sim = pd.DataFrame({"Sequence": np.arange(1, 61), "Temp": seq})
    ai_fig = px.line(
        df_sim,
        x="Sequence",
        y="Temp",
        title=f"AI Input Sequence Ending at {target_temp:.2f} C",
        markers=True,
    )
    ai_fig.update_layout(template="plotly_dark", dragmode="zoom")
    ai_fig.update_xaxes(fixedrange=False)
    ai_fig.update_yaxes(fixedrange=False)
    c2.plotly_chart(ai_fig, width="stretch", config=PLOT_CONFIG)
else:
    c2.info("Enable the AI brain from the sidebar to load the prediction model.")

st.divider()
if st.button("Generate Mission Report"):
    if pred_val is not None:
        pdf_file = generate_report(live_temp_val, pred_val)
        with open(pdf_file, "rb") as file_handle:
            st.download_button(
                label="Download PDF",
                data=file_handle,
                file_name=pdf_file,
                mime="application/pdf",
            )
    else:
        st.warning("Enable the AI brain to generate a report.")

if pred_val is not None and not df_live.empty:
    st.subheader("Future Horizon (Next 5 Seconds)")
    past_time = np.arange(-len(seq), 0)
    future_time = np.array([5])
    df_horizon = pd.DataFrame(
        {
            "Time_Seconds": list(past_time) + list(future_time),
            "Temperature_C": list(seq) + [pred_val],
            "Type": ["History"] * len(seq) + ["Prediction"],
        }
    )

    horizon_fig = px.line(
        df_horizon,
        x="Time_Seconds",
        y="Temperature_C",
        color="Type",
        line_dash="Type",
        title=f"Past to Future (Live {target_temp:.1f} C to Pred {pred_val:.1f} C)",
        markers=True,
    )
    horizon_fig.update_layout(template="plotly_dark", dragmode="zoom")
    horizon_fig.update_xaxes(fixedrange=False)
    horizon_fig.update_yaxes(fixedrange=False)
    st.plotly_chart(horizon_fig, width="stretch", config=PLOT_CONFIG)
