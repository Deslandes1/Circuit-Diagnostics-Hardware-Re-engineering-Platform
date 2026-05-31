import streamlit as st
import serial
import serial.tools.list_ports
import json
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
        "caption": "Connect a real USB probe (Arduino) OR enable Demo Mode. AI diagnoses faults + helps you build new hardware.",
        "sidebar_instructions": "**Instructions for REAL hardware**\n1. Build an Arduino probe (see code).\n2. Connect to computer via USB.\n3. Select COM port and click Connect.\n4. Probe sends JSON lines like {\"chip\":\"U3600\",\"voltage\":3.3}\n5. Run diagnostic.",
        "demo_mode_label": "🎮 Demo Mode (simulate readings)",
        "load_demo_btn": "Load Demo iPhone 8+ Readings",
        "demo_loaded_msg": "Loaded {} demo readings.",
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
        "probe_readings_title": "📊 Readings (Real or Demo)",
        "clear_readings_btn": "Clear Readings",
        "no_data": "No readings yet. Connect a real probe or load demo readings.",
        "diagnostic_btn": "🚀 Run Full Diagnostic",
        "running_diag": "Running AI diagnostics...",
        "diag_complete": "Diagnostic completed.",
        "diagnostic_report": "🩺 Diagnostic Report",
        "device_type": "Device Type (inferred)",
        "manual_device_override": "Manual Device Type Override (if auto fails)",
        "probe_data_status": "Data source",
        "probe_data_real": "✅ Real hardware ({} live measurements)",
        "probe_data_demo": "🎮 Demonstration mode ({} simulated readings)",
        "probe_data_none": "⚠️ No readings. Please load demo or connect a probe.",
        "fault_summary": "Fault Summary",
        "actions": "Actions",
        "recommended_tools": "Recommended Tools",
        "build_title": "🤖 Build New Hardware from this Board",
        "build_desc": "Ask the AI to redesign the salvageable chips into a completely new device.",
        "chat_placeholder": "Describe what you want to build (e.g., 'Make a drone flight controller')",
        "designing": "Designing your new hardware...",
        "footer": "🔧 Built with Streamlit + Groq AI + USB Serial.",
        "sidebar_company": "🌐 GlobalInternet.py",
        "sidebar_credit": "AI Multi‑Language Voice Translator",
        "sidebar_founder": "Built by **Gesner Deslandes**, Engineer-in-Chief",
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
        "caption": "Connectez une sonde USB réelle (Arduino) OU activez le mode démo. L'IA diagnostique les pannes + aide à construire un nouveau matériel.",
        "sidebar_instructions": "**Instructions pour matériel réel**\n1. Construisez une sonde Arduino.\n2. Connectez-la par USB.\n3. Sélectionnez le port COM et cliquez Connecter.\n4. La sonde envoie des lignes JSON comme {\"chip\":\"U3600\",\"voltage\":3.3}\n5. Lancez le diagnostic.",
        "demo_mode_label": "🎮 Mode Démo (simuler des lectures)",
        "load_demo_btn": "Charger les lectures démo iPhone 8+",
        "demo_loaded_msg": "{} lectures démo chargées.",
        "usb_title": "🔌 Sonde USB RÉELLE (Arduino/FTDI)",
        "select_port": "Sélectionnez le port USB",
        "connect_btn": "Connecter",
        "disconnect_btn": "Déconnecter",
        "connected_success": "Connecté à {}",
        "failed_connect": "Échec de la connexion",
        "disconnected": "Déconnecté",
        "last_reading": "Dernière lecture : {}",
        "image_upload": "📸 Téléchargement de l'image du circuit (Optionnel)",
        "upload_label": "Prenez une photo du circuit (optionnel)",
        "analyze_btn": "🔍 Analyser l'image avec l'IA",
        "analyzing": "Analyse de l'image (Groq Vision)...",
        "analysis_complete": "Analyse terminée",
        "probe_readings_title": "📊 Lectures (réelles ou démo)",
        "clear_readings_btn": "Effacer les lectures",
        "no_data": "Pas encore de lectures. Connectez une sonde réelle ou chargez les lectures démo.",
        "diagnostic_btn": "🚀 Exécuter le diagnostic complet",
        "running_diag": "Diagnostic IA en cours...",
        "diag_complete": "Diagnostic terminé.",
        "diagnostic_report": "🩺 Rapport de diagnostic",
        "device_type": "Type d'appareil (déduit)",
        "manual_device_override": "Remplacement manuel du type d'appareil",
        "probe_data_status": "Source des données",
        "probe_data_real": "✅ Matériel réel ({} mesures en direct)",
        "probe_data_demo": "🎮 Mode démonstration ({} lectures simulées)",
        "probe_data_none": "⚠️ Aucune lecture. Chargez une démo ou connectez une sonde.",
        "fault_summary": "Résumé des pannes",
        "actions": "Actions",
        "recommended_tools": "Outils recommandés",
        "build_title": "🤖 Construire un nouveau matériel à partir de cette carte",
        "build_desc": "Demandez à l'IA de reconcevoir les puces récupérables en un tout nouvel appareil.",
        "chat_placeholder": "Décrivez ce que vous voulez construire (ex: 'Fabrique un contrôleur de drone')",
        "designing": "Conception du nouveau matériel...",
        "footer": "🔧 Construit avec Streamlit + Groq AI + USB Serial.",
        "sidebar_company": "🌐 GlobalInternet.py",
        "sidebar_credit": "Traduction vocale IA multi‑langues",
        "sidebar_founder": "Construit par **Gesner Deslandes**, Ingénieur en chef",
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
        "caption": "Conecte una sonda USB real (Arduino) O active el modo demo. La IA diagnostica fallos + ayuda a construir nuevo hardware.",
        "sidebar_instructions": "**Instrucciones para hardware real**\n1. Construya una sonda Arduino.\n2. Conéctela por USB.\n3. Seleccione el puerto COM y haga clic en Conectar.\n4. La sonda envía líneas JSON como {\"chip\":\"U3600\",\"voltage\":3.3}\n5. Ejecute el diagnóstico.",
        "demo_mode_label": "🎮 Modo Demo (simular lecturas)",
        "load_demo_btn": "Cargar lecturas demo iPhone 8+",
        "demo_loaded_msg": "{} lecturas demo cargadas.",
        "usb_title": "🔌 Sonda USB REAL (Arduino/FTDI)",
        "select_port": "Seleccione el puerto USB",
        "connect_btn": "Conectar",
        "disconnect_btn": "Desconectar",
        "connected_success": "Conectado a {}",
        "failed_connect": "Error de conexión",
        "disconnected": "Desconectado",
        "last_reading": "Última lectura: {}",
        "image_upload": "📸 Subir imagen del circuito (Opcional)",
        "upload_label": "Tome una foto del circuito (opcional)",
        "analyze_btn": "🔍 Analizar imagen con IA",
        "analyzing": "Analizando imagen (Groq Vision)...",
        "analysis_complete": "Análisis completo",
        "probe_readings_title": "📊 Lecturas (reales o demo)",
        "clear_readings_btn": "Borrar lecturas",
        "no_data": "Aún no hay lecturas. Conecte una sonda real o cargue lecturas demo.",
        "diagnostic_btn": "🚀 Ejecutar diagnóstico completo",
        "running_diag": "Diagnóstico IA en curso...",
        "diag_complete": "Diagnóstico completado.",
        "diagnostic_report": "🩺 Informe de diagnóstico",
        "device_type": "Tipo de dispositivo (inferido)",
        "manual_device_override": "Anulación manual del tipo de dispositivo",
        "probe_data_status": "Fuente de datos",
        "probe_data_real": "✅ Hardware real ({} mediciones en directo)",
        "probe_data_demo": "🎮 Modo demostración ({} lecturas simuladas)",
        "probe_data_none": "⚠️ Sin lecturas. Cargue una demo o conecte una sonda.",
        "fault_summary": "Resumen de fallos",
        "actions": "Acciones",
        "recommended_tools": "Herramientas recomendadas",
        "build_title": "🤖 Construir nuevo hardware desde esta placa",
        "build_desc": "Pida a la IA que rediseñe los chips recuperables en un dispositivo completamente nuevo.",
        "chat_placeholder": "Describa lo que quiere construir (ej: 'Haz un controlador de dron')",
        "designing": "Diseñando su nuevo hardware...",
        "footer": "🔧 Construido con Streamlit + Groq AI + USB Serial.",
        "sidebar_company": "🌐 GlobalInternet.py",
        "sidebar_credit": "Traducción de voz por IA multilingüe",
        "sidebar_founder": "Construido por **Gesner Deslandes**, Ingeniero Jefe",
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
        "caption": "Konekte yon sond USB reyèl (Arduino) OSWA aktive Mod Demo. AI fè dyagnostik + ede w konstwi nouvo aparèy.",
        "sidebar_instructions": "**Enstriksyon pou materyèl reyèl**\n1. Konstwi yon sond Arduino.\n2. Konekte li nan òdinatè w atravè USB.\n3. Chwazi pò COM epi klike Konekte.\n4. Sond la voye liy JSON tankou {\"chip\":\"U3600\",\"voltage\":3.3}\n5. Kouri dyagnostik la.",
        "demo_mode_label": "🎮 Mod Demo (simile lekti)",
        "load_demo_btn": "Chaje lekti demo iPhone 8+",
        "demo_loaded_msg": "{} lekti demo chaje.",
        "usb_title": "🔌 Sond USB RÉYÈL (Arduino/FTDI)",
        "select_port": "Chwazi pò USB",
        "connect_btn": "Konekte",
        "disconnect_btn": "Dekonekte",
        "connected_success": "Konekte nan {}",
        "failed_connect": "Echèk koneksyon",
        "disconnected": "Dekonekte",
        "last_reading": "Dènye lekti: {}",
        "image_upload": "📸 Chaje imaj sikwi a (Opsyonèl)",
        "upload_label": "Pran yon foto sikwi a (si ou vle)",
        "analyze_btn": "🔍 Analize imaj ak AI",
        "analyzing": "Analiz imaj (Groq Vision)...",
        "analysis_complete": "Analiz fini",
        "probe_readings_title": "📊 Lekti (reyèl oswa demo)",
        "clear_readings_btn": "Efase lekti yo",
        "no_data": "Pa gen lekti ankò. Konekte yon sond reyèl oswa chaje lekti demo.",
        "diagnostic_btn": "🚀 Kouri dyagnostik konplè",
        "running_diag": "Dyagnostik AI ap kouri...",
        "diag_complete": "Dyagnostik fini.",
        "diagnostic_report": "🩺 Rapò dyagnostik",
        "device_type": "Kalite aparèy (dedui)",
        "manual_device_override": "Ranplasman maniyèl kalite aparèy",
        "probe_data_status": "Sous done",
        "probe_data_real": "✅ Materyèl reyèl ({} mezi an dirèk)",
        "probe_data_demo": "🎮 Mod demonstrasyon ({} lekti simule)",
        "probe_data_none": "⚠️ Pa gen lekti. Chaje yon demo oswa konekte yon sond.",
        "fault_summary": "Rezime pwoblèm",
        "actions": "Aksyon",
        "recommended_tools": "Zouti rekòmande",
        "build_title": "🤖 Konstwi nouvo materyèl apati plak sa a",
        "build_desc": "Mande AI a pou l repwenti chips yo nan yon nouvo aparèy.",
        "chat_placeholder": "Dekri sa w vle konstwi (egzanp: 'Fè yon kontwolè drone')",
        "designing": "Ap desine nouvo materyèl w la...",
        "footer": "🔧 Konstwi ak Streamlit + Groq AI + USB Serial.",
        "sidebar_company": "🌐 GlobalInternet.py",
        "sidebar_credit": "Tradiksyon vwa AI miltilang",
        "sidebar_founder": "Bati pa **Gesner Deslandes**, Enjenyè anchèf",
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
            return json.loads(line)
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
        return {"error": str(e), "chips": []}

# ================== Device Identification ==================
def identify_device(image_analysis, readings, manual_override):
    if manual_override and manual_override != "Auto-detect":
        return manual_override
    chip_labels = [r.get("chip", "").upper().strip() for r in readings if "chip" in r]
    all_labels = " ".join(chip_labels)
    iphone_chips = ["U3600", "U3301", "U3100", "U5600", "U4701", "U6100"]
    if any(chip in all_labels for chip in iphone_chips):
        return "iPhone 8+ (or similar Apple smartphone)"
    # Add Samsung tablet detection based on typical chip labels (optional)
    samsung_chips = ["S2", "S3", "MAX776", "S6", "S7"]
    if any(chip in all_labels for chip in samsung_chips):
        return "Samsung Tablet (Galaxy Tab series)"
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
Readings: {json.dumps(probe_readings, indent=2)}
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
The user has a broken board with this data: {json.dumps(context, indent=2)}
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
    "U3600": {"type": "PMIC (Power Management)", "expected": {"VBATT": 3.8, "VDD_MAIN": 3.8}},
    "U3301": {"type": "NAND Flash", "expected": {"VDD_NAND": 1.8}},
    "U3100": {"type": "A11 Bionic CPU", "expected": {"VCC_MAIN": 3.8}},
    "U5600": {"type": "USB/Charging IC", "expected": {"V_BUS": 5.0, "VBATT": 3.8}},
    "U1": {"type": "Voltage Regulator", "expected": {"out": 5.0}},
}

# ================== Demo Readings ==================
DEMO_READINGS = [
    {"chip": "U3600", "voltage": 3.8, "expected": 3.8},
    {"chip": "U3301", "voltage": 0.0, "expected": 1.8},
    {"chip": "U3100", "voltage": 0.5, "expected": 3.8},
    {"chip": "U5600", "voltage": 5.0, "expected": 5.0},
]

# ================== Session State ==================
if "probe_serial" not in st.session_state:
    st.session_state.probe_serial = None
if "probe_connected" not in st.session_state:
    st.session_state.probe_connected = False
if "image_analysis" not in st.session_state:
    st.session_state.image_analysis = None
if "readings" not in st.session_state:
    st.session_state.readings = []
if "diagnosis_result" not in st.session_state:
    st.session_state.diagnosis_result = None
if "device_type" not in st.session_state:
    st.session_state.device_type = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "lang" not in st.session_state:
    st.session_state.lang = "English"
if "manual_device_override" not in st.session_state:
    st.session_state.manual_device_override = "Auto-detect"
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False

# ================== Sidebar ==================
st.sidebar.markdown(f"## {LANGUAGES[st.session_state.lang]['sidebar_company']}")
st.sidebar.markdown(f"### {LANGUAGES[st.session_state.lang]['sidebar_credit']}")
st.sidebar.markdown(LANGUAGES[st.session_state.lang]['sidebar_founder'])
st.sidebar.markdown("---")

# Language selector
lang_options = list(LANGUAGES.keys())
selected_lang = st.sidebar.selectbox("🌐 Language / Langue / Idioma", lang_options, index=lang_options.index(st.session_state.lang))
if selected_lang != st.session_state.lang:
    st.session_state.lang = selected_lang
    st.rerun()
t = LANGUAGES[st.session_state.lang]

st.sidebar.markdown("---")

# Demo Mode Toggle
demo_toggle = st.sidebar.checkbox(t["demo_mode_label"], value=st.session_state.demo_mode)
if demo_toggle != st.session_state.demo_mode:
    st.session_state.demo_mode = demo_toggle
    if st.session_state.demo_mode:
        # Clear real probe connection if any
        if st.session_state.probe_serial:
            st.session_state.probe_serial.close()
        st.session_state.probe_connected = False
        st.session_state.probe_serial = None
    st.rerun()

if not st.session_state.demo_mode:
    # Real hardware mode
    st.sidebar.title(t["usb_title"])
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
else:
    # Demo mode
    st.sidebar.info("🎮 **Demo Mode Active** – No hardware needed.")
    if st.sidebar.button(t["load_demo_btn"]):
        st.session_state.readings = DEMO_READINGS.copy()
        st.sidebar.success(t["demo_loaded_msg"].format(len(DEMO_READINGS)))
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.info(t["sidebar_instructions"])

# Manual device override (applies in both modes)
device_options = ["Auto-detect", "iPhone 8+", "iPhone X", "Samsung Tablet", "Samsung Galaxy", "Laptop", "Desktop"]
st.sidebar.selectbox(t["manual_device_override"], device_options, key="manual_device_override")

st.sidebar.markdown("---")
st.sidebar.subheader(t["sidebar_contact"])
st.sidebar.write(t["phone"])
st.sidebar.write(t["email"])
st.sidebar.markdown(f"[{t['website']}]({t['website_link']})")
st.sidebar.markdown("---")

# ================== Main Layout ==================
st.markdown(f"<h1 class='main-header'>{t['app_title']}</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='credit'>{t['credit']}</p>", unsafe_allow_html=True)
st.caption(t["caption"])

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
        st.info(t["no_data"])

# Diagnostic Button
if st.button(t["diagnostic_btn"]):
    if not st.session_state.readings:
        st.warning("Please add readings (load demo or connect a real probe).")
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
                target_language=t["lang_code"]
            )
            st.session_state.diagnosis_result = result
            st.success(t["diag_complete"])

if st.session_state.diagnosis_result:
    st.subheader(t["diagnostic_report"])
    res = st.session_state.diagnosis_result
    st.write(f"**{t['device_type']}:** {st.session_state.device_type}")
    st.write(f"**{t['probe_data_status']}:**")
    if st.session_state.demo_mode:
        st.info(t["probe_data_demo"].format(len(st.session_state.readings)))
    elif st.session_state.probe_connected and st.session_state.readings:
        st.success(t["probe_data_real"].format(len(st.session_state.readings)))
    else:
        st.warning(t["probe_data_none"])
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
        "readings": st.session_state.readings[-10:],
        "diagnosis": st.session_state.diagnosis_result,
        "device_type": st.session_state.device_type
    }
    with st.chat_message("assistant"):
        with st.spinner(t["designing"]):
            answer = redesign_question(prompt, context, t["lang_code"])
            st.markdown(answer)
    st.session_state.chat_history.append({"role": "assistant", "content": answer})

st.markdown("---")
st.caption(t["footer"])
