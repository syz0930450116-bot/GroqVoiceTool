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
CURRENT_VERSION = "v1.2.0"
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
    6: ("help", 0x0001, 0x48)              # ID 6: Alt + H (說明卡)
}

# ----------------- 自動更新模組 -----------------
def check_for_updates():
    if not getattr(sys, 'frozen', False):
        return  # 若在 .py 腳本開發模式下執行則跳過更新

    try:
        resp = requests.get(GITHUB_RELEASE_URL, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            latest_tag = data.get("tag_name", "").strip()
            
            # 當 GitHub tag 版本與當前版本不符合時觸發更新
            if latest_tag and latest_tag != CURRENT_VERSION:
                exe_asset = None
                for asset in data.get("assets", []):
                    if asset.get("name", "").endswith(".exe"):
                        exe_asset = asset
                        break
                
                if exe_asset:
                    download_url = exe_asset.get("browser_download_url")
                    set_status(f"🚀 發現新版本 {latest_tag}，更新中...", "#61AFEF")
                    
                    # 下載新版 `.exe`
                    r = requests.get(download_url, stream=True, timeout=30)
                    new_exe_path = os.path.join(APPDATA_DIR, "update_temp.exe")
                    with open(new_exe_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    current_exe = sys.executable
                    bat_path = os.path.join(APPDATA_DIR, "update.bat")
                    
                    # 建立暫存檔批次寫入腳本進行覆蓋並重新啟動
                    bat_content = f"""@echo off
timeout /t 2 /nobreak > NUL
move /y "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
                    with open(bat_path, "w", encoding="utf-8") as f:
                        f.write(bat_content)
                    
                    set_status("🔄 更新完成，重啟中...", "#98C379")
                    time.sleep(1.0)
                    subprocess.Popen(bat_path, shell=True)
                    os._exit(0)
    except Exception:
        pass

# ----------------- 配置檔管理 -----------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

config = load_config()
GROQ_API_KEY = config.get("groq_api_key", "")

recording = False
is_processing = False
audio_data = []
stream = None
current_mode = "zh"
last_trigger_time = 0

# ----------------- UI 系統 -----------------
root = None
status_win = None
status_label = None

def init_gui():
    global root, status_win, status_label
    root = tk.Tk()
    root.withdraw()

    status_win = tk.Toplevel(root)
    status_win.overrideredirect(True)
    status_win.attributes("-topmost", True)
    status_win.withdraw()
    
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    w, h = 180, 36
    x = sw - w - 25
    y = sh - h - 60
    status_win.geometry(f"{w}x{h}+{x}+{y}")

    status_label = tk.Label(status_win, text="", font=("Microsoft JhengHei", 10, "bold"), fg="#FFFFFF")
    status_label.pack(fill="both", expand=True)

    show_startup_notice()

    # 啟動時發起背景執行更新檢查
    threading.Thread(target=check_for_updates, daemon=True).start()

    if not GROQ_API_KEY:
        root.after(1500, prompt_api_key_gui)

def update_status_ui(text, bg_color):
    if status_win and status_label:
        status_label.config(text=text, bg=bg_color)
        status_win.configure(bg=bg_color)
        status_win.deiconify()

def hide_status_ui():
    if status_win:
        status_win.withdraw()

def set_status(text, bg_color):
    if root: root.after(0, update_status_ui, text, bg_color)

def hide_status():
    if root: root.after(0, hide_status_ui)

def show_startup_notice():
    set_status("🚀 語音助理已啟動", "#98C379")
    if root:
        root.after(2000, hide_status)

def exit_program():
    set_status("👋 語音助理已關閉", "#E06C75")
    time.sleep(0.8)
    os._exit(0)

# ----------------- API Key 設定視窗 -----------------
def prompt_api_key_gui():
    global GROQ_API_KEY
    win = tk.Toplevel(root)
    win.title("設定 Groq API Key")
    win.attributes("-topmost", True)
    
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    w, h = 400, 200
    win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
    win.configure(bg="#21252B")

    tk.Label(win, text="🔑 歡迎使用 AI 語音助理", font=("Microsoft JhengHei", 12, "bold"), fg="#61AFEF", bg="#21252B").pack(pady=(15, 5))
    tk.Label(win, text="請輸入您的 Groq API Key：", font=("Microsoft JhengHei", 9), fg="#ABB2BF", bg="#21252B").pack()

    entry = tk.Entry(win, width=45, font=("Consolas", 10), show="*")
    entry.pack(pady=10)
    if GROQ_API_KEY:
        entry.insert(0, GROQ_API_KEY)

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

    width, height = 460, 430
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    win.geometry(f"{width}x{height}+{(sw - width) // 2}+{(sh - height) // 2}")

    tk.Label(win, text=f"🎙️ Groq AI 語音與文字工具 ({CURRENT_VERSION})", font=("Microsoft JhengHei", 13, "bold"), fg="#61AFEF", bg="#1E1E1E").pack(pady=(12, 5))

    card_frame = tk.Frame(win, bg="#252526", bd=1, relief="solid")
    card_frame.pack(fill="both", expand=True, padx=15, pady=5)

    features = [
        ("【 Alt + S 】", "🎙️ 語音打字 (繁體中文)", "對著麥克風說話，自動轉為繁體中文貼出。\n👉 適用：聊天、打報告、不用手動打字時。"),
        ("【 Alt + Shift + S 】", "🔠 語音中譯英", "口述中文，AI 自動翻譯成流暢英文貼出。\n👉 適用：寫英文 Email、遊戲外服交流、跨國對話。"),
        ("【 Alt + C 】", "🔍 反白劃詞彈窗翻譯", "選取外文後按快捷鍵，彈窗顯示繁體中文翻譯。\n👉 適用：閱讀英文網頁、查單字或句型。"),
        ("【 Alt + Shift + C 】", "✏️ 反白劃詞原位替換", "選取外文/簡體字，直接用繁體中文在原處取代。\n👉 適用：修改論文、整理簡體文件草稿。"),
        ("【 Alt + A 】", "✨ AI 文章潤飾與摘要", "選取文章或對話草稿，AI 自動整理摘要或精修語氣。\n👉 適用：會議紀錄摘要、語氣修飾得體。"),
        ("【 Alt + Shift + Q 】", "👋 退出程式", "安全平滑關閉後台程式。")
    ]

    canvas = tk.Canvas(card_frame, bg="#252526", highlightthickness=0)
    scrollbar = tk.Scrollbar(card_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#252526")

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    for key, title, desc in features:
        item = tk.Frame(scrollable_frame, bg="#2D2D30", pady=6, padx=8)
        item.pack(fill="x", expand=True, pady=4, padx=5)

        head = tk.Frame(item, bg="#2D2D30")
        head.pack(fill="x")

        tk.Label(head, text=key, font=("Consolas", 10, "bold"), fg="#E5C07B", bg="#2D2D30").pack(side="left")
        tk.Label(head, text=f"  {title}", font=("Microsoft JhengHei", 10, "bold"), fg="#98C379", bg="#2D2D30").pack(side="left")

        tk.Label(item, text=desc, font=("Microsoft JhengHei", 8), fg="#ABB2BF", bg="#2D2D30", justify="left").pack(anchor="w", pady=(2, 0))

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    btn_frame = tk.Frame(win, bg="#1E1E1E")
    btn_frame.pack(fill="x", pady=10, padx=15)
    tk.Button(btn_frame, text="修改 API Key", command=prompt_api_key_gui, bg="#E5C07B", fg="#1E1E1E", font=("Microsoft JhengHei", 9, "bold"), relief="flat", padx=10).pack(side="left")
    tk.Button(btn_frame, text="關閉 (Esc)", command=win.destroy, bg="#4CAF50", fg="white", font=("Microsoft JhengHei", 9, "bold"), relief="flat", padx=10).pack(side="right")

    win.bind("<Escape>", lambda e: win.destroy())

def show_help_card():
    if root: root.after(0, show_help_card_gui)

def show_ai_window_gui(title, original_text, result_text):
    win = tk.Toplevel(root)
    win.title(title)
    win.geometry("480x320")
    win.attributes("-topmost", True)
    
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    win.geometry(f"480x320+{sw - 500}+{sh - 400}")

    tk.Label(win, text="【原文】", font=("Microsoft JhengHei", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
    orig_box = tk.Text(win, height=3, font=("Microsoft JhengHei", 9), wrap="word")
    orig_box.insert(tk.END, original_text)
    orig_box.config(state="disabled")
    orig_box.pack(fill="x", padx=10, pady=2)

    tk.Label(win, text="【AI 處理結果】", font=("Microsoft JhengHei", 9, "bold"), fg="blue").pack(anchor="w", padx=10, pady=(5, 0))
    trans_box = scrolledtext.ScrolledText(win, height=8, font=("Microsoft JhengHei", 10), wrap="word")
    trans_box.insert(tk.END, result_text)
    trans_box.pack(fill="both", expand=True, padx=10, pady=2)

    def copy_result():
        pyperclip.copy(result_text)
        win.destroy()

    btn_frame = tk.Frame(win)
    btn_frame.pack(fill="x", padx=10, pady=8)
    tk.Button(btn_frame, text="複製結果並關閉", command=copy_result, bg="#4CAF50", fg="white").pack(side="right")
    tk.Button(btn_frame, text="關閉 (Esc)", command=win.destroy).pack(side="right", padx=5)

    win.bind("<Escape>", lambda e: win.destroy())

def show_ai_window(title, original_text, result_text):
    if root: root.after(0, show_ai_window_gui, title, original_text, result_text)

# ----------------- 音訊與 API -----------------
def callback(indata, frames, time_info, status):
    if recording:
        audio_data.append(indata.copy())

def release_mod_keys():
    ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
    ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)
    ctypes.windll.user32.keybd_event(0x11, 0, 2, 0)

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
        set_status("⚠️ 未設定 API Key", "#E06C75")
        time.sleep(1.5)
        hide_status()
        show_help_card()
        is_processing = False
        return

    try:
        audio_array = np.concatenate(data, axis=0)
        wav_buffer = io.BytesIO()
        write(wav_buffer, SAMPLE_RATE, (audio_array * 32767).astype(np.int16))
        wav_bytes = wav_buffer.getvalue()
        
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

        set_status("⚡ 語音辨識中...", "#D19A66")
        url_transcribe = "https://api.groq.com/openai/v1/audio/transcriptions"
        files = {
            "file": ("audio.wav", wav_bytes, "audio/wav"),
            "model": (None, "whisper-large-v3"),
            "language": (None, "zh")
        }
        
        response = requests.post(url_transcribe, headers=headers, files=files, timeout=10)
        
        if response.status_code == 200:
            raw_text = response.json().get("text", "").strip()
            if raw_text:
                if mode == "en":
                    set_status("🔠 AI 翻譯英文中...", "#61AFEF")
                    url_chat = "https://api.groq.com/openai/v1/chat/completions"
                    
                    payload = {
                        "model": "openai/gpt-oss-20b",
                        "messages": [
                            {
                                "role": "system", 
                                "content": "You are a professional translator. Translate the given Chinese text into clear, natural, accurate English. Output ONLY the English translation without any Chinese characters, quotes, or explanations."
                            },
                            {"role": "user", "content": raw_text}
                        ],
                        "temperature": 0.1
                    }
                    chat_resp = requests.post(url_chat, headers=headers, json=payload, timeout=10)
                    if chat_resp.status_code == 200:
                        final_text = chat_resp.json()["choices"][0]["message"]["content"].strip()
                    else:
                        show_ai_window("翻譯失敗", f"Chat API 錯誤 ({chat_resp.status_code})", chat_resp.text)
                        final_text = ""
                else:
                    final_text = to_tw_trad(raw_text)

                if final_text:
                    pyperclip.copy(final_text)
                    time.sleep(0.15)
                    send_paste()
        else:
            show_ai_window("語音辨識失敗", f"Whisper API 錯誤 ({response.status_code})", response.text)
    except Exception as e:
        show_ai_window("執行異常", "程式發生錯誤", str(e))
    finally:
        is_processing = False
        hide_status()

def process_selection(task_type):
    global is_processing
    if is_processing: return
    is_processing = True

    if not GROQ_API_KEY:
        set_status("⚠️ 未設定 API Key", "#E06C75")
        time.sleep(1.5)
        hide_status()
        show_help_card()
        is_processing = False
        return

    try:
        if task_type == "replace":
            set_status("⚡ 劃詞替換中...", "#61AFEF")
        elif task_type == "translate":
            set_status("⚡ 劃詞翻譯中...", "#98C379")
        else:
            set_status("⚡ AI 潤飾中...", "#E06C75")
            
        pyperclip.copy("")
        send_copy()
        time.sleep(0.4)
        selected_text = pyperclip.paste().strip()

        if not selected_text:
            set_status("⚠️ 未選取文字", "#E06C75")
            time.sleep(1.0)
            hide_status()
            is_processing = False
            return

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        system_prompt = "你是一個精通多國語言的專業翻譯員。將輸入文字精準翻譯為符合台灣用語習慣的繁體中文。只需輸出翻譯結果。"
        if task_type == "ai_refine":
            system_prompt = (
                "你是一個高效率的 AI 文字助理。請判斷使用者輸入的文字：\n"
                "1. 若為長篇文章或新聞：請整理出 3 個條列式精確重點摘要。\n"
                "2. 若為短句或草稿：請潤飾修訂為文筆流暢、專業客氣且語意通順的繁體中文。\n"
                "只需直接輸出潤飾或摘要結果，不需要任何開場白。"
            )

        payload = {
            "model": "openai/gpt-oss-20b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": selected_text}
            ],
            "temperature": 0.3
        }
        response = requests.post(url, headers=headers, json=payload, timeout=8)
        
        if response.status_code == 200:
            ai_result = response.json()["choices"][0]["message"]["content"].strip()
            ai_result = to_tw_trad(ai_result)
            if task_type == "replace":
                pyperclip.copy(ai_result)
                time.sleep(0.1)
                send_paste()
            elif task_type == "translate":
                show_ai_window("Groq AI 劃詞翻譯", selected_text, ai_result)
            elif task_type == "ai_refine":
                show_ai_window("Groq AI 精修潤飾 / 重點摘要", selected_text, ai_result)
        else:
            if task_type != "replace":
                show_ai_window("AI 處理失敗", selected_text, f"請求失敗 ({response.status_code})\n{response.text}")

    except Exception as e:
        show_ai_window("劃詞異常", "處理失敗", str(e))
    finally:
        is_processing = False
        hide_status()

def start_recording(mode):
    global recording, audio_data, stream, current_mode
    recording = True
    current_mode = mode
    audio_data = []
    
    if mode == "en":
        set_status("🎙️ 錄音中 (中譯英)...", "#61AFEF")
    else:
        set_status("🎙️ 錄音中 (中文)...", "#E06C75")
        
    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback)
    stream.start()

def stop_recording():
    global recording, stream, is_processing, current_mode
    recording = False
    is_processing = True
    
    if stream:
        stream.stop()
        stream.close()
        stream = None
        
    if audio_data:
        threading.Thread(target=process_audio, args=(audio_data.copy(), current_mode), daemon=True).start()
    else:
        is_processing = False
        hide_status()

def trigger_zh():
    global recording, is_processing, current_mode, last_trigger_time
    now = time.time()
    if now - last_trigger_time < 0.4 or is_processing: return
    last_trigger_time = now

    if not recording: start_recording("zh")
    elif current_mode == "zh": stop_recording()

def trigger_en():
    global recording, is_processing, current_mode, last_trigger_time
    now = time.time()
    if now - last_trigger_time < 0.4 or is_processing: return
    last_trigger_time = now

    if not recording: start_recording("en")
    elif current_mode == "en": stop_recording()

# ----------------- 原生 Win32 消息循環線程 -----------------
def win32_hotkey_loop():
    user32 = ctypes.windll.user32

    for hk_id, (name, mod, vk) in HOTKEY_IDS.items():
        user32.UnregisterHotKey(None, hk_id)
        user32.RegisterHotKey(None, hk_id, mod, vk)

    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        if msg.message == 0x0312:  # WM_HOTKEY
            hk_id = msg.wParam
            if hk_id == 4:
                threading.Thread(target=process_selection, args=("replace",), daemon=True).start()
            elif hk_id == 2:
                trigger_en()
            elif hk_id == 3:
                threading.Thread(target=process_selection, args=("translate",), daemon=True).start()
            elif hk_id == 1:
                trigger_zh()
            elif hk_id == 5:
                threading.Thread(target=process_selection, args=("ai_refine",), daemon=True).start()
            elif hk_id == 6:
                show_help_card()
            elif hk_id == 7:
                threading.Thread(target=exit_program, daemon=True).start()
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

if __name__ == "__main__":
    threading.Thread(target=win32_hotkey_loop, daemon=True).start()
    init_gui()
    root.mainloop()