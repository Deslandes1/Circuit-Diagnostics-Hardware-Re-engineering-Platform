import streamlit as st
import serial
import serial.tools.list_ports
import json
import time
import base64
import io
import pandas as pd
from groq import Groq
from PIL import Image

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
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: rgba(255,255,255,0.1) !important;
        color: white !important;
        border: 1px solid #e0aaff !important;
    }
    .stChatInput input {
        background-color: rgba(255,255,255,0.1) !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ================== Translation Dictionary ==================
LANGUAGES = {
    "English": {
        "app_title": "⚡ Circuit Diagnostics & Hardware Re‑engineering",
        "credit": "built by Gesner Deslandes",
        "caption": "Upload a photo (optional) of a broken circuit board, or connect a real USB probe. AI will diagnose faults + help you build new hardware.",
        "sidebar_instructions": "**Instructions for REAL hardware**\n1. Build an Arduino probe (see README).\n2. Connect it to your computer via USB.\n3. Select the COM port and click Connect.\n4. The probe must send JSON lines like: {\"chip\":\"U3600\",\"voltage\":3.3}\n5. Run diagnostic.",
        "usb_title": "🔌 REAL USB Probe (Arduino/FTDI)",
        "select_port": "Select USB Port",
        "connect_btn": "Connect",
        "disconnect_btn": "Disconnect",
        "connected_success": "Connected to {}",
        "failed_connect": "Failed to connect",
        "disconnected": "Disconnected",
        "last_reading": "Last reading: {}",
        "image_upload": "📸 Circuit Image Upload (Optional)",
        "upload_label": "Take a picture of the circuit (optional)",
        "analyze_btn": "🔍 Analyze Image with AI",
        "analyzing": "Analyzing image (Groq Vision)...",
        "analysis_complete": "Analysis complete",
        "probe_readings_title": "📊 Real-time Readings (from USB probe)",
        "clear_readings_btn": "Clear Readings",
        "no_data": "No readings yet. Connect your real USB probe.",
        "diagnostic_btn": "🚀 Run Full Diagnostic (REAL hardware)",
        "running_diag": "Running AI diagnostics with real data...",
        "diag_complete": "Diagnostic completed.",
        "diagnostic_report": "🩺 Diagnostic Report (REAL measurements)",
        "device_type": "Device Type (inferred)",
        "manual_device_override": "Manual Device Type Override (if auto fails)",
        "probe_data_status": "Real probe data used",
        "probe_data_yes": "✅ Yes – {} live measurements from USB probe.",
        "probe_data_no": "⚠️ No real probe data. Please connect your Arduino probe.",
        "fault_summary": "Fault Summary",
        "actions": "Actions",
        "recommended_tools": "Recommended Tools",
        "build_title": "🤖 Build New Hardware from this Board",
        "build_desc": "Ask the AI to redesign the salvageable chips into a completely new device.",
        "chat_placeholder": "Describe what you want to build (e.g., 'Make a drone flight controller')",
        "designing": "Designing your new hardware...",
        "footer": "🔧 Built with Streamlit + Groq AI + USB Serial.",
        "sidebar_contact": "📞 Contact",
        "phone": "📱 (509)-47385663",
        "email": "✉️ deslandes78@gmail.com",
        "website": "🌐 GlobalInternet.py",
        "website_link": "https://globalinternetsitepy-abh7v6tnmskxxnuplrdcgk.streamlit.app/",
        "manual_add": "✏️ Manual Entry (only if no hardware)",
        "manual_chip": "Chip name (e.g., U3600)",
        "manual_voltage": "Measured Voltage (V)",
        "manual_expected": "Expected Voltage (V)",
        "manual_add_btn": "Add Reading",
        "lang_code": "English"
    }
}

# ================== Groq Setup ==================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    st.error("Missing GROQ_API_KEY in secrets.")
    st.stop()
client = Groq(api_key=GROQ_API_KEY)

# ================== USB Probe Functions ==================
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

# ================== Image Analysis ==================
def analyze_circuit_image(uploaded_image):
    if uploaded_image is None:
        return None
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
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": str(e), "chips": [], "likely_failed_components": "Could not analyze"}

# ================== Device Identification ==================
def identify_device(image_analysis, readings, manual_override):
    if manual_override and manual_override != "Auto-detect":
        return manual_override
    chip_labels = [r.get("chip", "").upper().strip() for r in readings if "chip" in r]
    all_labels = " ".join(chip_labels)
    iphone_chips = ["U3600", "U3301", "U3100", "U5600", "U4701", "U6100"]
    if any(chip in all_labels for chip in iphone_chips):
        return "iPhone 8+ (or similar Apple smartphone)"
    generic_chips = ["U1", "U2", "U3", "U4"]
    if any(chip in all_labels for chip in generic_chips):
        return "Generic laptop / desktop motherboard"
    if image_analysis and not image_analysis.get("error"):
        prompt = f"""Answer in English. Based on this image analysis, identify the device type.
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
            return json.loads(response.choices[0].message.content).get("device_type", "Unknown device")
        except:
            return "Unknown device"
    return "Unknown device"

# ================== Diagnostic Reasoning ==================
def diagnose_faults(chip_data, probe_readings, image_analysis, device_type, target_language):
    language_instruction = f"Output JSON in {target_language}."
    img_info = image_analysis if image_analysis and not image_analysis.get("error") else {"chips": [], "visible_damage": [], "likely_failed_components": []}
    prompt = f"""{language_instruction}
Device Type: {device_type}
Readings (REAL hardware): {json.dumps(probe_readings, indent=2)}
Image Analysis (if any): {json.dumps(img_info, indent=2)}
Chip Database: {json.dumps(chip_data, indent=2)}

Return JSON with keys:
- "fault_summary": string
- "actions": list of objects with keys "chip", "fault", "action", "reason"
- "recommended_tools": list of strings
"""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# ================== Redesign Assistant ==================
def redesign_question(question, context, target_language):
    language_instruction = f"Answer in {target_language}."
    prompt = f"""{language_instruction}
The user has a broken board with this real hardware data: {json.dumps(context, indent=2)}
They ask: "{question}"
Suggest which chips can be reused, new components, wiring, and firmware.
"""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=1500
    )
    return response.choices[0].message.content

# ================== Chip Database ==================
CHIP_DB = {
    "U3600": {"type": "PMIC (Power Management)", "pins": {"VBATT": "3.8V", "VDD_MAIN": "3.8V"}, "common_faults": ["overheating", "short"]},
    "U3301": {"type": "NAND Flash", "pins": {"VDD_NAND": "1.8V"}, "common_faults": ["dead", "no power"]},
    "U3100": {"type": "A11 Bionic CPU", "pins": {"VCC_MAIN": "3.8V"}, "common_faults": ["shorted capacitor", "dead CPU"]},
    "U5600": {"type": "USB/Charging IC", "pins": {"V_BUS": "5V", "VBATT": "3.8V"}, "common_faults": ["overvoltage", "no charging"]},
    "U1": {"type": "Voltage Regulator (LM7805)", "pins": {"in": "5-12V", "out": "5V"}, "common_faults": ["overheating"]},
}

# ================== Session State ==================
for key in ["probe_serial", "probe_connected", "image_analysis", "readings", "diagnosis_result", "device_type", "chat_history", "lang", "manual_device_override"]:
    if key not in st.session_state:
        st.session_state[key] = None if "serial" in key else (False if "connected" in key else ([] if "readings" in key or "chat_history" in key else ({} if "analysis" in key else ("English" if key == "lang" else "Auto-detect"))))

t = LANGUAGES["English"]

# ================== Sidebar ==================
st.sidebar.title("🔧 Real Hardware Connection")
ports = list_usb_ports()
if ports:
    port_options = {p["device"]: f"{p['device']} - {p['description']}" for p in ports}
    selected_port = st.sidebar.selectbox(t["select_port"], options=list(port_options.keys()), format_func=lambda x: port_options[x])
else:
    selected_port = None
    st.sidebar.warning("No USB ports detected. Plug in your Arduino probe and refresh.")

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

if st.session_state.probe_connected:
    data = read_probe_data(st.session_state.probe_serial)
    if data:
        st.session_state.readings.append(data)
        st.sidebar.success(f"✅ Live data: {data}")
    else:
        st.sidebar.warning("⏳ Waiting for data from Arduino...")

st.sidebar.markdown("---")
st.sidebar.info(t["sidebar_instructions"])

# Manual device override
device_options = ["Auto-detect", "iPhone 8+", "iPhone X", "Samsung Galaxy", "Laptop", "Desktop"]
st.sidebar.selectbox(t["manual_device_override"], device_options, key="manual_device_override")

# ================== Main Layout ==================
st.markdown(f"<h1 class='main-header'>{t['app_title']}</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='credit'>{t['credit']}</p>", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1:
    st.subheader(t["image_upload"])
    uploaded_image = st.file_uploader(t["upload_label"], type=["jpg", "jpeg", "png"])
    if uploaded_image:
        st.image(uploaded_image, width=300)
        if st.button(t["analyze_btn"]):
            with st.spinner(t["analyzing"]):
                st.session_state.image_analysis = analyze_circuit_image(uploaded_image)
                st.success(t["analysis_complete"])
with col2:
    st.subheader(t["probe_readings_title"])
    if st.session_state.readings:
        st.dataframe(pd.DataFrame(st.session_state.readings))
        if st.button(t["clear_readings_btn"]):
            st.session_state.readings = []
            st.rerun()
    else:
        st.info("No live readings yet. Connect your Arduino probe and ensure it sends JSON.")

# Diagnostic Button
if st.button(t["diagnostic_btn"]):
    if not st.session_state.readings:
        st.warning("No real hardware readings. Please connect your USB probe first.")
    else:
        with st.spinner(t["running_diag"]):
            if uploaded_image and not st.session_state.image_analysis:
                st.session_state.image_analysis = analyze_circuit_image(uploaded_image)
            st.session_state.device_type = identify_device(
                st.session_state.image_analysis,
                st.session_state.readings,
                st.session_state.manual_device_override
            )
            result = diagnose_faults(
                chip_data=CHIP_DB,
                probe_readings=st.session_state.readings,
                image_analysis=st.session_state.image_analysis,
                device_type=st.session_state.device_type,
                target_language="English"
            )
            st.session_state.diagnosis_result = result
            st.success(t["diag_complete"])

if st.session_state.diagnosis_result:
    st.subheader(t["diagnostic_report"])
    res = st.session_state.diagnosis_result
    st.write(f"**{t['device_type']}:** {st.session_state.device_type}")
    st.write(f"**Real probe data used:** ✅ {len(st.session_state.readings)} live measurements")
    st.write(f"**{t['fault_summary']}:** {res.get('fault_summary', 'N/A')}")
    st.write(f"**{t['actions']}:**")
    for act in res.get('actions', []):
        st.markdown(f"- **{act.get('chip')}** : {act.get('fault')} → {act.get('action')} ({act.get('reason')})")
    st.write(f"**{t['recommended_tools']}:** {', '.join(res.get('recommended_tools', []))}")

# ================== Footer ==================
st.markdown("---")
st.caption(t["footer"])
