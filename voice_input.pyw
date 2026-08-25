import io
import time
import threading
import json
import os
import sys
import subprocess
import webbrowser
import urllib.parse
import requests
import ctypes
from ctypes import wintypes
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import pyperclip
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import base64
from PIL import Image, ImageDraw, ImageGrab
import winsound  # 🔊 Windows 內建提示音模組

# 🌟 視窗高解析度字體銳利化 (DPI Awareness)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
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

# 嘗試載入 OpenCC 進行簡轉繁
try:
    from opencc import OpenCC
    converter = OpenCC('s2twp')
    def to_tw_trad(text):
        return converter.convert(text)
except Exception:
    def to_tw_trad(text):
        return text

# ================= 設定與版本區 =================
CURRENT_VERSION = "v2.9.9"
GITHUB_RELEASE_URL = "https://api.github.com/repos/syz0930450116-bot/GroqVoiceTool/releases/latest"

APPDATA_DIR = os.path.join(os.getenv('LOCALAPPDATA'), 'GroqVoiceTool')
os.makedirs(APPDATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(APPDATA_DIR, "config.json")
HISTORY_FILE = os.path.join(APPDATA_DIR, "history.json")
SCREENSHOT_DIR = os.path.join(APPDATA_DIR, "Screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

SAMPLE_RATE = 16000

HOTKEY_IDS = {
    1: ("zh (Alt + S)", 0x0001, 0x53),               # ID 1: Alt + S (繁中智慧排版)
    2: ("en (Alt + Shift + S)", 0x0001 | 0x0004, 0x53),      # ID 2: Alt + Shift + S (中譯英)
    3: ("trans (Alt + C)", 0x0001, 0x43),            # ID 3: Alt + C (劃詞翻譯)
    4: ("replace (Alt + Shift + C)", 0x0001 | 0x0004, 0x43), # ID 4: Alt + Shift + C (劃詞替換)
    5: ("ai (Alt + A)", 0x0001, 0x41),               # ID 5: Alt + A (AI 潤飾)
    6: ("help (Alt + H)", 0x0001, 0x48),             # ID 6: Alt + H (說明卡)
    7: ("quit (Alt + Shift + Q)", 0x0001 | 0x0004, 0x51),    # ID 7: Alt + Shift + Q (退出)
    8: ("ocr (Alt + X)", 0x0001, 0x58),              # ID 8: Alt + X (截圖翻譯)
    9: ("custom_1 (Alt + 1)", 0x0001, 0x31),         # ID 9: Alt + 1 (自訂指令 1)
    10: ("custom_2 (Alt + 2)", 0x0001, 0x32),        # ID 10: Alt + 2 (自訂指令 2)
    11: ("tts (Alt + T)", 0x0001, 0x54),             # ID 11: Alt + T (語音朗讀)
    12: ("pause (Alt + Shift + P)", 0x0001 | 0x0004, 0x50),  # ID 12: Alt + Shift + P (防誤觸暫停)
    13: ("spotlight (Alt + Q)", 0x0001, 0x51),        # ID 13: Alt + Q (萬能指令與對話列)
    14: ("macro (Alt + M)", 0x0001, 0x4D)            # ID 14: Alt + M (語音指令巨集)
}

# ----------------- 主題色系定義 -----------------
THEMES = {
    "暗夜駭客 (Dark Hacker)": {
        "widget_bg": "#21252B",
        "widget_fg": "#FFFFFF",
        "btn_bg": "#4B5263",
        "accent": "#61AFEF",
        "card_bg": "#1E1E1E",
        "inner_bg": "#252526"
    },
    "賽博霓虹 (Cyberpunk Neon)": {
        "widget_bg": "#0F0E17",
        "widget_fg": "#FFFFFE",
        "btn_bg": "#3A3F58",
        "accent": "#FF8906",
        "card_bg": "#0F0E17",
        "inner_bg": "#2E2F3E"
    },
    "極簡純白 (Clean Minimalist)": {
        "widget_bg": "#F4F4F9",
        "widget_fg": "#101820",
        "btn_bg": "#D1D5DB",
        "accent": "#004643",
        "card_bg": "#FFFFFF",
        "inner_bg": "#F9FAFB"
    }
}

MODEL_MAP = {
    "openai/gpt-oss-20b": "openai/gpt-oss-20b (綜合平衡 / 日常推薦)",
    "llama-3.3-70b-versatile": "llama-3.3-70b-versatile (高階推理 / 精準複雜)",
    "llama-3.1-8b-instant": "llama-3.1-8b-instant (極速響應 / 輕量快閃)",
    "mixtral-8x7b-32768": "mixtral-8x7b-32768 (長文本支援 / 長容量)"
}

# ----------------- 自動更新模組 -----------------
def check_for_updates():
    if not getattr(sys, 'frozen', False): return
    try:
        resp = requests.get(GITHUB_RELEASE_URL, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            latest_tag = data.get("tag_name", "").strip()
            if latest_tag and latest_tag != CURRENT_VERSION:
                exe_asset = next((a for a in data.get("assets", []) if a.get("name", "").endswith(".exe")), None)
                if exe_asset:
                    set_status(f"🚀 發現新版本 {latest_tag}，更新中...", "#61AFEF")
                    r = requests.get(exe_asset.get("browser_download_url"), stream=True, timeout=30)
                    new_exe_path = os.path.join(APPDATA_DIR, "update_temp.exe")
                    with open(new_exe_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
                    
                    bat_path = os.path.join(APPDATA_DIR, "update.bat")
                    bat_content = f'@echo off\ntimeout /t 2 /nobreak > NUL\nmove /y "{new_exe_path}" "{sys.executable}"\nstart "" "{sys.executable}"\ndel "%~f0"\n'
                    with open(bat_path, "w", encoding="utf-8") as f: f.write(bat_content)
                    
                    set_status("🔄 更新完成，重啟中...", "#98C379")
                    time.sleep(1.0)
                    subprocess.Popen(bat_path, shell=True)
                    os._exit(0)
    except Exception: pass

# ----------------- 配置檔與歷史紀錄管理 -----------------
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
        if len(history) > 50:
            history = history[:50]
        save_history(history)
    except Exception: pass

config = load_config()
GROQ_API_KEY = config.get("groq_api_key", "")
CUSTOM_PROMPT_1 = config.get("custom_prompt_1", "請幫我將這段文字翻譯為專業的商用日文。")
CUSTOM_PROMPT_2 = config.get("custom_prompt_2", "請幫我把這段草稿改寫成委婉客氣的正式信件語氣。")
CURRENT_THEME_NAME = config.get("theme", "暗夜駭客 (Dark Hacker)")
AI_MODEL = config.get("ai_model", "openai/gpt-oss-20b")

recording = False
is_processing = False
is_paused = False
auto_clipboard_enabled = False
last_clipboard_text = ""
audio_data = []
stream = None
current_mode = "zh"
last_trigger_time = 0
root = None
status_win = None
status_label = None
tray_icon = None
floating_win = None
clip_btn_ref = None
spotlight_win = None
history_win = None
ai_result_win = None
chat_panel_win = None

# 🧠 對話記憶陣列
spotlight_history = [
    {"role": "system", "content": "你是一個高效、溫暖且全能的 AI 桌面助理。請用簡潔、專業且符合台灣用語習慣的繁體中文回答使用者的問題。並記住之前的對話脈絡進行連續討論。"}
]

def get_theme():
    return THEMES.get(CURRENT_THEME_NAME, THEMES["暗夜駭客 (Dark Hacker)"])

# ----------------- UI 系統 -----------------
def init_gui():
    global root, status_win, status_label
    root = tk.Tk()
    root.withdraw()

    status_win = tk.Toplevel(root)
    status_win.overrideredirect(True)
    status_win.attributes("-topmost", True)
    status_win.withdraw()
    
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    status_win.geometry(f"210x36+{sw - 235}+{sh - 96}")

    status_label = tk.Label(status_win, text="", font=("Microsoft JhengHei", 10, "bold"), fg="#FFFFFF")
    status_label.pack(fill="both", expand=True)

    show_startup_notice()
    toggle_floating_widget()
    
    threading.Thread(target=check_for_updates, daemon=True).start()
    threading.Thread(target=clipboard_monitor_loop, daemon=True).start()
    if TRAY_AVAILABLE: threading.Thread(target=setup_system_tray, daemon=True).start()
    if not GROQ_API_KEY: root.after(1500, prompt_api_key_gui)

def update_status_ui(text, bg_color):
    if status_win and status_label:
        status_label.config(text=text, bg=bg_color)
        status_win.configure(bg=bg_color)
        status_win.deiconify()

def hide_status_ui():
    if status_win: status_win.withdraw()

def set_status(text, bg_color):
    if root: root.after(0, update_status_ui, text, bg_color)

def hide_status():
    if root: root.after(0, hide_status_ui)

def show_startup_notice():
    set_status("🚀 助理 v2.9.9 提示優化版已啟動", "#98C379")
    if root: root.after(2000, hide_status)

def exit_program():
    set_status("👋 助理已關閉", "#E06C75")
    time.sleep(0.8)
    if tray_icon: tray_icon.stop()
    os._exit(0)

# ----------------- 💬 AI 聊天面板 -----------------
def toggle_chat_panel():
    root.after(0, _toggle_chat_panel_main)

def _toggle_chat_panel_main():
    global chat_panel_win
    if not GROQ_API_KEY:
        set_status("⚠️ 未設定 API Key", "#E06C75")
        root.after(1500, hide_status)
        prompt_api_key_gui()
        return

    if chat_panel_win is not None:
        try:
            chat_panel_win.destroy()
        except Exception:
            pass
        chat_panel_win = None
        return

    theme = get_theme()
    win = tk.Toplevel(root)
    win.title("Groq AI 互動聊天面板")
    win.attributes("-topmost", True)
    win.geometry(f"580x640+{(root.winfo_screenwidth()-580)//2}+{(root.winfo_screenheight()-640)//2}")
    win.configure(bg=theme["card_bg"])

    header_frame = tk.Frame(win, bg=theme["card_bg"])
    header_frame.pack(fill="x", padx=16, pady=(14, 8))

    tk.Label(header_frame, text="💬 AI 連續對話聊天室", font=("Microsoft JhengHei", 12, "bold"), fg=theme["accent"], bg=theme["card_bg"]).pack(side="left")

    def clear_chat_memory():
        global spotlight_history
        spotlight_history = [{"role": "system", "content": "你是一個高效、溫暖且全能的 AI 桌面助理。請用簡潔、專業且符合台灣用語習慣的繁體中文回答使用者的問題。"}]
        chat_box.config(state="normal")
        chat_box.delete("1.0", tk.END)
        chat_box.insert(tk.END, "系統：對話記憶已重置。\n\n")
        chat_box.config(state="disabled")
        set_status("🧹 對話記憶已清空", "#98C379")
        root.after(1500, hide_status)

    tk.Button(header_frame, text="清除記憶", command=clear_chat_memory, bg="#E06C75", fg="white", font=("Microsoft JhengHei", 8, "bold"), relief="flat", padx=8, pady=3).pack(side="right")

    chat_box = scrolledtext.ScrolledText(win, font=("Microsoft JhengHei", 10), wrap="word", bg=theme["inner_bg"], fg=theme["widget_fg"], state="normal", padx=8, pady=8)
    chat_box.pack(fill="both", expand=True, padx=16, pady=4)

    for msg in spotlight_history:
        role = msg.get("role")
        content = msg.get("content")
        if role == "user":
            chat_box.insert(tk.END, f"👤 你：\n{content}\n\n")
        elif role == "assistant":
            chat_box.insert(tk.END, f"🤖 AI 助理：\n{content}\n\n")
    chat_box.config(state="disabled")
    chat_box.see(tk.END)

    input_frame = tk.Frame(win, bg=theme["card_bg"])
    input_frame.pack(fill="x", padx=16, pady=(8, 14))

    entry = tk.Entry(input_frame, font=("Microsoft JhengHei", 11), bg=theme["inner_bg"], fg=theme["widget_fg"], insertbackground=theme["widget_fg"])
    entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=5)
    entry.insert(0, "輸入訊息與 AI 對話...")
    entry.selection_range(0, tk.END)

    def on_entry_focus(e):
        if entry.get().startswith("輸入訊息"):
            entry.delete(0, tk.END)

    entry.bind("<FocusIn>", on_entry_focus)

    def send_chat_message(event=None):
        global spotlight_history
        text = entry.get().strip()
        if not text or text.startswith("輸入訊息"):
            return
        
        entry.delete(0, tk.END)
        chat_box.config(state="normal")
        chat_box.insert(tk.END, f"👤 你：\n{text}\n\n")
        chat_box.config(state="disabled")
        chat_box.see(tk.END)

        set_status("💬 AI 思考中...", "#61AFEF")
        spotlight_history.append({"role": "user", "content": text})
        if len(spotlight_history) > 16:
            spotlight_history = [spotlight_history[0]] + spotlight_history[-15:]

        def background_query():
            try:
                headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                payload = {"model": AI_MODEL, "messages": spotlight_history, "temperature": 0.4}
                resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
                if resp.status_code == 200:
                    res_json = resp.json()
                    if "choices" in res_json and len(res_json["choices"]) > 0:
                        raw_content = res_json["choices"][0]["message"]["content"].strip()
                        if "</think>" in raw_content:
                            raw_content = raw_content.split("</think>")[-1].strip()
                        ai_result = to_tw_trad(raw_content)
                        spotlight_history.append({"role": "assistant", "content": ai_result})
                        add_history_entry("聊天面板對話", text, ai_result)
                        
                        def update_ui():
                            chat_box.config(state="normal")
                            chat_box.insert(tk.END, f"🤖 AI 助理：\n{ai_result}\n\n")
                            chat_box.config(state="disabled")
                            chat_box.see(tk.END)
                            hide_status()
                        win.after(0, update_ui)
            except Exception as e:
                def err_ui():
                    hide_status()
                win.after(0, err_ui)

        threading.Thread(target=background_query, daemon=True).start()

    entry.bind("<Return>", send_chat_message)
    tk.Button(input_frame, text="傳送", command=send_chat_message, bg="#4CAF50", fg="white", font=("Microsoft JhengHei", 9, "bold"), relief="flat", padx=14, pady=5).pack(side="right")

    win.protocol("WM_DELETE_WINDOW", lambda: [win.destroy(), globals().update(chat_panel_win=None)])
    win.bind("<Escape>", lambda e: [win.destroy(), globals().update(chat_panel_win=None)])
    chat_panel_win = win

# ----------------- 📜 歷史紀錄抽屜 -----------------
def toggle_history_window():
    root.after(0, _toggle_history_window_main)

def _toggle_history_window_main():
    global history_win
    if history_win is not None:
        try:
            history_win.destroy()
        except Exception:
            pass
        history_win = None
        return

    theme = get_theme()
    win = tk.Toplevel(root)
    win.title("Groq AI 歷史紀錄抽屜")
    win.attributes("-topmost", True)
    win.geometry(f"620x550+{(root.winfo_screenwidth()-620)//2}+{(root.winfo_screenheight()-550)//2}")
    win.configure(bg=theme["card_bg"])

    tk.Label(win, text="📜 AI 操作歷史紀錄 (卡片檢視)", font=("Microsoft JhengHei", 12, "bold"), fg=theme["accent"], bg=theme["card_bg"]).pack(pady=(12, 5))

    container = tk.Frame(win, bg=theme["card_bg"])
    container.pack(fill="both", expand=True, padx=15, pady=5)

    canvas = tk.Canvas(container, bg=theme["inner_bg"], highlightthickness=0)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=theme["inner_bg"])

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width))

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    history_data = load_history()
    if not history_data:
        empty_lbl = tk.Label(scrollable_frame, text="（目前尚無歷史紀錄，快去使用翻譯、對話或語音打字吧！）", font=("Microsoft JhengHei", 10), fg=theme["widget_fg"], bg=theme["inner_bg"])
        empty_lbl.pack(pady=40, padx=20)
    else:
        for idx, item in enumerate(history_data, 1):
            card = tk.Frame(scrollable_frame, bg=theme["widget_bg"], bd=1, relief="solid", padx=10, pady=8)
            card.pack(fill="x", expand=True, padx=8, pady=6)

            header_frame = tk.Frame(card, bg=theme["widget_bg"])
            header_frame.pack(fill="x", expand=True)

            type_label = tk.Label(header_frame, text=f"📌 #{idx} [{item.get('type')}]", font=("Microsoft JhengHei", 9, "bold"), fg=theme["accent"], bg=theme["widget_bg"])
            type_label.pack(side="left")

            time_label = tk.Label(header_frame, text=item.get('time'), font=("Consolas", 8), fg="#ABB2BF", bg=theme["widget_bg"])
            time_label.pack(side="right")

            orig_text = item.get('original', '')
            if orig_text:
                tk.Label(card, text="原文 / 問題：", font=("Microsoft JhengHei", 8, "bold"), fg="#98C379", bg=theme["widget_bg"]).pack(anchor="w", pady=(4, 0))
                orig_lbl = tk.Label(card, text=orig_text, font=("Microsoft JhengHei", 9), fg=theme["widget_fg"], bg=theme["widget_bg"], justify="left", wraplength=540)
                orig_lbl.pack(anchor="w", padx=4)

            res_text = item.get('result', '')
            if res_text:
                tk.Label(card, text="AI 結果：", font=("Microsoft JhengHei", 8, "bold"), fg="#E5C07B", bg=theme["widget_bg"]).pack(anchor="w", pady=(6, 0))
                res_lbl = tk.Label(card, text=res_text, font=("Microsoft JhengHei", 9, "bold"), fg=theme["widget_fg"], bg=theme["widget_bg"], justify="left", wraplength=540)
                res_lbl.pack(anchor="w", padx=4)

            btn_row = tk.Frame(card, bg=theme["widget_bg"])
            btn_row.pack(fill="x", pady=(8, 0))

            def make_copy_cmd(r_text):
                return lambda: [pyperclip.copy(r_text), set_status("📋 已複製此筆結果", "#98C379"), root.after(1500, hide_status)]

            copy_btn = tk.Button(btn_row, text="📋 複製此筆結果", command=make_copy_cmd(res_text), bg=theme["btn_bg"], fg="white", font=("Microsoft JhengHei", 8, "bold"), relief="flat", padx=6, pady=2)
            copy_btn.pack(side="right")

    btn_frame = tk.Frame(win, bg=theme["card_bg"])
    btn_frame.pack(fill="x", pady=10, padx=15)

    def clear_history():
        if messagebox.askyesno("確認清除", "確定要清空所有歷史紀錄嗎？", parent=win):
            save_history([])
            win.destroy()
            global history_win
            history_win = None
            set_status("🗑️ 歷史紀錄已清空", "#E06C75")
            root.after(1500, hide_status)

    tk.Button(btn_frame, text="清空歷史", command=clear_history, bg="#E06C75", fg="white", font=("Microsoft JhengHei", 9, "bold"), relief="flat", padx=10, pady=4).pack(side="left")
    tk.Button(btn_frame, text="關閉 (Esc)", command=lambda: [win.destroy(), globals().update(history_win=None)], bg=theme["btn_bg"], fg=theme["widget_fg"], font=("Microsoft JhengHei", 9, "bold"), relief="flat", padx=10, pady=4).pack(side="right")
    
    win.bind("<Escape>", lambda e: [win.destroy(), globals().update(history_win=None)])
    history_win = win

# ----------------- 💬 Spotlight 萬能指令列 -----------------
def toggle_spotlight_bar():
    root.after(0, _toggle_spotlight_bar_main)

def _toggle_spotlight_bar_main():
    global spotlight_win
    if not GROQ_API_KEY:
        set_status("⚠️ 未設定 API Key", "#E06C75")
        root.after(1500, hide_status)
        prompt_api_key_gui()
        return

    if spotlight_win is not None:
        try:
            spotlight_win.destroy()
        except Exception:
            pass
        spotlight_win = None
        return

    theme = get_theme()
    win = tk.Toplevel(root)
    win.title("Groq Spotlight Universal Bar")
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.attributes("-alpha", 0.95)

    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    win.geometry(f"650x55+{(sw - 650) // 2}+{sh // 3}")
    win.configure(bg=theme["widget_bg"])

    frame = tk.Frame(win, bg=theme["inner_bg"], bd=1, relief="solid")
    frame.pack(fill="both", expand=True, padx=2, pady=2)

    entry = tk.Entry(frame, font=("Microsoft JhengHei", 13), bg=theme["inner_bg"], fg=theme["widget_fg"], insertbackground=theme["widget_fg"], relief="flat")
    entry.pack(side="left", fill="both", expand=True, padx=(12, 5), pady=10)
    entry.insert(0, " 💬 輸入指令、問題，或點右側語音按鈕...")
    entry.selection_range(0, tk.END)

    def on_focus_in(event):
        if entry.get().strip().startswith("💬"):
            entry.delete(0, tk.END)

    def execute_query(event=None):
        global spotlight_history
        query = entry.get().strip()
        if not query or query.startswith("💬"):
            return
        
        if query.lower() == "/clear":
            spotlight_history = [{"role": "system", "content": "你是一個高效、溫暖且全能的 AI 桌面助理。請用簡潔、專業且符合台灣用語習慣的繁體中文回答使用者的問題。"}]
            set_status("🧹 對話記憶已重置", "#98C379")
            root.after(1500, hide_status)
            win.destroy()
            global spotlight_win
            spotlight_win = None
            return

        win.destroy()
        spotlight_win = None
        threading.Thread(target=process_smart_query, args=(query,), daemon=True).start()

    def record_spotlight_voice():
        win.destroy()
        global spotlight_win
        spotlight_win = None
        threading.Thread(target=record_and_fill_spotlight, daemon=True).start()

    mic_btn = tk.Button(frame, text="🎤 語音", command=record_spotlight_voice, bg="#FF8906", fg="white", font=("Microsoft JhengHei", 9, "bold"), relief="flat", padx=8, pady=2)
    mic_btn.pack(side="right", padx=(0, 8), pady=8)

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<Return>", execute_query)
    win.bind("<Escape>", lambda e: [win.destroy(), globals().update(spotlight_win=None)])
    
    spotlight_win = win
    entry.focus_set()

def record_and_fill_spotlight():
    global is_processing
    if not GROQ_API_KEY: return
    is_processing = True
    set_status("🎙️ 聆聽 Spotlight 語音中...", "#FF8906")
    winsound.Beep(800, 120)

    audio_chunks = []
    def mic_callback(indata, frames, time_info, status):
        audio_chunks.append(indata.copy())

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=mic_callback)
    stream.start()
    time.sleep(4.0)
    stream.stop()
    stream.close()
    winsound.Beep(600, 150)

    if audio_chunks:
        try:
            audio_array = np.concatenate(audio_chunks, axis=0)
            wav_buffer = io.BytesIO()
            write(wav_buffer, SAMPLE_RATE, (audio_array * 32767).astype(np.int16))
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
            
            resp = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, 
                                 files={"file": ("audio.wav", wav_buffer.getvalue(), "audio/wav"), "model": (None, "whisper-large-v3"), "language": (None, "zh")}, timeout=10)
            
            if resp.status_code == 200:
                spoken_text = resp.json().get("text", "").strip()
                if spoken_text:
                    set_status(f"✨ 識別: {spoken_text}", "#98C379")
                    threading.Thread(target=process_smart_query, args=(spoken_text,), daemon=True).start()
                    return
        except Exception as e:
            print(f"[Spotlight Voice Error] {e}")
    is_processing = False
    hide_status()

def process_smart_query(query):
    global is_processing, spotlight_history
    is_processing = True
    set_status("⚙️ AI 智慧意圖解析中...", "#C678DD")
    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        sys_intent_prompt = (
            "你是一個全能 AI 桌面助理的智慧意圖解析器。請根據使用者輸入的文字，判斷是否為「系統硬體控制、開啟應用程式、查詢天氣、或網頁搜尋」，並提取相關參數。\n"
            "可用動作代號：\n"
            "1. SYS_VOLUME_UP （音量調大、增大聲音）\n"
            "2. SYS_VOLUME_DOWN （音量調小、減小聲音）\n"
            "3. SYS_MUTE （靜音）\n"
            "4. OPEN_NOTEPAD （開啟記事本）\n"
            "5. OPEN_CALCULATOR （開啟計算機）\n"
            "6. OPEN_STEAM （開啟 Steam）\n"
            "7. GET_WEATHER （查詢天氣，需填入 city 欄位，如台北、台中）\n"
            "8. SEARCH_GOOGLE （用 Google 搜尋，需填入 query）\n"
            "9. SEARCH_YOUTUBE （在 YouTube 搜尋，需填入 query）\n"
            "10. OPEN_GMAIL （開啟 Gmail）\n"
            "11. NORMAL_CHAT （一般 AI 對話、寫作、翻譯或問答，非上述系統動作）\n"
            "請嚴格回傳標準 JSON 格式：\n"
            "{\"action\": \"代號\", \"query\": \"\", \"city\": \"\", \"reply\": \"簡短說明\"}"
        )
        
        intent_payload = {
            "model": AI_MODEL,
            "messages": [
                {"role": "system", "content": sys_intent_prompt},
                {"role": "user", "content": query}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        intent_resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=intent_payload, timeout=10)
        
        if intent_resp.status_code == 200:
            content = intent_resp.json()["choices"][0]["message"]["content"].strip()
            if "</think>" in content:
                content = content.split("</think>")[-1].strip()
            res_json = json.loads(content)
            action = res_json.get("action", "NORMAL_CHAT")
            q_val = res_json.get("query", "").strip()
            city = res_json.get("city", "Taipei").strip()

            if action == "SYS_VOLUME_UP":
                for _ in range(5):
                    ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
                set_status("🔊 已調高音量", "#98C379")
                winsound.Beep(1000, 100)
                add_history_entry("萬能列系統控制", query, "已調高音量")
                root.after(1500, hide_status)
                return
            elif action == "SYS_VOLUME_DOWN":
                for _ in range(5):
                    ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)
                set_status("🔉 已調低音量", "#98C379")
                winsound.Beep(800, 100)
                add_history_entry("萬能列系統控制", query, "已調低音量")
                root.after(1500, hide_status)
                return
            elif action == "SYS_MUTE":
                ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)
                set_status("🔇 已切換靜音", "#E5C07B")
                winsound.Beep(600, 100)
                add_history_entry("萬能列系統控制", query, "已切換靜音")
                root.after(1500, hide_status)
                return
            elif action == "OPEN_NOTEPAD":
                os.system("start notepad")
                set_status("📝 已開啟記事本", "#98C379")
                add_history_entry("萬能列系統控制", query, "已開啟記事本")
                root.after(1500, hide_status)
                return
            elif action == "OPEN_CALCULATOR":
                os.system("start calc")
                set_status("🔢 已開啟計算機", "#98C379")
                add_history_entry("萬能列系統控制", query, "已開啟計算機")
                root.after(1500, hide_status)
                return
            elif action == "OPEN_STEAM":
                os.system("start steam://")
                set_status("🎮 已開啟 Steam", "#98C379")
                add_history_entry("萬能列系統控制", query, "已開啟 Steam")
                root.after(1500, hide_status)
                return
            elif action == "GET_WEATHER":
                set_status("🌦️ 查詢即時天氣中...", "#61AFEF")
                w_resp = requests.get(f"https://wttr.in/{urllib.parse.quote(city)}?format=3", timeout=5)
                w_text = w_resp.text.strip() if w_resp.status_code == 200 else "無法取得天氣資訊"
                add_history_entry("萬能列天氣查詢", query, w_text)
                show_ai_window(f"🌦️ 即時天氣查詢 ({city})", query, w_text)
                return
            elif action == "SEARCH_GOOGLE":
                q_str = urllib.parse.quote(q_val if q_val else query)
                webbrowser.open(f"https://www.google.com/search?q={q_str}")
                set_status("🌐 Google 搜尋完成", "#98C379")
                root.after(1500, hide_status)
                return
            elif action == "SEARCH_YOUTUBE":
                q_str = urllib.parse.quote(q_val if q_val else query)
                webbrowser.open(f"https://www.youtube.com/results?search_query={q_str}")
                set_status("▶️ YouTube 搜尋完成", "#98C379")
                root.after(1500, hide_status)
                return
            elif action == "OPEN_GMAIL":
                webbrowser.open("https://mail.google.com")
                set_status("✉️ 已開啟 Gmail", "#98C379")
                root.after(1500, hide_status)
                return

        set_status("💬 AI 思考中...", "#61AFEF")
        spotlight_history.append({"role": "user", "content": query})
        if len(spotlight_history) > 16:
            spotlight_history = [spotlight_history[0]] + spotlight_history[-15:]

        payload = {
            "model": AI_MODEL,
            "messages": spotlight_history,
            "temperature": 0.4
        }
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            res_json = resp.json()
            if "choices" in res_json and len(res_json["choices"]) > 0:
                raw_content = res_json["choices"][0]["message"]["content"].strip()
                if "</think>" in raw_content:
                    raw_content = raw_content.split("</think>")[-1].strip()
                ai_result = to_tw_trad(raw_content)
                spotlight_history.append({"role": "assistant", "content": ai_result})
                add_history_entry("萬能列連續對話", query, ai_result)
                show_ai_window("💬 AI 智慧對話結果", query, ai_result)
        else:
            show_ai_window("查詢失敗", query, resp.text)
    except Exception as e:
        show_ai_window("查詢異常", query, str(e))
    finally:
        is_processing = False
        hide_status()

# ----------------- 📋 剪貼簿自動監控模組 -----------------
def toggle_auto_clipboard():
    global auto_clipboard_enabled, last_clipboard_text
    auto_clipboard_enabled = not auto_clipboard_enabled
    if auto_clipboard_enabled:
        try:
            last_clipboard_text = pyperclip.paste().strip()
        except Exception:
            last_clipboard_text = ""
        set_status("📋 自動剪貼簿翻譯：已開啟", "#56B6C2")
        winsound.Beep(1000, 100)
    else:
        set_status("📋 自動剪貼簿翻譯：已關閉", "#E5C07B")
        winsound.Beep(500, 100)
    root.after(1500, hide_status)
    root.after(0, update_clip_button_appearance)

def update_clip_button_appearance():
    global clip_btn_ref
    if clip_btn_ref is not None:
        try:
            theme = get_theme()
            clip_bg = theme["accent"] if auto_clipboard_enabled else theme["btn_bg"]
            clip_text = "📋開" if auto_clipboard_enabled else "📋關"
            clip_btn_ref.config(text=clip_text, bg=clip_bg)
        except Exception:
            pass

def clipboard_monitor_loop():
    global last_clipboard_text
    while True:
        time.sleep(0.8)
        if not auto_clipboard_enabled or is_paused or is_processing or not GROQ_API_KEY:
            continue
        try:
            current_text = pyperclip.paste().strip()
            if current_text and current_text != last_clipboard_text:
                if len(current_text) < 2000:
                    last_clipboard_text = current_text
                    threading.Thread(target=process_auto_clipboard, args=(current_text,), daemon=True).start()
        except Exception:
            pass

def process_auto_clipboard(text):
    global last_clipboard_text, is_processing
    is_processing = True
    set_status("📋 背景翻譯中...", "#56B6C2")
    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        sys_prompt = "你是一個精通多國語言的專業翻譯員。將輸入的文字精準翻譯為流暢、符合台灣用語習慣的繁體中文。只需直接輸出翻譯結果，不要任何多餘引號或說明。"
        payload = {
            "model": AI_MODEL,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": 0.2
        }
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
        
        if resp.status_code == 200:
            res_json = resp.json()
            if "choices" in res_json and len(res_json["choices"]) > 0:
                raw_content = res_json["choices"][0]["message"]["content"].strip()
                if "</think>" in raw_content:
                    raw_content = raw_content.split("</think>")[-1].strip()
                translated = to_tw_trad(raw_content)
                if translated:
                    pyperclip.copy(translated)
                    last_clipboard_text = translated
                    add_history_entry("自動剪貼簿翻譯", text, translated)
                    set_status("📋 翻譯完成並已覆蓋剪貼簿", "#98C379")
                    winsound.Beep(1200, 80)
                    root.after(1500, hide_status)
    except Exception:
        pass
    finally:
        is_processing = False

# ----------------- 語音巨集解析器 (Alt + M) -----------------
def process_voice_macro(data):
    global is_processing, spotlight_history
    if not GROQ_API_KEY:
        is_processing = False
        prompt_api_key_gui()
        return
    try:
        audio_array = np.concatenate(data, axis=0)
        wav_buffer = io.BytesIO()
        write(wav_buffer, SAMPLE_RATE, (audio_array * 32767).astype(np.int16))
        
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        set_status("🎙️ 語音助理接收指令中...", "#D19A66")
        
        resp = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, 
                             files={"file": ("audio.wav", wav_buffer.getvalue(), "audio/wav"), "model": (None, "whisper-large-v3"), "language": (None, "zh")}, timeout=10)
        
        if resp.status_code == 200:
            raw_text = resp.json().get("text", "").strip()
            if raw_text:
                process_smart_query(raw_text)
    except Exception as e:
        show_ai_window("助理執行異常", "程式發生錯誤", str(e))
    finally:
        is_processing = False

# ----------------- 🌟 懸浮快捷小工具 (v2.9.9) -----------------
def toggle_floating_widget():
    root.after(0, _toggle_floating_widget_main)

def refresh_floating_widget():
    global floating_win
    if floating_win is not None:
        try:
            floating_win.destroy()
        except Exception:
            pass
        floating_win = None
        _toggle_floating_widget_main()

def _toggle_floating_widget_main():
    global floating_win, clip_btn_ref
    if floating_win is not None:
        try:
            floating_win.destroy()
        except Exception:
            pass
        floating_win = None
        clip_btn_ref = None
        set_status("🥷 懸浮工具已隱藏", "#E5C07B")
        root.after(1500, hide_status)
    else:
        theme = get_theme()
        widget_win = tk.Toplevel(root)
        widget_win.title("Groq Floating Tool")
        widget_win.overrideredirect(True)
        widget_win.attributes("-topmost", True)
        widget_win.attributes("-alpha", 0.35)
        
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        widget_win.geometry(f"410x30+{sw - 430}+{sh - 92}")
        widget_win.configure(bg=theme["widget_bg"])
        
        def on_enter(event):
            widget_win.attributes("-alpha", 0.95)

        def on_leave(event):
            widget_win.attributes("-alpha", 0.35)

        widget_win.bind("<Enter>", on_enter)
        widget_win.bind("<Leave>", on_leave)

        def start_move(event):
            widget_win.x = event.x
            widget_win.y = event.y
        def do_move(event):
            deltax = event.x - widget_win.x
            deltay = event.y - widget_win.y
            x = widget_win.winfo_x() + deltax
            y = widget_win.winfo_y() + deltay
            widget_win.geometry(f"+{x}+{y}")
            
        widget_win.bind("<Button-1>", start_move)
        widget_win.bind("<B1-Motion>", do_move)
        
        btn_frame = tk.Frame(widget_win, bg=theme["widget_bg"])
        btn_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        btn_frame.bind("<Enter>", on_enter)
        btn_frame.bind("<Leave>", on_leave)

        def add_btn(text, cmd, bg_col):
            b = tk.Button(btn_frame, text=text, command=cmd, bg=bg_col, fg="white", 
                          font=("Microsoft JhengHei", 8, "bold"), relief="flat", padx=1, pady=0)
            b.pack(side="left", padx=1, expand=True, fill="both")
            b.bind("<Enter>", on_enter)
            b.bind("<Leave>", on_leave)
            return b
            
        add_btn("💬對話", toggle_spotlight_bar, theme["accent"])
        add_btn("💬聊天", toggle_chat_panel, "#FF8906")
        add_btn("🔍譯", lambda: threading.Thread(target=process_selection, args=("translate",), daemon=True).start(), "#98C379")
        add_btn("✨潤", lambda: threading.Thread(target=process_selection, args=("ai_refine",), daemon=True).start(), "#C678DD")
        
        clip_bg = theme["accent"] if auto_clipboard_enabled else theme["btn_bg"]
        clip_text = "📋開" if auto_clipboard_enabled else "📋關"
        clip_btn_ref = add_btn(clip_text, toggle_auto_clipboard, clip_bg)

        add_btn("📜歷", toggle_history_window, "#D19A66")
        add_btn("🛡️防", toggle_pause_mode, "#E5C07B")
        add_btn("⚙️", prompt_api_key_gui, theme["btn_bg"])
        add_btn("✕", toggle_floating_widget, "#E06C75")

        floating_win = widget_win
        set_status("✨ v2.9.9 提示優化版已啟動", "#98C379")
        root.after(1500, hide_status)

# ----------------- 系統匣常駐 (System Tray) -----------------
def create_tray_image():
    image = Image.new('RGB', (64, 64), color=(33, 37, 43))
    dc = ImageDraw.Draw(image)
    dc.rectangle((16, 16, 48, 48), fill=(97, 175, 239))
    return image

def setup_system_tray():
    global tray_icon
    if not TRAY_AVAILABLE: return
    menu = pystray.Menu(
        pystray.MenuItem("⚙️ 設定中心 & API 申請教學", lambda icon, item: root.after(0, prompt_api_key_gui)),
        pystray.MenuItem("💬 開啟 AI 互動聊天面板", lambda icon, item: toggle_chat_panel()),
        pystray.MenuItem("📜 查看歷史紀錄抽屜", lambda icon, item: toggle_history_window()),
        pystray.MenuItem("📖 使用指南 (Alt + H)", lambda icon, item: root.after(0, show_help_card)),
        pystray.MenuItem("💬 萬能指令與對話列 (Alt + Q)", lambda icon, item: toggle_spotlight_bar()),
        pystray.MenuItem("📌 切換懸浮工具顯示/隱藏", lambda icon, item: toggle_floating_widget()),
        pystray.MenuItem("📋 切換自動剪貼簿翻譯", lambda icon, item: toggle_auto_clipboard()),
        pystray.MenuItem("🛡️ 切換防誤觸暫停", lambda icon, item: toggle_pause_mode()),
        pystray.MenuItem("👋 結束程式", lambda icon, item: exit_program())
    )
    tray_icon = pystray.Icon("GroqVoiceTool", create_tray_image(), "Groq AI 語音助理", menu)
    tray_icon.run()

def toggle_pause_mode():
    global is_paused
    is_paused = not is_paused
    if is_paused:
        set_status("⏸️ 助理已暫停 (防誤觸)", "#E5C07B")
    else:
        set_status("▶️ 助理已恢復運作", "#98C379")
        root.after(1500, hide_status)

# ----------------- 設定中心 (含自訂指令介面詳細提示) -----------------
def prompt_api_key_gui():
    global GROQ_API_KEY, CUSTOM_PROMPT_1, CUSTOM_PROMPT_2, CURRENT_THEME_NAME, AI_MODEL
    try:
        win = tk.Toplevel(root)
        win.title("設定中心 & API 申請教學")
        win.attributes("-topmost", True)
        win.geometry(f"540x660+{(root.winfo_screenwidth()-540)//2}+{(root.winfo_screenheight()-660)//2}")
        win.configure(bg="#21252B")

        tk.Label(win, text="⚙️ 系統設定與新手教學中心", font=("Microsoft JhengHei", 12, "bold"), fg="#61AFEF", bg="#21252B").pack(pady=(12, 8))

        # 新手引導 Frame
        guide_card = tk.Frame(win, bg="#2D3139", bd=1, relief="solid")
        guide_card.pack(fill="x", padx=25, pady=2)

        tk.Label(guide_card, text="💡 第一次使用？如何免費取得 API Key：", font=("Microsoft JhengHei", 9, "bold"), fg="#98C379", bg="#2D3139").pack(anchor="w", padx=12, pady=(6, 2))
        
        guide_text = (
            "1. 點擊下方按鈕前往官網，用 Google 帳號免費登入。\n"
            "2. 點擊左側選單的 「API Keys」，再按 「Create API Key」。\n"
            "3. 複製產生的金鑰 (gsk_...)，貼到下方的輸入框中即完成！"
        )
        tk.Label(guide_card, text=guide_text, font=("Microsoft JhengHei", 9), fg="#ABB2BF", bg="#2D3139", justify="left").pack(anchor="w", padx=12, pady=(0, 4))

        def open_api_website():
            webbrowser.open("https://console.groq.com/")

        tk.Button(guide_card, text="🌐 點我前往 Groq 官網免費申請 Key", command=open_api_website, bg="#61AFEF", fg="#21252B", font=("Microsoft JhengHei", 9, "bold"), relief="flat", padx=10, pady=3).pack(anchor="w", padx=12, pady=(0, 8))

        # 設定選項
        tk.Label(win, text="🤖 AI 模型選擇：", font=("Microsoft JhengHei", 9), fg="#61AFEF", bg="#21252B").pack(anchor="w", padx=25, pady=(6, 2))
        model_display_values = list(MODEL_MAP.values())
        model_combo = ttk.Combobox(win, values=model_display_values, state="readonly", font=("Microsoft JhengHei", 9), width=52)
        model_combo.pack(padx=25, anchor="w")
        current_display = MODEL_MAP.get(AI_MODEL, model_display_values[0])
        model_combo.set(current_display)

        tk.Label(win, text="🎨 界面風格主題：", font=("Microsoft JhengHei", 9), fg="#98C379", bg="#21252B").pack(anchor="w", padx=25, pady=(6, 2))
        theme_combo = ttk.Combobox(win, values=list(THEMES.keys()), state="readonly", font=("Microsoft JhengHei", 9), width=52)
        theme_combo.pack(padx=25, anchor="w")
        theme_combo.set(CURRENT_THEME_NAME)

        tk.Label(win, text="🔑 Groq API Key：", font=("Microsoft JhengHei", 9), fg="#ABB2BF", bg="#21252B").pack(anchor="w", padx=25, pady=(6, 2))
        entry_api = tk.Entry(win, width=54, font=("Consolas", 10), show="*")
        entry_api.pack(padx=25, anchor="w")
        if GROQ_API_KEY: entry_api.insert(0, GROQ_API_KEY)

        # 🌟 自訂指令 1 (附帶詳細介面說明：可自由更換任意提示詞)
        tk.Label(win, text="自訂指令 1 (Alt + 1) [💡 可自由更改為任意指令，如翻譯法文、精簡摘要等]：", font=("Microsoft JhengHei", 9), fg="#98C379", bg="#21252B").pack(anchor="w", padx=25, pady=(6, 2))
        entry_p1 = tk.Entry(win, width=54, font=("Microsoft JhengHei", 9))
        entry_p1.pack(padx=25, anchor="w")
        entry_p1.insert(0, CUSTOM_PROMPT_1)

        # 🌟 自訂指令 2 (附帶詳細介面說明：可自由更換任意提示詞)
        tk.Label(win, text="自訂指令 2 (Alt + 2) [💡 可自由更改為任意指令，如改寫語氣、寫信等]：", font=("Microsoft JhengHei", 9), fg="#E5C07B", bg="#21252B").pack(anchor="w", padx=25, pady=(6, 2))
        entry_p2 = tk.Entry(win, width=54, font=("Microsoft JhengHei", 9))
        entry_p2.pack(padx=25, anchor="w")
        entry_p2.insert(0, CUSTOM_PROMPT_2)

        def save():
            global GROQ_API_KEY, CUSTOM_PROMPT_1, CUSTOM_PROMPT_2, CURRENT_THEME_NAME, AI_MODEL
            key = entry_api.get().strip()
            p1 = entry_p1.get().strip()
            p2 = entry_p2.get().strip()
            sel_theme = theme_combo.get()
            sel_display = model_combo.get()
            sel_model = sel_display.split(" ")[0]
            
            if key:
                GROQ_API_KEY = key
                CUSTOM_PROMPT_1 = p1
                CUSTOM_PROMPT_2 = p2
                CURRENT_THEME_NAME = sel_theme
                AI_MODEL = sel_model
                save_config({
                    "groq_api_key": key,
                    "custom_prompt_1": p1,
                    "custom_prompt_2": p2,
                    "theme": sel_theme,
                    "ai_model": sel_model
                })
                messagebox.showinfo("成功", "設定、模型與主題已儲存！", parent=win)
                win.destroy()
                refresh_floating_widget()
            else:
                messagebox.showwarning("提示", "API Key 不能為空！", parent=win)

        tk.Button(win, text="儲存並套用", command=save, bg="#4CAF50", fg="white", font=("Microsoft JhengHei", 10, "bold"), relief="flat", padx=15, pady=6).pack(pady=12)
    except Exception as e:
        print(f"[Settings GUI Error] {e}")

def show_help_card_gui():
    theme = get_theme()
    win = tk.Toplevel(root)
    win.title("Groq AI 語音與文字助理 - 使用指南")
    win.attributes("-topmost", True)
    win.configure(bg=theme["card_bg"])
    win.geometry(f"500x580+{(root.winfo_screenwidth() - 500) // 2}+{(root.winfo_screenheight() - 580) // 2}")

    tk.Label(win, text=f"🎙️ Groq AI 語音與文字工具 ({CURRENT_VERSION})", font=("Microsoft JhengHei", 13, "bold"), fg=theme["accent"], bg=theme["card_bg"]).pack(pady=(12, 5))
    card_frame = tk.Frame(win, bg=theme["inner_bg"], bd=1, relief="solid")
    card_frame.pack(fill="both", expand=True, padx=15, pady=5)

    features = [
        ("【 Alt + S 】", "🎙️ 語音打字 (繁中+智慧排版)", "對麥克風說話，自動過濾贅字、加標點並轉為繁中貼出。"),
        ("【 Alt+Shift+S 】", "🔠 語音中譯英", "口述中文自動翻譯成英文貼出。"),
        ("【 Alt + M 】", "🎙️ 語音助理 (共用連續記憶大腦)", "語音控制硬體、查天氣或與 AI 連續對話。"),
        ("【 Alt + Q 】", "💬 萬能指令與對話列 (支援語音按鈕)", "可打字、可點右側語音按鈕說話，共用連續對話記憶！視窗會自動覆蓋更新。"),
        ("【 💬聊天按鈕 】", "💬 AI 互動聊天面板", "開啟獨立對話室視窗，支援上下滾動檢視與連續對話。"),
        ("【 Alt + C 】", "🔍 劃詞翻譯", "選取外文按快捷鍵彈窗翻譯。"),
        ("【 Alt+Shift+C 】", "✏️ 原位替換", "選取外文，直接用繁中在原處取代。"),
        ("【 Alt + X 】", "🖼️ 截圖翻譯", "拖曳框選畫面，自動辨識圖片文字並翻譯。"),
        ("【 Alt + A 】", "✨ AI 潤飾", "選取草稿，AI 自動精修或摘要。"),
        ("【 Alt + 1 】", "⚙️ 自訂指令 1 (可於設定自由更改)", "套用設定中心的指令 1 處理文字。"),
        ("【 Alt + 2 】", "⚙️ 自訂指令 2 (可於設定自由更改)", "套用設定中心的指令 2 處理文字。"),
        ("【 Alt + T 】", "🔊 語音朗讀", "反白文字直接用系統語音唸出來。"),
        ("【 Alt+Shift+P 】", "🛡️ 防誤觸暫停", "一鍵暫時鎖定所有熱鍵（遊戲模式）。"),
        ("【 Alt+Shift+Q 】", "👋 退出程式", "安全關閉後台程式。")
    ]

    canvas = tk.Canvas(card_frame, bg=theme["inner_bg"], highlightthickness=0)
    scrollbar = tk.Scrollbar(card_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=theme["inner_bg"])
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    for key, title, desc in features:
        item = tk.Frame(scrollable_frame, bg=theme["widget_bg"], pady=4, padx=8)
        item.pack(fill="x", expand=True, pady=4, padx=5)
        head = tk.Frame(item, bg=theme["widget_bg"])
        head.pack(fill="x")
        tk.Label(head, text=key, font=("Consolas", 10, "bold"), fg="#E5C07B", bg=theme["widget_bg"]).pack(side="left")
        tk.Label(head, text=f"  {title}", font=("Microsoft JhengHei", 10, "bold"), fg="#98C379", bg=theme["widget_bg"]).pack(side="left")
        tk.Label(item, text=desc, font=("Microsoft JhengHei", 9), fg=theme["widget_fg"], bg=theme["widget_bg"], justify="left").pack(anchor="w")

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    btn_frame = tk.Frame(win, bg=theme["card_bg"])
    btn_frame.pack(fill="x", pady=10, padx=15)
    tk.Button(btn_frame, text="設定中心 (模型 & 主題)", command=prompt_api_key_gui, bg="#E5C07B", fg="#1E1E1E", font=("Microsoft JhengHei", 9, "bold")).pack(side="left")
    tk.Button(btn_frame, text="關閉 (Esc)", command=win.destroy, bg="#4CAF50", fg="white", font=("Microsoft JhengHei", 9, "bold")).pack(side="right")
    win.bind("<Escape>", lambda e: win.destroy())

def show_help_card():
    if root: root.after(0, show_help_card_gui)

# ----------------- 🧠 唯一 AI 結果視窗 -----------------
def show_ai_window_gui(title, original_text, result_text):
    global ai_result_win
    if ai_result_win is not None:
        try:
            ai_result_win.destroy()
        except Exception:
            pass
        ai_result_win = None

    theme = get_theme()
    win = tk.Toplevel(root)
    win.title(title)
    win.attributes("-topmost", True)
    win.geometry(f"480x320+{root.winfo_screenwidth() - 500}+{root.winfo_screenheight() - 400}")
    win.configure(bg=theme["card_bg"])

    tk.Label(win, text="【輸入指令 / 問題】", font=("Microsoft JhengHei", 9, "bold"), fg=theme["widget_fg"], bg=theme["card_bg"]).pack(anchor="w", padx=10, pady=(10, 0))
    orig_box = tk.Text(win, height=3, font=("Microsoft JhengHei", 9), wrap="word", bg=theme["inner_bg"], fg=theme["widget_fg"])
    orig_box.insert(tk.END, original_text)
    orig_box.config(state="disabled")
    orig_box.pack(fill="x", padx=10, pady=2)

    tk.Label(win, text="【AI 執行結果】", font=("Microsoft JhengHei", 9, "bold"), fg=theme["accent"], bg=theme["card_bg"]).pack(anchor="w", padx=10, pady=(5, 0))
    trans_box = scrolledtext.ScrolledText(win, height=8, font=("Microsoft JhengHei", 10), wrap="word", bg=theme["inner_bg"], fg=theme["widget_fg"])
    trans_box.insert(tk.END, result_text)
    trans_box.pack(fill="both", expand=True, padx=10, pady=2)

    btn_frame = tk.Frame(win, bg=theme["card_bg"])
    btn_frame.pack(fill="x", padx=10, pady=8)
    
    def close_and_clear():
        try:
            win.destroy()
        except Exception:
            pass
        global ai_result_win
        ai_result_win = None

    tk.Button(btn_frame, text="複製結果並關閉", command=lambda: [pyperclip.copy(result_text), close_and_clear()], bg="#4CAF50", fg="white").pack(side="right")
    tk.Button(btn_frame, text="關閉 (Esc)", command=close_and_clear, bg=theme["btn_bg"], fg=theme["widget_fg"]).pack(side="right", padx=5)
    
    win.protocol("WM_DELETE_WINDOW", close_and_clear)
    win.bind("<Escape>", lambda e: close_and_clear())
    
    ai_result_win = win

def show_ai_window(title, original_text, result_text):
    if root: root.after(0, show_ai_window_gui, title, original_text, result_text)

# ----------------- 截圖與 OCR 翻譯模組 -----------------
class SnippingTool:
    def __init__(self, mode="translate"):
        self.mode = mode
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
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="green" if self.mode=="pure" else "red", width=2, fill="white")

    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
        self.snip_win.destroy()
        if x2 - x1 > 10 and y2 - y1 > 10:
            if self.mode == "pure":
                root.after(100, lambda: threading.Thread(target=process_pure_screenshot, args=(x1, y1, x2, y2), daemon=True).start())
            else:
                root.after(100, lambda: threading.Thread(target=process_screenshot, args=(x1, y1, x2, y2), daemon=True).start())

def process_pure_screenshot(x1, y1, x2, y2):
    try:
        img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        filename = f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png"
        save_path = os.path.join(SCREENSHOT_DIR, filename)
        img.save(save_path)
        add_history_entry("純畫面截圖", "（截取畫面區域）", f"已存檔: {save_path}")
        set_status(f"📸 截圖已儲存！", "#98C379")
        show_ai_window("📸 畫面截圖成功", f"截圖已成功儲存至資料夾：\n{save_path}", f"檔案路徑: {save_path}")
    except Exception as e:
        show_ai_window("截圖失敗", "無法儲存截圖", str(e))
    finally:
        root.after(1500, hide_status)

def process_screenshot(x1, y1, x2, y2):
    global is_processing
    is_processing = True
    set_status("🖼️ 圖片辨識翻譯中...", "#61AFEF")

    try:
        img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        payload = {
            "model": "qwen/qwen3.6-27b",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all the text you see in this image and translate it directly into smooth Traditional Chinese. Output ONLY the Traditional Chinese translation, with no extra explanation or quotes."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}
                    ]
                }
            ],
            "temperature": 0.2
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code == 200:
            raw_content = resp.json()["choices"][0]["message"]["content"].strip()
            if "</think>" in raw_content:
                raw_content = raw_content.split("</think>")[-1].strip()
            ai_result = to_tw_trad(raw_content)
            add_history_entry("截圖 OCR 翻譯", "（圖片截取區域）", ai_result)
            show_ai_window("截圖 OCR 翻譯", "（圖片截取區域）", ai_result)
        else:
            show_ai_window("辨識失敗", "Vision API 錯誤", resp.text)
    except Exception as e:
        show_ai_window("截圖異常", "處理失敗", str(e))
    finally:
        is_processing = False
        hide_status()

# ----------------- 語音朗讀 (TTS) 模組 -----------------
def process_tts():
    global is_processing
    if is_processing: return
    if not TTS_AVAILABLE: return
    is_processing = True

    try:
        set_status("🔊 準備朗讀中...", "#98C379")
        pyperclip.copy("")
        send_copy()
        time.sleep(0.3)
        selected_text = pyperclip.paste().strip()

        if not selected_text:
            hide_status()
            is_processing = False
            return

        set_status("🔊 語音朗讀中...", "#98C379")
        engine = pyttsx3.init()
        engine.setProperty('rate', 155)
        voices = engine.getProperty('voices')
        for voice in voices:
            voice_id_lower = voice.id.lower()
            if 'zh' in voice_id_lower or 'chinese' in voice_id_lower or 'huihui' in voice_id_lower or 'hanhan' in voice_id_lower:
                engine.setProperty('voice', voice.id)
                break

        engine.say(selected_text)
        engine.runAndWait()
    except Exception as e:
        print(f"[TTS Exception] {e}")
    finally:
        is_processing = False
        hide_status()

# ----------------- 音訊與 API -----------------
def callback(indata, frames, time_info, status):
    if recording: audio_data.append(indata.copy())

def release_mod_keys():
    user32 = ctypes.windll.user32
    for k in (0x12, 0x10, 0x11): user32.keybd_event(k, 0, 2, 0)

def send_paste():
    release_mod_keys()
    time.sleep(0.1)
    ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x56, 0, 0, 0)
    time.sleep(0.03)
    ctypes.windll.user32.keybd_event(0x56, 0, 2, 0)
    ctypes.windll.user32.keybd_event(0x11, 0, 2, 0)

def send_copy():
    user32 = ctypes.windll.user32
    while user32.GetAsyncKeyState(0x12) & 0x8000:
        time.sleep(0.02)
    
    release_mod_keys()
    time.sleep(0.1)
    user32.keybd_event(0x11, 0, 0, 0)
    user32.keybd_event(0x43, 0, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(0x43, 0, 2, 0)
    user32.keybd_event(0x11, 0, 2, 0)

def process_audio(data, mode):
    global is_processing
    if not GROQ_API_KEY:
        is_processing = False
        prompt_api_key_gui()
        return
    try:
        audio_array = np.concatenate(data, axis=0)
        wav_buffer = io.BytesIO()
        write(wav_buffer, SAMPLE_RATE, (audio_array * 32767).astype(np.int16))
        
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        set_status("⚡ 語音辨識中...", "#D19A66")
        
        resp = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, 
                             files={"file": ("audio.wav", wav_buffer.getvalue(), "audio/wav"), "model": (None, "whisper-large-v3"), "language": (None, "zh")}, timeout=10)
        
        if resp.status_code == 200:
            raw_text = resp.json().get("text", "").strip()
            if raw_text:
                if mode == "en":
                    set_status("🔠 AI 翻譯英文中...", "#61AFEF")
                    payload = {"model": AI_MODEL, "messages": [{"role": "system", "content": "You are a professional translator. Translate the given Chinese text into clear, natural, accurate English. Output ONLY the English translation without any Chinese characters, quotes, or explanations."}, {"role": "user", "content": raw_text}], "temperature": 0.1}
                    chat_resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
                    final_text = chat_resp.json()["choices"][0]["message"]["content"].strip() if chat_resp.status_code == 200 else ""
                    if final_text:
                        add_history_entry("語音中譯英", raw_text, final_text)
                else:
                    set_status("✨ AI 智慧排版中...", "#C678DD")
                    cleanup_payload = {
                        "model": AI_MODEL,
                        "messages": [
                            {"role": "system", "content": "你是一個專業的語音逐字稿智慧排版助理。請清理以下語音轉文字的口語草稿：過濾掉口語贅字（如「然後」、「呃」、「那個」等），修正語病，並自動加上適當的標點符號與段落分行。只需輸出優化後的乾淨正文，不要任何引號或額外說明。"},
                            {"role": "user", "content": raw_text}
                        ],
                        "temperature": 0.2
                    }
                    chat_resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=cleanup_payload, timeout=10)
                    if chat_resp.status_code == 200:
                        raw_content = chat_resp.json()["choices"][0]["message"]["content"].strip()
                        if "</think>" in raw_content:
                            raw_content = raw_content.split("</think>")[-1].strip()
                        final_text = to_tw_trad(raw_content)
                        add_history_entry("語音智慧排版", raw_text, final_text)
                    else:
                        final_text = to_tw_trad(raw_text)

                if final_text:
                    pyperclip.copy(final_text)
                    time.sleep(0.15)
                    send_paste()
    except Exception as e: show_ai_window("執行異常", "程式發生錯誤", str(e))
    finally:
        is_processing = False
        hide_status()

def process_selection(task_type):
    global is_processing
    if is_processing: return
    if not GROQ_API_KEY:
        prompt_api_key_gui()
        return
    is_processing = True

    try:
        task_names = {
            "replace": "劃詞替換",
            "translate": "劃詞翻譯",
            "ai_refine": "AI 潤飾",
            "custom_1": "自訂指令 1",
            "custom_2": "自訂指令 2"
        }
        display_name = task_names.get(task_type, task_type)

        if task_type == "replace": set_status("⚡ 劃詞替換中...", "#61AFEF")
        elif task_type == "translate": set_status("⚡ 劃詞翻譯中...", "#98C379")
        elif task_type == "custom_1": set_status("⚡ 執行指令 1...", "#C678DD")
        elif task_type == "custom_2": set_status("⚡ 執行指令 2...", "#D19A66")
        else: set_status("⚡ AI 潤飾中...", "#E06C75")
            
        pyperclip.copy("")
        send_copy()
        time.sleep(0.3)
        selected_text = pyperclip.paste().strip()

        if not selected_text:
            hide_status()
            is_processing = False
            return

        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        sys_prompt = "你是一個精通多國語言的專業翻譯員。將輸入文字精準翻譯為符合台灣用語習慣的繁體中文。只需輸出翻譯結果。"
        if task_type == "ai_refine": 
            sys_prompt = "你是一個高效率的 AI 文字助理。判斷輸入文字：長篇請整理3個重點摘要；短句草稿請潤飾為專業客氣的繁體中文。只需直接輸出結果。"
        elif task_type == "custom_1":
            sys_prompt = f"嚴格遵循以下指令處理文字，且一律使用繁體中文輸出結果：{CUSTOM_PROMPT_1}。直接給予最終結果，不要任何問候語或解釋。"
        elif task_type == "custom_2":
            sys_prompt = f"嚴格遵循以下指令處理文字，且一律使用繁體中文輸出結果：{CUSTOM_PROMPT_2}。直接給予最終結果，不要任何問候語或解釋。"

        payload = {"model": AI_MODEL, "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": selected_text}], "temperature": 0.3}
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            res_json = response.json()
            if "choices" in res_json and len(res_json["choices"]) > 0:
                raw_content = res_json["choices"][0]["message"]["content"].strip()
                if "</think>" in raw_content:
                    raw_content = raw_content.split("</think>")[-1].strip()
                ai_result = to_tw_trad(raw_content)
                add_history_entry(display_name, selected_text, ai_result)
                
                if task_type == "replace":
                    pyperclip.copy(ai_result)
                    time.sleep(0.1)
                    send_paste()
                elif task_type == "translate": show_ai_window("Groq AI 劃詞翻譯", selected_text, ai_result)
                elif task_type == "ai_refine": show_ai_window("Groq AI 精修 / 摘要", selected_text, ai_result)
                elif task_type == "custom_1": show_ai_window("✨ 自訂指令 1 處理結果", selected_text, ai_result)
                elif task_type == "custom_2": show_ai_window("✨ 自訂指令 2 處理結果", selected_text, ai_result)
            else:
                show_ai_window("AI 回應格式錯誤", selected_text, str(res_json))
        else: 
            show_ai_window("AI 處理失敗", selected_text, f"請求失敗 ({response.status_code})\n{response.text}")
    except Exception as e:
        show_ai_window("執行異常", "程式發生錯誤", str(e))
    finally:
        is_processing = False
        hide_status()

def start_recording(mode):
    global recording, audio_data, stream, current_mode
    recording = True
    current_mode = mode
    audio_data = []
    winsound.Beep(800, 120)
    
    if mode == "en":
        set_status("🎙️ 錄音中 (中譯英)...", "#61AFEF")
    elif mode == "macro":
        set_status("🎙️ 語音助理聆聽中...", "#FF8906")
    else:
        set_status("🎙️ 錄音中 (智慧排版)...", "#C678DD")

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback)
    stream.start()

def stop_recording():
    global recording, stream, is_processing
    recording, is_processing = False, True
    winsound.Beep(600, 150)
    if stream: stream.stop(); stream.close(); stream = None
    if audio_data:
        if current_mode == "macro":
            threading.Thread(target=process_voice_macro, args=(audio_data.copy(),), daemon=True).start()
        else:
            threading.Thread(target=process_audio, args=(audio_data.copy(), current_mode), daemon=True).start()
    else: is_processing = False; hide_status()

def trigger_mode(mode):
    global last_trigger_time
    if is_paused: return
    now = time.time()
    if now - last_trigger_time < 0.4 or is_processing: return
    last_trigger_time = now
    if not recording: start_recording(mode)
    elif current_mode == mode: stop_recording()

def win32_hotkey_loop():
    user32 = ctypes.windll.user32
    print("[INFO] 開始註冊全域快捷鍵...")
    for hk_id, (name, mod, vk) in HOTKEY_IDS.items():
        user32.UnregisterHotKey(None, hk_id)
        res = user32.RegisterHotKey(None, hk_id, mod, vk)
        if not res:
            print(f"[WARNING] 註冊快捷鍵 [{name}] 失敗！可能已被其他程式佔用。")
        else:
            print(f"[INFO] 成功註冊快捷鍵: [{name}]")

    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        if msg.message == 0x0312:
            hk_id = msg.wParam
            print(f"[DEBUG] 收到快捷鍵觸發 ID: {hk_id}")
            
            if hk_id == 12:
                toggle_pause_mode()
                continue
            
            if is_paused:
                print("[INFO] 目前處於防誤觸暫停狀態，忽略快捷鍵。")
                continue

            if hk_id == 8: root.after(0, lambda: SnippingTool(mode="translate"))
            elif hk_id == 4: threading.Thread(target=process_selection, args=("replace",), daemon=True).start()
            elif hk_id == 2: trigger_mode("en")
            elif hk_id == 3: threading.Thread(target=process_selection, args=("translate",), daemon=True).start()
            elif hk_id == 1: trigger_mode("zh")
            elif hk_id == 5: threading.Thread(target=process_selection, args=("ai_refine",), daemon=True).start()
            elif hk_id == 9: threading.Thread(target=process_selection, args=("custom_1",), daemon=True).start()
            elif hk_id == 10: threading.Thread(target=process_selection, args=("custom_2",), daemon=True).start()
            elif hk_id == 11: threading.Thread(target=process_tts, daemon=True).start()
            elif hk_id == 13: toggle_spotlight_bar()
            elif hk_id == 14: trigger_mode("macro")  # 🎙️ 語音助理 (Alt + M)
            elif hk_id == 6: show_help_card()
            elif hk_id == 7: threading.Thread(target=exit_program, daemon=True).start()
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

if __name__ == "__main__":
    try:
        print("[INFO] 語音助理 v2.9.9 提示優化版正在啟動...")
        threading.Thread(target=win32_hotkey_loop, daemon=True).start()
        init_gui()
        root.mainloop()
    except Exception as e:
        print(f"[CRITICAL ERROR] 程式發生嚴重錯誤: {e}")
        input("請按 Enter 鍵結束...")