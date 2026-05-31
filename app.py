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

# ================== Translation Dictionary (full, same as before) ==================
LANGUAGES = {
    "English": {
        "app_title": "⚡ Circuit Diagnostics & Hardware Re‑engineering",
        "credit": "built by Gesner Deslandes",
        "caption": "Upload a photo (optional) of a broken circuit board, connect USB probe or enter manual readings. AI will diagnose faults + help you build new hardware.",
        "sidebar_instructions": "**Instructions**\n1. (Optional) Upload a circuit photo for visual damage detection.\n2. Connect a USB probe (Arduino/FTDI) that sends JSON over Serial, OR enter manual readings below.\n3. Run diagnostic.\n4. Ask AI to redesign new hardware.",
        "usb_title": "🔌 USB Probe",
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
        "probe_readings_title": "📊 Probe / Manual Readings",
        "clear_readings_btn": "Clear Readings",
        "no_data": "No readings yet. Add manual readings below or connect a USB probe.",
        "diagnostic_btn": "🚀 Run Full Diagnostic",
        "upload_first": "Please upload an image OR add some manual readings first.",
        "running_diag": "Running AI diagnostics...",
        "diag_complete": "Diagnostic completed.",
        "diagnostic_report": "🩺 Diagnostic Report",
        "device_type": "Inferred Device Type",
        "probe_data_status": "Real probe data used",
        "probe_data_yes": "✅ Yes – {} measurements were received.",
        "probe_data_no": "⚠️ No real probe data. Using manual entries only.",
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
        "manual_add": "✏️ Manual Probe Data Entry (no hardware)",
        "manual_chip": "Chip name (e.g., U3600)",
        "manual_voltage": "Voltage (V)",
        "manual_expected": "Expected voltage (V)",
        "manual_add_btn": "Add Reading",
        "lang_code": "English"
    },
    "French": {
        "app_title": "⚡ Diagnostic de Circuits & Réingénierie Matérielle",
        "credit": "conçu par Gesner Deslandes",
        "caption": "Téléchargez une photo (facultative) d'une carte électronique, connectez une sonde USB ou entrez des lectures manuelles. L'IA diagnostiquera les pannes + vous aidera à construire un nouveau matériel.",
        "sidebar_instructions": "**Instructions**\n1. (Optionnel) Téléchargez une photo pour la détection des dommages visuels.\n2. Connectez une sonde USB (Arduino/FTDI) qui envoie du JSON, OU entrez des lectures manuelles ci-dessous.\n3. Lancez le diagnostic.\n4. Demandez à l'IA de reconcevoir un nouveau matériel.",
        "usb_title": "🔌 Sonde USB",
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
        "probe_readings_title": "📊 Lectures (sonde / manuelles)",
        "clear_readings_btn": "Effacer les lectures",
        "no_data": "Pas encore de lectures. Ajoutez des lectures manuelles ou connectez une sonde USB.",
        "diagnostic_btn": "🚀 Exécuter le diagnostic complet",
        "upload_first": "Veuillez télécharger une image ou ajouter des lectures manuelles.",
        "running_diag": "Diagnostic IA en cours...",
        "diag_complete": "Diagnostic terminé.",
        "diagnostic_report": "🩺 Rapport de diagnostic",
        "device_type": "Type d'appareil déduit",
        "probe_data_status": "Mesures réelles de la sonde utilisées",
        "probe_data_yes": "✅ Oui – {} mesures ont été reçues.",
        "probe_data_no": "⚠️ Aucune donnée réelle. Utilisation des entrées manuelles uniquement.",
        "fault_summary": "Résumé des pannes",
        "actions": "Actions",
        "recommended_tools": "Outils recommandés",
        "build_title": "🤖 Construire un nouveau matériel à partir de cette carte",
        "build_desc": "Demandez à l'IA de reconcevoir les puces récupérables en un tout nouvel appareil.",
        "chat_placeholder": "Décrivez ce que vous voulez construire (ex: 'Fabrique un contrôleur de drone')",
        "designing": "Conception du nouveau matériel...",
        "footer": "🔧 Construit avec Streamlit + Groq AI + USB Serial.",
        "sidebar_contact": "📞 Contact",
        "phone": "📱 (509)-47385663",
        "email": "✉️ deslandes78@gmail.com",
        "website": "🌐 GlobalInternet.py",
        "website_link": "https://globalinternetsitepy-abh7v6tnmskxxnuplrdcgk.streamlit.app/",
        "manual_add": "✏️ Saisie manuelle des données (sans matériel)",
        "manual_chip": "Nom de la puce (ex: U3600)",
        "manual_voltage": "Tension (V)",
        "manual_expected": "Tension attendue (V)",
        "manual_add_btn": "Ajouter une lecture",
        "lang_code": "French"
    },
    "Spanish": {
        "app_title": "⚡ Diagnóstico de Circuitos & Reingeniería de Hardware",
        "credit": "construido por Gesner Deslandes",
        "caption": "Sube una foto (opcional) de una placa rota, conecta una sonda USB o ingresa lecturas manuales. La IA diagnosticará fallos + te ayudará a construir nuevo hardware.",
        "sidebar_instructions": "**Instrucciones**\n1. (Opcional) Sube una foto para detección visual de daños.\n2. Conecta una sonda USB (Arduino/FTDI) que envíe JSON, O ingresa lecturas manuales abajo.\n3. Ejecuta el diagnóstico.\n4. Pide a la IA que rediseñe un nuevo hardware.",
        "usb_title": "🔌 Sonda USB",
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
        "probe_readings_title": "📊 Lecturas (sonda / manuales)",
        "clear_readings_btn": "Borrar lecturas",
        "no_data": "Aún no hay lecturas. Agregue lecturas manuales o conecte una sonda USB.",
        "diagnostic_btn": "🚀 Ejecutar diagnóstico completo",
        "upload_first": "Suba una imagen o agregue lecturas manuales primero.",
        "running_diag": "Ejecutando diagnóstico IA...",
        "diag_complete": "Diagnóstico completado.",
        "diagnostic_report": "🩺 Informe de diagnóstico",
        "device_type": "Tipo de dispositivo inferido",
        "probe_data_status": "Mediciones reales de la sonda utilizadas",
        "probe_data_yes": "✅ Sí – se recibieron {} mediciones.",
        "probe_data_no": "⚠️ No se recibieron datos reales. Usando solo entradas manuales.",
        "fault_summary": "Resumen de fallos",
        "actions": "Acciones",
        "recommended_tools": "Herramientas recomendadas",
        "build_title": "🤖 Construir nuevo hardware desde esta placa",
        "build_desc": "Pida a la IA que rediseñe los chips recuperables en un dispositivo completamente nuevo.",
        "chat_placeholder": "Describa lo que quiere construir (ej: 'Haz un controlador de dron')",
        "designing": "Diseñando su nuevo hardware...",
        "footer": "🔧 Construido con Streamlit + Groq AI + USB Serial.",
        "sidebar_contact": "📞 Contacto",
        "phone": "📱 (509)-47385663",
        "email": "✉️ deslandes78@gmail.com",
        "website": "🌐 GlobalInternet.py",
        "website_link": "https://globalinternetsitepy-abh7v6tnmskxxnuplrdcgk.streamlit.app/",
        "manual_add": "✏️ Ingreso manual de datos (sin hardware)",
        "manual_chip": "Nombre del chip (ej: U3600)",
        "manual_voltage": "Voltaje (V)",
        "manual_expected": "Voltaje esperado (V)",
        "manual_add_btn": "Agregar lectura",
        "lang_code": "Spanish"
    },
    "Haitian Creole": {
        "app_title": "⚡ Dyagnostik Sikwi & Re-enjenyèri Materyèl",
        "credit": "bati pa Gesner Deslandes",
        "caption": "Chaje yon foto (si ou vle) yon sikwi ki kraze, konekte sond USB oswa antre lekti manyèl. AI ap fè dyagnostik + ede w konstwi nouvo aparèy.",
        "sidebar_instructions": "**Enstriksyon**\n1. (Opsyonèl) Chaje yon foto pou deteksyon domaj vizyèl.\n2. Konekte yon sond USB ki voye JSON, OSWA antre lekti manyèl anba a.\n3. Kouri dyagnostik la.\n4. Mande AI a pou l repwenti yon nouvo aparèy.",
        "usb_title": "🔌 Sond USB",
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
        "probe_readings_title": "📊 Lekti (sond / manyèl)",
        "clear_readings_btn": "Efase lekti yo",
        "no_data": "Pa gen lekti ankò. Ajoute lekti manyèl oswa konekte yon sond USB.",
        "diagnostic_btn": "🚀 Kouri dyagnostik konplè",
        "upload_first": "Tanpri chaje yon foto oswa ajoute lekti manyèl anvan.",
        "running_diag": "Dyagnostik AI ap kouri...",
        "diag_complete": "Dyagnostik fini.",
        "diagnostic_report": "🩺 Rapò dyagnostik",
        "device_type": "Kalite aparèy dedui",
        "probe_data_status": "Mezi reyèl sond yo itilize",
        "probe_data_yes": "✅ Wi – {} mezi yo te resevwa.",
        "probe_data_no": "⚠️ Pa gen done reyèl. Sèlman lekti manyèl.",
        "fault_summary": "Rezime pwoblèm",
        "actions": "Aksyon",
        "recommended_tools": "Zouti rekòmande",
        "build_title": "🤖 Konstwi nouvo materyèl apati plak sa a",
        "build_desc": "Mande AI a pou l repwenti chips yo nan yon nouvo aparèy.",
        "chat_placeholder": "Dekri sa w vle konstwi (egzanp: 'Fè yon kontwolè drone')",
        "designing": "Ap desine nouvo materyèl w la...",
        "footer": "🔧 Konstwi ak Streamlit + Groq AI + USB Serial.",
        "sidebar_contact": "📞 Kontak",
        "phone": "📱 (509)-47385663",
        "email": "✉️ deslandes78@gmail.com",
        "website": "🌐 GlobalInternet.py",
        "website_link": "https://globalinternetsitepy-abh7v6tnmskxxnuplrdcgk.streamlit.app/",
        "manual_add": "✏️ Antre Manyèl Done (san materyèl)",
        "manual_chip": "Non chip (egzanp: U3600)",
        "manual_voltage": "Vòltaj (V)",
        "manual_expected": "Vòltaj espere (V)",
        "manual_add_btn": "Ajoute lekti",
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

# ================== Image Analysis (Optional) ==================
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

# ================== Device Identification (Optional) ==================
def identify_device(image_analysis, readings, target_language):
    # If image analysis exists, use it. Otherwise, guess from chip labels.
    if image_analysis and not image_analysis.get("error"):
        language_instruction = f"Answer in {target_language}."
        prompt = f"""{language_instruction}
Based on this image analysis, identify the device type (laptop, desktop, tablet, smartphone, etc.) and brand if possible.
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
            pass
    # If no image, infer from chip labels in readings
    chip_labels = [r.get("chip", "") for r in readings if "chip" in r]
    all_labels = " ".join(chip_labels).upper()
    if any(x in all_labels for x in ["U3600", "U3301", "U3100", "U5600"]):
        return "iPhone 8+ (or similar Apple smartphone)"
    elif any(x in all_labels for x in ["U1", "U2", "U3"]):
        return "Generic circuit board (unknown device)"
    else:
        return "Unknown device (no image, cannot determine)"

# ================== Diagnostic Reasoning ==================
def diagnose_faults(chip_data, probe_readings, image_analysis, device_type, target_language):
    language_instruction = f"Output JSON in {target_language}."
    # Use image analysis if available, else empty dict
    img_info = image_analysis if image_analysis and not image_analysis.get("error") else {"chips": [], "visible_damage": [], "likely_failed_components": []}
    prompt = f"""{language_instruction}
Device Type: {device_type}
Probe/Manual Readings: {json.dumps(probe_readings, indent=2)}
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
The user has a broken board with this information: {json.dumps(context, indent=2)}
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

# ================== Mock Chip Database ==================
DEFAULT_CHIP_DB = {
    "U3600": {"type": "PMIC (Power Management)", "pins": {"VBATT": "3.8V", "VDD_MAIN": "3.8V"}, "common_faults": ["overheating", "short"]},
    "U3301": {"type": "NAND Flash", "pins": {"VDD_NAND": "1.8V"}, "common_faults": ["dead", "no power"]},
    "U3100": {"type": "A11 Bionic CPU", "pins": {"VCC_MAIN": "3.8V"}, "common_faults": ["shorted capacitor", "dead CPU"]},
    "U5600": {"type": "USB/Charging IC", "pins": {"V_BUS": "5V", "VBATT": "3.8V"}, "common_faults": ["overvoltage", "no charging"]},
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
    st.session_state.image_analysis = None
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
    st.sidebar.warning("No USB ports detected. Plug in a real Arduino/FTDI device and refresh, or use manual entry below.")

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
        st.sidebar.success("✅ Receiving data!")
    else:
        st.sidebar.warning("⏳ Waiting for data... Ensure probe is sending JSON lines.")

st.sidebar.markdown("---")
st.sidebar.info(t["sidebar_instructions"])

# Manual data entry
with st.sidebar.expander(t["manual_add"]):
    manual_chip = st.text_input(t["manual_chip"], key="manual_chip")
    manual_voltage = st.number_input(t["manual_voltage"], value=0.0, step=0.1, key="manual_voltage")
    manual_expected = st.number_input(t["manual_expected"], value=0.0, step=0.1, key="manual_expected")
    if st.button(t["manual_add_btn"]):
        if manual_chip:
            st.session_state.probe_readings.append({
                "chip": manual_chip,
                "voltage": manual_voltage,
                "expected": manual_expected
            })
            st.sidebar.success(f"Added reading for {manual_chip}")
            st.rerun()

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
    uploaded_image = st.file_uploader(t["upload_label"], type=["jpg", "jpeg", "png"], key="image_uploader")
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
    if not st.session_state.probe_readings:
        st.warning("Please add at least one manual reading or connect a USB probe before running diagnostic.")
    else:
        with st.spinner(t["running_diag"]):
            # Ensure image analysis exists if image was uploaded
            if uploaded_image and not st.session_state.image_analysis:
                st.session_state.image_analysis = analyze_circuit_image(uploaded_image)
            # Identify device (from image OR from chip labels in readings)
            st.session_state.device_type = identify_device(
                st.session_state.image_analysis,
                st.session_state.probe_readings,
                t["lang_code"]
            )
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
    st.write(f"**{t['probe_data_status']}:**")
    if st.session_state.probe_connected and len(st.session_state.probe_readings) > 0:
        st.success(t["probe_data_yes"].format(len(st.session_state.probe_readings)))
    else:
        st.info(t["probe_data_no"])
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
        "device_type": st.session_state.device_type
    }
    with st.chat_message("assistant"):
        with st.spinner(t["designing"]):
            answer = redesign_question(prompt, context, t["lang_code"])
            st.markdown(answer)
    st.session_state.chat_history.append({"role": "assistant", "content": answer})

st.markdown("---")
st.caption(t["footer"])
