import warnings
warnings.filterwarnings("ignore")
import os
os.environ["PYTHONWARNINGS"] = "ignore"
import io
import time
import threading
import json
import sys
import subprocess
import webbrowser
import urllib.parse
import requests
import re
import ctypes
from ctypes import wintypes
import winreg
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import pyperclip
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from PIL import Image, ImageDraw, ImageGrab
import winsound
import traceback

# 🌟 視窗高解析度字體銳利化 (DPI Awareness)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# 🌟 設定 Windows 視窗原生深色標題列 (DWM Immersive Dark Mode)
def set_dark_title_bar(window):
    try:
        window.update()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            hwnd = window.winfo_id()
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass

# 安全載入 pyttsx3
try:
    import pyttsx3
    TTS_AVAILABLE = True
except Exception:
    TTS_AVAILABLE = False

# 安全載入系統匣套件 pystray
try:
    import pystray
    TRAY_AVAILABLE = True
except Exception:
    TRAY_AVAILABLE = False

# 嘗試載入 OpenCC 簡轉繁
try:
    from opencc import OpenCC
    converter = OpenCC('s2twp')
    def to_tw_trad(text):
        return converter.convert(text)
except Exception:
    def to_tw_trad(text):
        return text

# ================= 設定與版本區 =================
CURRENT_VERSION = "v7.0.2"
DISCORD_USERNAME = "loey3"
DISCORD_USER_ID = "816981477946032150"
DISCORD_PROFILE_URL = f"https://discord.com/users/{DISCORD_USER_ID}"
GITHUB_REPO = "syz0930450116-bot/GroqVoiceTool"

# 🌟 遠端動態推播 API 廣播網址 (可指向 GitHub Raw JSON 或 Gist)
BROADCAST_API_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/broadcast.json"

APPDATA_DIR = os.path.join(os.getenv('LOCALAPPDATA'), 'GroqVoiceTool')
os.makedirs(APPDATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(APPDATA_DIR, "config.json")
HISTORY_FILE = os.path.join(APPDATA_DIR, "history.json")
SCREENSHOT_DIR = os.path.join(APPDATA_DIR, "Screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

SAMPLE_RATE = 16000

HOTKEY_IDS = {
    1: ("zh (Alt + S)", 0x0001, 0x53),
    2: ("en (Alt + Shift + S)", 0x0001 | 0x0004, 0x53),
    3: ("trans (Alt + C)", 0x0001, 0x43),
    4: ("replace (Alt + Shift + C)", 0x0001 | 0x0004, 0x43),
    5: ("ai (Alt + A)", 0x0001, 0x41),
    6: ("help (Alt + H)", 0x0001, 0x48),
    7: ("quit (Alt + Shift + Q)", 0x0001 | 0x0004, 0x51),
    8: ("ocr (Alt + X)", 0x0001, 0x58),
    9: ("custom_1 (Alt + 1)", 0x0001, 0x31),
    10: ("custom_2 (Alt + 2)", 0x0001, 0x32),
    11: ("tts (Alt + T)", 0x0001, 0x54),
    12: ("pause (Alt + Shift + P)", 0x0001 | 0x0004, 0x50),
    13: ("spotlight (Alt + Q)", 0x0001, 0x51)
}

THEMES = {
    "暗夜駭客 (Dark Hacker)": {
        "widget_bg": "#21252B", "widget_fg": "#FFFFFF", "btn_bg": "#4B5263",
        "accent": "#61AFEF", "card_bg": "#1E1E1E", "inner_bg": "#252526"
    },
    "賽博霓虹 (Cyberpunk Neon)": {
        "widget_bg": "#0F0E17", "widget_fg": "#FFFFFE", "btn_bg": "#3A3F58",
        "accent": "#FF8906", "card_bg": "#0F0E17", "inner_bg": "#2E2F3E"
    },
    "極簡純白 (Clean Minimalist)": {
        "widget_bg": "#F4F4F9", "widget_fg": "#101820", "btn_bg": "#D1D5DB",
        "accent": "#004643", "card_bg": "#FFFFFF", "inner_bg": "#F9FAFB"
    }
}

MODEL_MAP = {
    "openai/gpt-oss-20b": "openai/gpt-oss-20b (極速通用)",
    "openai/gpt-oss-120b": "openai/gpt-oss-120b (OpenAI 高階推理)",
    "qwen-2.5-32b": "qwen-2.5-32b (中文與事實查核能力極強)",
    "deepseek-r1-distill-llama-70b": "deepseek-r1-distill-llama-70b (深度邏輯推理)"
}

SCALE_OPTIONS = {
    "標準字體 (1.0x)": 1.0,
    "中等字體 (1.2x)": 1.2,
    "大級字體 (1.35x - 推薦)": 1.35,
    "特大字體 (1.5x)": 1.5,
    "超大字體 (1.8x)": 1.8
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: pass
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(cfg, f, indent=4, ensure_ascii=False)

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: pass
    return []

def save_history(hist):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f: json.dump(hist, f, indent=4, ensure_ascii=False)
    except Exception: pass

def add_history_entry(task_type, original, result):
    try:
        history = load_history()
        entry = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": task_type,
            "original": original,
            "result": result
        }
        history.insert(0, entry)
        if len(history) > 50: history = history[:50]
        save_history(history)
    except Exception: pass

config = load_config()
GROQ_API_KEY = config.get("groq_api_key", "")
TAVILY_API_KEY = config.get("tavily_api_key", "")
CUSTOM_PROMPT_1 = config.get("custom_prompt_1", "請幫我將這段文字翻譯為日文。")
CUSTOM_PROMPT_2 = config.get("custom_prompt_2", "請幫我將這段文字翻譯為英文。")
CURRENT_THEME_NAME = config.get("theme", "暗夜駭客 (Dark Hacker)")
FONT_SCALE = config.get("font_scale", 1.35)

MODEL_VOICE = config.get("model_voice", "openai/gpt-oss-20b")
MODEL_CHAT = config.get("model_chat", "qwen-2.5-32b")
MODEL_SELECTION = config.get("model_selection", "openai/gpt-oss-20b")

LOCAL_PREVIOUS_VERSION = config.get("last_version", "尚未紀錄（首次安裝）")
SEEN_BROADCAST_IDS = config.get("seen_broadcast_ids", [])

config["last_version"] = CURRENT_VERSION
save_config(config)

def sf(base_size):
    return max(9, int(base_size * FONT_SCALE))

def open_discord_profile():
    webbrowser.open(DISCORD_PROFILE_URL)

def copy_discord_username(parent_win=None):
    pyperclip.copy(DISCORD_USERNAME)
    messagebox.showinfo("複製成功", f"已複製 Discord 帳號：{DISCORD_USERNAME}\n歡迎貼上並私訊進行功能建議或反饋！", parent=parent_win)

# ================= 📢 底層核心：動態遠端推播 / API 廣播模組 =================
def fetch_remote_broadcast():
    def worker():
        try:
            resp = requests.get(BROADCAST_API_URL, headers={"User-Agent": "GroqVoiceTool-BroadcastFetcher"}, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                msg_id = data.get("id", "")
                msg_type = data.get("type", "info") # info, warning, force_update
                title = data.get("title", "📢 系統廣播通知")
                message = data.get("message", "")
                url = data.get("url", "")

                if msg_id and msg_id not in SEEN_BROADCAST_IDS:
                    SEEN_BROADCAST_IDS.append(msg_id)
                    config["seen_broadcast_ids"] = SEEN_BROADCAST_IDS
                    save_config(config)

                    if root: root.after(0, lambda: _show_broadcast_gui(title, message, msg_type, url))
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()

def _show_broadcast_gui(title, message, msg_type, url):
    if msg_type == "info":
        set_status(f"📢 {message[:30]}...", "#61AFEF")
        root.after(4000, hide_status)
        return

    bc_win = tk.Toplevel(root)
    bc_win.title(title)
    bc_win.geometry(f"500x320+{(root.winfo_screenwidth()-500)//2}+{(root.winfo_screenheight()-320)//2}")
    bc_win.attributes("-topmost", True)
    bc_win.configure(bg="#1E1E1E")
    set_dark_title_bar(bc_win)

    header_color = "#E06C75" if msg_type == "force_update" else "#E5C07B"
    
    top_bar = tk.Frame(bc_win, bg=header_color)
    top_bar.pack(fill="x")
    tk.Label(top_bar, text=title, font=("Microsoft JhengHei", sf(11), "bold"), fg="#FFFFFF", bg=header_color).pack(pady=8)

    content_f = tk.Frame(bc_win, bg="#1E1E1E", padx=16, pady=12)
    content_f.pack(fill="both", expand=True)

    msg_box = scrolledtext.ScrolledText(content_f, font=("Microsoft JhengHei", sf(10)), bg="#252526", fg="#FFFFFF", wrap="word")
    msg_box.pack(fill="both", expand=True)
    msg_box.insert(tk.END, message)
    msg_box.config(state="disabled")

    btn_f = tk.Frame(bc_win, bg="#1E1E1E")
    btn_f.pack(fill="x", padx=16, pady=10)

    if url:
        tk.Button(btn_f, text="🔗 查看詳情 / 前往連結", command=lambda: webbrowser.open(url), bg="#61AFEF", fg="#21252B", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=12, pady=5).pack(side="left")

    tk.Button(btn_f, text="我知道了", command=bc_win.destroy, bg="#4B5263", fg="white", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=14, pady=5).pack(side="right")

# ================= 🔄 底層核心：自動熱更新模組 =================
def check_for_updates(manual=False):
    def update_worker():
        try:
            if manual: set_status("🔍 正在檢查雲端最新版本...", "#61AFEF")
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            headers = {"User-Agent": "GroqVoiceTool-AutoUpdater"}
            resp = requests.get(url, headers=headers, timeout=6)
            
            if resp.status_code == 200:
                data = resp.json()
                latest_tag = data.get("tag_name", "").strip()
                body = data.get("body", "無更新日誌說明。")
                assets = data.get("assets", [])

                if latest_tag and latest_tag != CURRENT_VERSION:
                    download_url = None
                    for asset in assets:
                        if asset.get("name", "").endswith(".exe"):
                            download_url = asset.get("browser_download_url")
                            break
                    
                    if not download_url and assets:
                        download_url = assets[0].get("browser_download_url")

                    if download_url:
                        if root: root.after(0, lambda: _prompt_update_gui(latest_tag, body, download_url))
                        return

            if manual:
                set_status("✨ 當前已是最新版本！", "#98C379")
                root.after(2000, hide_status)
        except Exception:
            if manual:
                set_status("⚠️ 檢查更新失敗", "#E5C07B")
                root.after(2000, hide_status)

    threading.Thread(target=update_worker, daemon=True).start()

# ✅ 正確的寫法
def _prompt_update_gui(latest_tag, release_notes, download_url):
    up_win = tk.Toplevel(root)
    up_win.title(f"🚀 發現新版本：{latest_tag}")
    
    # 🌟 加大視窗高度 (560x480)，確保按鈕完整呈現在畫面上
    up_win.geometry(f"560x480+{(root.winfo_screenwidth()-560)//2}+{(root.winfo_screenheight()-480)//2}")
    up_win.attributes("-topmost", True)
    up_win.configure(bg="#1E1E1E")

    tk.Label(up_win, text=f"🎉 發現軟體最新升級版本：{latest_tag}", font=("Microsoft JhengHei", sf(12), "bold"), fg="#61AFEF", bg="#1E1E1E").pack(anchor="w", padx=16, pady=(14, 4))
    tk.Label(up_win, text=f"（您當前的執行版本：{CURRENT_VERSION}）", font=("Microsoft JhengHei", sf(10)), fg="#ABB2BF", bg="#1E1E1E").pack(anchor="w", padx=16)

    tk.Label(up_win, text="📝 更新內容說明：", font=("Microsoft JhengHei", sf(10), "bold"), fg="#98C379", bg="#1E1E1E").pack(anchor="w", padx=16, pady=(10, 2))
    
    # 稍微縮減文字框高度，留出足夠空間給底部按鈕列
    notes_box = scrolledtext.ScrolledText(up_win, height=6, font=("Microsoft JhengHei", sf(10)), bg="#252526", fg="#FFFFFF", wrap="word")
    notes_box.pack(fill="both", expand=True, padx=16, pady=4)
    notes_box.insert(tk.END, release_notes)
    notes_box.config(state="disabled")

    btn_f = tk.Frame(up_win, bg="#1E1E1E")
    btn_f.pack(fill="x", padx=16, pady=16)

    def start_download(event=None):
        up_win.destroy()
        threading.Thread(target=_perform_auto_update, args=(download_url,), daemon=True).start()

    # 升級按鈕
    btn_upgrade = tk.Button(btn_f, text="⚡ 立即一鍵自動升級 (Enter)", command=start_download, bg="#4CAF50", fg="white", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=16, pady=8)
    btn_upgrade.pack(side="right")
    
    tk.Button(btn_f, text="稍後再說", command=up_win.destroy, bg="#4B5263", fg="white", font=("Microsoft JhengHei", sf(10)), relief="flat", padx=12, pady=8).pack(side="right", padx=8)

    # 🌟 關鍵修復：將視窗焦點鎖定在升級按鈕上，並綁定 Enter / Space 按鍵
    btn_upgrade.focus_set()
    up_win.bind("<Return>", start_download)
    up_win.bind("<space>", start_download)
    up_win.bind("<Escape>", lambda e: up_win.destroy())

    set_dark_title_bar(up_win)

def _perform_auto_update(download_url):
    set_status("🚀 正在背景下載最新升級套件...", "#61AFEF")
    try:
        current_exe = sys.executable
        if not current_exe.endswith(".exe"):
            set_status("⚠️ 開發環境腳本無法自動替換，請下載 exe 測試", "#E5C07B")
            root.after(3000, hide_status)
            return

        new_exe_path = os.path.join(APPDATA_DIR, "GroqVoiceTool_new.exe")
        resp = requests.get(download_url, stream=True, timeout=30)
        if resp.status_code == 200:
            with open(new_exe_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk: f.write(chunk)
            
            set_status("✨ 下載完成，即將自動覆蓋並重啟...", "#98C379")
            time.sleep(1.0)

            bat_path = os.path.join(APPDATA_DIR, "update_installer.bat")
            bat_script = f"""@echo off
timeout /t 1 /nobreak > NUL
move /y "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
            with open(bat_path, "w", encoding="ansi") as f:
                f.write(bat_script)

            subprocess.Popen([bat_path], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            os._exit(0)
        else:
            set_status("⚠️ 更新檔下載失敗", "#E06C75")
    except Exception as e:
        trigger_cdn_error_modal("自動熱更新過程發生例外", traceback.format_exc())
    finally:
        root.after(3000, hide_status)

def set_autostart(enable=True):
    try:
        startup_dir = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        shortcut_path = os.path.join(startup_dir, "GroqVoiceTool.lnk")
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            winreg.DeleteValue(key, "GroqVoiceTool")
            winreg.CloseKey(key)
        except Exception:
            pass

        if enable:
            target_exe = sys.executable
            work_dir = os.path.dirname(target_exe)
            ps_command = f"""
            $WshShell = New-Object -comObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
            $Shortcut.TargetPath = "{target_exe}"
            $Shortcut.WorkingDirectory = "{work_dir}"
            $Shortcut.Save()
            """
            subprocess.run(["powershell", "-Command", ps_command], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
    except Exception as e:
        print(f"[Autostart Error] {e}")

if "autostart" not in config:
    config["autostart"] = True
    save_config(config)
    set_autostart(True)
else:
    set_autostart(config.get("autostart", True))

recording = False
is_processing = False
is_paused = False
auto_clipboard_enabled = False
last_clipboard_text = ""
stream = None
current_mode = "zh"
last_trigger_time = 0
root = None
status_win = None
status_label = None
tray_icon = None
floating_ball_win = None
ball_menu_win = None
clip_btn_ref = None
chat_panel_win = None
ai_result_win = None

audio_frames = []

def get_web_search_context(query):
    if TAVILY_API_KEY.strip():
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": TAVILY_API_KEY.strip(),
                "query": query,
                "search_depth": "basic",
                "include_answer": False,
                "max_results": 3
            }
            resp = requests.post(url, json=payload, timeout=3.5)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                snippets = []
                for item in results:
                    title = item.get("title", "")
                    snippet = item.get("content", "")
                    if snippet:
                        snippets.append(f"• [{title}] {snippet[:150]}")
                if snippets:
                    return "\n".join(snippets)
        except Exception:
            pass

    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
        resp = requests.get(url, headers=headers, timeout=1.5)
        if resp.status_code == 200:
            snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', resp.text, re.DOTALL)
            clean_snippets = []
            for s in snippets[:3]:
                clean = re.sub(r'<[^>]+>', '', s).strip()
                if clean: clean_snippets.append(clean[:120])
            if clean_snippets:
                return "\n".join([f"• {cs}" for cs in clean_snippets])
    except Exception:
        pass
    return ""

def get_system_prompt():
    cur_time = time.strftime('%Y-%m-%d %H:%M:%S')
    return (
        f"你是一個具備實時資訊理解能力的高效 AI 桌面助理。當前系統真實時間為：{cur_time}（2026年）。\n"
        "【原則與事實查核】：\n"
        "1. 請用繁體中文（台灣用語習慣）精準回答問題。\n"
        "2. 面對知名人物、網紅或真實事件時，請嚴格核對事實，切勿將不同人的本名、經歷或背景混淆或張冠李戴。\n"
        "3. 若遇到不確定的資訊，請依據檢索到的網路內容為準，不要隨意猜測。"
    )

spotlight_history = [
    {"role": "system", "content": get_system_prompt()}
]

def sanitize_spotlight_history():
    global spotlight_history
    sys_msg = {"role": "system", "content": get_system_prompt()}
    if not spotlight_history:
        spotlight_history = [sys_msg]
        return

    raw_dialog = spotlight_history[1:]
    clean_dialog = []

    for msg in raw_dialog:
        content = msg.get("content", "").strip()
        role = msg.get("role", "")
        if not content or role not in ("user", "assistant"):
            continue
        if clean_dialog and clean_dialog[-1]["role"] == role:
            clean_dialog[-1] = {"role": role, "content": content}
        else:
            clean_dialog.append({"role": role, "content": content})

    while clean_dialog and clean_dialog[0]["role"] != "user":
        clean_dialog.pop(0)

    if len(clean_dialog) > 12:
        clean_dialog = clean_dialog[-12:]
        while clean_dialog and clean_dialog[0]["role"] != "user":
            clean_dialog.pop(0)

    spotlight_history = [sys_msg] + clean_dialog

def get_theme():
    return THEMES.get(CURRENT_THEME_NAME, THEMES["暗夜駭客 (Dark Hacker)"])

def init_gui():
    global root, status_win, status_label
    root = tk.Tk()
    root.withdraw()

    status_win = tk.Toplevel(root)
    status_win.overrideredirect(True)
    status_win.attributes("-topmost", True)
    status_win.withdraw()
    
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    status_win.geometry(f"340x50+{sw - 360}+{sh - 110}")
    status_label = tk.Label(status_win, text="", font=("Microsoft JhengHei", sf(11), "bold"), fg="#FFFFFF", wraplength=320, justify="left")
    status_label.pack(fill="both", expand=True, padx=6, pady=4)

    show_startup_notice()
    toggle_floating_ball()

    # 🌟 啟動時自動檢查更新與遠端推播廣播
    check_for_updates(manual=False)
    fetch_remote_broadcast()

    threading.Thread(target=clipboard_monitor_loop, daemon=True).start()
    if TRAY_AVAILABLE: threading.Thread(target=setup_system_tray, daemon=True).start()
    if not GROQ_API_KEY: root.after(1500, prompt_api_key_gui)

def update_status_ui(text, bg_color):
    if status_win and status_label:
        status_label.config(text=text, bg=bg_color)
        status_win.configure(bg=bg_color)
        status_win.deiconify()

def hide_status_ui():
    if status_win and not recording: status_win.withdraw()

def set_status(text, bg_color):
    if root: root.after(0, update_status_ui, text, bg_color)

def hide_status():
    if root: root.after(0, hide_status_ui)

def show_startup_notice():
    set_status(f"🚀 {CURRENT_VERSION} Groq AI 懸浮球已就緒", "#98C379")
    if root: root.after(2000, hide_status)

def exit_program():
    set_status("👋 助理已關閉", "#E06C75")
    time.sleep(0.8)
    if tray_icon: tray_icon.stop()
    os._exit(0)

def audio_record_callback(indata, frames, time_info, status):
    if recording: audio_frames.append(indata.copy())

def start_recording(mode):
    global recording, stream, current_mode, audio_frames
    try:
        audio_frames = []
        current_mode = mode
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=audio_record_callback)
        stream.start()
        recording = True
        winsound.Beep(800, 120)
        set_status("🔴 [錄音中] 請說話...", "#E06C75")
    except Exception as e:
        recording = False
        stream = None
        trigger_cdn_error_modal("麥克風啟動失敗", str(e))

def stop_recording():
    global recording, stream
    if not recording: return
    recording = False
    winsound.Beep(600, 150)
    try:
        if stream: stream.stop(); stream.close()
    except Exception: pass
    stream = None

    if len(audio_frames) > 0:
        threading.Thread(target=process_whisper_and_proofread, args=(current_mode,), daemon=True).start()
    else:
        set_status("⚠️ 未收到語音數據", "#E5C07B")
        root.after(2000, hide_status)

def trigger_mode(mode):
    global last_trigger_time
    if is_paused: return
    now = time.time()
    if now - last_trigger_time < 0.4: return
    last_trigger_time = now
    if not recording: start_recording(mode)
    else: stop_recording()

def process_whisper_and_proofread(mode):
    global is_processing
    if not GROQ_API_KEY:
        set_status("⚠️ 未設定 API Key", "#E06C75")
        root.after(1500, hide_status); prompt_api_key_gui(); return

    is_processing = True
    set_status("⚡ Groq Whisper 語音辨識中...", "#61AFEF")
    try:
        audio_data = np.concatenate(audio_frames, axis=0)
        wav_io = io.BytesIO()
        write(wav_io, SAMPLE_RATE, (audio_data * 32767).astype(np.int16))
        wav_bytes = wav_io.getvalue()

        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        files = {"file": ("speech.wav", wav_bytes, "audio/wav")}
        data = {"model": "whisper-large-v3", "language": "zh", "temperature": "0", "response_format": "json"}
        
        w_resp = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data=data, timeout=12)
        if w_resp.status_code == 200:
            raw_text = to_tw_trad(w_resp.json().get("text", "").strip())
            if not raw_text:
                set_status("⚠️ 未偵測到清晰語音", "#E5C07B")
                root.after(1500, hide_status); return

            set_status("✨ AI 智慧精修校對中...", "#C678DD")
            sys_prompt = "Translate Chinese speech to natural English." if mode == "en" else "修復繁體中文同音錯字並補齊標點符號，不要回答內容，直接輸出校對後文字。"

            candidate_models = [MODEL_VOICE, "openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen-2.5-32b", "deepseek-r1-distill-llama-70b"]
            unique_candidate_models = []
            for m in candidate_models:
                if m not in unique_candidate_models: unique_candidate_models.append(m)

            polished_text = ""
            for model_name in unique_candidate_models:
                payload = {"model": model_name, "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"請校對：{raw_text}"}], "temperature": 0.0}
                p_resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}, json=payload, timeout=10)
                if p_resp.status_code == 200:
                    raw_content = p_resp.json()["choices"][0]["message"]["content"].strip()
                    if "</think>" in raw_content: raw_content = raw_content.split("</think>")[-1].strip()
                    polished_text = to_tw_trad(raw_content)
                    break

            if polished_text:
                pyperclip.copy(polished_text); time.sleep(0.05); send_paste()
                add_history_entry("語音聽寫校對", raw_text, polished_text)
                set_status("✨ 辨識完成，已自動貼上！", "#98C379")
            else:
                pyperclip.copy(raw_text); send_paste()
                set_status("⚠️ AI 校對異常，已貼出原始文字", "#E5C07B")
        else:
            trigger_cdn_error_modal(f"Groq API 錯誤 (HTTP {w_resp.status_code})", w_resp.text[:200])
    except Exception as e:
        trigger_cdn_error_modal("語音處理例外錯誤", traceback.format_exc())
    finally:
        is_processing = False
        root.after(2500, hide_status)

def trigger_cdn_error_modal(error_title, error_detail):
    root.after(0, lambda: _show_cdn_error_gui(error_title, error_detail))

def _show_cdn_error_gui(error_title, error_detail):
    err_win = tk.Toplevel(root)
    err_win.title("🚨 系統診斷中心")
    err_win.geometry(f"680x540+{(root.winfo_screenwidth()-680)//2}+{(root.winfo_screenheight()-540)//2}")
    err_win.configure(bg="#181A1F")
    set_dark_title_bar(err_win)

    top_banner = tk.Frame(err_win, bg="#E06C75", height=50)
    top_banner.pack(fill="x")
    tk.Label(top_banner, text="⚠️ 執行異常報告", font=("Microsoft JhengHei", sf(12), "bold"), fg="#FFFFFF", bg="#E06C75").pack(pady=12)

    content_frame = tk.Frame(err_win, bg="#181A1F", padx=20, pady=15)
    content_frame.pack(fill="both", expand=True)

    tk.Label(content_frame, text=f"錯誤類型：{error_title}", font=("Microsoft JhengHei", sf(11), "bold"), fg="#E5C07B", bg="#181A1F").pack(anchor="w", pady=(0, 5))
    
    log_box = scrolledtext.ScrolledText(content_frame, height=8, font=("Consolas", sf(10)), bg="#21252B", fg="#ABB2BF", wrap="word")
    log_box.pack(fill="x", pady=5)
    log_box.insert(tk.END, f"[Version: {CURRENT_VERSION}]\n[Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}]\n\n{error_detail}")
    log_box.config(state="disabled")

    btn_frame = tk.Frame(content_frame, bg="#181A1F")
    btn_frame.pack(fill="x", pady=(10, 0))

    def copy_error_log():
        pyperclip.copy(f"--- Bug Report ---\nVersion: {CURRENT_VERSION}\nError: {error_title}\nDetail:\n{error_detail}")
        messagebox.showinfo("成功", "錯誤日誌已複製到剪貼簿！", parent=err_win)

    tk.Button(btn_frame, text="📋 複製錯誤日誌", command=copy_error_log, bg="#4B5263", fg="white", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=12, pady=6).pack(side="left")
    tk.Button(btn_frame, text="💬 開啟 Discord 私訊作者", command=open_discord_profile, bg="#5865F2", fg="white", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=12, pady=6).pack(side="left", padx=6)
    tk.Button(btn_frame, text="關閉視窗", command=err_win.destroy, bg="#E06C75", fg="white", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=12, pady=6).pack(side="right")
    err_win.bind("<Escape>", lambda e: err_win.destroy())

def release_mod_keys():
    user32 = ctypes.windll.user32
    for k in (0x12, 0x10, 0x11): user32.keybd_event(k, 0, 2, 0)

def send_paste():
    release_mod_keys()
    time.sleep(0.02)
    ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x56, 0, 0, 0)
    time.sleep(0.02)
    ctypes.windll.user32.keybd_event(0x56, 0, 2, 0)
    ctypes.windll.user32.keybd_event(0x11, 0, 2, 0)

def send_copy():
    user32 = ctypes.windll.user32
    while user32.GetAsyncKeyState(0x12) & 0x8000: time.sleep(0.02)
    release_mod_keys()
    time.sleep(0.1)
    user32.keybd_event(0x11, 0, 0, 0)
    user32.keybd_event(0x43, 0, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(0x43, 0, 2, 0)
    user32.keybd_event(0x11, 0, 2, 0)

def toggle_chat_panel(): root.after(0, _toggle_chat_panel_main)

def _toggle_chat_panel_main():
    global chat_panel_win
    if not GROQ_API_KEY: prompt_api_key_gui(); return
    if chat_panel_win is not None:
        try: chat_panel_win.destroy()
        except Exception: pass
        chat_panel_win = None; return

    theme = get_theme()
    win = tk.Toplevel(root)
    win.title(f"Groq AI 實時互動對話中心 ({CURRENT_VERSION})")
    win.geometry(f"720x760+{(root.winfo_screenwidth()-720)//2}+{(root.winfo_screenheight()-760)//2}")
    win.configure(bg=theme["card_bg"])
    set_dark_title_bar(win)

    header_frame = tk.Frame(win, bg=theme["card_bg"])
    header_frame.pack(fill="x", padx=16, pady=(14, 8))
    tk.Label(header_frame, text="💬 Groq AI 實時對話 🌐", font=("Microsoft JhengHei", sf(13), "bold"), fg=theme["accent"], bg=theme["card_bg"]).pack(side="left")

    def clear_chat_memory():
        global spotlight_history
        spotlight_history = [{"role": "system", "content": get_system_prompt()}]
        chat_box.config(state="normal"); chat_box.delete("1.0", tk.END); chat_box.insert(tk.END, "系統：對話紀錄已重置。\n\n"); chat_box.config(state="disabled")
        set_status("🧹 對話紀錄已清空", "#98C379"); root.after(1500, hide_status)

    tk.Button(header_frame, text="清空對話紀錄", command=clear_chat_memory, bg="#E06C75", fg="white", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=8, pady=3).pack(side="right")

    chat_box = scrolledtext.ScrolledText(win, font=("Microsoft JhengHei", sf(11)), wrap="word", bg=theme["inner_bg"], fg=theme["widget_fg"], padx=8, pady=8)
    chat_box.pack(fill="both", expand=True, padx=16, pady=4)
    
    for msg in spotlight_history:
        if msg.get("role") == "user": chat_box.insert(tk.END, f"👤 你：\n{msg.get('content')}\n\n")
        elif msg.get("role") == "assistant" and msg.get("content"): chat_box.insert(tk.END, f"🤖 AI 助理：\n{msg.get('content')}\n\n")
    chat_box.config(state="disabled"); chat_box.see(tk.END)

    status_tip = tk.Label(win, text="💡 提示：已整合專業 Tavily 實時搜尋，精準掌握人物背景與時事新聞。", font=("Microsoft JhengHei", sf(10)), fg="#98C379", bg=theme["card_bg"])
    status_tip.pack(anchor="w", padx=16, pady=(2, 0))

    input_frame = tk.Frame(win, bg=theme["card_bg"])
    input_frame.pack(fill="x", padx=16, pady=(8, 14))
    
    entry = tk.Entry(input_frame, font=("Microsoft JhengHei", sf(12)), bg=theme["inner_bg"], fg=theme["widget_fg"], insertbackground=theme["widget_fg"])
    entry.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=5)
    entry.insert(0, "輸入對話、問題或請 AI 寫程式碼...")
    entry.selection_range(0, tk.END)
    entry.bind("<FocusIn>", lambda e: entry.delete(0, tk.END) if entry.get().startswith("輸入對話") else None)

    def execute_chat_input(event=None):
        global is_processing
        if is_processing:
            set_status("⏳ AI 思考中，請稍候...", "#E5C07B")
            root.after(1500, hide_status)
            return

        text = entry.get().strip()
        if not text or text.startswith("輸入對話"): return
        entry.delete(0, tk.END)
        
        chat_box.config(state="normal")
        chat_box.insert(tk.END, f"👤 你：\n{text}\n\n🤖 AI 助理：\n")
        chat_box.config(state="disabled")
        chat_box.see(tk.END)
        
        threading.Thread(target=process_chat_logic, args=(text, chat_box), daemon=True).start()

    entry.bind("<Return>", execute_chat_input)
    tk.Button(input_frame, text="傳送", command=execute_chat_input, bg="#4CAF50", fg="white", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=14, pady=5).pack(side="left", padx=(0, 4))

    panel_recording = False
    panel_stream = None
    panel_frames = []

    def toggle_panel_voice():
        nonlocal panel_recording, panel_stream, panel_frames
        if not panel_recording:
            panel_frames = []
            try:
                def cb(indata, f_cnt, t_info, st):
                    if panel_recording: panel_frames.append(indata.copy())
                panel_stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=cb)
                panel_stream.start()
                panel_recording = True
                voice_btn.config(text="🛑 停止並送出", bg="#E06C75", fg="white")
                set_status("🔴 [對話錄音中] 請說話...", "#E06C75")
                winsound.Beep(800, 100)
            except Exception:
                panel_recording = False; panel_stream = None
                set_status("⚠️ 麥克風啟動失敗", "#E5C07B"); root.after(1500, hide_status)
        else:
            panel_recording = False
            voice_btn.config(text="🎙️ 語音輸入", bg="#61AFEF", fg="#21252B")
            try:
                if panel_stream: panel_stream.stop(); panel_stream.close()
            except Exception: pass
            panel_stream = None
            winsound.Beep(600, 120)

            if len(panel_frames) > 0:
                audio_data = np.concatenate(panel_frames, axis=0)
                set_status("⚡ 語音轉文字中...", "#61AFEF")
                def process_worker():
                    try:
                        wav_io = io.BytesIO()
                        write(wav_io, SAMPLE_RATE, (audio_data * 32767).astype(np.int16))
                        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
                        files = {"file": ("panel_voice.wav", wav_io.getvalue(), "audio/wav")}
                        resp = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data={"model": "whisper-large-v3", "language": "zh"}, timeout=12)
                        if resp.status_code == 200:
                            txt = to_tw_trad(resp.json().get("text", "").strip())
                            if txt: root.after(0, lambda: [entry.delete(0, tk.END), entry.insert(0, txt), execute_chat_input()])
                        set_status("✨ 語音辨識完成", "#98C379")
                    except Exception:
                        set_status("⚠️ 語音辨識失敗", "#E5C07B")
                    finally:
                        root.after(1500, hide_status)
                threading.Thread(target=process_worker, daemon=True).start()

    voice_btn = tk.Button(input_frame, text="🎙️ 語音輸入", command=toggle_panel_voice, bg="#61AFEF", fg="#21252B", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=10, pady=5)
    voice_btn.pack(side="left")

    win.protocol("WM_DELETE_WINDOW", lambda: [win.destroy(), globals().update(chat_panel_win=None)])
    win.bind("<Escape>", lambda e: [win.destroy(), globals().update(chat_panel_win=None)])
    chat_panel_win = win

def process_chat_logic(query, chat_box):
    global spotlight_history, is_processing
    is_processing = True
    set_status("🌐 檢索 Tavily 網路真實資料與 AI 推理中...", "#C678DD")
    
    try:
        web_context = get_web_search_context(query)

        spotlight_history.append({"role": "user", "content": query})
        sanitize_spotlight_history()

        api_messages = [dict(m) for m in spotlight_history]
        if web_context and api_messages and api_messages[-1]["role"] == "user":
            api_messages[-1]["content"] = f"【實時網路權威檢索資料】：\n{web_context}\n\n【使用者提問】：\n{query}"

        candidate_models = [MODEL_CHAT, "qwen-2.5-32b", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "deepseek-r1-distill-llama-70b"]
        unique_candidate_models = []
        for m in candidate_models:
            if m not in unique_candidate_models: unique_candidate_models.append(m)

        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        success = False
        last_error_text = ""

        for model_name in unique_candidate_models:
            payload = {
                "model": model_name,
                "messages": api_messages,
                "temperature": 0.2,
                "stream": True
            }

            url = "https://api.groq.com/openai/v1/chat/completions"
            resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=18)

            full_reply = ""
            if resp.status_code == 200:
                in_think = False
                for line in resp.iter_lines():
                    if line:
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data: "):
                            data_content = line_str[6:].strip()
                            if data_content == "[DONE]": break
                            try:
                                chunk_json = json.loads(data_content)
                                delta = chunk_json["choices"][0]["delta"].get("content", "")
                                if delta:
                                    if "<think>" in delta: in_think = True; continue
                                    if "</think>" in delta: in_think = False; continue
                                    if not in_think:
                                        chunk_trad = to_tw_trad(delta)
                                        full_reply += chunk_trad
                                        def append_chunk(c=chunk_trad):
                                            if chat_box and chat_box.winfo_exists():
                                                chat_box.config(state="normal")
                                                chat_box.insert(tk.END, c)
                                                chat_box.config(state="disabled")
                                                chat_box.see(tk.END)
                                        if root: root.after(0, append_chunk)
                            except Exception: pass
                
                def finalize_success():
                    if chat_box and chat_box.winfo_exists():
                        chat_box.config(state="normal")
                        chat_box.insert(tk.END, "\n\n")
                        chat_box.config(state="disabled")
                        chat_box.see(tk.END)
                if root: root.after(0, finalize_success)

                if full_reply.strip():
                    spotlight_history.append({"role": "assistant", "content": full_reply})
                    add_history_entry("AI 實時對話", query, full_reply)
                success = True
                break
            else:
                last_error_text = f"HTTP {resp.status_code}: {resp.text[:150]}"
                continue

        if not success:
            err_msg = f"❌ API 請求失敗：{last_error_text}\n（請稍後重試，或切換模型）\n\n"
            def print_err():
                if chat_box and chat_box.winfo_exists():
                    chat_box.config(state="normal")
                    chat_box.insert(tk.END, err_msg)
                    chat_box.config(state="disabled")
                    chat_box.see(tk.END)
            if root: root.after(0, print_err)
            if spotlight_history and spotlight_history[-1]["role"] == "user":
                spotlight_history.pop()

    except Exception as e:
        err_msg = f"❌ 系統連線例外錯誤：{str(e)}\n\n"
        def print_exc():
            if chat_box and chat_box.winfo_exists():
                chat_box.config(state="normal")
                chat_box.insert(tk.END, err_msg)
                chat_box.config(state="disabled")
                chat_box.see(tk.END)
        if root: root.after(0, print_exc)
        if spotlight_history and spotlight_history[-1]["role"] == "user":
            spotlight_history.pop()
    finally:
        is_processing = False
        hide_status()

def toggle_auto_clipboard():
    global auto_clipboard_enabled, last_clipboard_text
    auto_clipboard_enabled = not auto_clipboard_enabled
    if auto_clipboard_enabled:
        try: last_clipboard_text = pyperclip.paste().strip()
        except Exception: last_clipboard_text = ""
        set_status("📋 自動剪貼簿翻譯：已開啟", "#56B6C2"); winsound.Beep(1000, 100)
    else:
        set_status("📋 自動剪貼簿翻譯：已關閉", "#E5C07B"); winsound.Beep(500, 100)
    root.after(1500, hide_status)
    root.after(0, update_clip_button_appearance)

def update_clip_button_appearance():
    global clip_btn_ref
    if clip_btn_ref is not None:
        try:
            theme = get_theme()
            clip_btn_ref.config(text="📋自動" if auto_clipboard_enabled else "📋關閉", bg=theme["accent"] if auto_clipboard_enabled else theme["btn_bg"])
        except Exception: pass

def clipboard_monitor_loop():
    global last_clipboard_text
    while True:
        time.sleep(0.8)
        if not auto_clipboard_enabled or is_paused or is_processing or not GROQ_API_KEY: continue
        try:
            current_text = pyperclip.paste().strip()
            if current_text and current_text != last_clipboard_text:
                if len(current_text) < 2000:
                    last_clipboard_text = current_text
                    threading.Thread(target=process_auto_clipboard, args=(current_text,), daemon=True).start()
        except Exception: pass

def process_auto_clipboard(text):
    global last_clipboard_text, is_processing
    is_processing = True
    set_status("📋 背景翻譯中...", "#56B6C2")
    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        sys_prompt = "將輸入文字精準翻譯為流暢繁體中文。只需輸出翻譯結果。"
        payload = {"model": MODEL_SELECTION, "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": text}], "temperature": 0.2}
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            raw_content = resp.json()["choices"][0]["message"]["content"].strip()
            if "</think>" in raw_content: raw_content = raw_content.split("</think>")[-1].strip()
            translated = to_tw_trad(raw_content)
            if translated:
                pyperclip.copy(translated); last_clipboard_text = translated
                add_history_entry("自動剪貼簿翻譯", text, translated)
                set_status("📋 翻譯完成並已覆蓋剪貼簿", "#98C379"); winsound.Beep(1200, 80)
                root.after(1500, hide_status)
        else:
            trigger_cdn_error_modal(f"自動剪貼簿 API 錯誤 HTTP {resp.status_code}", resp.text[:200])
    except Exception:
        pass
    finally: is_processing = False

# 🌟 iPhone 風格懸浮球 (AssistiveTouch) 實現
def toggle_floating_ball(): root.after(0, _toggle_floating_ball_main)

def refresh_floating_widget():
    global floating_ball_win
    if floating_ball_win is not None:
        try: floating_ball_win.destroy()
        except Exception: pass
        floating_ball_win = None
        _toggle_floating_ball_main()

def close_ball_menu():
    global ball_menu_win
    if ball_menu_win is not None:
        try: ball_menu_win.destroy()
        except Exception: pass
        ball_menu_win = None

def _toggle_floating_ball_main():
    global floating_ball_win
    close_ball_menu()
    if floating_ball_win is not None:
        try: floating_ball_win.destroy()
        except Exception: pass
        floating_ball_win = None
        set_status("🥷 懸浮球已隱藏", "#E5C07B"); root.after(1500, hide_status)
    else:
        theme = get_theme()
        ball_win = tk.Toplevel(root)
        ball_win.title("Groq Floating Ball")
        ball_win.overrideredirect(True)
        ball_win.attributes("-topmost", True)
        ball_win.attributes("-alpha", 0.35)
        
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        ball_size = 42
        ball_win.geometry(f"{ball_size}x{ball_size}+{sw - 70}+{sh - 120}")
        ball_win.configure(bg="#000001")
        ball_win.wm_attributes("-transparentcolor", "#000001")

        canvas = tk.Canvas(ball_win, width=ball_size, height=ball_size, bg="#000001", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        canvas.create_oval(2, 2, ball_size-2, ball_size-2, fill=theme["accent"], outline="#FFFFFF", width=1.5)
        canvas.create_text(ball_size//2, ball_size//2, text="🤖", font=("Segoe UI Emoji", 14))

        ball_win.bind("<Enter>", lambda e: ball_win.attributes("-alpha", 0.90))
        ball_win.bind("<Leave>", lambda e: ball_win.attributes("-alpha", 0.35))
        
        drag_data = {"x": 0, "y": 0, "moved": False}

        def on_press(e):
            drag_data["x"] = e.x
            drag_data["y"] = e.y
            drag_data["moved"] = False

        def on_drag(e):
            if abs(e.x - drag_data["x"]) > 3 or abs(e.y - drag_data["y"]) > 3:
                drag_data["moved"] = True
            nx = ball_win.winfo_x() + e.x - drag_data["x"]
            ny = ball_win.winfo_y() + e.y - drag_data["y"]
            ball_win.geometry(f"+{nx}+{ny}")
            close_ball_menu()

        def on_release(e):
            if not drag_data["moved"]:
                toggle_ball_menu(ball_win)

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)

        floating_ball_win = ball_win
        set_status(f"✨ {CURRENT_VERSION} Groq AI 懸浮球已啟動", "#98C379")
        root.after(1500, hide_status)

def toggle_ball_menu(ball_win):
    global ball_menu_win, clip_btn_ref
    if ball_menu_win is not None:
        close_ball_menu()
        return

    theme = get_theme()
    menu_win = tk.Toplevel(root)
    menu_win.title("Groq Ball Menu")
    menu_win.overrideredirect(True)
    menu_win.attributes("-topmost", True)
    
    bx, by = ball_win.winfo_x(), ball_win.winfo_y()
    m_width, m_height = 430, 32
    
    mx = bx - m_width - 8 if bx - m_width - 8 > 10 else bx + 50
    my = by + 5

    menu_win.geometry(f"{m_width}x{m_height}+{mx}+{my}")
    menu_win.configure(bg=theme["widget_bg"])

    btn_frame = tk.Frame(menu_win, bg=theme["widget_bg"])
    btn_frame.pack(fill="both", expand=True, padx=2, pady=2)

    def exec_and_close(cmd):
        close_ball_menu()
        cmd()

    def add_menu_btn(text, cmd, bg_col):
        b = tk.Button(btn_frame, text=text, command=lambda: exec_and_close(cmd), bg=bg_col, fg="white", font=("Microsoft JhengHei", 9, "bold"), relief="flat", bd=0, padx=2, pady=0)
        b.pack(side="left", padx=1, expand=True, fill="both")
        return b

    add_menu_btn("💬對話", toggle_chat_panel, theme["accent"])
    add_menu_btn("🔍翻譯", lambda: threading.Thread(target=process_selection, args=("translate",), daemon=True).start(), "#98C379")
    add_menu_btn("✨潤飾", lambda: threading.Thread(target=process_selection, args=("ai_refine",), daemon=True).start(), "#C678DD")
    clip_btn_ref = add_menu_btn("📋自動" if auto_clipboard_enabled else "📋關閉", toggle_auto_clipboard, theme["accent"] if auto_clipboard_enabled else theme["btn_bg"])
    add_menu_btn("📜歷史", lambda: prompt_api_key_gui(default_tab_idx=3), "#D19A66")
    add_menu_btn("🛡️防護", toggle_pause_mode, "#E5C07B")
    add_menu_btn("🔄更新", lambda: check_for_updates(manual=True), "#56B6C2")
    add_menu_btn("⚙️", prompt_api_key_gui, theme["btn_bg"])
    add_menu_btn("✕", lambda: None, "#E06C75")

    ball_menu_win = menu_win

def create_tray_image():
    image = Image.new('RGB', (64, 64), color=(33, 37, 43))
    dc = ImageDraw.Draw(image); dc.rectangle((16, 16, 48, 48), fill=(97, 175, 239))
    return image

def setup_system_tray():
    global tray_icon
    if not TRAY_AVAILABLE: return
    menu = pystray.Menu(
        pystray.MenuItem("⚙️ 設定中心 & API 設定", lambda icon, item: root.after(0, prompt_api_key_gui)),
        pystray.MenuItem("💬 開啟 AI 實時對話", lambda icon, item: toggle_chat_panel()),
        pystray.MenuItem("🔄 檢查雲端軟體更新", lambda icon, item: check_for_updates(manual=True)),
        pystray.MenuItem("📌 切換懸浮球顯示/隱藏", lambda icon, item: toggle_floating_ball()),
        pystray.MenuItem("👋 結束程式", lambda icon, item: exit_program())
    )
    tray_icon = pystray.Icon("GroqVoiceTool", create_tray_image(), "Groq AI 助理", menu)
    tray_icon.run()

def toggle_pause_mode():
    global is_paused
    is_paused = not is_paused
    if is_paused: set_status("⏸️ 助理已暫停", "#E5C07B")
    else: set_status("▶️ 助理已恢復", "#98C379"); root.after(1500, hide_status)

class SnippingTool:
    def __init__(self, mode="translate"):
        self.mode = mode
        self.full_img = ImageGrab.grab(all_screens=True)
        
        self.snip_win = tk.Toplevel(root)
        self.snip_win.attributes("-fullscreen", True)
        self.snip_win.attributes("-alpha", 0.3)
        self.snip_win.attributes("-topmost", True)
        self.snip_win.config(cursor="cross")
        
        self.canvas = tk.Canvas(self.snip_win, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.start_x = self.start_y = self.rect = None
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.snip_win.bind("<Escape>", lambda e: self.snip_win.destroy())

    def on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2, fill="white")

    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        if self.start_x is None or self.start_y is None: return
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        
        sw = self.snip_win.winfo_screenwidth()
        sh = self.snip_win.winfo_screenheight()
        self.snip_win.destroy()
        
        rx1, rx2 = min(x1, x2), max(x1, x2)
        ry1, ry2 = min(y1, y2), max(y1, y2)
        
        if (rx2 - rx1) > 5 and (ry2 - ry1) > 5:
            scale_x = self.full_img.width / sw
            scale_y = self.full_img.height / sh
            pad = 15
            x_min = max(0, int(rx1 * scale_x) - pad)
            y_min = max(0, int(ry1 * scale_y) - pad)
            x_max = min(self.full_img.width, int(rx2 * scale_x) + pad)
            y_max = min(self.full_img.height, int(ry2 * scale_y) + pad)
            
            crop_box = (x_min, y_min, x_max, y_max)
            cropped_img = self.full_img.crop(crop_box)
            root.after(100, lambda: threading.Thread(target=process_screenshot, args=(cropped_img,), daemon=True).start())

def process_screenshot(img):
    global is_processing
    if not GROQ_API_KEY: prompt_api_key_gui(); return

    is_processing = True
    set_status("🖼️ Windows 內建 OCR 辨識中...", "#61AFEF")
    try:
        temp_img_path = os.path.abspath(os.path.join(SCREENSHOT_DIR, "temp_ocr.png"))
        img.save(temp_img_path)

        ps_script = f"""
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        Add-Type -AssemblyName System.Runtime.WindowsRuntime
        $null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
        $null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
        $null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Foundation, ContentType = WindowsRuntime]
        $null = [Windows.Storage.Streams.RandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]

        $getAwaiterBaseMethod = [WindowsRuntimeSystemExtensions].GetMember('GetAwaiter', 'Method', 'Public,Static') | Where-Object {{ $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }} | Select-Object -First 1
        function Await($AsyncTask, $As) {{
            return $getAwaiterBaseMethod.MakeGenericMethod($As).Invoke($null, @($AsyncTask)).GetResult()
        }}

        $ocrEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
        if ($null -eq $ocrEngine) {{ exit 1 }}

        $storageFile = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync('{temp_img_path}')) ([Windows.Storage.StorageFile])
        $fileStream = Await ($storageFile.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $bitmapDecoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($fileStream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $softwareBitmap = Await ($bitmapDecoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $ocrResult = Await ($ocrEngine.RecognizeAsync($softwareBitmap)) ([Windows.Media.Ocr.OcrResult])

        $ocrResult.Text
        """

        ps_file_path = os.path.abspath(os.path.join(SCREENSHOT_DIR, "ocr_script.ps1"))
        with open(ps_file_path, "w", encoding="utf-8") as f: f.write(ps_script)

        proc = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_file_path], capture_output=True, text=True, encoding="utf-8", errors="ignore", creationflags=subprocess.CREATE_NO_WINDOW)
        
        extracted_text = (proc.stdout or "").strip()
        if proc.returncode != 0 or not extracted_text:
            show_ai_window("截圖 OCR", "（畫面區域）", "⚠️ 未偵測到清晰文字。")
            return

        set_status("✨ Groq AI 繁中翻譯中...", "#C678DD")
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": MODEL_SELECTION, "messages": [{"role": "system", "content": "請將以下文字翻譯為繁體中文。"}, {"role": "user", "content": f"請翻譯：\n{extracted_text}"}], "temperature": 0.2}
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=12)
        if resp.status_code == 200:
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            if "</think>" in raw: raw = raw.split("</think>")[-1].strip()
            res = to_tw_trad(raw)
            add_history_entry("截圖 OCR 翻譯", extracted_text, res)
            show_ai_window("截圖 OCR 翻譯", f"【辨識原文】\n{extracted_text}", res)
        else:
            trigger_cdn_error_modal(f"OCR 翻譯 API 錯誤 HTTP {resp.status_code}", resp.text[:200])
    except Exception as e:
        trigger_cdn_error_modal("截圖處理例外錯誤", traceback.format_exc())
    finally:
        is_processing = False
        hide_status()

def process_selection(mode):
    global is_processing
    if not GROQ_API_KEY: prompt_api_key_gui(); return

    is_processing = True
    set_status("📋 取得選取文字中...", "#61AFEF")
    try:
        send_copy()
        time.sleep(0.15)
        text = pyperclip.paste().strip()
        if not text:
            set_status("⚠️ 未選取任何文字", "#E5C07B")
            root.after(1500, hide_status); return

        set_status("✨ AI 處理選取文字中...", "#C678DD")
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        if mode == "translate": sys_prompt = "請將以下文字精準翻譯為流暢繁體中文。"; title = "劃詞翻譯"
        elif mode == "ai_refine": sys_prompt = "請將以下文字進行潤飾與精簡摘要。"; title = "AI 潤飾摘要"
        elif mode == "custom_1": sys_prompt = CUSTOM_PROMPT_1; title = "自訂提示 1"
        elif mode == "custom_2": sys_prompt = CUSTOM_PROMPT_2; title = "自訂提示 2"
        elif mode == "replace": sys_prompt = "請修正語法並優化以下文字，直接輸出優化後的繁體中文。"; title = "劃詞原地替換"
        else: sys_prompt = "請優化以下文字。"; title = "AI 處理"

        payload = {"model": MODEL_SELECTION, "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": text}], "temperature": 0.2}
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=12)
        if resp.status_code == 200:
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            if "</think>" in raw: raw = raw.split("</think>")[-1].strip()
            res = to_tw_trad(raw)
            
            if mode == "replace":
                pyperclip.copy(res); time.sleep(0.05); send_paste()
                set_status("✨ 替換完成並已貼上！", "#98C379")
            else:
                add_history_entry(title, text, res)
                show_ai_window(title, text, res)
        else:
            trigger_cdn_error_modal(f"劃詞處理 API 錯誤 HTTP {resp.status_code}", resp.text[:200])
    except Exception as e:
        trigger_cdn_error_modal("劃詞處理例外錯誤", traceback.format_exc())
    finally:
        is_processing = False
        hide_status()

def process_tts():
    if not TTS_AVAILABLE:
        set_status("⚠️ 未安裝 pyttsx3 語音套件", "#E5C07B")
        root.after(1500, hide_status); return
    try:
        send_copy()
        time.sleep(0.15)
        text = pyperclip.paste().strip()
        if not text: return
        
        def tts_worker():
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            
        threading.Thread(target=tts_worker, daemon=True).start()
        set_status("🔊 正在朗讀文字...", "#98C379")
        root.after(1500, hide_status)
    except Exception as e:
        trigger_cdn_error_modal("TTS 語音朗讀例外", traceback.format_exc())

unified_center_win = None
is_settings_locked = True

def prompt_api_key_gui(default_tab_idx=0):
    global unified_center_win, GROQ_API_KEY, TAVILY_API_KEY, CUSTOM_PROMPT_1, CUSTOM_PROMPT_2, CURRENT_THEME_NAME, FONT_SCALE, MODEL_VOICE, MODEL_CHAT, MODEL_SELECTION, is_settings_locked
    if unified_center_win is not None:
        try:
            unified_center_win.deiconify()
            unified_center_win.lift()
            notebook_ref = getattr(unified_center_win, 'notebook_ref', None)
            if notebook_ref and default_tab_idx < len(notebook_ref.tabs()):
                notebook_ref.select(default_tab_idx)
            return
        except Exception: pass
        unified_center_win = None

    theme = get_theme()
    win = tk.Toplevel(root)
    win.title(f"🚀 Groq AI 控制中心 ({CURRENT_VERSION})")
    
    win.geometry(f"920x820+{(root.winfo_screenwidth()-920)//2}+{(root.winfo_screenheight()-820)//2}")
    win.configure(bg=theme["card_bg"])

    header = tk.Frame(win, bg=theme["card_bg"])
    header.pack(fill="x", padx=20, pady=(12, 6))
    tk.Label(header, text="⚙️ Groq AI 系統控制中心", font=("Microsoft JhengHei", sf(14), "bold"), fg=theme["accent"], bg=theme["card_bg"]).pack(side="left")
    
    tk.Button(header, text="🔄 檢查雲端軟體更新", command=lambda: check_for_updates(manual=True), bg="#56B6C2", fg="white", font=("Microsoft JhengHei", sf(9), "bold"), relief="flat", padx=8, pady=2).pack(side="right", padx=(8, 0))
    tk.Button(header, text="💬 開啟 Discord 私訊作者", command=open_discord_profile, bg="#5865F2", fg="white", font=("Microsoft JhengHei", sf(9), "bold"), relief="flat", padx=8, pady=2).pack(side="right", padx=(8, 0))
    tk.Label(header, text=f"版本: {CURRENT_VERSION}", font=("Consolas", sf(10), "bold"), fg="#98C379", bg=theme["card_bg"]).pack(side="right")

    style = ttk.Style()
    style.theme_use('default')
    style.configure("TNotebook", background=theme["card_bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=theme["btn_bg"], foreground=theme["widget_fg"], font=("Microsoft JhengHei", sf(10), "bold"), padding=[10, 6])
    style.map("TNotebook.Tab", background=[("selected", theme["accent"])], foreground=[("selected", "#101820")])

    notebook = ttk.Notebook(win)
    notebook.pack(fill="both", expand=True, padx=20, pady=4)
    win.notebook_ref = notebook

    def create_scrollable_tab(tab_name):
        container = tk.Frame(notebook, bg=theme["inner_bg"])
        canvas = tk.Canvas(container, bg=theme["inner_bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=theme["inner_bg"], padx=15, pady=15)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.pack(side="left", fill="both", expand=True); scrollbar.pack(side="right", fill="y")
        notebook.add(container, text=tab_name)
        return scrollable_frame

    def add_feedback_card(parent_frame):
        fb_card = tk.Frame(parent_frame, bg=theme["widget_bg"], bd=1, relief="solid", padx=12, pady=10)
        fb_card.pack(fill="x", pady=(10, 5))

        tk.Label(fb_card, text="💬 使用者建議與功能反饋管道", font=("Microsoft JhengHei", sf(10), "bold"), fg="#61AFEF", bg=theme["widget_bg"]).pack(anchor="w")
        tk.Label(
            fb_card, 
            text="若您對程式有任何最佳化建議、新功能想法或使用疑難，歡迎隨時點擊下方按鈕直接跳轉至 Discord 私訊我！", 
            font=("Microsoft JhengHei", sf(10)), 
            fg=theme["widget_fg"], 
            bg=theme["widget_bg"], 
            justify="left", 
            wraplength=760
        ).pack(anchor="w", pady=(3, 6))

        fb_btns = tk.Frame(fb_card, bg=theme["widget_bg"])
        fb_btns.pack(anchor="w")

        tk.Button(fb_btns, text="💬 直接開啟 Discord 私訊作者", command=open_discord_profile, bg="#5865F2", fg="white", font=("Microsoft JhengHei", sf(9), "bold"), relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 6))
        tk.Button(fb_btns, text=f"📋 複製帳號 ({DISCORD_USERNAME})", command=lambda: copy_discord_username(win), bg=theme["btn_bg"], fg=theme["widget_fg"], font=("Microsoft JhengHei", sf(9), "bold"), relief="flat", padx=10, pady=4).pack(side="left")

    # 📌 1. 新手指南
    tab_guide = create_scrollable_tab("📖 新手指南")
    add_feedback_card(tab_guide)
    
    tk.Label(tab_guide, text="⌨️ 全系統快捷熱鍵操作對照：", font=("Microsoft JhengHei", sf(11), "bold"), fg="#98C379", bg=theme["inner_bg"]).pack(anchor="w", pady=(10, 8))
    for title, hk, desc in [
        ("💬 AI 實時對話面板", "Alt + Q", "喚起 AI 聊天視窗，支援發問、寫程式碼與即時 Tavily 網路檢索。"),
        ("🎙️ 語音聽寫輸入", "Alt + S", "錄音辨識並由 AI 精修錯字與全形標點後自動貼上。"),
        ("🔠 語音中譯英", "Alt + Shift + S", "口述中文直接輸出標準美式英文。"),
        ("🔍 劃詞翻譯", "Alt + C", "滑鼠選取外文即時彈窗顯示流暢繁中翻譯。"),
        ("✏️ 劃詞替換", "Alt + Shift + C", "選取文字直接由 AI 改寫並原地覆蓋替換。"),
        ("✨ AI 潤飾摘要", "Alt + A", "長篇文章重點整理或文案潤飾。"),
        ("🖼️ 截圖 OCR 辨識", "Alt + X", "框選螢幕區域，透過 Windows 原生 OCR 引擎辨識並翻譯。"),
        ("🎯 自訂提示 1 / 2", "Alt + 1 / Alt + 2", "執行設定好的自訂 Prompt 任務。"),
        ("⏸️ 防誤觸暫停", "Alt + Shift + P", "一鍵暫停或恢復所有熱鍵與背景監聽。")
    ]:
        card = tk.Frame(tab_guide, bg=theme["widget_bg"], bd=1, relief="solid", padx=12, pady=8)
        card.pack(fill="x", expand=True, pady=4)
        head = tk.Frame(card, bg=theme["widget_bg"]); head.pack(fill="x")
        tk.Label(head, text=title, font=("Microsoft JhengHei", sf(10), "bold"), fg=theme["accent"], bg=theme["widget_bg"]).pack(side="left")
        tk.Label(head, text=f"[{hk}]", font=("Consolas", sf(10), "bold"), fg="#E5C07B", bg=theme["widget_bg"]).pack(side="right")
        tk.Label(card, text=desc, font=("Microsoft JhengHei", sf(10)), fg=theme["widget_fg"], bg=theme["widget_bg"], justify="left").pack(anchor="w", pady=(3, 0))

    # 📌 2. 使用小技巧
    tab_tips = create_scrollable_tab("💡 使用小技巧")
    tk.Label(tab_tips, text="🚀 幫助您快速上手與理解核心功能的操作指南：", font=("Microsoft JhengHei", sf(11), "bold"), fg="#61AFEF", bg=theme["inner_bg"]).pack(anchor="w", pady=(2, 8))
    for t_title, t_desc in [
        ("📢 動態遠端 API 廣播系統", "軟體支援雲端推播廣播！系統能即時傳送重要公告、維護通知與手動升級引導至您的螢幕。"),
        ("🔄 內建自動熱更新機制", "程式啟動時會在背景發送 API 請求自動檢查最新版本，點擊「一鍵升級」即可自動完成軟體替換！"),
        ("💬 AssistiveTouch 懸浮小球設計", "類似 iPhone 的小球介面，平時完全透明省空間，點擊即可彈出全功能選單！"),
        ("💬 Discord 意見與建議直通車", "覺得軟體缺了什麼功能？點擊「直接開啟 Discord 私訊作者」即可一鍵開啟私訊視窗傳送建議！")
    ]:
        card = tk.Frame(tab_tips, bg=theme["widget_bg"], bd=1, relief="solid", padx=12, pady=10)
        card.pack(fill="x", expand=True, pady=6)
        tk.Label(card, text=t_title, font=("Microsoft JhengHei", sf(10), "bold"), fg=theme["accent"], bg=theme["widget_bg"]).pack(anchor="w")
        tk.Label(card, text=t_desc, font=("Microsoft JhengHei", sf(10)), fg=theme["widget_fg"], bg=theme["widget_bg"], justify="left", wraplength=760).pack(anchor="w", pady=(4, 0))

    # 📌 3. 版本對比
    tab_ver = create_scrollable_tab("📑 版本對比")
    ver_card = tk.Frame(tab_ver, bg=theme["widget_bg"], bd=1, relief="solid", padx=12, pady=10)
    ver_card.pack(fill="x", pady=(0, 10))
    tk.Label(ver_card, text=f"📌 本地電腦先前安裝紀錄版本：{LOCAL_PREVIOUS_VERSION}", font=("Microsoft JhengHei", sf(10), "bold"), fg="#E06C75", bg=theme["widget_bg"]).pack(anchor="w")
    tk.Label(ver_card, text=f"✨ 當前系統升級執行版本：{CURRENT_VERSION}", font=("Microsoft JhengHei", sf(10), "bold"), fg="#98C379", bg=theme["widget_bg"]).pack(anchor="w", pady=(2, 0))

    tk.Label(tab_ver, text="🔍 相較於您本地電腦的歷史舊版，v7.0.0 帶來的重要改進：", font=("Microsoft JhengHei", sf(10), "bold"), fg=theme["accent"], bg=theme["inner_bg"]).pack(anchor="w", pady=(6, 4))

    diff_items = [
        ("新增「動態遠端推播 API」底層架構", "支援從雲端即時發送 info/warning/force_update 三種等級的公告廣播。", "解決舊版無廣播機制的痛點，隨時向使用者傳遞最新通知。"),
        ("整合底層「自動熱更新」系統", "內建雲端版本比對與背景一鍵覆蓋升級機制，永保最新功能與效能。", "無縫自動更新，使用者無需再手動前往網頁下載新版 exe。"),
        ("全面升級為 iPhone 風格懸浮小球", "引入類似 AssistiveTouch 的極簡小球，點擊彈出選單，點擊功能自動收合。", "極致節省螢幕空間，解決長條選單擋畫面的痛點。")
    ]

    for item_title, item_detail, item_benefit in diff_items:
        card_d = tk.Frame(tab_ver, bg=theme["widget_bg"], bd=1, relief="solid", padx=12, pady=8)
        card_d.pack(fill="x", expand=True, pady=4)
        tk.Label(card_d, text=f"⚡ {item_title}", font=("Microsoft JhengHei", sf(10), "bold"), fg=theme["accent"], bg=theme["widget_bg"]).pack(anchor="w")
        tk.Label(card_d, text=f"說明：{item_detail}", font=("Microsoft JhengHei", sf(10)), fg=theme["widget_fg"], bg=theme["widget_bg"], justify="left", wraplength=760).pack(anchor="w", pady=(2, 1))
        tk.Label(card_d, text=f"效益：{item_benefit}", font=("Microsoft JhengHei", sf(10), "bold"), fg="#98C379", bg=theme["widget_bg"], justify="left", wraplength=760).pack(anchor="w")

    # 📌 4. 歷史紀錄
    tab_hist_page = create_scrollable_tab("📜 歷史紀錄")
    hist_mechanism_card = tk.Frame(tab_hist_page, bg=theme["widget_bg"], bd=1, relief="solid", padx=12, pady=10)
    hist_mechanism_card.pack(fill="x", pady=(0, 10))
    tk.Label(hist_mechanism_card, text="💡 歷史紀錄具體運作機制說明：", font=("Microsoft JhengHei", sf(10), "bold"), fg="#98C379", bg=theme["widget_bg"]).pack(anchor="w")
    mech_text = (
        "• 本地持久化儲存：所有紀錄均自動儲存於您電腦硬碟中的 history.json 檔案，重啟程式不會遺失。\n"
        "• 上限滾動替換 (容量保護)：預設最多保存最新 50 筆紀錄，達上限時會自動淘汰最舊紀錄。\n"
        "• 資料隱私安全：所有紀錄全數保留在您的本機電腦中，不會被上傳至任何第三方雲端伺服器。"
    )
    tk.Label(hist_mechanism_card, text=mech_text, font=("Microsoft JhengHei", sf(10)), fg=theme["widget_fg"], bg=theme["widget_bg"], justify="left", wraplength=760).pack(anchor="w", pady=(3, 0))

    tk.Label(tab_hist_page, text="📜 所有 AI 對話、聽寫校對與劃詞翻譯的歷史紀錄清單：", font=("Microsoft JhengHei", sf(11), "bold"), fg=theme["accent"], bg=theme["inner_bg"]).pack(anchor="w", pady=(2, 6))

    hist_container = tk.Frame(tab_hist_page, bg=theme["inner_bg"])
    hist_container.pack(fill="both", expand=True, pady=5)

    hist_canvas = tk.Canvas(hist_container, bg=theme["inner_bg"], highlightthickness=0)
    hist_scrollbar = ttk.Scrollbar(hist_container, orient="vertical", command=hist_canvas.yview)
    hist_scrollable_frame = tk.Frame(hist_canvas, bg=theme["inner_bg"])
    hist_scrollable_frame.bind("<Configure>", lambda e: hist_canvas.configure(scrollregion=hist_canvas.bbox("all")))
    hist_canvas_window = hist_canvas.create_window((0, 0), window=hist_scrollable_frame, anchor="nw")
    hist_canvas.configure(yscrollcommand=hist_scrollbar.set)
    hist_canvas.bind('<Configure>', lambda e: hist_canvas.itemconfig(hist_canvas_window, width=e.width))
    hist_canvas.pack(side="left", fill="both", expand=True); hist_scrollbar.pack(side="right", fill="y")

    def refresh_history_tab_ui():
        for widget in hist_scrollable_frame.winfo_children(): widget.destroy()
        history_data = load_history()
        if not history_data:
            tk.Label(hist_scrollable_frame, text="（目前尚無任何歷史紀錄）", font=("Microsoft JhengHei", sf(11)), fg=theme["widget_fg"], bg=theme["inner_bg"]).pack(pady=40, padx=20)
        else:
            for idx, item in enumerate(history_data, 1):
                card = tk.Frame(hist_scrollable_frame, bg=theme["widget_bg"], bd=1, relief="solid", padx=10, pady=8)
                card.pack(fill="x", expand=True, padx=4, pady=5)
                tk.Label(card, text=f"📌 #{idx} [{item.get('type')}] - {item.get('time')}", font=("Microsoft JhengHei", sf(10), "bold"), fg=theme["accent"], bg=theme["widget_bg"]).pack(anchor="w")
                if item.get('original'):
                    tk.Label(card, text=f"提問/輸入：{item.get('original')}", font=("Microsoft JhengHei", sf(10)), fg=theme["widget_fg"], bg=theme["widget_bg"], justify="left", wraplength=740).pack(anchor="w", padx=4)
                if item.get('result'):
                    tk.Label(card, text=f"回覆：{item.get('result')}", font=("Microsoft JhengHei", sf(10), "bold"), fg="#E5C07B", bg=theme["widget_bg"], justify="left", wraplength=740).pack(anchor="w", padx=4)

    refresh_history_tab_ui()

    hist_btn_frame = tk.Frame(tab_hist_page, bg=theme["inner_bg"])
    hist_btn_frame.pack(fill="x", pady=10)

    def manual_clear_history_tab():
        if messagebox.askyesno("確認清除", "確定要清空所有對話歷史紀錄嗎？", parent=win):
            save_history([])
            refresh_history_tab_ui()
            set_status("🧹 歷史紀錄已清空", "#98C379"); root.after(1500, hide_status)

    tk.Button(hist_btn_frame, text="🗑️ 清空所有歷史紀錄", command=manual_clear_history_tab, bg="#E06C75", fg="white", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=12, pady=6).pack(side="left")

    # 📌 5. 系統設定
    tab_settings_container = tk.Frame(notebook, bg=theme["inner_bg"])
    notebook.add(tab_settings_container, text="⚙️ 系統設定")
    canvas_s = tk.Canvas(tab_settings_container, bg=theme["inner_bg"], highlightthickness=0)
    scrollbar_s = ttk.Scrollbar(tab_settings_container, orient="vertical", command=canvas_s.yview)
    tab_settings = tk.Frame(canvas_s, bg=theme["inner_bg"], padx=20, pady=15)
    tab_settings.bind("<Configure>", lambda e: canvas_s.configure(scrollregion=canvas_s.bbox("all")))
    canvas_s_window = canvas_s.create_window((0, 0), window=tab_settings, anchor="nw")
    canvas_s.configure(yscrollcommand=scrollbar_s.set)
    canvas_s.bind('<Configure>', lambda e: canvas_s.itemconfig(canvas_s_window, width=e.width))
    canvas_s.pack(side="left", fill="both", expand=True); scrollbar_s.pack(side="right", fill="y")

    # 設定鎖控制橫幅
    lock_bar = tk.Frame(tab_settings, bg=theme["widget_bg"], padx=10, pady=8, bd=1, relief="solid")
    lock_bar.pack(fill="x", pady=(0, 10))
    lock_status_lbl = tk.Label(lock_bar, text="🔒 設定狀態：已鎖定 (唯讀保護中，防止誤觸)", font=("Microsoft JhengHei", sf(10), "bold"), fg="#E5C07B", bg=theme["widget_bg"])
    lock_status_lbl.pack(side="left")

    def toggle_lock():
        global is_settings_locked
        is_settings_locked = not is_settings_locked
        apply_lock_state()

    lock_btn = tk.Button(lock_bar, text="🔓 解鎖設定", command=toggle_lock, bg="#E06C75", fg="white", font=("Microsoft JhengHei", sf(9), "bold"), relief="flat", padx=10, pady=3)
    lock_btn.pack(side="right")

    guide_card = tk.Frame(tab_settings, bg=theme["widget_bg"], bd=1, relief="solid", padx=12, pady=10)
    guide_card.pack(fill="x", pady=(0, 10))
    tk.Label(guide_card, text="💡 取得 免費 API Key：", font=("Microsoft JhengHei", sf(10), "bold"), fg="#98C379", bg=theme["widget_bg"]).pack(anchor="w")
    tk.Label(guide_card, text="1. Groq API：至 console.groq.com 免費申請 (gsk_...)。\n2. Tavily Search API：至 tavily.com 註冊免費取得 (tvly-...)。", font=("Microsoft JhengHei", sf(10)), fg=theme["widget_fg"], bg=theme["widget_bg"], justify="left").pack(anchor="w", pady=(2, 6))

    btn_f_urls = tk.Frame(guide_card, bg=theme["widget_bg"])
    btn_f_urls.pack(anchor="w")
    tk.Button(btn_f_urls, text="🌐 開啟 Groq 官網", command=lambda: webbrowser.open("https://console.groq.com/"), bg="#61AFEF", fg="#21252B", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=8, pady=2).pack(side="left", padx=(0, 6))
    tk.Button(btn_f_urls, text="🔍 開啟 Tavily 官網", command=lambda: webbrowser.open("https://tavily.com/"), bg="#E5C07B", fg="#21252B", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=8, pady=2).pack(side="left")

    autostart_var = tk.BooleanVar(value=config.get("autostart", True))
    chk_autostart = tk.Checkbutton(tab_settings, text="🚀 開機自動啟動 (Windows 啟動資料夾捷徑)", variable=autostart_var, font=("Microsoft JhengHei", sf(10), "bold"), fg="#98C379", bg=theme["inner_bg"], selectcolor=theme["widget_bg"])
    chk_autostart.pack(anchor="w", pady=(4, 6))

    # 區塊一：各功能 AI 模型選擇
    model_box = tk.LabelFrame(tab_settings, text=" 🎯 各功能獨立 AI 模型偏好設定 ", font=("Microsoft JhengHei", sf(10), "bold"), fg="#E5C07B", bg=theme["inner_bg"], padx=10, pady=8)
    model_box.pack(fill="x", pady=(4, 10))

    tk.Label(model_box, text="🎙️ 語音聽寫與精修 (Alt + S)：", font=("Microsoft JhengHei", sf(9), "bold"), fg=theme["widget_fg"], bg=theme["inner_bg"]).pack(anchor="w", pady=(2, 1))
    combo_v = ttk.Combobox(model_box, values=list(MODEL_MAP.values()), state="readonly", font=("Microsoft JhengHei", sf(9)))
    combo_v.pack(fill="x", pady=(0, 6))
    combo_v.set(MODEL_MAP.get(MODEL_VOICE, list(MODEL_MAP.values())[0]))

    tk.Label(model_box, text="💬 AI 實時對話中心 (Alt + Q)：", font=("Microsoft JhengHei", sf(9), "bold"), fg=theme["widget_fg"], bg=theme["inner_bg"]).pack(anchor="w", pady=(2, 1))
    combo_c = ttk.Combobox(model_box, values=list(MODEL_MAP.values()), state="readonly", font=("Microsoft JhengHei", sf(9)))
    combo_c.pack(fill="x", pady=(0, 6))
    combo_c.set(MODEL_MAP.get(MODEL_CHAT, list(MODEL_MAP.values())[2]))

    tk.Label(model_box, text="🔍 劃詞翻譯 / 潤飾 / OCR / 剪貼簿：", font=("Microsoft JhengHei", sf(9), "bold"), fg=theme["widget_fg"], bg=theme["inner_bg"]).pack(anchor="w", pady=(2, 1))
    combo_s = ttk.Combobox(model_box, values=list(MODEL_MAP.values()), state="readonly", font=("Microsoft JhengHei", sf(9)))
    combo_s.pack(fill="x", pady=(0, 4))
    combo_s.set(MODEL_MAP.get(MODEL_SELECTION, list(MODEL_MAP.values())[0]))

    # 區塊二：界面樣式與預覽
    style_box = tk.LabelFrame(tab_settings, text=" 🎨 介面外觀與預覽 ", font=("Microsoft JhengHei", sf(10), "bold"), fg="#98C379", bg=theme["inner_bg"], padx=10, pady=8)
    style_box.pack(fill="x", pady=(0, 10))

    tk.Label(style_box, text="🔍 UI 介面文字字型大小：", font=("Microsoft JhengHei", sf(9), "bold"), fg="#61AFEF", bg=theme["inner_bg"]).pack(anchor="w", pady=(2, 1))
    scale_combo = ttk.Combobox(style_box, values=list(SCALE_OPTIONS.keys()), state="readonly", font=("Microsoft JhengHei", sf(9)))
    scale_combo.pack(fill="x", pady=(0, 6))
    
    current_scale_str = "大級字體 (1.35x - 推薦)"
    for k, v in SCALE_OPTIONS.items():
        if abs(v - FONT_SCALE) < 0.05:
            current_scale_str = k; break
    scale_combo.set(current_scale_str)

    tk.Label(style_box, text="🎨 介面風格主題：", font=("Microsoft JhengHei", sf(9), "bold"), fg="#98C379", bg=theme["inner_bg"]).pack(anchor="w", pady=(2, 1))
    theme_combo = ttk.Combobox(style_box, values=list(THEMES.keys()), state="readonly", font=("Microsoft JhengHei", sf(9)))
    theme_combo.pack(fill="x", pady=(0, 8))
    theme_combo.set(CURRENT_THEME_NAME)

    def preview_ui():
        global CURRENT_THEME_NAME, FONT_SCALE
        CURRENT_THEME_NAME = theme_combo.get()
        FONT_SCALE = SCALE_OPTIONS.get(scale_combo.get(), 1.35)
        refresh_floating_widget()
        win.destroy()
        root.after(50, lambda: prompt_api_key_gui(default_tab_idx=4))

    btn_preview = tk.Button(style_box, text="👁️ 即時預覽 UI 主題與字體", command=preview_ui, bg="#61AFEF", fg="#21252B", font=("Microsoft JhengHei", sf(9), "bold"), relief="flat", padx=10, pady=4)
    btn_preview.pack(anchor="w")

    # 區塊三：API 密鑰與 Prompt
    tk.Label(tab_settings, text="🔑 Groq API Key：", font=("Microsoft JhengHei", sf(10), "bold"), fg=theme["widget_fg"], bg=theme["inner_bg"]).pack(anchor="w", pady=(4, 2))
    entry_api = tk.Entry(tab_settings, font=("Consolas", sf(11)), show="*")
    entry_api.pack(fill="x", anchor="w", pady=(0, 8), ipady=3)
    if GROQ_API_KEY: entry_api.insert(0, GROQ_API_KEY)

    tk.Label(tab_settings, text="🌐 Tavily Search API Key (實現即時精準查證)：", font=("Microsoft JhengHei", sf(10), "bold"), fg="#E5C07B", bg=theme["inner_bg"]).pack(anchor="w", pady=(4, 2))
    entry_tavily = tk.Entry(tab_settings, font=("Consolas", sf(11)), show="*")
    entry_tavily.pack(fill="x", anchor="w", pady=(0, 8), ipady=3)
    if TAVILY_API_KEY: entry_tavily.insert(0, TAVILY_API_KEY)

    tk.Label(tab_settings, text="自訂提示 1 (Alt + 1)：", font=("Microsoft JhengHei", sf(10), "bold"), fg="#98C379", bg=theme["inner_bg"]).pack(anchor="w", pady=(4, 2))
    entry_p1 = tk.Entry(tab_settings, font=("Microsoft JhengHei", sf(10)))
    entry_p1.pack(fill="x", anchor="w", pady=(0, 8), ipady=3)
    entry_p1.insert(0, CUSTOM_PROMPT_1)

    tk.Label(tab_settings, text="自訂提示 2 (Alt + 2)：", font=("Microsoft JhengHei", sf(10), "bold"), fg="#E5C07B", bg=theme["inner_bg"]).pack(anchor="w", pady=(4, 2))
    entry_p2 = tk.Entry(tab_settings, font=("Microsoft JhengHei", sf(10)))
    entry_p2.pack(fill="x", anchor="w", pady=(0, 8), ipady=3)
    entry_p2.insert(0, CUSTOM_PROMPT_2)

    def save_settings():
        global GROQ_API_KEY, TAVILY_API_KEY, CUSTOM_PROMPT_1, CUSTOM_PROMPT_2, CURRENT_THEME_NAME, FONT_SCALE, MODEL_VOICE, MODEL_CHAT, MODEL_SELECTION, is_settings_locked
        key = entry_api.get().strip()
        t_key = entry_tavily.get().strip()
        if key:
            MODEL_VOICE = combo_v.get().split(" ")[0]
            MODEL_CHAT = combo_c.get().split(" ")[0]
            MODEL_SELECTION = combo_s.get().split(" ")[0]
            selected_scale = SCALE_OPTIONS.get(scale_combo.get(), 1.35)
            
            GROQ_API_KEY, TAVILY_API_KEY, CUSTOM_PROMPT_1, CUSTOM_PROMPT_2, CURRENT_THEME_NAME, FONT_SCALE = key, t_key, entry_p1.get().strip(), entry_p2.get().strip(), theme_combo.get(), selected_scale
            set_autostart(autostart_var.get())
            
            save_config({
                "groq_api_key": key,
                "tavily_api_key": t_key,
                "custom_prompt_1": CUSTOM_PROMPT_1,
                "custom_prompt_2": CUSTOM_PROMPT_2,
                "theme": CURRENT_THEME_NAME,
                "font_scale": FONT_SCALE,
                "model_voice": MODEL_VOICE,
                "model_chat": MODEL_CHAT,
                "model_selection": MODEL_SELECTION,
                "last_version": CURRENT_VERSION,
                "seen_broadcast_ids": SEEN_BROADCAST_IDS,
                "autostart": autostart_var.get()
            })
            is_settings_locked = True
            messagebox.showinfo("成功", "設定已儲存並自動鎖定！", parent=win)
            win.destroy()
            refresh_floating_widget()
        else:
            messagebox.showwarning("提示", "Groq API Key 不能為空！", parent=win)

    btn_save = tk.Button(tab_settings, text="💾 儲存並套用設定", command=save_settings, bg="#4CAF50", fg="white", font=("Microsoft JhengHei", sf(11), "bold"), relief="flat", padx=16, pady=8)
    btn_save.pack(pady=15)

    def apply_lock_state():
        state_str = "disabled" if is_settings_locked else "normal"
        combo_state = "disabled" if is_settings_locked else "readonly"
        
        lock_status_lbl.config(
            text="🔒 設定狀態：已鎖定 (唯讀保護中，防止誤觸)" if is_settings_locked else "🔓 設定狀態：已解鎖 (可自由修改與編輯)",
            fg="#E5C07B" if is_settings_locked else "#98C379"
        )
        lock_btn.config(text="🔓 解鎖設定" if is_settings_locked else "🔒 鎖定設定", bg="#E06C75" if is_settings_locked else "#4B5263")

        combo_v.config(state=combo_state)
        combo_c.config(state=combo_state)
        combo_s.config(state=combo_state)
        scale_combo.config(state=combo_state)
        theme_combo.config(state=combo_state)

        chk_autostart.config(state=state_str)
        entry_api.config(state=state_str)
        entry_tavily.config(state=state_str)
        entry_p1.config(state=state_str)
        entry_p2.config(state=state_str)
        btn_preview.config(state=state_str)
        btn_save.config(state=state_str)

    apply_lock_state()

    # 📌 6. 報錯與排錯
    tab_err = create_scrollable_tab("🚨 報錯與排錯")
    add_feedback_card(tab_err)

    tk.Label(tab_err, text="🔍 全系統常態問題自主診斷與詳細排除指南：", font=("Microsoft JhengHei", sf(11), "bold"), fg="#E06C75", bg=theme["inner_bg"]).pack(anchor="w", pady=(10, 8))
    
    trouble_shooting_list = [
        ("HTTP 401 Unauthorized / Invalid API Key", 
         "【問題原因】：輸入的 Groq API Key 不正確、過期或包含空格。\n"
         "【自主排除步驟】：前往「系統設定」點擊「🔓 解鎖設定」，重新貼上 console.groq.com 產生的正確 API Key (gsk_...) 並儲存。"),
        
        ("HTTP 429 Rate Limit Exceeded", 
         "【問題原因】：觸發 Groq 免費帳號每日 Token 額度上限。\n"
         "【自主排除步驟】：系統會自動平滑切換至備用模型；若全數額度用盡請休息 15 分鐘再試。"),

        ("AI 人物或時事回答不準確 (幻覺問題)", 
         "【問題原因】：舊版爬蟲抓取資訊破碎或 AI 憑記憶猜測。\n"
         "【自主排除步驟】：前往「系統設定」填入 Tavily API Key，並在 AI 對話中點擊「清空對話紀錄」重新提問即可解決。")
    ]

    for e_title, e_desc in trouble_shooting_list:
        card = tk.Frame(tab_err, bg=theme["widget_bg"], bd=1, relief="solid", padx=12, pady=10)
        card.pack(fill="x", expand=True, pady=5)
        tk.Label(card, text=f"❓ {e_title}", font=("Microsoft JhengHei", sf(10), "bold"), fg="#E5C07B", bg=theme["widget_bg"]).pack(anchor="w")
        tk.Label(card, text=e_desc, font=("Microsoft JhengHei", sf(10)), fg=theme["widget_fg"], bg=theme["widget_bg"], justify="left", wraplength=760).pack(anchor="w", pady=(4, 0))

    # 底部關閉與意見反饋按鈕
    bottom_btn_frame = tk.Frame(win, bg=theme["card_bg"])
    bottom_btn_frame.pack(pady=10)
    
    tk.Button(bottom_btn_frame, text="💬 開啟 Discord 私訊作者", command=open_discord_profile, bg="#5865F2", fg="white", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=16, pady=6).pack(side="left", padx=5)
    tk.Button(bottom_btn_frame, text="關閉控制中心 (Esc)", command=lambda: [win.destroy(), globals().update(unified_center_win=None)], bg=theme["btn_bg"], fg=theme["widget_fg"], font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=16, pady=6).pack(side="left", padx=5)
    
    win.bind("<Escape>", lambda e: [win.destroy(), globals().update(unified_center_win=None)])
    
    set_dark_title_bar(win)
    unified_center_win = win
    if default_tab_idx < len(notebook.tabs()):
        notebook.select(default_tab_idx)

def show_ai_window(title, original_text, result_text):
    if root: root.after(0, show_ai_window_gui, title, original_text, result_text)

def show_ai_window_gui(title, original_text, result_text):
    global ai_result_win
    if ai_result_win is not None:
        try: ai_result_win.destroy()
        except Exception: pass
        ai_result_win = None

    theme = get_theme()
    win = tk.Toplevel(root)
    win.title(title)
    win.attributes("-topmost", True)
    win.geometry(f"520x360+{root.winfo_screenwidth() - 540}+{root.winfo_screenheight() - 420}")
    win.configure(bg=theme["card_bg"])

    tk.Label(win, text="【輸入 / 原文】", font=("Microsoft JhengHei", sf(10), "bold"), fg=theme["widget_fg"], bg=theme["card_bg"]).pack(anchor="w", padx=10, pady=(10, 0))
    orig_box = tk.Text(win, height=3, font=("Microsoft JhengHei", sf(10)), wrap="word", bg=theme["inner_bg"], fg=theme["widget_fg"])
    orig_box.insert(tk.END, original_text); orig_box.config(state="disabled"); orig_box.pack(fill="x", padx=10, pady=2)

    tk.Label(win, text="【AI 回覆結果】", font=("Microsoft JhengHei", sf(10), "bold"), fg=theme["accent"], bg=theme["card_bg"]).pack(anchor="w", padx=10, pady=(5, 0))
    trans_box = scrolledtext.ScrolledText(win, height=8, font=("Microsoft JhengHei", sf(11)), wrap="word", bg=theme["inner_bg"], fg=theme["widget_fg"])
    trans_box.insert(tk.END, result_text); trans_box.pack(fill="both", expand=True, padx=10, pady=2)

    btn_frame = tk.Frame(win, bg=theme["card_bg"])
    btn_frame.pack(fill="x", padx=10, pady=8)
    tk.Button(btn_frame, text="複製結果並關閉", command=lambda: [pyperclip.copy(result_text), win.destroy(), globals().update(ai_result_win=None)], bg="#4CAF50", fg="white", font=("Microsoft JhengHei", sf(10), "bold")).pack(side="right")
    tk.Button(btn_frame, text="關閉 (Esc)", command=lambda: [win.destroy(), globals().update(ai_result_win=None)], bg=theme["btn_bg"], fg=theme["widget_fg"], font=("Microsoft JhengHei", sf(10), "bold")).pack(side="right", padx=5)
    win.bind("<Escape>", lambda e: [win.destroy(), globals().update(ai_result_win=None)])
    
    set_dark_title_bar(win)
    ai_result_win = win

def win32_hotkey_loop():
    user32 = ctypes.windll.user32
    for hk_id, (name, mod, vk) in HOTKEY_IDS.items(): user32.RegisterHotKey(None, hk_id, mod, vk)
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        if msg.message == 0x0312:
            hk_id = msg.wParam
            if hk_id == 12: toggle_pause_mode(); continue
            if is_paused: continue
            if hk_id == 8: root.after(0, lambda: SnippingTool())
            elif hk_id == 4: threading.Thread(target=process_selection, args=("replace",), daemon=True).start()
            elif hk_id == 2: trigger_mode("en")
            elif hk_id == 3: threading.Thread(target=process_selection, args=("translate",), daemon=True).start()
            elif hk_id == 1: trigger_mode("zh")
            elif hk_id == 5: threading.Thread(target=process_selection, args=("ai_refine",), daemon=True).start()
            elif hk_id == 9: threading.Thread(target=process_selection, args=("custom_1",), daemon=True).start()
            elif hk_id == 10: threading.Thread(target=process_selection, args=("custom_2",), daemon=True).start()
            elif hk_id == 11: threading.Thread(target=process_tts, daemon=True).start()
            elif hk_id == 13: toggle_chat_panel()
            elif hk_id == 6: prompt_api_key_gui()
            elif hk_id == 7: threading.Thread(target=exit_program, daemon=True).start()
        user32.TranslateMessage(ctypes.byref(msg)); user32.DispatchMessageW(ctypes.byref(msg))

if __name__ == "__main__":
    try:
        threading.Thread(target=win32_hotkey_loop, daemon=True).start()
        init_gui()
        root.mainloop()
    except Exception as e:
        print(f"Critical Exception: {e}")