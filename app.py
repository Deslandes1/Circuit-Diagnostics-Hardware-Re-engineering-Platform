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
        background: linear-gradient(135deg, #2d1b69 0%, #5e2a84 100%) !important;
        background-attachment: fixed;
    }
    [data-testid="stSidebar"], [data-testid="stSidebarUserContent"], section[data-testid="stSidebar"] {
        background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%) !important;
        background-attachment: fixed;
    }
    h1, h2, h3, h4, p, label, .stMarkdown, .stSelectbox label, .st-bb, .st-at, .stSidebar * {
        color: #ffffff !important;
    }
    .stSidebar .stAlert, .stSidebar .stInfo {
        background: rgba(0,0,0,0.3) !important;
        color: white !important;
    }
    .main-header {
        font-size: 2.5rem;
        background: linear-gradient(90deg, #e0aaff, #ff99cc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
    }
    .credit {
        text-align: center;
        font-size: 1rem;
        color: #e0aaff !important;
        margin-top: -0.5rem;
        margin-bottom: 1rem;
    }
    .diagnostic-card {
        background: rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #e0aaff;
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: rgba(255,255,255,0.1) !important;
        color: white !important;
        border: 1px solid #e0aaff !important;
    }
    .stChatInput input {
        background-color: rgba(255,255,255,0.1) !important;
        color: white !important;
    }
    .info-box {
        background: rgba(0,0,0,0.5);
        padding: 10px;
        border-radius: 8px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ================== Translation Dictionary (shortened for brevity – keep full from previous version) ==================
LANGUAGES = {
    "English": {
        "app_title": "⚡ Circuit Diagnostics & Hardware Re‑engineering",
        "credit": "built by Gesner Deslandes",
        "caption": "Upload a photo of a broken circuit board, connect USB probe, and let AI diagnose faults + help you build new hardware from the salvageable chips.",
        "sidebar_instructions": "**Instructions**\n1. Connect your USB probe (Arduino or any device that sends JSON over Serial).\n2. Select the correct COM port below and click Connect.\n3. Your probe MUST send lines like: {\"chip\":\"U1\",\"voltage\":3.3}\n4. Upload a photo of the circuit.\n5. Run diagnostic.",
        "usb_title": "🔌 USB Probe",
        "select_port": "Select USB Port",
        "connect_btn": "Connect",
        "disconnect_btn": "Disconnect",
        "connected_success": "Connected to {}",
        "failed_connect": "Failed to connect",
        "disconnected": "Disconnected",
        "last_reading": "Last reading: {}",
        "image_upload": "📸 Circuit Image Upload",
        "upload_label": "Take a picture of the waste circuit",
        "analyze_btn": "🔍 Analyze Image with AI",
        "analyzing": "Analyzing image (Groq Vision)...",
        "analysis_complete": "Analysis complete",
        "probe_readings_title": "📊 Probe Readings (USB)",
        "clear_readings_btn": "Clear Readings",
        "no_data": "No data received yet. Make sure your probe is sending JSON lines.",
        "diagnostic_btn": "🚀 Run Full Diagnostic (Image + Probe)",
        "upload_first": "Please upload an image first.",
        "running_diag": "Running AI diagnostics...",
        "diag_complete": "Diagnostic completed.",
        "diagnostic_report": "🩺 Diagnostic Report",
        "device_type": "Device Type",
        "probe_data_status": "Real probe data used",
        "probe_data_yes": "✅ Yes – {} measurements were received from the USB probe.",
        "probe_data_no": "⚠️ No real probe data was received. Diagnostic is a simulation based only on the image. Please check your USB connection and make sure the probe sends JSON lines.",
        "fault_summary": "Fault Summary",
        "actions": "Actions",
        "recommended_tools": "Recommended Tools",
        "build_title": "🤖 Build New Hardware from this Board",
        "build_desc": "Ask the AI to redesign the salvageable chips into a completely new device.",
        "chat_placeholder": "Describe what you want to build",
        "designing": "Designing your new hardware...",
        "footer": "🔧 Built with Streamlit + Groq AI + USB Serial.",
        "sidebar_contact": "📞 Contact",
        "phone": "📱 (509)-47385663",
        "email": "✉️ deslandes78@gmail.com",
        "website": "🌐 GlobalInternet.py",
        "website_link": "https://globalinternetsitepy-abh7v6tnmskxxnuplrdcgk.streamlit.app/",
        "lang_code": "English"
    },
    # ... include other languages similarly (French, Spanish, Creole) from previous version
}

# ================== Groq Setup ==================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    st.error("Missing GROQ_API_KEY in secrets.")
    st.stop()
client = Groq(api_key=GROQ_API_KEY)

# ================== Hardware USB Probe ==================
def list_usb_ports():
    ports = serial.tools.list_ports.comports()
    return [{"device": port.device, "description": port.description} for port in ports]

def connect_to_probe(port, baudrate=115200, timeout=2):
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout)
        return ser
    except Exception as e:
        st.error(f"USB connection error: {e}")
        return None

def read_probe_data(ser):
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
    img = Image.open(uploaded_image)
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    prompt = """You are a circuit board expert. Analyze this PCB image and:
1. List all major ICs/chips you can identify.
2. Note any visible damage.
3. Suggest likely failed components.
4. Provide a diagnostic plan.
Return as JSON with keys: chips, visible_damage, likely_failed_components, diagnostic_plan.
"""
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
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

# ================== Device Identification ==================
def identify_device(image_analysis, target_language):
    language_instruction = f"Answer in {target_language}."
    prompt = f"""
{language_instruction}
Based on the following circuit board image analysis, identify what type of device this board comes from (laptop, desktop, tablet, etc.). Include brand if possible.
Image analysis: {json.dumps(image_analysis, indent=2)}
Return JSON with key "device_type".
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("device_type", "Unknown device")
    except Exception:
        return "Unknown device"

# ================== Diagnostic Reasoning ==================
def diagnose_faults(chip_data, probe_readings, image_analysis, device_type, target_language):
    language_instruction = f"Output JSON in {target_language}."
    prompt = f"""
{language_instruction}
Device Type: {device_type}
Probe Readings (USB): {json.dumps(probe_readings, indent=2)}
Image Analysis: {json.dumps(image_analysis, indent=2)}
Chip Database: {json.dumps(chip_data, indent=2)}

Return JSON with keys: "fault_summary", "actions" (list of {chip, fault, action, reason}), "recommended_tools".
"""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# ================== Hardware Redesign Assistant ==================
def redesign_question(question, current_circuit_info, target_language):
    language_instruction = f"Answer in {target_language}."
    prompt = f"""
{language_instruction}
The user has a broken board with: {json.dumps(current_circuit_info, indent=2)}
Question: "{question}"
Suggest reuse of chips, new components, wiring, and firmware.
"""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=1500
    )
    return response.choices[0].message.content

# ================== Mock Chip Database ==================
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
if "device_type" not in st.session_state:
    st.session_state.device_type = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "lang" not in st.session_state:
    st.session_state.lang = "English"

# ================== Sidebar ==================
st.sidebar.title("🌐 Language")
selected_lang = st.sidebar.selectbox("", list(LANGUAGES.keys()), index=list(LANGUAGES.keys()).index(st.session_state.lang))
if selected_lang != st.session_state.lang:
    st.session_state.lang = selected_lang
    st.rerun()

t = LANGUAGES[st.session_state.lang]

st.sidebar.markdown("---")
st.sidebar.title(t["usb_title"])
ports = list_usb_ports()
if ports:
    port_options = {p["device"]: f"{p['device']} - {p['description']}" for p in ports}
    selected_port = st.sidebar.selectbox(t["select_port"], options=list(port_options.keys()), format_func=lambda x: port_options[x])
else:
    selected_port = None
    st.sidebar.warning("No USB ports detected. Plug in your probe and refresh.")

if st.sidebar.button(t["connect_btn"], disabled=st.session_state.probe_connected):
    if selected_port:
        ser = connect_to_probe(selected_port)
        if ser:
            st.session_state.probe_serial = ser
            st.session_state.probe_connected = True
            st.sidebar.success(t["connected_success"].format(selected_port))
        else:
            st.sidebar.error(t["failed_connect"])
if st.sidebar.button(t["disconnect_btn"]):
    if st.session_state.probe_serial:
        st.session_state.probe_serial.close()
    st.session_state.probe_connected = False
    st.session_state.probe_serial = None
    st.sidebar.info(t["disconnected"])

# Try to read data if connected
if st.session_state.probe_connected:
    data = read_probe_data(st.session_state.probe_serial)
    if data:
        st.session_state.probe_readings.append(data)
        st.sidebar.write(t["last_reading"].format(data))
        # Show success icon in sidebar
        st.sidebar.success("✅ Receiving data!")
    else:
        st.sidebar.warning("⏳ Waiting for data... Make sure your probe is sending JSON lines.")

st.sidebar.markdown("---")
st.sidebar.info(t["sidebar_instructions"])
st.sidebar.markdown("---")
st.sidebar.subheader(t["sidebar_contact"])
st.sidebar.write(t["phone"])
st.sidebar.write(t["email"])
st.sidebar.markdown(f"[{t['website']}]({t['website_link']})")

# ================== Main Layout ==================
st.markdown(f"<h1 class='main-header'>{t['app_title']}</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='credit'>{t['credit']}</p>", unsafe_allow_html=True)
st.caption(t["caption"])

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader(t["image_upload"])
    uploaded_image = st.file_uploader(t["upload_label"], type=["jpg", "jpeg", "png"])
    if uploaded_image:
        st.image(uploaded_image, caption="Uploaded circuit", width=300)
        if st.button(t["analyze_btn"]):
            with st.spinner(t["analyzing"]):
                analysis = analyze_circuit_image(uploaded_image)
                st.session_state.image_analysis = analysis
                st.success(t["analysis_complete"])
                st.json(analysis)

with col2:
    st.subheader(t["probe_readings_title"])
    if st.session_state.probe_readings:
        st.dataframe(pd.DataFrame(st.session_state.probe_readings))
        if st.button(t["clear_readings_btn"]):
            st.session_state.probe_readings = []
            st.rerun()
    else:
        st.info(t["no_data"])

# Diagnostic Button
if st.button(t["diagnostic_btn"]):
    if not st.session_state.image_analysis and not uploaded_image:
        st.warning(t["upload_first"])
    else:
        with st.spinner(t["running_diag"]):
            if uploaded_image and not st.session_state.image_analysis:
                st.session_state.image_analysis = analyze_circuit_image(uploaded_image)
            st.session_state.device_type = identify_device(st.session_state.image_analysis, t["lang_code"])
            result = diagnose_faults(
                chip_data=DEFAULT_CHIP_DB,
                probe_readings=st.session_state.probe_readings,
                image_analysis=st.session_state.image_analysis,
                device_type=st.session_state.device_type,
                target_language=t["lang_code"]
            )
            st.session_state.diagnosis_result = result
            st.success(t["diag_complete"])

if st.session_state.diagnosis_result:
    st.subheader(t["diagnostic_report"])
    res = st.session_state.diagnosis_result
    st.write(f"**{t['device_type']}:** {st.session_state.device_type}")
    
    # Real probe data indicator
    st.write(f"**{t['probe_data_status']}:**")
    if st.session_state.probe_readings:
        st.success(t["probe_data_yes"].format(len(st.session_state.probe_readings)))
    else:
        st.warning(t["probe_data_no"])
    
    st.write(f"**{t['fault_summary']}:** {res.get('fault_summary', 'N/A')}")
    st.write(f"**{t['actions']}:**")
    for act in res.get('actions', []):
        st.markdown(f"- **{act.get('chip')}** : {act.get('fault')} → {act.get('action')} ({act.get('reason')})")
    st.write(f"**{t['recommended_tools']}:** {', '.join(res.get('recommended_tools', []))}")

# Redesign Chatbot
st.markdown("---")
st.subheader(t["build_title"])
st.write(t["build_desc"])

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input(t["chat_placeholder"]):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    context = {
        "image_analysis": st.session_state.image_analysis,
        "probe_readings": st.session_state.probe_readings[-10:],
        "diagnosis": st.session_state.diagnosis_result,
        "available_chips": DEFAULT_CHIP_DB,
        "device_type": st.session_state.device_type
    }
    with st.chat_message("assistant"):
        with st.spinner(t["designing"]):
            answer = redesign_question(prompt, context, target_language=t["lang_code"])
            st.markdown(answer)
    st.session_state.chat_history.append({"role": "assistant", "content": answer})

st.markdown("---")
st.caption(t["footer"])
