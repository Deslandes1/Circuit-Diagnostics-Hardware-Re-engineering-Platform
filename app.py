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
</style>
""", unsafe_allow_html=True)

# ================== Translation Dictionary ==================
LANGUAGES = {
    "English": {
        "app_title": "⚡ Circuit Diagnostics & Hardware Re‑engineering",
        "credit": "built by Gesner Deslandes",
        "caption": "Upload a photo of a broken circuit board, connect USB probe, and let AI diagnose faults + help you build new hardware from the salvageable chips.",
        "sidebar_instructions": "**Instructions**\n1. Connect USB probe to your laptop.\n2. Upload a photo of the waste circuit.\n3. Run diagnostic.\n4. Ask the AI to redesign a new hardware from the broken board.",
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
        "no_data": "No data yet. Connect USB probe and ensure the hardware is sending JSON lines.",
        "diagnostic_btn": "🚀 Run Full Diagnostic (Image + Probe)",
        "upload_first": "Please upload an image first.",
        "running_diag": "Running AI diagnostics...",
        "diag_complete": "Diagnostic completed.",
        "diagnostic_report": "🩺 Diagnostic Report",
        "device_type": "Device Type",
        "fault_summary": "Fault Summary",
        "actions": "Actions",
        "recommended_tools": "Recommended Tools",
        "build_title": "🤖 Build New Hardware from this Board",
        "build_desc": "Ask the AI to redesign the salvageable chips into a completely new device (e.g., a custom drone controller, USB peripheral, etc.).",
        "chat_placeholder": "Describe what you want to build (e.g., 'Make a drone flight controller using the existing microcontroller and MOSFETs')",
        "designing": "Designing your new hardware...",
        "footer": "🔧 Built with Streamlit + Groq AI + USB Serial. For full hardware integration, connect a probe that sends JSON diagnostics over USB.",
        "sidebar_contact": "📞 Contact",
        "phone": "📱 (509)-47385663",
        "email": "✉️ deslandes78@gmail.com",
        "website": "🌐 GlobalInternet.py",
        "website_link": "https://globalinternetsitepy-abh7v6tnmskxxnuplrdcgk.streamlit.app/",
        "lang_code": "English"
    },
    "French": {
        "app_title": "⚡ Diagnostic de Circuits & Réingénierie Matérielle",
        "credit": "conçu par Gesner Deslandes",
        "caption": "Téléchargez une photo d'une carte électronique défectueuse, connectez la sonde USB, et laissez l'IA diagnostiquer les pannes + vous aider à construire un nouveau matériel à partir des puces récupérables.",
        "sidebar_instructions": "**Instructions**\n1. Connectez la sonde USB à votre ordinateur.\n2. Téléchargez une photo du circuit défectueux.\n3. Lancez le diagnostic.\n4. Demandez à l'IA de reconcevoir un nouveau matériel à partir de la carte cassée.",
        "usb_title": "🔌 Sonde USB",
        "select_port": "Sélectionnez le port USB",
        "connect_btn": "Connecter",
        "disconnect_btn": "Déconnecter",
        "connected_success": "Connecté à {}",
        "failed_connect": "Échec de la connexion",
        "disconnected": "Déconnecté",
        "last_reading": "Dernière lecture : {}",
        "image_upload": "📸 Téléchargement de l'image du circuit",
        "upload_label": "Prenez une photo du circuit défectueux",
        "analyze_btn": "🔍 Analyser l'image avec l'IA",
        "analyzing": "Analyse de l'image (Groq Vision)...",
        "analysis_complete": "Analyse terminée",
        "probe_readings_title": "📊 Lectures de la sonde (USB)",
        "clear_readings_btn": "Effacer les lectures",
        "no_data": "Pas encore de données. Connectez la sonde USB et assurez-vous qu'elle envoie des lignes JSON.",
        "diagnostic_btn": "🚀 Exécuter le diagnostic complet (Image + Sonde)",
        "upload_first": "Veuillez d'abord télécharger une image.",
        "running_diag": "Diagnostic IA en cours...",
        "diag_complete": "Diagnostic terminé.",
        "diagnostic_report": "🩺 Rapport de diagnostic",
        "device_type": "Type d'appareil",
        "fault_summary": "Résumé des pannes",
        "actions": "Actions",
        "recommended_tools": "Outils recommandés",
        "build_title": "🤖 Construire un nouveau matériel à partir de cette carte",
        "build_desc": "Demandez à l'IA de reconcevoir les puces récupérables en un tout nouvel appareil (ex: contrôleur de drone, périphérique USB, etc.).",
        "chat_placeholder": "Décrivez ce que vous voulez construire (ex: 'Fabrique un contrôleur de drone avec le microcontrôleur et les MOSFET existants')",
        "designing": "Conception du nouveau matériel...",
        "footer": "🔧 Construit avec Streamlit + Groq AI + USB Serial. Pour une intégration matérielle complète, connectez une sonde qui envoie des diagnostics JSON sur USB.",
        "sidebar_contact": "📞 Contact",
        "phone": "📱 (509)-47385663",
        "email": "✉️ deslandes78@gmail.com",
        "website": "🌐 GlobalInternet.py",
        "website_link": "https://globalinternetsitepy-abh7v6tnmskxxnuplrdcgk.streamlit.app/",
        "lang_code": "French"
    },
    "Spanish": {
        "app_title": "⚡ Diagnóstico de Circuitos & Reingeniería de Hardware",
        "credit": "construido por Gesner Deslandes",
        "caption": "Sube una foto de una placa de circuito rota, conecta la sonda USB y deja que la IA diagnostique fallos + te ayude a construir un nuevo hardware a partir de los chips recuperables.",
        "sidebar_instructions": "**Instrucciones**\n1. Conecte la sonda USB a su computadora.\n2. Suba una foto del circuito defectuoso.\n3. Ejecute el diagnóstico.\n4. Pida a la IA que rediseñe un nuevo hardware a partir de la placa rota.",
        "usb_title": "🔌 Sonda USB",
        "select_port": "Seleccione el puerto USB",
        "connect_btn": "Conectar",
        "disconnect_btn": "Desconectar",
        "connected_success": "Conectado a {}",
        "failed_connect": "Error de conexión",
        "disconnected": "Desconectado",
        "last_reading": "Última lectura: {}",
        "image_upload": "📸 Subir imagen del circuito",
        "upload_label": "Tome una foto del circuito defectuoso",
        "analyze_btn": "🔍 Analizar imagen con IA",
        "analyzing": "Analizando imagen (Groq Vision)...",
        "analysis_complete": "Análisis completo",
        "probe_readings_title": "📊 Lecturas de la sonda (USB)",
        "clear_readings_btn": "Borrar lecturas",
        "no_data": "Aún no hay datos. Conecte la sonda USB y asegúrese de que envíe líneas JSON.",
        "diagnostic_btn": "🚀 Ejecutar diagnóstico completo (Imagen + Sonda)",
        "upload_first": "Primero suba una imagen.",
        "running_diag": "Ejecutando diagnóstico IA...",
        "diag_complete": "Diagnóstico completado.",
        "diagnostic_report": "🩺 Informe de diagnóstico",
        "device_type": "Tipo de dispositivo",
        "fault_summary": "Resumen de fallos",
        "actions": "Acciones",
        "recommended_tools": "Herramientas recomendadas",
        "build_title": "🤖 Construir nuevo hardware desde esta placa",
        "build_desc": "Pida a la IA que rediseñe los chips recuperables en un dispositivo completamente nuevo (ej: controlador de dron, periférico USB, etc.).",
        "chat_placeholder": "Describa lo que quiere construir (ej: 'Haz un controlador de dron con el microcontrolador y los MOSFET existentes')",
        "designing": "Diseñando su nuevo hardware...",
        "footer": "🔧 Construido con Streamlit + Groq AI + USB Serial. Para integración completa de hardware, conecte una sonda que envíe diagnósticos JSON por USB.",
        "sidebar_contact": "📞 Contacto",
        "phone": "📱 (509)-47385663",
        "email": "✉️ deslandes78@gmail.com",
        "website": "🌐 GlobalInternet.py",
        "website_link": "https://globalinternetsitepy-abh7v6tnmskxxnuplrdcgk.streamlit.app/",
        "lang_code": "Spanish"
    },
    "Haitian Creole": {
        "app_title": "⚡ Dyagnostik Sikwi & Re-enjenyèri Materyèl",
        "credit": "bati pa Gesner Deslandes",
        "caption": "Chaje yon foto yon sikwi ki kraze, konekte sond USB a, epi kite AI a fè dyagnostik epi ede w konstwi yon nouvo aparèy ak chips ki kapab itilize yo.",
        "sidebar_instructions": "**Enstriksyon**\n1. Konekte sond USB a nan òdinatè w.\n2. Chaje yon foto sikwi a.\n3. Kouri dyagnostik la.\n4. Mande AI a pou l repwenti yon nouvo aparèy apati sikwi a.",
        "usb_title": "🔌 Sond USB",
        "select_port": "Chwazi pò USB",
        "connect_btn": "Konekte",
        "disconnect_btn": "Dekonekte",
        "connected_success": "Konekte nan {}",
        "failed_connect": "Echèk koneksyon",
        "disconnected": "Dekonekte",
        "last_reading": "Dènye lekti: {}",
        "image_upload": "📸 Chaje imaj sikwi a",
        "upload_label": "Pran yon foto sikwi a",
        "analyze_btn": "🔍 Analize imaj ak AI",
        "analyzing": "Analiz imaj (Groq Vision)...",
        "analysis_complete": "Analiz fini",
        "probe_readings_title": "📊 Lekti sond (USB)",
        "clear_readings_btn": "Efase lekti yo",
        "no_data": "Pa gen done ankò. Konekte sond USB a epi asire w li voye liy JSON.",
        "diagnostic_btn": "🚀 Kouri dyagnostik konplè (Imaj + Sond)",
        "upload_first": "Tanpri chaje yon foto anvan.",
        "running_diag": "Dyagnostik AI ap kouri...",
        "diag_complete": "Dyagnostik fini.",
        "diagnostic_report": "🩺 Rapò dyagnostik",
        "device_type": "Kalite aparèy",
        "fault_summary": "Rezime pwoblèm",
        "actions": "Aksyon",
        "recommended_tools": "Zouti rekòmande",
        "build_title": "🤖 Konstwi nouvo materyèl apati plak sa a",
        "build_desc": "Mande AI a pou l repwenti chips yo nan yon nouvo aparèy (egzanp: kontwolè drone, periferik USB, elatriye).",
        "chat_placeholder": "Dekri sa w vle konstwi (egzanp: 'Fè yon kontwolè drone ak mikrokontwolè ak MOSFET ki la yo')",
        "designing": "Ap desine nouvo materyèl w la...",
        "footer": "🔧 Konstwi ak Streamlit + Groq AI + USB Serial. Pou entegrasyon materyèl konplè, konekte yon sond ki voye dyagnostik JSON sou USB.",
        "sidebar_contact": "📞 Kontak",
        "phone": "📱 (509)-47385663",
        "email": "✉️ deslandes78@gmail.com",
        "website": "🌐 GlobalInternet.py",
        "website_link": "https://globalinternetsitepy-abh7v6tnmskxxnuplrdcgk.streamlit.app/",
        "lang_code": "Haitian Creole"
    }
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
    return [port.device for port in ports]

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
1. List all major ICs/chips you can identify (by package, label, or position).
2. For each, note any visible damage (burn marks, cracks, corrosion).
3. Suggest the most likely failed component(s) and why.
4. Provide a step-by-step diagnostic plan.
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
Based on the following circuit board image analysis, identify what type of device this board comes from (e.g., laptop, desktop computer, tablet, smartphone, gaming console, etc.). Also include the brand or model if you can infer.

Image analysis: {json.dumps(image_analysis, indent=2)}

Return a JSON with keys:
- "device_type": short description (e.g., "Laptop motherboard - Dell Inspiron")
- "confidence": high/medium/low
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
    language_instruction = f"Output the entire JSON in {target_language}. "
    prompt = f"""
You are a hardware diagnostic engineer. Based on the following information, identify which chips are malfunctioning, what is wrong, and what should be done (remove, repair, replace, or rework).

{language_instruction}
Device Type: {device_type}
Image Analysis: {json.dumps(image_analysis, indent=2)}
Probe Readings (USB): {json.dumps(probe_readings, indent=2)}
Chip Database (known good values): {json.dumps(chip_data, indent=2)}

Provide output as JSON with keys:
- "fault_summary": brief description in {target_language}
- "actions": list of dicts with keys "chip", "fault", "action" (remove/repair/replace), "reason" (all strings in {target_language})
- "recommended_tools": list of tool names in {target_language}
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
selected_port = st.sidebar.selectbox(t["select_port"], ports) if ports else None
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
        st.session_state.probe_readings.append(data)
        st.sidebar.write(t["last_reading"].format(data))

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
