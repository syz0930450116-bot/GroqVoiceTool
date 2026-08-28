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
from requests.adapters import HTTPAdapter
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
import base64

# 🌟 全域執行緒安全鎖 (Thread Safety Mutex)
state_lock = threading.Lock()
history_lock = threading.Lock()
clip_lock = threading.Lock()

# 🌟 初始化全域 requests Session 連線池，降低 TLS 握手與 TCP 連線延遲
http_session = requests.Session()
http_adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20)
http_session.mount('http://', http_adapter)
http_session.mount('https://', http_adapter)

# 🌟 核心 API 抽象層：支援 Groq 與 Gemini 雙引擎
def _execute_unified_chat(messages, model, temperature=0.2, timeout=12):
    try:
        if model.startswith("gemini"):
            if not GEMINI_API_KEY:
                return False, "未設定 Gemini API Key，請至設定中心填寫"
            headers = {"Authorization": f"Bearer {GEMINI_API_KEY}", "Content-Type": "application/json"}
            url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        else:
            if not GROQ_API_KEY:
                return False, "未設定 Groq API Key，請至設定中心填寫"
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            url = "https://api.groq.com/openai/v1/chat/completions"

        payload = {"model": model, "messages": messages, "temperature": temperature}
        resp = http_session.post(url, headers=headers, json=payload, timeout=timeout)
        
        if resp.status_code == 200:
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            if "</think>" in raw: raw = raw.split("</think>")[-1].strip()
            return True, to_tw_trad(raw)
        else:
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, f"Exception: {str(e)}"

# 🌟 剪貼簿安全存取機制 (含重試防護)
def safe_clipboard_copy(text, retries=3, delay=0.1):
    for _ in range(retries):
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            time.sleep(delay)
    return False

def safe_clipboard_paste(retries=3, delay=0.1):
    for _ in range(retries):
        try:
            return pyperclip.paste()
        except Exception:
            time.sleep(delay)
    return ""

# 🌟 視窗高解析度字體銳利化 (DPI Awareness)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# 🌟 設定 Windows 視窗原生深色標題列
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

# 🌟 設定 Windows 視窗滑鼠穿透 (Click-Through) 與無焦點防護
def set_window_click_through(window):
    try:
        window.update()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            hwnd = window.winfo_id()
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_NOACTIVATE = 0x08000000
        ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE)
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
CURRENT_VERSION = "v7.6.5"
DISCORD_USERNAME = "loey3"
DISCORD_USER_ID = "816981477946032150"
DISCORD_PROFILE_URL = f"https://discord.com/users/{DISCORD_USER_ID}"
GITHUB_REPO = "syz0930450116-bot/GroqVoiceTool"

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
    "openai/gpt-oss-20b": "openai/gpt-oss-20b (Groq 極速通用)",
    "openai/gpt-oss-120b": "openai/gpt-oss-120b (Groq 高階推理)",
    "qwen-2.5-32b": "qwen-2.5-32b (Groq 中文事實查核)",
    "deepseek-r1-distill-llama-70b": "deepseek-r1-distill-llama-70b (Groq 深度邏輯)",
    "gemini-1.5-flash": "gemini-1.5-flash (Google 原生超低延遲)",
    "gemini-1.5-pro": "gemini-1.5-pro (Google 原生強大推理)",
    "gemini-2.5-flash": "gemini-2.5-flash (Google 實驗端點)"
}

SCALE_OPTIONS = {
    "標準字體 (1.0x)": 1.0,
    "中等字體 (1.2x)": 1.2,
    "大級字體 (1.35x - 推薦)": 1.35,
    "特大字體 (1.5x)": 1.5,
    "超大字體 (1.8x)": 1.8
}

def parse_ver(v_str):
    try:
        clean_str = str(v_str).strip().lower().lstrip("v")
        return tuple(map(int, clean_str.split(".")))
    except Exception:
        return (0, 0, 0)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: pass
    return {}

# 🌟 JSON 原子寫入
def save_config(cfg):
    try:
        tmp_file = CONFIG_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f: 
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        os.replace(tmp_file, CONFIG_FILE)
    except Exception:
        pass

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: pass
    return []

def save_history(hist):
    try:
        tmp_file = HISTORY_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f: 
            json.dump(hist, f, indent=4, ensure_ascii=False)
        os.replace(tmp_file, HISTORY_FILE)
    except Exception: 
        pass

def add_history_entry(task_type, original, result):
    try:
        with history_lock:
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
GEMINI_API_KEY = config.get("gemini_api_key", "")
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
    safe_clipboard_copy(DISCORD_USERNAME)
    messagebox.showinfo("複製成功", f"已複製 Discord 帳號：{DISCORD_USERNAME}\n歡迎貼上並私訊進行功能建議或反饋！", parent=parent_win)

# ================= 📢 底層核心：動態遠端推播 =================
def fetch_remote_broadcast():
    def worker():
        try:
            resp = http_session.get(BROADCAST_API_URL, headers={"User-Agent": "GroqVoiceTool-BroadcastFetcher"}, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                msg_id = data.get("id", "")
                msg_type = data.get("type", "info")
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

# ================= 🔄 底層核心：自動熱更新 =================
def check_for_updates(manual=False):
    def update_worker():
        try:
            if manual: set_status("🔍 正在檢查雲端最新版本...", "#61AFEF")
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            headers = {"User-Agent": "GroqVoiceTool-AutoUpdater"}
            resp = http_session.get(url, headers=headers, timeout=6)
            
            if resp.status_code == 200:
                data = resp.json()
                latest_tag = data.get("tag_name", "").strip()
                body = data.get("body", "無更新日誌說明。")
                assets = data.get("assets", [])

                if latest_tag and parse_ver(latest_tag) > parse_ver(CURRENT_VERSION):
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

def _prompt_update_gui(latest_tag, release_notes, download_url):
    up_win = tk.Toplevel(root)
    up_win.title(f"🚀 發現新版本：{latest_tag}")
    up_win.geometry(f"560x480+{(root.winfo_screenwidth()-560)//2}+{(root.winfo_screenheight()-480)//2}")
    up_win.attributes("-topmost", True)
    up_win.configure(bg="#1E1E1E")

    safe_notes = str(release_notes) if release_notes is not None else "尚無更新說明。"

    tk.Label(up_win, text=f"🎉 發現軟體最新升級版本：{latest_tag}", font=("Microsoft JhengHei", sf(12), "bold"), fg="#61AFEF", bg="#1E1E1E").pack(anchor="w", padx=16, pady=(14, 4))
    tk.Label(up_win, text=f"（您當前的執行版本：{CURRENT_VERSION}）", font=("Microsoft JhengHei", sf(10)), fg="#ABB2BF", bg="#1E1E1E").pack(anchor="w", padx=16)

    tk.Label(up_win, text="📝 更新內容說明：", font=("Microsoft JhengHei", sf(10), "bold"), fg="#98C379", bg="#1E1E1E").pack(anchor="w", padx=16, pady=(10, 2))
    
    notes_box = scrolledtext.ScrolledText(up_win, height=6, font=("Microsoft JhengHei", sf(10)), bg="#252526", fg="#FFFFFF", wrap="word")
    notes_box.pack(fill="both", expand=True, padx=16, pady=4)
    notes_box.insert(tk.END, safe_notes)
    notes_box.config(state="disabled")

    btn_f = tk.Frame(up_win, bg="#1E1E1E")
    btn_f.pack(fill="x", padx=16, pady=16)

    def start_download(event=None):
        up_win.destroy()
        threading.Thread(target=_perform_auto_update, args=(download_url,), daemon=True).start()

    btn_upgrade = tk.Button(btn_f, text="⚡ 頁面一鍵自動升級 (Enter)", command=start_download, bg="#4CAF50", fg="white", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=16, pady=8)
    btn_upgrade.pack(side="right")
    
    tk.Button(btn_f, text="稍後再說", command=up_win.destroy, bg="#4B5263", fg="white", font=("Microsoft JhengHei", sf(10)), relief="flat", padx=12, pady=8).pack(side="right", padx=8)

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
        resp = http_session.get(download_url, stream=True, timeout=30)
        if resp.status_code == 200:
            with open(new_exe_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk: f.write(chunk)
            
            set_status("✨ 下載完成，即將自動覆蓋並重啟...", "#98C379")
            time.sleep(1.0)

            bat_path = os.path.join(APPDATA_DIR, "update_installer.bat")
            # 🌟 修復 PyInstaller 安全性驗證死結：加入 timeout 以延長母處理序生命週期
            bat_script = f"""@echo off
chcp 65001 > nul
timeout /t 2 /nobreak > nul
move /y "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
timeout /t 3 /nobreak > nul
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

# OSD (On-Screen Display) 元件
osd_win = None
osd_label = None
osd_timer = None

# 全域截圖單例保護
snip_active = False
audio_frames = []

def should_trigger_search(query):
    clean_q = query.strip().lower()
    chat_phrases = ["哈囉", "你好", "在嗎", "聽到嗎", "謝謝", "早安", "午安", "晚安", "拜拜", "hello", "hi", "hey", "test"]
    if len(clean_q) <= 6 and any(p in clean_q for p in chat_phrases):
        return False
    search_keywords = ["誰是", "什麼是", "新聞", "時事", "多少錢", "價格", "今天", "最近", "介紹", "原因", "如何", "怎麼"]
    if any(k in clean_q for k in search_keywords) or len(clean_q) > 12:
        return True
    return False

def get_web_search_context(query):
    if not should_trigger_search(query):
        return ""

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
            resp = http_session.post(url, json=payload, timeout=3.5)
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
        resp = http_session.get(url, headers=headers, timeout=1.5)
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
        "【原則與聊天規範】：\n"
        "1. 請用自然、流暢且親切的繁體中文（台灣用語習慣）回答問題。\n"
        "2. 當使用者進行日常閒聊、打招呼或簡單測試時，請簡短親切地回應即可，絕對不要主動吐出不相關的背景資料或資料列表。\n"
        "3. 面對知名人物、網紅或真實事件時，請嚴格核對事實，切勿將不同人的本名或背景張冠李戴。"
    )

spotlight_history = [
    {"role": "system", "content": get_system_prompt()}
]

def sanitize_spotlight_history():
    global spotlight_history
    with history_lock:
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

# 🌟 初始化持久化 OSD 系統
def init_osd():
    global osd_win, osd_label
    osd_win = tk.Toplevel(root)
    osd_win.overrideredirect(True)
    osd_win.attributes("-topmost", True)
    osd_win.attributes("-disabled", True)
    osd_win.withdraw()
    osd_label = tk.Label(osd_win, text="", font=("Microsoft JhengHei", sf(14), "bold"), padx=24, pady=12)
    osd_label.pack()
    set_window_click_through(osd_win)

def show_osd(text, auto_hide=True):
    if root:
        root.after(0, _show_osd_gui, text, auto_hide)

def _show_osd_gui(text, auto_hide):
    global osd_timer
    if osd_win is None: return
    if osd_timer:
        root.after_cancel(osd_timer)
        osd_timer = None
        
    theme = get_theme()
    osd_label.config(text=text, bg=theme["widget_bg"], fg=theme["accent"])
    osd_win.configure(bg=theme["widget_bg"])
    osd_win.update_idletasks()
    
    w = osd_win.winfo_reqwidth()
    h = osd_win.winfo_reqheight()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    osd_win.geometry(f"{w}x{h}+{(sw-w)//2}+{int(sh * 0.82)}")
    osd_win.attributes("-alpha", 0.95)
    osd_win.deiconify()
    set_window_click_through(osd_win)
    
    def fade_out():
        alpha = osd_win.attributes("-alpha")
        if alpha > 0.1:
            osd_win.attributes("-alpha", alpha - 0.1)
            global osd_timer
            osd_timer = root.after(35, fade_out)
        else:
            osd_win.withdraw()
            
    if auto_hide:
        osd_timer = root.after(1500, fade_out)

def init_gui():
    global root, status_win, status_label
    root = tk.Tk()
    root.withdraw()

    status_win = tk.Toplevel(root)
    status_win.overrideredirect(True)
    status_win.attributes("-topmost", True)
    status_win.attributes("-disabled", True)
    status_win.withdraw()
    
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    status_win.geometry(f"380x75+{sw - 400}+{sh - 130}")
    status_label = tk.Label(status_win, text="", font=("Microsoft JhengHei", sf(10), "bold"), fg="#FFFFFF", wraplength=360, justify="left", padx=8, pady=6)
    status_label.pack(fill="both", expand=True)

    set_window_click_through(status_win)
    init_osd()

    show_startup_notice()
    toggle_floating_ball()

    check_for_updates(manual=False)
    fetch_remote_broadcast()

    threading.Thread(target=clipboard_monitor_loop, daemon=True).start()
    if TRAY_AVAILABLE: threading.Thread(target=setup_system_tray, daemon=True).start()
    if not GROQ_API_KEY and not GEMINI_API_KEY: root.after(1500, prompt_api_key_gui)

def update_status_ui(text, bg_color):
    if status_win and status_label:
        status_label.config(text=text, bg=bg_color)
        status_win.configure(bg=bg_color)
        status_win.deiconify()

def hide_status_ui():
    if status_win and not recording and not snip_active: status_win.withdraw()

def set_status(text, bg_color):
    if root: root.after(0, update_status_ui, text, bg_color)

def hide_status():
    if root: root.after(0, hide_status_ui)

def show_startup_notice():
    set_status(f"🚀 {CURRENT_VERSION} AI 懸浮球已就緒", "#98C379")
    if root: root.after(2000, hide_status)

def exit_program():
    set_status("👋 助理已關閉", "#E06C75")
    show_osd("👋 系統正在關閉...", auto_hide=True)
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
        show_osd("🔴 [錄音中] 正在聆聽語音...", auto_hide=False)
    except Exception as e:
        recording = False
        stream = None
        trigger_cdn_error_modal("麥克風啟動失敗", str(e))
        show_osd("⚠️ 麥克風啟動失敗", auto_hide=True)

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
        show_osd("⚠️ 未收到語音數據", auto_hide=True)
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
        set_status("⚠️ 未設定 Groq API Key (Whisper 必須)", "#E06C75")
        show_osd("⚠️ 缺少 Groq API Key", auto_hide=True)
        root.after(1500, hide_status); prompt_api_key_gui(); return

    with state_lock:
        if is_processing:
            set_status("⏳ 系統處理中，請稍候...", "#E5C07B")
            root.after(1500, hide_status)
            return
        is_processing = True

    set_status("⚡ Groq Whisper 語音辨識中...", "#61AFEF")
    show_osd("⚡ AI 語音辨識與精修中...", auto_hide=False)
    try:
        audio_data = np.concatenate(audio_frames, axis=0)
        wav_io = io.BytesIO()
        write(wav_io, SAMPLE_RATE, (audio_data * 32767).astype(np.int16))
        wav_bytes = wav_io.getvalue()

        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        files = {"file": ("speech.wav", wav_bytes, "audio/wav")}
        data = {"model": "whisper-large-v3", "language": "zh", "temperature": "0", "response_format": "json"}
        
        w_resp = http_session.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data=data, timeout=12)
        if w_resp.status_code == 200:
            raw_text = to_tw_trad(w_resp.json().get("text", "").strip())
            if not raw_text:
                set_status("⚠️ 未偵測到清晰語音", "#E5C07B")
                show_osd("⚠️ 未偵測到語音", auto_hide=True)
                return

            set_status("✨ AI 智慧精修校對中...", "#C678DD")
            sys_prompt = "Translate Chinese speech to natural English." if mode == "en" else "修復繁體中文同音錯字並補齊標點符號，不要回答內容，直接輸出校對後文字。"

            candidate_models = [MODEL_VOICE, "gemini-1.5-flash", "openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen-2.5-32b", "deepseek-r1-distill-llama-70b"]
            unique_candidate_models = []
            for m in candidate_models:
                if m not in unique_candidate_models: unique_candidate_models.append(m)

            polished_text = ""
            for model_name in unique_candidate_models:
                success, result = _execute_unified_chat([{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"請校對：{raw_text}"}], model_name, 0.0, 10)
                if success:
                    polished_text = result
                    break

            if polished_text:
                safe_clipboard_copy(polished_text); time.sleep(0.05); send_paste()
                add_history_entry("語音聽寫校對", raw_text, polished_text)
                set_status("✨ 辨識完成，已自動貼上！", "#98C379")
                show_osd("✅ 語音輸入完成，已貼上", auto_hide=True)
            else:
                safe_clipboard_copy(raw_text); send_paste()
                set_status("⚠️ AI 校對異常，已貼出原始文字", "#E5C07B")
                show_osd("⚠️ 精修失敗，輸出原文", auto_hide=True)
        else:
            trigger_cdn_error_modal(f"Groq API 錯誤 (HTTP {w_resp.status_code})", w_resp.text[:200])
            show_osd("❌ 語音服務異常", auto_hide=True)
    except Exception as e:
        trigger_cdn_error_modal("語音處理例外錯誤", traceback.format_exc())
        show_osd("❌ 系統例外錯誤", auto_hide=True)
    finally:
        with state_lock:
            is_processing = False
        root.after(2500, hide_status)

# ================= 🛡️ 核心防護與「靜默全自動自我修復」 =================
def auto_execute_system_repair():
    try:
        subprocess.run(["taskkill", "/F", "/IM", "powershell.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        global is_processing, snip_active
        with state_lock:
            is_processing = False
            snip_active = False
        set_status("🛠️ 自我修復：核心組件已重置！", "#98C379")
        show_osd("🛠️ 系統組件已重置", auto_hide=True)
        root.after(2500, hide_status)
        return True
    except Exception:
        return False

def trigger_cdn_error_modal(title, err_msg):
    def _repair_and_diagnose_flow():
        set_status("🤖 AI 自動修復引擎啟動中...", "#61AFEF")
        auto_execute_system_repair()

        prompt = f"以下是系統捕捉到的 Exception/Error 日誌：\n{err_msg}\n\n請以簡短 2 句話繁體中文說明原因並給予建議。"
        try:
            success, result = _execute_unified_chat([{"role": "user", "content": prompt}], MODEL_SELECTION, 0.1, 8)
            if success: ai_diagnosis = result
            else: ai_diagnosis = "無法取得 AI 連線診斷，可能為網路斷線或 API Key 額度耗盡。"
        except Exception:
            ai_diagnosis = "無法取得 AI 連線診斷，可能為網路斷線或 API Key 額度耗盡。"

        def _show_gui():
            modal = tk.Toplevel(root)
            modal.title(f"🛠️ 靜默自動修復日誌：{title}")
            modal.geometry("560x450")
            modal.attributes("-topmost", True)
            modal.configure(bg="#282C34")
            set_dark_title_bar(modal)

            tk.Label(modal, text=f"🤖 AI 自動自我修復報告", font=("Microsoft JhengHei", 12, "bold"), fg="#98C379", bg="#282C34").pack(pady=(12, 2))
            tk.Label(modal, text="已在背景自動執行 Task 清理與核心組件重置。", font=("Microsoft JhengHei", 9), fg="#ABB2BF", bg="#282C34").pack()

            if ai_diagnosis:
                diag_card = tk.Frame(modal, bg="#21252B", bd=1, relief="solid", padx=10, pady=8)
                diag_card.pack(padx=15, pady=8, fill="x")
                tk.Label(diag_card, text="💡 AI 智慧診斷原因與建議：", font=("Microsoft JhengHei", 9, "bold"), fg="#61AFEF", bg="#21252B").pack(anchor="w")
                tk.Label(diag_card, text=ai_diagnosis, font=("Microsoft JhengHei", 9), fg="#FFFFFF", bg="#21252B", justify="left", wraplength=500).pack(anchor="w", pady=(2, 0))

            txt = scrolledtext.ScrolledText(modal, wrap="word", height=8, font=("Consolas", 9), bg="#1E1E1E", fg="#ABB2BF")
            txt.insert("1.0", f"【原始錯誤日誌】\n{err_msg}")
            txt.config(state="disabled")
            txt.pack(padx=15, pady=5, fill="both", expand=True)

            btn_frame = tk.Frame(modal, bg="#282C34")
            btn_frame.pack(pady=10)

            tk.Button(btn_frame, text="⚡ 再次重置核心", command=lambda: [auto_execute_system_repair(), modal.destroy()], bg="#98C379", fg="white", font=("Microsoft JhengHei", 10, "bold"), relief="flat", padx=10).pack(side="left", padx=5)
            tk.Button(btn_frame, text="我知道了 (Esc)", command=modal.destroy, bg="#5C6370", fg="white", font=("Microsoft JhengHei", 10), relief="flat", padx=10).pack(side="left", padx=5)
            modal.bind("<Escape>", lambda e: modal.destroy())

        if root: root.after(0, _show_gui)

    threading.Thread(target=_repair_and_diagnose_flow, daemon=True).start()

# ================= ⌨️ Win32 SendInput 硬體級鍵盤模擬引擎 =================
PUL = ctypes.POINTER(ctypes.c_ulong)
class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]

def send_key(vk_code, up=False):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    flags = 0x0002 if up else 0x0000
    ii_.ki = KeyBdInput(vk_code, 0, flags, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def wait_for_modifier_release(timeout=2.0):
    user32 = ctypes.windll.user32
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not ((user32.GetAsyncKeyState(0x12) & 0x8000) or 
                (user32.GetAsyncKeyState(0x11) & 0x8000) or 
                (user32.GetAsyncKeyState(0x10) & 0x8000) or 
                (user32.GetAsyncKeyState(0x5B) & 0x8000) or 
                (user32.GetAsyncKeyState(0x5C) & 0x8000)):
            break
        time.sleep(0.01)

def send_paste():
    wait_for_modifier_release()
    time.sleep(0.05)
    send_key(0x11, up=False) # CTRL down
    send_key(0x56, up=False) # V down
    time.sleep(0.02)
    send_key(0x56, up=True)  # V up
    send_key(0x11, up=True)  # CTRL up

def send_copy():
    wait_for_modifier_release()
    time.sleep(0.05)
    send_key(0x11, up=False) # CTRL down
    send_key(0x43, up=False) # C down
    time.sleep(0.03)
    send_key(0x43, up=True)  # C up
    send_key(0x11, up=True)  # CTRL up

def toggle_chat_panel(): root.after(0, _toggle_chat_panel_main)

def _toggle_chat_panel_main():
    global chat_panel_win
    if not GROQ_API_KEY and not GEMINI_API_KEY: prompt_api_key_gui(); return
    if chat_panel_win is not None:
        try: chat_panel_win.destroy()
        except Exception: pass
        chat_panel_win = None; return

    theme = get_theme()
    win = tk.Toplevel(root)
    win.title(f"AI 實時互動對話中心 ({CURRENT_VERSION})")
    win.geometry(f"720x760+{(root.winfo_screenwidth()-720)//2}+{(root.winfo_screenheight()-760)//2}")
    win.configure(bg=theme["card_bg"])
    set_dark_title_bar(win)

    header_frame = tk.Frame(win, bg=theme["card_bg"])
    header_frame.pack(fill="x", padx=16, pady=(14, 8))
    tk.Label(header_frame, text="💬 雙引擎 AI 實時對話 🌐", font=("Microsoft JhengHei", sf(13), "bold"), fg=theme["accent"], bg=theme["card_bg"]).pack(side="left")

    def clear_chat_memory():
        global spotlight_history
        with history_lock:
            spotlight_history = [{"role": "system", "content": get_system_prompt()}]
        chat_box.config(state="normal"); chat_box.delete("1.0", tk.END); chat_box.insert(tk.END, "系統：對話紀錄已重置。\n\n"); chat_box.config(state="disabled")
        set_status("🧹 對話紀錄已清空", "#98C379"); root.after(1500, hide_status)

    tk.Button(header_frame, text="清空對話紀錄", command=clear_chat_memory, bg="#E06C75", fg="white", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=8, pady=3).pack(side="right")

    chat_box = scrolledtext.ScrolledText(win, font=("Microsoft JhengHei", sf(11)), wrap="word", bg=theme["inner_bg"], fg=theme["widget_fg"], padx=8, pady=8)
    chat_box.pack(fill="both", expand=True, padx=16, pady=4)
    
    with history_lock:
        for msg in spotlight_history:
            if msg.get("role") == "user": chat_box.insert(tk.END, f"👤 你：\n{msg.get('content')}\n\n")
            elif msg.get("role") == "assistant" and msg.get("content"): chat_box.insert(tk.END, f"🤖 AI 助理：\n{msg.get('content')}\n\n")
    chat_box.config(state="disabled"); chat_box.see(tk.END)

    status_tip = tk.Label(win, text="💡 提示：智慧 Tavily 搜尋機制，僅在提問時精準查證，閒聊不打擾。", font=("Microsoft JhengHei", sf(10)), fg="#98C379", bg=theme["card_bg"])
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
        with state_lock:
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
                set_status("⚡ 語音辨識與 AI 校對中...", "#61AFEF")
                def process_worker():
                    if not GROQ_API_KEY:
                        set_status("⚠️ 面板語音需要 Groq API", "#E06C75")
                        return
                    try:
                        wav_io = io.BytesIO()
                        write(wav_io, SAMPLE_RATE, (audio_data * 32767).astype(np.int16))
                        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
                        files = {"file": ("panel_voice.wav", wav_io.getvalue(), "audio/wav")}
                        resp = http_session.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data={"model": "whisper-large-v3", "language": "zh"}, timeout=12)
                        if resp.status_code == 200:
                            raw_txt = to_tw_trad(resp.json().get("text", "").strip())
                            if raw_txt:
                                sys_prompt = "修復繁體中文同音錯字並補齊標點符號，不要回答內容，直接輸出校對後文字。"
                                success, result = _execute_unified_chat([{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"請校對：{raw_txt}"}], MODEL_VOICE, 0.0, 8)
                                polished = result if success else raw_txt
                                root.after(0, lambda: [entry.delete(0, tk.END), entry.insert(0, polished), execute_chat_input()])
                        set_status("✨ 語音校對完成", "#98C379")
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
    with state_lock:
        is_processing = True
    
    is_search_needed = should_trigger_search(query)
    if is_search_needed:
        set_status("🌐 檢索 Tavily 網路真實資料與 AI 推理中...", "#C678DD")
    else:
        set_status("🤖 AI 思考回應中...", "#61AFEF")
    
    try:
        web_context = get_web_search_context(query) if is_search_needed else ""

        with history_lock:
            spotlight_history.append({"role": "user", "content": query})
        sanitize_spotlight_history()

        with history_lock:
            api_messages = [dict(m) for m in spotlight_history]
            
        if web_context and api_messages and api_messages[-1]["role"] == "user":
            api_messages[-1]["content"] = f"【實時網路權威檢索資料】：\n{web_context}\n\n【使用者提問】：\n{query}"

        candidate_models = [MODEL_CHAT, "gemini-1.5-flash", "qwen-2.5-32b", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "deepseek-r1-distill-llama-70b"]
        unique_candidate_models = []
        for m in candidate_models:
            if m not in unique_candidate_models: unique_candidate_models.append(m)

        success = False
        last_error_text = ""

        for model_name in unique_candidate_models:
            is_gemini = model_name.startswith("gemini")
            if is_gemini and not GEMINI_API_KEY: continue
            if not is_gemini and not GROQ_API_KEY: continue

            if is_gemini:
                headers = {"Authorization": f"Bearer {GEMINI_API_KEY}", "Content-Type": "application/json"}
                url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            else:
                headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                url = "https://api.groq.com/openai/v1/chat/completions"

            payload = {
                "model": model_name,
                "messages": api_messages,
                "temperature": 0.3,
                "stream": True
            }

            try:
                resp = http_session.post(url, headers=headers, json=payload, stream=True, timeout=18)
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
                        with history_lock:
                            spotlight_history.append({"role": "assistant", "content": full_reply})
                        add_history_entry("AI 實時對話", query, full_reply)
                    success = True
                    break
                else:
                    last_error_text = f"HTTP {resp.status_code}: {resp.text[:150]}"
                    continue
            except Exception as req_e:
                last_error_text = str(req_e)
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
            with history_lock:
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
        with history_lock:
            if spotlight_history and spotlight_history[-1]["role"] == "user":
                spotlight_history.pop()
    finally:
        with state_lock:
            is_processing = False
        hide_status()

def toggle_auto_clipboard():
    global auto_clipboard_enabled, last_clipboard_text
    auto_clipboard_enabled = not auto_clipboard_enabled
    if auto_clipboard_enabled:
        with clip_lock:
            last_clipboard_text = safe_clipboard_paste().strip()
        set_status("📋 自動剪貼簿翻譯：已開啟", "#56B6C2")
        show_osd("📋 自動剪貼翻譯：已開啟", auto_hide=True)
        winsound.Beep(1000, 100)
    else:
        set_status("📋 自動剪貼簿翻譯：已關閉", "#E5C07B")
        show_osd("📋 自動剪貼翻譯：已關閉", auto_hide=True)
        winsound.Beep(500, 100)
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
        with state_lock:
            proc_state = is_processing
        if not auto_clipboard_enabled or is_paused or proc_state or (not GROQ_API_KEY and not GEMINI_API_KEY): continue
        try:
            current_text = safe_clipboard_paste().strip()
            with clip_lock:
                if current_text and current_text != last_clipboard_text:
                    if len(current_text) < 2000:
                        last_clipboard_text = current_text
                        threading.Thread(target=process_auto_clipboard, args=(current_text,), daemon=True).start()
        except Exception: pass

def process_auto_clipboard(text):
    global last_clipboard_text, is_processing
    with state_lock:
        is_processing = True
    set_status("📋 背景翻譯中...", "#56B6C2")
    show_osd("📋 背景剪貼簿翻譯中...", auto_hide=False)
    try:
        sys_prompt = "將輸入文字精準翻譯為流暢繁體中文。只需輸出翻譯結果。"
        success, result = _execute_unified_chat([{"role": "system", "content": sys_prompt}, {"role": "user", "content": text}], MODEL_SELECTION, 0.2, 10)
        if success and result:
            safe_clipboard_copy(result)
            with clip_lock:
                last_clipboard_text = result
            add_history_entry("自動剪貼簿翻譯", text, result)
            set_status("📋 翻譯完成並已覆蓋剪貼簿", "#98C379")
            show_osd("✅ 剪貼簿翻譯完成", auto_hide=True)
            winsound.Beep(1200, 80)
            root.after(1500, hide_status)
        elif not success:
            trigger_cdn_error_modal("自動剪貼簿 API 錯誤", result)
            show_osd("❌ 翻譯 API 錯誤", auto_hide=True)
    except Exception:
        show_osd("❌ 翻譯發生例外", auto_hide=True)
    finally:
        with state_lock:
            is_processing = False

# 🌟 iPhone 風格懸浮球
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
        set_status(f"✨ {CURRENT_VERSION} 雙引擎 AI 懸浮球已啟動", "#98C379")
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
    tray_icon = pystray.Icon("GroqVoiceTool", create_tray_image(), "雙引擎 AI 助理", menu)
    tray_icon.run()

def toggle_pause_mode():
    global is_paused
    with state_lock:
        is_paused = not is_paused
        current_pause_state = is_paused
    if current_pause_state: 
        set_status("⏸️ 助理已暫停", "#E5C07B")
        show_osd("⏸️ 系統已暫停 (防護開啟)", auto_hide=True)
    else: 
        set_status("▶️ 助理已恢復", "#98C379")
        show_osd("▶️ 系統已恢復", auto_hide=True)
        root.after(1500, hide_status)

# 🌟 截圖引擎 (單例鎖定 snip_active)
class SnippingTool:
    def __init__(self, mode="translate"):
        global snip_active
        with state_lock:
            if snip_active:
                return
            snip_active = True

        set_status("📸 [截圖進行中] 請拖曳框選區域...", "#61AFEF")
        self.mode = mode
        self.full_img = ImageGrab.grab(all_screens=True)
        
        self.snip_win = tk.Toplevel(root)
        self.snip_win.attributes("-fullscreen", True)
        self.snip_win.attributes("-alpha", 0.3)
        self.snip_win.attributes("-topmost", True)
        self.snip_win.config(cursor="cross")
        
        self.canvas = tk.Canvas(self.snip_win, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        sw = self.snip_win.winfo_screenwidth()
        tip_frame = tk.Frame(self.snip_win, bg="#21252B", padx=16, pady=8, bd=1, relief="solid")
        tip_frame.place(relx=0.5, y=30, anchor="n")
        tk.Label(tip_frame, text="📸 請拖曳滑鼠框選截圖區域  |  按 Esc 鍵可取消截圖", font=("Microsoft JhengHei", sf(11), "bold"), fg="#FFFFFF", bg="#21252B").pack()

        self.start_x = self.start_y = self.rect = None
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.snip_win.bind("<Escape>", self.cancel_snip)

    def cancel_snip(self, event=None):
        global snip_active
        with state_lock:
            snip_active = False
        try: self.snip_win.destroy()
        except Exception: pass
        set_status("✕ 已取消截圖", "#E5C07B")
        show_osd("✕ 取消截圖", auto_hide=True)
        root.after(1500, hide_status)

    def on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="#61AFEF", width=2, fill="white")

    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        global snip_active
        if self.start_x is None or self.start_y is None:
            self.cancel_snip()
            return

        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        
        sw = self.snip_win.winfo_screenwidth()
        sh = self.snip_win.winfo_screenheight()
        
        try: self.snip_win.destroy()
        except Exception: pass
        
        with state_lock:
            snip_active = False
        
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
        else:
            set_status("✕ 框選區域過小，已取消", "#E5C07B")
            show_osd("✕ 範圍過小，取消截圖", auto_hide=True)
            root.after(1500, hide_status)

# 🌟 無磁碟 I/O 記憶體串流 OCR (管線枯竭修復與 Lanczos 影像放大)
def process_screenshot(img):
    global is_processing
    if not GROQ_API_KEY and not GEMINI_API_KEY: prompt_api_key_gui(); return

    with state_lock:
        if is_processing:
            set_status("⏳ 系統處理中，請稍候...", "#E5C07B")
            root.after(1500, hide_status)
            return
        is_processing = True

    set_status("🖼️ Windows 記憶體 OCR 辨識中 (無磁碟延遲)...", "#61AFEF")
    show_osd("🖼️ OCR 辨識中...", auto_hide=False)
    try:
        width, height = img.size
        if width < 400 or height < 150:
            scale_factor = 3
            try:
                resample_filter = Image.Resampling.LANCZOS
            except AttributeError:
                resample_filter = Image.LANCZOS
            img = img.resize((width * scale_factor, height * scale_factor), resample_filter)

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        base64_data = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

        ps_script = f"""
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        Add-Type -AssemblyName System.Runtime.WindowsRuntime
        $null = [Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
        $null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
        $null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Foundation, ContentType = WindowsRuntime]

        $getAwaiterBaseMethod = [WindowsRuntimeSystemExtensions].GetMember('GetAwaiter', 'Method', 'Public,Static') | Where-Object {{ $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }} | Select-Object -First 1
        function Await($AsyncTask, $As) {{
            return $getAwaiterBaseMethod.MakeGenericMethod($As).Invoke($null, @($AsyncTask)).GetResult()
        }}

        $ocrEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
        if ($null -eq $ocrEngine) {{ exit 1 }}

        $base64String = '{base64_data}'
        if ([string]::IsNullOrEmpty($base64String)) {{ exit 1 }}

        $imageBytes = [Convert]::FromBase64String($base64String)
        $stream = [Windows.Storage.Streams.InMemoryRandomAccessStream]::new()
        $dataWriter = [Windows.Storage.Streams.DataWriter]::new($stream)
        $dataWriter.WriteBytes($imageBytes)
        Await ($dataWriter.StoreAsync()) ([uint32]) | Out-Null
        $dataWriter.FlushAsync().GetResults() | Out-Null
        $dataWriter.DetachStream() | Out-Null
        $stream.Seek(0) | Out-Null

        $bitmapDecoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $softwareBitmap = Await ($bitmapDecoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $ocrResult = Await ($ocrEngine.RecognizeAsync($softwareBitmap)) ([Windows.Media.Ocr.OcrResult])
        $stream.Dispose()

        $ocrResult.Text
        """

        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        stdout_data, stderr_data = proc.communicate(input=ps_script)
        extracted_text = (stdout_data or "").strip()

        if proc.returncode != 0 or not extracted_text:
            show_ai_window("截圖 OCR", "（畫面區域）", "⚠️ 未偵測到清晰文字。")
            show_osd("⚠️ 辨識不到文字", auto_hide=True)
            return

        set_status("✨ 雙引擎 AI 繁中翻譯中...", "#C678DD")
        show_osd("✨ AI 翻譯中...", auto_hide=False)
        success, result = _execute_unified_chat([{"role": "system", "content": "請將以下文字翻譯為繁體中文。"}, {"role": "user", "content": f"請翻譯：\n{extracted_text}"}], MODEL_SELECTION, 0.2, 12)
        if success:
            add_history_entry("截圖 OCR 翻譯", extracted_text, result)
            show_ai_window("截圖 OCR 翻譯", f"【辨識原文】\n{extracted_text}", result)
            show_osd("✅ OCR 翻譯完成", auto_hide=True)
        else:
            trigger_cdn_error_modal("OCR 翻譯 API 錯誤", result)
            show_osd("❌ OCR 翻譯失敗", auto_hide=True)
    except Exception as e:
        trigger_cdn_error_modal("截圖處理例外錯誤", traceback.format_exc())
        show_osd("❌ 截圖處理例外", auto_hide=True)
    finally:
        with state_lock:
            is_processing = False
        hide_status()

def process_selection(mode):
    global is_processing
    if not GROQ_API_KEY and not GEMINI_API_KEY: prompt_api_key_gui(); return

    with state_lock:
        if is_processing:
            set_status("⏳ 系統處理中，請稍候...", "#E5C07B")
            root.after(1500, hide_status)
            return
        is_processing = True

    set_status("📋 取得選取文字中...", "#61AFEF")
    try:
        send_copy()
        text = safe_clipboard_paste().strip()
        if not text:
            set_status("⚠️ 未選取任何文字", "#E5C07B")
            show_osd("⚠️ 未選取文字", auto_hide=True)
            root.after(1500, hide_status); return

        set_status("✨ AI 處理選取文字中...", "#C678DD")
        
        if mode == "translate": sys_prompt = "請將以下文字精準翻譯為流暢繁體中文。"; title = "劃詞翻譯"
        elif mode == "ai_refine": sys_prompt = "請將以下文字進行潤飾與精簡摘要。"; title = "AI 潤飾摘要"
        elif mode == "custom_1": sys_prompt = CUSTOM_PROMPT_1; title = "自訂提示 1"
        elif mode == "custom_2": sys_prompt = CUSTOM_PROMPT_2; title = "自訂提示 2"
        elif mode == "replace": sys_prompt = "請修正語法並優化以下文字，直接輸出優化後的繁體中文。"; title = "劃詞原地替換"
        else: sys_prompt = "請優化以下文字。"; title = "AI 處理"

        show_osd(f"⏳ {title} 處理中...", auto_hide=False)

        success, result = _execute_unified_chat([{"role": "system", "content": sys_prompt}, {"role": "user", "content": text}], MODEL_SELECTION, 0.2, 12)
        if success:
            if mode == "replace":
                safe_clipboard_copy(result); time.sleep(0.05); send_paste()
                set_status("✨ 替換完成並已貼上！", "#98C379")
                show_osd("✅ 替換完成，已貼上", auto_hide=True)
            else:
                add_history_entry(title, text, result)
                show_ai_window(title, text, result)
                show_osd(f"✅ {title} 完成", auto_hide=True)
        else:
            trigger_cdn_error_modal("劃詞處理 API 錯誤", result)
            show_osd("❌ AI 處理失敗", auto_hide=True)
    except Exception as e:
        trigger_cdn_error_modal("劃詞處理例外錯誤", traceback.format_exc())
        show_osd("❌ 處理發生例外", auto_hide=True)
    finally:
        with state_lock:
            is_processing = False
        hide_status()

def process_tts():
    if not TTS_AVAILABLE:
        set_status("⚠️ 未安裝 pyttsx3 語音套件", "#E5C07B")
        show_osd("⚠️ 缺少 TTS 模組", auto_hide=True)
        root.after(1500, hide_status); return
    try:
        send_copy()
        text = safe_clipboard_paste().strip()
        if not text: return
        
        def tts_worker():
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            show_osd("✅ 朗讀結束", auto_hide=True)
            
        threading.Thread(target=tts_worker, daemon=True).start()
        set_status("🔊 正在朗讀文字...", "#98C379")
        show_osd("🔊 正在朗讀...", auto_hide=False)
        root.after(1500, hide_status)
    except Exception as e:
        trigger_cdn_error_modal("TTS 語音朗讀例外", traceback.format_exc())

unified_center_win = None
is_settings_locked = True

def prompt_api_key_gui(default_tab_idx=0):
    global unified_center_win, GROQ_API_KEY, GEMINI_API_KEY, TAVILY_API_KEY, CUSTOM_PROMPT_1, CUSTOM_PROMPT_2, CURRENT_THEME_NAME, FONT_SCALE, MODEL_VOICE, MODEL_CHAT, MODEL_SELECTION, is_settings_locked
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
    win.title(f"🚀 Groq & Gemini 控制中心 ({CURRENT_VERSION})")
    
    win.geometry(f"920x820+{(root.winfo_screenwidth()-920)//2}+{(root.winfo_screenheight()-820)//2}")
    win.configure(bg=theme["card_bg"])

    header = tk.Frame(win, bg=theme["card_bg"])
    header.pack(fill="x", padx=20, pady=(12, 6))
    tk.Label(header, text="⚙️ 系統控制中心", font=("Microsoft JhengHei", sf(14), "bold"), fg=theme["accent"], bg=theme["card_bg"]).pack(side="left")
    
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
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        notebook.add(container, text=tab_name)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        container.bind("<Enter>", _bind_mousewheel)
        container.bind("<Leave>", _unbind_mousewheel)

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

    # 📌 2. 核心技術與使用技巧
    tab_tips = create_scrollable_tab("💡 核心技術與小技巧")
    tk.Label(tab_tips, text="🛠️ 本軟體底層核心架構與技術解析：", font=("Microsoft JhengHei", sf(11), "bold"), fg="#61AFEF", bg=theme["inner_bg"]).pack(anchor="w", pady=(2, 8))
    
    core_tech_list = [
        ("🎙️ 1. 高精準語音聽寫引擎 (Whisper + LLM 雙引擎)", 
         "底層透過 `sounddevice` 以 16kHz 採集聲波，打包送往 Groq API 進行 Whisper-large-v3 語音辨識；隨後自動流轉至 LLM 進行同音字修復與全形標點補齊，再透過 Win32 API 模擬貼上。"),
        
        ("⌨️ 2. Win32 全域熱鍵與鍵盤模擬引擎", 
         "使用 `ctypes` 直接對接 Windows `user32.dll` (`RegisterHotKey` / `GetMessageW`) 在背景高效率捕捉全域快捷鍵；並運用 `SendInput` 結構體實現非侵入式與極高相容性的選取文字複製與原地覆蓋貼上。"),

        ("🖼️ 3. Windows 記憶體管線 OCR 與單例截圖鎖定", 
         "繪製 Tkinter 透明全螢幕遮罩進行區域截圖，具備單例鎖定機制 (Win+Shift+S 風格) 防止重複觸發黑屏；底層透過 Base64 與 stdin 管線將截圖送入 PowerShell `InMemoryRandomAccessStream` 進行無硬碟 I/O 辨識。"),

        ("🌐 4. 實時 RAG 智慧檢索與聊天門檻機制", 
         "對話模組具備智慧意圖過濾，日常打招呼不打擾；僅在問題需要時發送 Tavily 檢索，精準將 Context 注入 Prompt 徹底消弭 AI 幻覺。"),

        ("🛠️ 5. 靜默全自動自我修復引擎 (Auto Self-Healing)", 
         "當系統捕捉到未預期的 Exception/Error 時，背景觸發 `auto_execute_system_repair()` 自動執行清理 PowerShell 處理序、釋放 Socket 連線與變數重設，並由 AI 背景產生診斷報告。"),

        ("🎨 6. 狀態持久化 OSD 系統與無焦點保護", 
         "提供高可見度、淡出動畫的 OSD 提示窗，支援長時間任務持久化顯示；具備 Win32 滑鼠穿透與無焦點保護，確保打機時絕不搶奪焦點或造成滑鼠失靈。")
    ]

    for t_title, t_desc in core_tech_list:
        card = tk.Frame(tab_tips, bg=theme["widget_bg"], bd=1, relief="solid", padx=12, pady=10)
        card.pack(fill="x", expand=True, pady=5)
        tk.Label(card, text=t_title, font=("Microsoft JhengHei", sf(10), "bold"), fg=theme["accent"], bg=theme["widget_bg"]).pack(anchor="w")
        tk.Label(card, text=t_desc, font=("Microsoft JhengHei", sf(10)), fg=theme["widget_fg"], bg=theme["widget_bg"], justify="left", wraplength=760).pack(anchor="w", pady=(4, 0))

    # 📌 3. 版本對比
    tab_ver = create_scrollable_tab("📑 版本對比")
    ver_card = tk.Frame(tab_ver, bg=theme["widget_bg"], bd=1, relief="solid", padx=12, pady=10)
    ver_card.pack(fill="x", pady=(0, 10))
    tk.Label(ver_card, text=f"📌 本地電腦先前安裝紀錄版本：{LOCAL_PREVIOUS_VERSION}", font=("Microsoft JhengHei", sf(10), "bold"), fg="#E06C75", bg=theme["widget_bg"]).pack(anchor="w")
    tk.Label(ver_card, text=f"✨ 當前系統升級執行版本：{CURRENT_VERSION}", font=("Microsoft JhengHei", sf(10), "bold"), fg="#98C379", bg=theme["widget_bg"]).pack(anchor="w", pady=(2, 0))

    tk.Label(tab_ver, text="🔍 相較於您本地電腦的歷史舊版，v7.6.3 帶來的重要改進：", font=("Microsoft JhengHei", sf(10), "bold"), fg=theme["accent"], bg=theme["inner_bg"]).pack(anchor="w", pady=(6, 4))

    diff_items = [
        ("PyInstaller 安全性驗證死結修復 (Hotfix)", "在熱更新重啟邏輯中，強制延長母處理序生命週期 3 秒鐘。", "完美解決新版程式 Bootloader 因無法追蹤母處理序而觸發 Security validation failure 的系統崩潰，保障更新無縫完成。"),
        ("記憶體 OCR 管線枯竭修復 (Hotfix)", "捨棄 `[Console]::In.ReadToEnd()`，改由 f-string 將 Base64 直接注入 PowerShell 變數。", "徹底解決管線 EOF 讀取衝突，保證大尺寸截圖 100% 成功傳送至 OCR 引擎而不崩潰。"),
        ("微小字體辨識升級 (Lanczos Upscaling)", "當截圖區域低於 400x150 時，系統自動透過 PIL 呼叫 Lanczos 演算法進行 3 倍無損放大。", "奇蹟般增強 Windows 原生 OCR 引擎對遊戲內小字體或模糊邊緣文字的靈敏度。"),
        ("Google Gemini 原生雙引擎矩陣導入", "在核心 API 抽象層加入對 `gemini-1.5-flash`, `gemini-1.5-pro` 的支援，動態解析模型前綴發送至 Google API 端點。", "提供多雲容錯與模型備援能力，再也不怕單一供應商斷線或額度耗盡，且零套件安裝相依。"),
        ("OSD 視覺回饋狀態機持久化 (Stateful OSD)", "重構 `show_osd` 支援 `auto_hide=False` 參數，讓系統在執行耗時任務（如 AI 思考、語音辨識）時，OSD 提示會持續懸浮在螢幕中央不消失。", "極大化系統狀態可視性，給予使用者明確的操作進度與安全感。")
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
    hist_canvas.pack(side="left", fill="both", expand=True)
    hist_scrollbar.pack(side="right", fill="y")
    
    def _hist_mousewheel(event):
        hist_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    def _bind_hist_mw(e):
        hist_canvas.bind_all("<MouseWheel>", _hist_mousewheel)
    def _unbind_hist_mw(e):
        hist_canvas.unbind_all("<MouseWheel>")
    hist_container.bind("<Enter>", _bind_hist_mw)
    hist_container.bind("<Leave>", _unbind_hist_mw)

    def refresh_history_tab_ui():
        for widget in hist_scrollable_frame.winfo_children(): widget.destroy()
        with history_lock:
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
            with history_lock:
                save_history([])
            refresh_history_tab_ui()
            set_status("🧹 歷史紀錄已清空", "#98C379")
            show_osd("🧹 歷史紀錄已清空", auto_hide=True)
            root.after(1500, hide_status)

    tk.Button(hist_btn_frame, text="🗑️ 清空所有歷史紀錄", command=manual_clear_history_tab, bg="#E06C75", fg="white", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=12, pady=6).pack(side="left")

    # 📌 5. 系統設定
    tab_settings = create_scrollable_tab("⚙️ 系統設定")

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

    manual_repair_btn = tk.Button(lock_bar, text="⚡ 一鍵手動重置核心", command=auto_execute_system_repair, bg="#98C379", fg="white", font=("Microsoft JhengHei", sf(9), "bold"), relief="flat", padx=10, pady=3)
    manual_repair_btn.pack(side="right", padx=(0, 8))

    guide_card = tk.Frame(tab_settings, bg=theme["widget_bg"], bd=1, relief="solid", padx=12, pady=10)
    guide_card.pack(fill="x", pady=(0, 10))
    tk.Label(guide_card, text="💡 取得 免費 API Key：", font=("Microsoft JhengHei", sf(10), "bold"), fg="#98C379", bg=theme["widget_bg"]).pack(anchor="w")
    tk.Label(guide_card, text="1. Groq API：至 console.groq.com 申請極速模型。\n2. Google Gemini API：至 aistudio.google.com 申請強大推理模型。\n3. Tavily Search API：至 tavily.com 註冊免費取得。", font=("Microsoft JhengHei", sf(10)), fg=theme["widget_fg"], bg=theme["widget_bg"], justify="left").pack(anchor="w", pady=(2, 6))

    btn_f_urls = tk.Frame(guide_card, bg=theme["widget_bg"])
    btn_f_urls.pack(anchor="w")
    tk.Button(btn_f_urls, text="🌐 開啟 Groq 官網", command=lambda: webbrowser.open("https://console.groq.com/"), bg="#61AFEF", fg="#21252B", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=8, pady=2).pack(side="left", padx=(0, 6))
    tk.Button(btn_f_urls, text="🧠 開啟 Gemini 官網", command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey"), bg="#C678DD", fg="#21252B", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=8, pady=2).pack(side="left", padx=(0, 6))
    tk.Button(btn_f_urls, text="🔍 開啟 Tavily 官網", command=lambda: webbrowser.open("https://tavily.com/"), bg="#E5C07B", fg="#21252B", font=("Microsoft JhengHei", sf(10), "bold"), relief="flat", padx=8, pady=2).pack(side="left")

    autostart_var = tk.BooleanVar(value=config.get("autostart", True))
    chk_autostart = tk.Checkbutton(tab_settings, text="🚀 開機自動啟動 (Windows 啟動資料夾捷徑)", variable=autostart_var, font=("Microsoft JhengHei", sf(10), "bold"), fg="#98C379", bg=theme["inner_bg"], selectcolor=theme["widget_bg"])
    chk_autostart.pack(anchor="w", pady=(4, 6))

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

    tk.Label(tab_settings, text="🔑 Groq API Key：", font=("Microsoft JhengHei", sf(10), "bold"), fg=theme["widget_fg"], bg=theme["inner_bg"]).pack(anchor="w", pady=(4, 2))
    entry_api = tk.Entry(tab_settings, font=("Consolas", sf(11)), show="*")
    entry_api.pack(fill="x", anchor="w", pady=(0, 8), ipady=3)
    if GROQ_API_KEY: entry_api.insert(0, GROQ_API_KEY)

    tk.Label(tab_settings, text="🔑 Google Gemini API Key：", font=("Microsoft JhengHei", sf(10), "bold"), fg="#C678DD", bg=theme["inner_bg"]).pack(anchor="w", pady=(4, 2))
    entry_gemini = tk.Entry(tab_settings, font=("Consolas", sf(11)), show="*")
    entry_gemini.pack(fill="x", anchor="w", pady=(0, 8), ipady=3)
    if GEMINI_API_KEY: entry_gemini.insert(0, GEMINI_API_KEY)

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
        global GROQ_API_KEY, GEMINI_API_KEY, TAVILY_API_KEY, CUSTOM_PROMPT_1, CUSTOM_PROMPT_2, CURRENT_THEME_NAME, FONT_SCALE, MODEL_VOICE, MODEL_CHAT, MODEL_SELECTION, is_settings_locked
        key = entry_api.get().strip()
        gemini_key = entry_gemini.get().strip()
        t_key = entry_tavily.get().strip()
        
        if key or gemini_key:
            MODEL_VOICE = combo_v.get().split(" ")[0]
            MODEL_CHAT = combo_c.get().split(" ")[0]
            MODEL_SELECTION = combo_s.get().split(" ")[0]
            selected_scale = SCALE_OPTIONS.get(scale_combo.get(), 1.35)
            
            GROQ_API_KEY, GEMINI_API_KEY, TAVILY_API_KEY, CUSTOM_PROMPT_1, CUSTOM_PROMPT_2, CURRENT_THEME_NAME, FONT_SCALE = key, gemini_key, t_key, entry_p1.get().strip(), entry_p2.get().strip(), theme_combo.get(), selected_scale
            set_autostart(autostart_var.get())
            
            save_config({
                "groq_api_key": key,
                "gemini_api_key": gemini_key,
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
            messagebox.showwarning("提示", "至少需填入一個 Groq 或 Gemini API Key！", parent=win)

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
        entry_gemini.config(state=state_str)
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
         "【問題原因】：輸入的 Groq/Gemini API Key 不正確、過期或包含空格。\n"
         "【自主排除步驟】：前往「系統設定」點擊「🔓 解鎖設定」，重新貼上平台產生的正確 API Key 並儲存。"),
        
        ("HTTP 429 Rate Limit Exceeded", 
         "【問題原因】：觸發免費帳號每日 Token 額度上限。\n"
         "【自主排除步驟】：由於系統支援雙引擎，您可以填入另一家的 API Key 讓系統自動容錯備援。"),

        ("AI 人物或時事回答不準確 (幻覺問題)", 
         "【問題原因】：舊版爬蟲抓取資訊破碎或 AI 憑記憶猜測。\n"
         "【自主排除步驟】：前往「系統設定」填入 Tavily API Key，並在 AI 對話中點擊「清空對話紀錄」重新提問即可解決。")
    ]

    for e_title, e_desc in trouble_shooting_list:
        card = tk.Frame(tab_err, bg=theme["widget_bg"], bd=1, relief="solid", padx=12, pady=10)
        card.pack(fill="x", expand=True, pady=5)
        tk.Label(card, text=f"❓ {e_title}", font=("Microsoft JhengHei", sf(10), "bold"), fg="#E5C07B", bg=theme["widget_bg"]).pack(anchor="w")
        tk.Label(card, text=e_desc, font=("Microsoft JhengHei", sf(10)), fg=theme["widget_fg"], bg=theme["widget_bg"], justify="left", wraplength=760).pack(anchor="w", pady=(4, 0))

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
    tk.Button(btn_frame, text="複製結果並關閉", command=lambda: [safe_clipboard_copy(result_text), win.destroy(), globals().update(ai_result_win=None)], bg="#4CAF50", fg="white", font=("Microsoft JhengHei", sf(10), "bold")).pack(side="right")
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
            if hk_id == 12: 
                toggle_pause_mode()
                continue
            if is_paused: continue
            
            if hk_id == 8: 
                show_osd("📸 截圖 OCR 辨識", auto_hide=False)
                root.after(0, lambda: SnippingTool())
            elif hk_id == 4: 
                show_osd("✏️ 劃詞原地替換", auto_hide=False)
                threading.Thread(target=process_selection, args=("replace",), daemon=True).start()
            elif hk_id == 2: 
                trigger_mode("en")
            elif hk_id == 3: 
                show_osd("🔍 劃詞翻譯", auto_hide=False)
                threading.Thread(target=process_selection, args=("translate",), daemon=True).start()
            elif hk_id == 1: 
                trigger_mode("zh")
            elif hk_id == 5: 
                show_osd("✨ AI 潤飾摘要", auto_hide=False)
                threading.Thread(target=process_selection, args=("ai_refine",), daemon=True).start()
            elif hk_id == 9: 
                show_osd("🎯 自訂提示 1", auto_hide=False)
                threading.Thread(target=process_selection, args=("custom_1",), daemon=True).start()
            elif hk_id == 10: 
                show_osd("🎯 自訂提示 2", auto_hide=False)
                threading.Thread(target=process_selection, args=("custom_2",), daemon=True).start()
            elif hk_id == 11: 
                show_osd("🔊 語音朗讀 (TTS)", auto_hide=False)
                threading.Thread(target=process_tts, daemon=True).start()
            elif hk_id == 13: 
                show_osd("💬 實時對話面板", auto_hide=True)
                toggle_chat_panel()
            elif hk_id == 6: 
                show_osd("⚙️ 系統控制中心", auto_hide=True)
                prompt_api_key_gui()
            elif hk_id == 7: 
                threading.Thread(target=exit_program, daemon=True).start()
        user32.TranslateMessage(ctypes.byref(msg)); user32.DispatchMessageW(ctypes.byref(msg))

if __name__ == "__main__":
    try:
        threading.Thread(target=win32_hotkey_loop, daemon=True).start()
        init_gui()
        root.mainloop()
    except Exception as e:
        print(f"Critical Exception: {e}")