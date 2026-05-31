import streamlit as st
import serial
import serial.tools.list_ports
import json
import time
import base64
import asyncio
import re
from groq import Groq
import requests
from PIL import Image
import io
import pandas as pd

# ================== Page Config ==================
st.set_page_config(
    page_title="Circuit Diagnostics & Hardware Re‑engineering",
    page_icon="🔌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================== Styling ==================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0a0f1e 0%, #0d1b2a 100%);
    }
    .main-header {
        font-size: 2.5rem;
        background: linear-gradient(90deg, #00d4ff, #7b2ff7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
    }
    .diagnostic-card {
        background: rgba(255,255,255,0.05);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #00d4ff;
    }
    .fault-badge {
        background: #ff4b4b;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.7rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# ================== Groq Setup ==================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    st.error("Missing GROQ_API_KEY in secrets.")
    st.stop()
client = Groq(api_key=GROQ_API_KEY)

# ================== Hardware USB Probe (Mock / Real) ==================
def list_usb_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def connect_to_probe(port, baudrate=115200, timeout=2):
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout)
        return ser
    except Exception as e:
        st.error(f"USB connection error: {e}")
        return None

def read_probe_data(ser):
    """Read line from serial probe. Expected JSON: {"chip": "U1", "pin": 5, "voltage": 3.3, "expected": 3.3}"""
    if ser and ser.in_waiting:
        line = ser.readline().decode('utf-8').strip()
        try:
            data = json.loads(line)
            return data
        except:
            return {"raw": line}
    return None

# ================== Image Analysis (Groq Vision) ==================
def analyze_circuit_image(uploaded_image):
    """Send image to Groq's vision model to identify chips and possible faults."""
    # Convert PIL image to base64
    img = Image.open(uploaded_image)
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    prompt = """You are a circuit board expert. Analyze this PCB image and:
1. List all major ICs/chips you can identify (by package, label, or position).
2. For each, note any visible damage (burn marks, cracks, corrosion).
3. Suggest the most likely failed component(s) and why.
4. Provide a step-by-step diagnostic plan.
Return as JSON with keys: chips, visible_damage, likely_failed_components, diagnostic_plan.
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                ]}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        return {"error": str(e), "chips": [], "likely_failed_components": "Could not analyze"}

# ================== Diagnostic Reasoning (LLM) ==================
def diagnose_faults(chip_data, probe_readings, image_analysis):
    prompt = f"""
You are a hardware diagnostic engineer. Based on the following information, identify which chips are malfunctioning, what is wrong, and what should be done (remove, repair, replace, or rework).

Image Analysis: {json.dumps(image_analysis, indent=2)}
Probe Readings (USB): {json.dumps(probe_readings, indent=2)}
Chip Database (known good values): {json.dumps(chip_data, indent=2)}

Provide output as JSON with keys:
- "fault_summary": brief description
- "actions": list of dicts with keys "chip", "fault", "action" (remove/repair/replace), "reason"
- "recommended_tools": list of tools needed
"""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# ================== Hardware Redesign Assistant ==================
def redesign_question(question, current_circuit_info):
    prompt = f"""
You are a hardware re‑engineering expert. The user has a broken circuit board with the following known components and faults:
{json.dumps(current_circuit_info, indent=2)}

The user asks: "{question}"

Based on the existing chips, suggest modifications, component substitutions, or a new schematic to build a custom hardware device that fulfills the request.
Provide a detailed answer including:
- Which chips can be reused.
- What new components are needed.
- How to wire them (conceptual).
- Any firmware or programming required.
Answer in clear, actionable language.
"""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=1500
    )
    return response.choices[0].message.content

# ================== Mock Chip Database ==================
# FIXED: All values are now strings (no syntax error)
DEFAULT_CHIP_DB = {
    "U1": {"type": "Voltage Regulator (LM7805)", "pins": {"in": "5-12V", "out": "5V", "gnd": "0V"}, "common_faults": ["overheating", "output short"]},
    "U2": {"type": "Microcontroller (STM32F103)", "pins": {"VDD": "3.3V", "VSS": "0V", "PA9": "TX"}, "common_faults": ["bent pins", "brownout"]},
    "Q1": {"type": "MOSFET (IRFZ44N)", "pins": {"Gate": "0-5V", "Drain": "12V", "Source": "GND"}, "common_faults": ["shorted gate", "overcurrent"]}
}

# ================== Session State ==================
if "probe_serial" not in st.session_state:
    st.session_state.probe_serial = None
if "probe_connected" not in st.session_state:
    st.session_state.probe_connected = False
if "image_analysis" not in st.session_state:
    st.session_state.image_analysis = {}
if "probe_readings" not in st.session_state:
    st.session_state.probe_readings = []
if "diagnosis_result" not in st.session_state:
    st.session_state.diagnosis_result = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ================== Sidebar: USB Connection ==================
st.sidebar.title("🔌 USB Probe")
ports = list_usb_ports()
selected_port = st.sidebar.selectbox("Select USB Port", ports) if ports else None
if st.sidebar.button("Connect", disabled=st.session_state.probe_connected):
    if selected_port:
        ser = connect_to_probe(selected_port)
        if ser:
            st.session_state.probe_serial = ser
            st.session_state.probe_connected = True
            st.sidebar.success(f"Connected to {selected_port}")
        else:
            st.sidebar.error("Failed to connect")
if st.sidebar.button("Disconnect"):
    if st.session_state.probe_serial:
        st.session_state.probe_serial.close()
    st.session_state.probe_connected = False
    st.session_state.probe_serial = None
    st.sidebar.info("Disconnected")

if st.session_state.probe_connected:
    # Poll for data (simple loop in Streamlit – works for demo)
    data = read_probe_data(st.session_state.probe_serial)
    if data:
        st.session_state.probe_readings.append(data)
        st.sidebar.write(f"Last reading: {data}")

st.sidebar.markdown("---")
st.sidebar.info("**Instructions**\n1. Connect USB probe to your laptop.\n2. Upload a photo of the waste circuit.\n3. Run diagnostic.\n4. Ask the AI to redesign a new hardware from the broken board.")

# ================== Main Layout ==================
st.markdown("<h1 class='main-header'>⚡ Circuit Diagnostics & Hardware Re‑engineering</h1>", unsafe_allow_html=True)
st.caption("Upload a photo of a broken circuit board, connect USB probe, and let AI diagnose faults + help you build new hardware from the salvageable chips.")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📸 Circuit Image Upload")
    uploaded_image = st.file_uploader("Take a picture of the waste circuit", type=["jpg", "jpeg", "png"])
    if uploaded_image:
        st.image(uploaded_image, caption="Uploaded circuit", width=300)
        if st.button("🔍 Analyze Image with AI"):
            with st.spinner("Analyzing image (Groq Vision)..."):
                analysis = analyze_circuit_image(uploaded_image)
                st.session_state.image_analysis = analysis
                st.success("Analysis complete")
                st.json(analysis)

with col2:
    st.subheader("📊 Probe Readings (USB)")
    if st.session_state.probe_readings:
        st.dataframe(pd.DataFrame(st.session_state.probe_readings))
        if st.button("Clear Readings"):
            st.session_state.probe_readings = []
            st.rerun()
    else:
        st.info("No data yet. Connect USB probe and ensure the hardware is sending JSON lines.")

# ================== Diagnostic Button ==================
if st.button("🚀 Run Full Diagnostic (Image + Probe)"):
    if not st.session_state.image_analysis and not uploaded_image:
        st.warning("Please upload an image first.")
    else:
        with st.spinner("Running AI diagnostics..."):
            # Use the latest image analysis (or re-run)
            if uploaded_image and not st.session_state.image_analysis:
                st.session_state.image_analysis = analyze_circuit_image(uploaded_image)
            result = diagnose_faults(
                chip_data=DEFAULT_CHIP_DB,
                probe_readings=st.session_state.probe_readings,
                image_analysis=st.session_state.image_analysis
            )
            st.session_state.diagnosis_result = result
            st.success("Diagnostic completed.")

if st.session_state.diagnosis_result:
    st.subheader("🩺 Diagnostic Report")
    res = st.session_state.diagnosis_result
    st.write(f"**Fault Summary:** {res.get('fault_summary', 'N/A')}")
    st.write("**Actions:**")
    for act in res.get('actions', []):
        st.markdown(f"- **{act.get('chip')}** : {act.get('fault')} → {act.get('action')} ({act.get('reason')})")
    st.write(f"**Recommended Tools:** {', '.join(res.get('recommended_tools', []))}")

# ================== Hardware Redesign Chatbot ==================
st.markdown("---")
st.subheader("🤖 Build New Hardware from this Board")
st.write("Ask the AI to redesign the salvageable chips into a completely new device (e.g., a custom drone controller, USB peripheral, etc.).")

# Display chat history
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input for user query
if prompt := st.chat_input("Describe what you want to build (e.g., 'Make a drone flight controller using the existing microcontroller and MOSFETs')"):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Prepare context: current image analysis + probe readings + diagnosis
    context = {
        "image_analysis": st.session_state.image_analysis,
        "probe_readings": st.session_state.probe_readings[-10:],  # last 10
        "diagnosis": st.session_state.diagnosis_result,
        "available_chips": DEFAULT_CHIP_DB
    }
    with st.chat_message("assistant"):
        with st.spinner("Designing your new hardware..."):
            answer = redesign_question(prompt, context)
            st.markdown(answer)
    st.session_state.chat_history.append({"role": "assistant", "content": answer})

# ================== Footer ==================
st.markdown("---")
st.caption("🔧 Built with Streamlit + Groq AI + USB Serial. For full hardware integration, connect a probe that sends JSON diagnostics over USB.")
