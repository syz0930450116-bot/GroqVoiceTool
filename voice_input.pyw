import io
import time
import threading
import json
import os
import sys
import subprocess
import requests
import ctypes
from ctypes import wintypes
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import pyperclip
import tkinter as tk
from tkinter import scrolledtext, messagebox
import base64
from PIL import ImageGrab

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
CURRENT_VERSION = "v1.4.2"
GITHUB_RELEASE_URL = "https://api.github.com/repos/syz0930450116-bot/GroqVoiceTool/releases/latest"

APPDATA_DIR = os.path.join(os.getenv('LOCALAPPDATA'), 'GroqVoiceTool')
os.makedirs(APPDATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(APPDATA_DIR, "config.json")
SAMPLE_RATE = 16000

HOTKEY_IDS = {
    2: ("en", 0x0001 | 0x0004, 0x53),      # ID 2: Alt + Shift + S (中譯英)
    4: ("replace", 0x0001 | 0x0004, 0x43), # ID 4: Alt + Shift + C (劃詞替換)
    7: ("quit", 0x0001 | 0x0004, 0x51),    # ID 7: Alt + Shift + Q (退出)
    1: ("zh", 0x0001, 0x53),               # ID 1: Alt + S (繁體中文)
    3: ("trans", 0x0001, 0x43),            # ID 3: Alt + C (劃詞翻譯)
    5: ("ai", 0x0001, 0x41),               # ID 5: Alt + A (AI 潤飾)
    6: ("help", 0x0001, 0x48),             # ID 6: Alt + H (說明卡)
    8: ("ocr", 0x0001, 0x58)               # ID 8: Alt + X (截圖翻譯)
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

# ----------------- 配置檔管理 -----------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: pass
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(cfg, f, indent=4, ensure_ascii=False)

config = load_config()
GROQ_API_KEY = config.get("groq_api_key", "")
recording = False
is_processing = False
audio_data = []
stream = None
current_mode = "zh"
last_trigger_time = 0
root = None
status_win = None
status_label = None

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
    status_win.geometry(f"180x36+{sw - 205}+{sh - 96}")

    status_label = tk.Label(status_win, text="", font=("Microsoft JhengHei", 10, "bold"), fg="#FFFFFF")
    status_label.pack(fill="both", expand=True)

    show_startup_notice()
    threading.Thread(target=check_for_updates, daemon=True).start()
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
    set_status("🚀 語音助理已啟動", "#98C379")
    if root: root.after(2000, hide_status)

def exit_program():
    set_status("👋 語音助理已關閉", "#E06C75")
    time.sleep(0.8)
    os._exit(0)

def prompt_api_key_gui():
    global GROQ_API_KEY
    win = tk.Toplevel(root)
    win.title("設定 Groq API Key")
    win.attributes("-topmost", True)
    win.geometry(f"400x200+{(root.winfo_screenwidth()-400)//2}+{(root.winfo_screenheight()-200)//2}")
    win.configure(bg="#21252B")

    tk.Label(win, text="🔑 歡迎使用 AI 語音助理", font=("Microsoft JhengHei", 12, "bold"), fg="#61AFEF", bg="#21252B").pack(pady=(15, 5))
    tk.Label(win, text="請輸入您的 Groq API Key：", font=("Microsoft JhengHei", 9), fg="#ABB2BF", bg="#21252B").pack()

    entry = tk.Entry(win, width=45, font=("Consolas", 10), show="*")
    entry.pack(pady=10)
    if GROQ_API_KEY: entry.insert(0, GROQ_API_KEY)

    def save():
        global GROQ_API_KEY
        key = entry.get().strip()
        if key:
            GROQ_API_KEY = key
            save_config({"groq_api_key": key})
            messagebox.showinfo("成功", "API Key 已儲存！", parent=win)
            win.destroy()

    tk.Button(win, text="儲存並開始使用", command=save, bg="#98C379", fg="#21252B", font=("Microsoft JhengHei", 9, "bold"), relief="flat", padx=10, pady=4).pack(pady=5)

def show_help_card_gui():
    win = tk.Toplevel(root)
    win.title("Groq AI 語音與文字助理 - 使用指南")
    win.attributes("-topmost", True)
    win.configure(bg="#1E1E1E")
    win.geometry(f"480x480+{(root.winfo_screenwidth() - 480) // 2}+{(root.winfo_screenheight() - 480) // 2}")

    tk.Label(win, text=f"🎙️ Groq AI 語音與文字工具 ({CURRENT_VERSION})", font=("Microsoft JhengHei", 13, "bold"), fg="#61AFEF", bg="#1E1E1E").pack(pady=(12, 5))
    card_frame = tk.Frame(win, bg="#252526", bd=1, relief="solid")
    card_frame.pack(fill="both", expand=True, padx=15, pady=5)

    features = [
        ("【 Alt + S 】", "🎙️ 語音打字 (繁中)", "對麥克風說話自動轉為繁體中文貼出。"),
        ("【 Alt+Shift+S 】", "🔠 語音中譯英", "口述中文自動翻譯成英文貼出。"),
        ("【 Alt + C 】", "🔍 劃詞翻譯", "選取外文按快捷鍵彈窗翻譯。"),
        ("【 Alt+Shift+C 】", "✏️ 原位替換", "選取外文/簡體字，直接用繁中在原處取代。"),
        ("【 Alt + X 】", "🖼️ 截圖翻譯", "滑鼠拖曳框選畫面，自動辨識圖片文字並翻譯。"),
        ("【 Alt + A 】", "✨ AI 潤飾", "選取草稿，AI 自動精修或摘要。"),
        ("【 Alt+Shift+Q 】", "👋 退出程式", "安全關閉後台程式。")
    ]

    canvas = tk.Canvas(card_frame, bg="#252526", highlightthickness=0)
    scrollbar = tk.Scrollbar(card_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#252526")
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    for key, title, desc in features:
        item = tk.Frame(scrollable_frame, bg="#2D2D30", pady=4, padx=8)
        item.pack(fill="x", expand=True, pady=4, padx=5)
        head = tk.Frame(item, bg="#2D2D30")
        head.pack(fill="x")
        tk.Label(head, text=key, font=("Consolas", 10, "bold"), fg="#E5C07B", bg="#2D2D30").pack(side="left")
        tk.Label(head, text=f"  {title}", font=("Microsoft JhengHei", 10, "bold"), fg="#98C379", bg="#2D2D30").pack(side="left")
        tk.Label(item, text=desc, font=("Microsoft JhengHei", 8), fg="#ABB2BF", bg="#2D2D30", justify="left").pack(anchor="w")

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    btn_frame = tk.Frame(win, bg="#1E1E1E")
    btn_frame.pack(fill="x", pady=10, padx=15)
    tk.Button(btn_frame, text="修改 API Key", command=prompt_api_key_gui, bg="#E5C07B", fg="#1E1E1E", font=("Microsoft JhengHei", 9, "bold")).pack(side="left")
    tk.Button(btn_frame, text="關閉 (Esc)", command=win.destroy, bg="#4CAF50", fg="white", font=("Microsoft JhengHei", 9, "bold")).pack(side="right")
    win.bind("<Escape>", lambda e: win.destroy())

def show_help_card():
    if root: root.after(0, show_help_card_gui)

def show_ai_window_gui(title, original_text, result_text):
    win = tk.Toplevel(root)
    win.title(title)
    win.attributes("-topmost", True)
    win.geometry(f"480x320+{root.winfo_screenwidth() - 500}+{root.winfo_screenheight() - 400}")

    tk.Label(win, text="【原文】", font=("Microsoft JhengHei", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
    orig_box = tk.Text(win, height=3, font=("Microsoft JhengHei", 9), wrap="word")
    orig_box.insert(tk.END, original_text)
    orig_box.config(state="disabled")
    orig_box.pack(fill="x", padx=10, pady=2)

    tk.Label(win, text="【AI 處理結果】", font=("Microsoft JhengHei", 9, "bold"), fg="blue").pack(anchor="w", padx=10, pady=(5, 0))
    trans_box = scrolledtext.ScrolledText(win, height=8, font=("Microsoft JhengHei", 10), wrap="word")
    trans_box.insert(tk.END, result_text)
    trans_box.pack(fill="both", expand=True, padx=10, pady=2)

    btn_frame = tk.Frame(win)
    btn_frame.pack(fill="x", padx=10, pady=8)
    tk.Button(btn_frame, text="複製結果並關閉", command=lambda: [pyperclip.copy(result_text), win.destroy()], bg="#4CAF50", fg="white").pack(side="right")
    tk.Button(btn_frame, text="關閉 (Esc)", command=win.destroy).pack(side="right", padx=5)
    win.bind("<Escape>", lambda e: win.destroy())

def show_ai_window(title, original_text, result_text):
    if root: root.after(0, show_ai_window_gui, title, original_text, result_text)

# ----------------- 截圖 OCR 翻譯模組 -----------------
class SnippingTool:
    def __init__(self):
        self.snip_win = tk.Toplevel(root)
        self.snip_win.attributes("-fullscreen", True)
        self.snip_win.attributes("-alpha", 0.3)
        self.snip_win.attributes("-topmost", True)
        self.snip_win.config(cursor="cross")

        self.canvas = tk.Canvas(self.snip_win, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.start_x = None
        self.start_y = None
        self.rect = None

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.snip_win.bind("<Escape>", lambda e: self.snip_win.destroy())

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2, fill="white")

    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
        self.snip_win.destroy()
        if x2 - x1 > 10 and y2 - y1 > 10:
            root.after(100, lambda: threading.Thread(target=process_screenshot, args=(x1, y1, x2, y2), daemon=True).start())

def launch_snipping_tool():
    if not GROQ_API_KEY:
        set_status("⚠️ 未設定 API Key", "#E06C75")
        root.after(1500, hide_status)
        return
    SnippingTool()

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
            "model": "llama-3.2-90b-vision-preview",
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
            ai_result = resp.json()["choices"][0]["message"]["content"].strip()
            ai_result = to_tw_trad(ai_result)
            show_ai_window("截圖 OCR 翻譯", "（圖片截取區域）", ai_result)
        else:
            show_ai_window("辨識失敗", "Vision API 錯誤", resp.text)
    except Exception as e:
        show_ai_window("截圖異常", "處理失敗", str(e))
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
    release_mod_keys()
    time.sleep(0.1)
    ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x43, 0, 0, 0)
    time.sleep(0.03)
    ctypes.windll.user32.keybd_event(0x43, 0, 2, 0)
    ctypes.windll.user32.keybd_event(0x11, 0, 2, 0)

def process_audio(data, mode):
    global is_processing
    if not GROQ_API_KEY:
        is_processing = False
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
                    payload = {"model": "openai/gpt-oss-20b", "messages": [{"role": "system", "content": "You are a professional translator. Translate the given Chinese text into clear, natural, accurate English. Output ONLY the English translation without any Chinese characters, quotes, or explanations."}, {"role": "user", "content": raw_text}], "temperature": 0.1}
                    chat_resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
                    final_text = chat_resp.json()["choices"][0]["message"]["content"].strip() if chat_resp.status_code == 200 else ""
                else: final_text = to_tw_trad(raw_text)

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
    if is_processing or not GROQ_API_KEY: return
    is_processing = True

    try:
        if task_type == "replace": set_status("⚡ 劃詞替換中...", "#61AFEF")
        elif task_type == "translate": set_status("⚡ 劃詞翻譯中...", "#98C379")
        else: set_status("⚡ AI 潤飾中...", "#E06C75")
            
        pyperclip.copy("")
        send_copy()
        time.sleep(0.4)
        selected_text = pyperclip.paste().strip()

        if not selected_text:
            hide_status()
            is_processing = False
            return

        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        sys_prompt = "你是一個精通多國語言的專業翻譯員。將輸入文字精準翻譯為符合台灣用語習慣的繁體中文。只需輸出翻譯結果。"
        if task_type == "ai_refine": sys_prompt = "你是一個高效率的 AI 文字助理。判斷輸入文字：長篇請整理3個重點摘要；短句草稿請潤飾為專業客氣的繁體中文。只需直接輸出結果。"

        payload = {"model": "openai/gpt-oss-20b", "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": selected_text}], "temperature": 0.3}
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=8)
        
        if response.status_code == 200:
            ai_result = to_tw_trad(response.json()["choices"][0]["message"]["content"].strip())
            if task_type == "replace":
                pyperclip.copy(ai_result)
                time.sleep(0.1)
                send_paste()
            elif task_type == "translate": show_ai_window("Groq AI 劃詞翻譯", selected_text, ai_result)
            elif task_type == "ai_refine": show_ai_window("Groq AI 精修 / 摘要", selected_text, ai_result)
        else: show_ai_window("AI 處理失敗", selected_text, f"請求失敗 ({response.status_code})")
    finally:
        is_processing = False
        hide_status()

def start_recording(mode):
    global recording, audio_data, stream, current_mode
    recording = True
    current_mode = mode
    audio_data = []
    set_status("🎙️ 錄音中 (中譯英)..." if mode == "en" else "🎙️ 錄音中 (中文)...", "#61AFEF" if mode == "en" else "#E06C75")
    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback)
    stream.start()

def stop_recording():
    global recording, stream, is_processing
    recording, is_processing = False, True
    if stream: stream.stop(); stream.close(); stream = None
    if audio_data: threading.Thread(target=process_audio, args=(audio_data.copy(), current_mode), daemon=True).start()
    else: is_processing = False; hide_status()

def trigger_mode(mode):
    global last_trigger_time
    now = time.time()
    if now - last_trigger_time < 0.4 or is_processing: return
    last_trigger_time = now
    if not recording: start_recording(mode)
    elif current_mode == mode: stop_recording()

def win32_hotkey_loop():
    user32 = ctypes.windll.user32
    for hk_id, (_, mod, vk) in HOTKEY_IDS.items():
        user32.UnregisterHotKey(None, hk_id)
        user32.RegisterHotKey(None, hk_id, mod, vk)

    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        if msg.message == 0x0312:
            hk_id = msg.wParam
            if hk_id == 8: root.after(0, launch_snipping_tool)
            elif hk_id == 4: threading.Thread(target=process_selection, args=("replace",), daemon=True).start()
            elif hk_id == 2: trigger_mode("en")
            elif hk_id == 3: threading.Thread(target=process_selection, args=("translate",), daemon=True).start()
            elif hk_id == 1: trigger_mode("zh")
            elif hk_id == 5: threading.Thread(target=process_selection, args=("ai_refine",), daemon=True).start()
            elif hk_id == 6: show_help_card()
            elif hk_id == 7: threading.Thread(target=exit_program, daemon=True).start()
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

if __name__ == "__main__":
    threading.Thread(target=win32_hotkey_loop, daemon=True).start()
    init_gui()
    root.mainloop()