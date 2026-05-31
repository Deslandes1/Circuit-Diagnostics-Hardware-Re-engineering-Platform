import streamlit as st
import os
import subprocess
import requests
import asyncio
import re
from groq import Groq
import edge_tts

# yt-dlp (optional)
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    st.warning("yt-dlp not installed. For YouTube/Vimeo, install it: pip install yt-dlp")

# ================== Page Config ==================
st.set_page_config(
    page_title="GlobalInternet.py AI Video Voice Translator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================== Styling ==================
st.markdown(
    """
    <style>
    .stApp, [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #0b1329 !important;
        background-image: radial-gradient(at 0% 0%, hsla(224,53%,12%,1) 0, transparent 55%), 
                          radial-gradient(at 100% 0%, hsla(210,70%,15%,1) 0, transparent 55%),
                          radial-gradient(at 50% 100%, hsla(220,60%,10%,1) 0, transparent 50%) !important;
        background-attachment: fixed !important;
    }
    h1, h2, h3, h4, p, span, label, li { color: #ffffff !important; }
    .feature-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px; padding: 25px; margin-bottom: 20px;
    }
    .status-box {
        background: rgba(11, 19, 41, 0.7); padding: 20px;
        border-radius: 8px; border-left: 5px solid #00ebc7; margin-bottom: 20px;
    }
    .footer-white-right {
        text-align: right !important; color: #ffffff !important;
        font-weight: 800 !important; font-size: 0.9rem; margin-top: 60px;
    }
    .stButton>button {
        background-color: #00ebc7 !important; color: #0b1329 !important;
        font-weight: 700 !important; border: none !important; width: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ================== Helper Functions ==================
def get_duration(file_path):
    if not os.path.exists(file_path):
        return 0.0
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        return float(result.stdout.decode('utf-8').strip())
    except:
        return 0.0

def extend_video_with_last_frame(original_video, output_video, target_duration):
    orig_dur = get_duration(original_video)
    if orig_dur >= target_duration - 0.1:
        subprocess.run([
            "ffmpeg", "-i", original_video, "-c:v", "copy", "-c:a", "copy", output_video, "-y"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_video
    pad_duration = target_duration - orig_dur
    subprocess.run([
        "ffmpeg", "-i", original_video,
        "-vf", f"tpad=stop_mode=clone:stop_duration={pad_duration}",
        "-af", f"apad=pad_dur={pad_duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(target_duration),
        output_video, "-y"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_video

def generate_srt_file(text, duration_sec, output_srt_path):
    words = text.split()
    if not words:
        words = ["Processing..."]
    chunk_size = 6
    chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
    num_chunks = len(chunks)
    chunk_duration = duration_sec / max(1, num_chunks)

    def fmt(sec):
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int((sec % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with open(output_srt_path, "w", encoding="utf-8") as f:
        for idx, chunk in enumerate(chunks):
            start = idx * chunk_duration
            end = (idx + 1) * chunk_duration
            f.write(f"{idx+1}\n{fmt(start)} --> {fmt(end)}\n{' '.join(chunk)}\n\n")

def clean_repetitions(text):
    words = text.split()
    if len(words) > 400 and words[-10:] and len(set(words[-10:])) < 2:
        unique = []
        for w in words:
            if w not in unique or len(unique) > 100:
                break
            unique.append(w)
        return " ".join(unique)
    return text

def split_text_into_chunks(text, max_chars=1000):
    sentences = re.split(r'(?<=[。！？.!?])', text)
    chunks = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) <= max_chars:
            current += sent
        else:
            if current:
                chunks.append(current.strip())
            current = sent
    if current:
        chunks.append(current.strip())
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            final_chunks.append(chunk)
        else:
            for i in range(0, len(chunk), max_chars):
                final_chunks.append(chunk[i:i+max_chars])
    return final_chunks

async def generate_tts(text, output_path, voice_name, fallback_voice):
    if len(text) < 1500:
        try:
            comm = edge_tts.Communicate(text, voice_name)
            await comm.save(output_path)
            if os.path.getsize(output_path) > 0:
                return True
        except Exception as e:
            st.warning(f"Direct TTS failed: {e}. Trying fallback.")
            try:
                comm = edge_tts.Communicate(text, fallback_voice)
                await comm.save(output_path)
                return os.path.getsize(output_path) > 0
            except:
                return False
    else:
        st.info(f"Text length {len(text)} chars → splitting into chunks (max 1000 chars).")
        chunks = split_text_into_chunks(text, max_chars=1000)
        temp_files = []
        for i, chunk in enumerate(chunks):
            temp_file = f"temp_tts_{i}.mp3"
            try:
                comm = edge_tts.Communicate(chunk, voice_name)
                await comm.save(temp_file)
                if os.path.getsize(temp_file) == 0:
                    raise Exception("Empty file")
                temp_files.append(temp_file)
            except Exception as e:
                st.warning(f"Chunk {i+1} failed with primary voice: {e}. Trying fallback.")
                try:
                    comm = edge_tts.Communicate(chunk, fallback_voice)
                    await comm.save(temp_file)
                    if os.path.getsize(temp_file) > 0:
                        temp_files.append(temp_file)
                    else:
                        st.error(f"Fallback also failed for chunk {i+1}")
                except Exception as e2:
                    st.error(f"Chunk {i+1} completely failed: {e2}")
        if not temp_files:
            return False
        concat_file = "concat_list.txt"
        with open(concat_file, "w") as f:
            for tf in temp_files:
                f.write(f"file '{tf}'\n")
        cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", output_path, "-y"]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for tf in temp_files:
            os.remove(tf)
        os.remove(concat_file)
        return os.path.getsize(output_path) > 0

# ================== Download functions (unchanged) ==================
def is_aria2_available():
    try:
        subprocess.run(["aria2c", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except:
        return False

def is_valid_video(file_path):
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return False
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type", "-of", "default=nokey=1:noprint_wrappers=1", file_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        st.warning(f"ffprobe error: {result.stderr.decode()}")
        return False
    output = result.stdout.decode().strip()
    return output == "video"

def file_info(path):
    if not os.path.exists(path):
        return "does not exist"
    size = os.path.getsize(path)
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=format_name", "-of", "default=noprint_wrappers=1:nokey=1", path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    fmt = result.stdout.decode().strip() if result.returncode == 0 else "unknown"
    return f"exists, size={size} bytes, format={fmt}"

def check_cookies_format(cookie_path):
    if not cookie_path or not os.path.exists(cookie_path):
        return False, "No cookie file"
    try:
        with open(cookie_path, 'r') as f:
            first_line = f.readline().strip()
            if not first_line.startswith('# Netscape HTTP Cookie File'):
                return False, f"Invalid format: first line is '{first_line[:50]}' (should start with '# Netscape HTTP Cookie File')"
            content = f.read()
            if not re.search(r'^[^#].*\t.*\t.*\t.*\t.*\t.*$', content, re.MULTILINE):
                return False, "No valid cookie entries found"
            return True, "OK"
    except Exception as e:
        return False, str(e)

def download_video_with_ytdlp_subprocess(url, output_path, cookie_file):
    cmd = [
        "yt-dlp",
        "--cookies", cookie_file,
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", output_path,
        "--quiet", "--no-warnings",
        "--concurrent-fragments", "8",
        "--retries", "10",
        "--sleep-interval", "5",
        "--max-sleep-interval", "10",
        "--no-check-certificates",
        url
    ]
    try:
        st.info("Running yt-dlp command line with cookies...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            st.error(f"yt-dlp subprocess error: {result.stderr}")
            return False
        return True
    except Exception as e:
        st.error(f"yt-dlp subprocess exception: {e}")
        return False

def download_video(url, output_path, cookie_file=None):
    if is_aria2_available():
        st.info("Trying aria2c with 16 parallel connections ...")
        cmd = [
            "aria2c", "-x", "16", "-s", "16", "-k", "1M",
            "--console-log-level=error", "-o", output_path, url
        ]
        try:
            subprocess.run(cmd, check=True, timeout=600)
            st.write(f"aria2c result: {file_info(output_path)}")
            if is_valid_video(output_path):
                st.success("Downloaded with aria2c – valid video file.")
                return True
            else:
                st.warning(f"aria2c downloaded file but not a valid video. Info: {file_info(output_path)}")
        except Exception as e:
            st.warning(f"aria2c failed: {e}")

    if YT_DLP_AVAILABLE:
        st.info("Using yt-dlp with parallel fragments...")
        if not output_path.endswith('.mp4'):
            output_path = output_path + '.mp4'
        ydl_opts = {
            'outtmpl': output_path,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'quiet': False,
            'no_warnings': False,
            'concurrent_fragment_downloads': 8,
            'retries': 10,
            'fragment_retries': 10,
            'buffersize': 8192 * 16,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extractor_args': {'youtube': {'skip': ['hls', 'dash']}},
            'sleep_interval': 5,
            'max_sleep_interval': 10,
        }
        if cookie_file and os.path.exists(cookie_file):
            ydl_opts['cookiefile'] = cookie_file
            st.info("Using uploaded cookies.txt for authentication.")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                actual_file = ydl.prepare_filename(info)
                if actual_file and os.path.exists(actual_file):
                    if not actual_file.endswith('.mp4') and os.path.exists(actual_file + '.mp4'):
                        actual_file = actual_file + '.mp4'
                    if actual_file != output_path and os.path.exists(actual_file):
                        os.rename(actual_file, output_path)
            with open(output_path, 'rb') as f:
                head = f.read(500)
                if b'<html' in head.lower() or b'<!doctype' in head.lower():
                    raise Exception("HTML page received")
            st.write(f"yt-dlp result: {file_info(output_path)}")
            if is_valid_video(output_path):
                st.success("Downloaded with yt-dlp – valid video file.")
                return True
            else:
                st.error(f"yt-dlp produced invalid file.")
        except Exception as e:
            st.warning(f"yt-dlp API failed: {e}")
            if cookie_file and os.path.exists(cookie_file):
                if download_video_with_ytdlp_subprocess(url, output_path, cookie_file):
                    if is_valid_video(output_path):
                        st.success("Downloaded with yt-dlp command line.")
                        return True

    st.info("Trying direct HTTP download ...")
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, stream=True, timeout=60, headers=headers)
        r.raise_for_status()
        content_type = r.headers.get('content-type', '')
        if 'text/html' in content_type:
            st.error("Direct HTTP returned HTML.")
            return False
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192 * 16):
                f.write(chunk)
        if is_valid_video(output_path):
            st.success("Downloaded via direct HTTP.")
            return True
    except Exception as e:
        st.error(f"Direct download failed: {e}")
    return False

# ================== Sidebar ==================
st.sidebar.markdown("## GlobalInternet.py")
st.sidebar.markdown("### AI Multi-Language Voice Translator")
st.sidebar.markdown("Built by **Gesner Deslandes**, Engineer-in-Chief")
st.sidebar.markdown("---")

st.sidebar.markdown("### YouTube Authentication (optional)")
st.sidebar.markdown("Upload a `cookies.txt` file (Netscape format) from your browser while logged into YouTube.")
cookies_file = st.sidebar.file_uploader("Upload cookies.txt", type=["txt"])
cookies_path = None
if cookies_file is not None:
    cookies_path = "cookies.txt"
    with open(cookies_path, "wb") as f:
        f.write(cookies_file.getbuffer())
    valid, msg = check_cookies_format(cookies_path)
    if valid:
        st.sidebar.success("Cookies file looks valid. YouTube downloads should work.")
    else:
        st.sidebar.error(f"Invalid cookies file: {msg}")
        st.sidebar.info("Please export cookies again using the 'Get cookies.txt LOCALLY' extension in Edge/Chrome.")
        cookies_path = None
else:
    st.sidebar.info("No cookies provided. YouTube links may fail. For best results, export cookies from a logged‑in YouTube session.")

with st.sidebar.expander("📖 How to get cookies.txt (Edge)"):
    st.markdown("""
    1. Install **"Get cookies.txt LOCALLY"** from [Edge Add-ons](https://microsoftedge.microsoft.com/addons/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc).
    2. Log into YouTube in Edge.
    3. Click the extension icon → **Export** → **Export All Cookies**.
    4. Upload the downloaded file here.
    """)

st.sidebar.markdown("---")

voice_options = {
    "Français (Native French Male - Henri)": "fr-FR-HenriNeural",
    "Español (Native Spanish Male - Alvaro)": "es-ES-AlvaroNeural",
    "English (Native US Male - Christopher)": "en-US-ChristopherNeural",
    "中文 (Chinese Mandarin Male - Yunxi)": "zh-CN-YunxiNeural",
    "العربية (Arabic Male - Hamed)": "ar-SA-HamedNeural",
    "Português (Brazilian Portuguese Male - Antonio)": "pt-BR-AntonioNeural",
    "Jamaican Patois (English-based Creole)": "en-US-ChristopherNeural"
}
selected_voice_label = st.sidebar.selectbox("Select Native Overdub Language Layer", list(voice_options.keys()))
voice_code = voice_options[selected_voice_label]

st.title("AI Video Voice Translation Engine")
st.markdown("### On-Demand Multimedia Linguistic Overdubbing Platform")
st.markdown("---")

col_left, col_right = st.columns([2, 1.8])

with col_left:
    st.markdown('<div class="feature-card">', unsafe_allow_html=True)
    st.markdown("<h4>Source Input Interface</h4>", unsafe_allow_html=True)
    input_method = st.radio(
        "Select Input Source Layer:",
        ["Upload Video from this Computer (.MP4)", 
         "Paste Video Link (YouTube, Dropbox, Google Drive, Vimeo, direct MP4)",
         "🎙️ AI Voiceover for Silent Video (Describe Software)"]
    )
    video_ready = False
    download_url = ""
    uploaded_file = None
    custom_script = None
    generate_desc = False

    if input_method == "Paste Video Link (YouTube, Dropbox, Google Drive, Vimeo, direct MP4)":
        raw_url = st.text_input("Paste Video Link Here:").strip()
        if raw_url:
            if not (raw_url.startswith("http://") or raw_url.startswith("https://")):
                st.error("Please enter a valid URL (starts with http:// or https://)")
            else:
                if "dropbox.com" in raw_url:
                    if "dl=0" in raw_url:
                        raw_url = raw_url.replace("dl=0", "dl=1")
                        st.info("Converted Dropbox link to direct download (dl=1).")
                    elif "?dl=" not in raw_url:
                        raw_url = raw_url + "?dl=1"
                        st.info("Added ?dl=1 to Dropbox link.")
                download_url = raw_url
                video_ready = True
                try:
                    st.video(raw_url)
                except:
                    st.info("Link accepted – will be downloaded during processing.")
    elif input_method == "Upload Video from this Computer (.MP4)":
        uploaded_file = st.file_uploader("Choose a video file:", type=["mp4", "mov", "mkv", "avi"])
        if uploaded_file is not None:
            st.video(uploaded_file)
            video_ready = True
    else:  # Voiceover mode
        st.markdown("**🎙️ Create AI voiceover for your silent demo video**")
        raw_url = st.text_input("Paste your demo video link (no audio):").strip()
        if raw_url:
            if not (raw_url.startswith("http://") or raw_url.startswith("https://")):
                st.error("Please enter a valid URL (starts with http:// or https://)")
            else:
                if "dropbox.com" in raw_url:
                    if "dl=0" in raw_url:
                        raw_url = raw_url.replace("dl=0", "dl=1")
                        st.info("Converted Dropbox link to direct download (dl=1).")
                    elif "?dl=" not in raw_url:
                        raw_url = raw_url + "?dl=1"
                        st.info("Added ?dl=1 to Dropbox link.")
                download_url = raw_url
                video_ready = True
                try:
                    st.video(raw_url)
                except:
                    st.info("Video link accepted.")
        
        st.markdown("**Voiceover Script**")
        script_option = st.radio("Select script source:", ["AI Auto-generate description", "Write my own script"])
        if script_option == "Write my own script":
            custom_script = st.text_area("Enter your voiceover text (in the selected language):", height=150,
                placeholder="Example: This software shows how to diagnose a Samsung tablet circuit...")
        else:
            generate_desc = True
            st.info("AI will generate a professional description of the Circuit Diagnostics & Hardware Re‑engineering software.")
    
    st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="feature-card">', unsafe_allow_html=True)
    st.markdown("<h4>Neural Pipeline Controls</h4>", unsafe_allow_html=True)
    process_btn = st.button("Execute Voice Sync Overdub & Captions")

    if process_btn:
        if not video_ready:
            st.error("Error: Please provide a video file or a valid link.")
        elif "GROQ_API_KEY" not in st.secrets:
            st.error("Missing Groq API key. Add GROQ_API_KEY to your Streamlit secrets.")
        else:
            st.markdown('<div class="status-box">', unsafe_allow_html=True)
            st.markdown("<h5>System Pipeline Progress Status</h5>", unsafe_allow_html=True)
            status = st.empty()
            progress_bar = st.progress(0)

            try:
                for f in ["video.mp4", "extracted_audio.mp3", "translated_voice.mp3", "subtitles.srt", "final_output.mp4", "extended_video.mp4"]:
                    if os.path.exists(f):
                        os.remove(f)

                status.text("Downloading / reading video...")
                progress_bar.progress(10)
                if uploaded_file:
                    with open("video.mp4", "wb") as f:
                        f.write(uploaded_file.getbuffer())
                else:
                    if not download_video(download_url, "video.mp4", cookie_file=cookies_path):
                        raise Exception("Failed to download video. Please check the link.")

                if not os.path.exists("video.mp4") or os.path.getsize("video.mp4") == 0:
                    raise Exception("Video file is empty or could not be saved.")

                video_duration = get_duration("video.mp4")
                if video_duration <= 0:
                    video_duration = 30.0

                client = Groq(api_key=st.secrets["GROQ_API_KEY"])

                if input_method == "🎙️ AI Voiceover for Silent Video (Describe Software)":
                    status.text("Preparing voiceover script...")
                    progress_bar.progress(25)
                    
                    if generate_desc:
                        # Determine target language instruction (neutral)
                        if "Français" in selected_voice_label:
                            lang_name = "French"
                        elif "Español" in selected_voice_label:
                            lang_name = "Spanish"
                        elif "中文" in selected_voice_label:
                            lang_name = "Mandarin Chinese (Simplified)"
                        elif "العربية" in selected_voice_label:
                            lang_name = "Modern Standard Arabic"
                        elif "Português" in selected_voice_label:
                            lang_name = "Brazilian Portuguese"
                        else:
                            lang_name = "English"

                        desc_prompt = f"""You are a professional AI voiceover script writer. Write a clear, engaging voiceover script in {lang_name} for a demonstration video of the software "Circuit Diagnostics & Hardware Re‑engineering". The viewer will see a screen recording where a user interacts with the app.

IMPORTANT: 
- Do not mention that you are choosing a specific language like French. Instead, say: "You can choose any language you prefer" or similar.
- The script must include the credit: "This software was built by Gesner Deslandes at GlobalInternet.py."
- The tone should be professional, confident, and suitable for a product demo.

Software features to describe (match the visual actions in the video):
- Language selection: show how the user selects a language from the sidebar (e.g., English, French, Spanish, etc.)
- Upload a Samsung tablet circuit image for visual damage analysis.
- Enable Demo Mode and load pre‑set readings.
- Run the full diagnostic to get a fault summary, actions, and recommended tools.
- Ask the redesign chatbot: "How can I use this tablet circuit to build a new drone hardware circuit?" and show the AI's answer.

The script should flow naturally as the mouse moves. Keep the length around 200-300 words (about 1-2 minutes of speech). Output only the script text, no extra commentary.
"""
                        response = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": desc_prompt}],
                            temperature=0.4,
                            max_tokens=800
                        )
                        localized_text = response.choices[0].message.content.strip()
                        # Ensure the credit is present (if not, prepend)
                        if "Gesner Deslandes" not in localized_text or "GlobalInternet.py" not in localized_text:
                            localized_text = "This software was built by Gesner Deslandes at GlobalInternet.py. " + localized_text
                        st.info("AI-generated script ready.")
                    else:
                        localized_text = custom_script.strip()
                        if not localized_text:
                            raise Exception("Please provide a custom script or enable auto-generation.")
                else:
                    # Original translation pipeline
                    status.text("Extracting audio...")
                    progress_bar.progress(25)
                    subprocess.run([
                        "ffmpeg", "-i", "video.mp4", "-vn",
                        "-acodec", "libmp3lame", "-q:a", "2", "extracted_audio.mp3", "-y"
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if not os.path.exists("extracted_audio.mp3") or os.path.getsize("extracted_audio.mp3") == 0:
                        raise Exception("Failed to extract audio from video.")

                    status.text("Transcribing original audio...")
                    progress_bar.progress(40)
                    with open("extracted_audio.mp3", "rb") as audio_file:
                        transcription = client.audio.translations.create(
                            file=("extracted_audio.mp3", audio_file.read()),
                            model="whisper-large-v3",
                            response_format="text"
                        )
                    base_text = str(transcription).strip()

                    status.text("Localizing text...")
                    progress_bar.progress(55)
                    if "Jamaican Patois" in selected_voice_label:
                        lang_instr = "authentic Jamaican Patois"
                    elif "Français" in selected_voice_label:
                        lang_instr = "natural French"
                    elif "Español" in selected_voice_label:
                        lang_instr = "natural Spanish"
                    elif "中文" in selected_voice_label:
                        lang_instr = "natural Mandarin Chinese (Simplified)"
                    elif "العربية" in selected_voice_label:
                        lang_instr = "natural Modern Standard Arabic"
                    elif "Português" in selected_voice_label:
                        lang_instr = "natural Brazilian Portuguese"
                    else:
                        lang_instr = "natural US English"
                    system_prompt = f"""You are a voiceover localizer. Rewrite the transcript into fluid, natural spoken prose.
Target style: {lang_instr}
Rules:
- Keep the original meaning exactly.
- Remove stiff grammar, literal translations, and repetition.
- Return ONLY the polished text, nothing else."""
                    response = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": base_text}
                        ],
                        temperature=0.2,
                        max_tokens=800,
                    )
                    localized_text = response.choices[0].message.content.strip()
                    localized_text = clean_repetitions(localized_text)
                    st.info(f"Localized script: \"{localized_text[:300]}...\"")

                status.text("Generating voiceover (chunked for long text)...")
                progress_bar.progress(70)
                output_audio = "translated_voice.mp3"
                if "Français" in selected_voice_label:
                    fallback = "fr-FR-HenriNeural"
                elif "Español" in selected_voice_label:
                    fallback = "es-ES-AlvaroNeural"
                elif "中文" in selected_voice_label:
                    fallback = "zh-CN-XiaoxiaoNeural"
                else:
                    fallback = "en-US-ChristopherNeural"

                tts_success = asyncio.run(generate_tts(localized_text, output_audio, voice_code, fallback))
                if not tts_success:
                    raise Exception("TTS generation failed.")
                if not os.path.exists(output_audio) or os.path.getsize(output_audio) == 0:
                    raise Exception("TTS produced an empty file.")
                audio_duration = get_duration(output_audio)

                status.text("Synchronizing video and audio...")
                progress_bar.progress(85)
                if audio_duration > video_duration:
                    st.warning(f"Voiceover longer ({audio_duration:.1f}s) than video ({video_duration:.1f}s). Extending video.")
                    working_video = extend_video_with_last_frame("video.mp4", "extended_video.mp4", audio_duration)
                    working_audio = output_audio
                    final_duration = audio_duration
                else:
                    st.info(f"Voiceover shorter ({audio_duration:.1f}s). Original audio will be replaced.")
                    working_video = "video.mp4"
                    working_audio = output_audio
                    final_duration = video_duration

                generate_srt_file(localized_text, final_duration, "subtitles.srt")

                status.text("Mixing audio and burning subtitles...")
                final_output = "final_output.mp4"
                cmd = [
                    "ffmpeg", "-i", working_video, "-i", working_audio,
                    "-map", "0:v:0", "-map", "1:a:0",
                    "-vf", "subtitles=subtitles.srt",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k",
                    final_output, "-y"
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    st.error(f"FFmpeg error: {result.stderr}")
                    raise Exception("Mixing failed.")

                if not os.path.exists(final_output) or os.path.getsize(final_output) == 0:
                    raise Exception("Final output file is empty.")

                for tmp in ["video.mp4", "extracted_audio.mp3", "translated_voice.mp3", "subtitles.srt", "extended_video.mp4"]:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                if cookies_path and os.path.exists(cookies_path):
                    os.remove(cookies_path)

                progress_bar.progress(100)
                status.text("All systems harmonized! Video ready.")
                st.markdown('</div>', unsafe_allow_html=True)

                st.success("Final video created successfully:")
                st.video(final_output, format="video/mp4")

            except Exception as e:
                progress_bar.empty()
                status.empty()
                st.error(f"Pipeline error: {str(e)}")
                st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="footer-white-right">
        Built by Gesner Deslandes, Engineer-in-Chief at GlobalInternet.py | Advanced Cognitive Systems Integration.
    </div>
    """,
    unsafe_allow_html=True
)
