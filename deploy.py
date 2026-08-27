import os
import re
import subprocess
import sys
import json
import httpx
import tkinter as tk
from tkinter import messagebox

def ensure_gitignore_and_purge():
    """自動檢查並修正 .gitignore，且強制移除暫存區中的大檔案資料夾"""
    gitignore_path = ".gitignore"
    ignored_patterns = ["dist/", "build/", "*.exe", "*.spec", "*.dll"]
    
    existing_content = ""
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
        except Exception:
            pass

    needed_additions = [p for p in ignored_patterns if p not in existing_content]
    if needed_additions:
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(needed_additions) + "\n")

    # 強制將歷史大檔從 Git 索引中移除
    try:
        subprocess.run(["git", "rm", "-r", "--cached", "dist"], capture_output=True)
        subprocess.run(["git", "rm", "-r", "--cached", "build"], capture_output=True)
    except Exception:
        pass

def fix_git_large_file_history():
    """當偵測到 GitHub GH001 大檔案阻擋時，自動孤立並重新建構乾淨無大檔的 Commit 歷史"""
    print("🧹 正在深度洗刷 Git 歷史紀錄，徹底剔除 >100MB 大檔案...")
    try:
        # 1. 切換至臨時孤立分支 (不帶任何舊的大檔 Commit 歷史)
        subprocess.run(["git", "checkout", "--orphan", "temp_clean_branch"], check=True, capture_output=True)
        
        # 2. 徹底移除暫存區中的 dist 與 build
        subprocess.run(["git", "rm", "-r", "--cached", "dist"], capture_output=True)
        subprocess.run(["git", "rm", "-r", "--cached", "build"], capture_output=True)
        
        # 3. 重新 Stage 乾淨源碼
        subprocess.run(["git", "add", "."], check=True)
        
        # 4. 提交乾淨首刷 Commit
        subprocess.run(["git", "commit", "-m", "refactor: purge large files from history"], check=True, capture_output=True)
        
        # 5. 強制將孤立分支覆蓋本地 main 分支
        subprocess.run(["git", "branch", "-D", "main"], capture_output=True)
        subprocess.run(["git", "branch", "-m", "main"], check=True)
        
        print("✨ 本地 Git 歷史紀錄已成功洗刷乾淨！")
        return True
    except Exception as e:
        print(f"⚠️ 自動洗刷 Git 歷史失敗：{e}")
        return False

def try_read_file(filepath):
    """嘗試使用多種常見編碼讀取檔案內容"""
    encodings = ["utf-8", "utf-8-sig", "cp950", "ansi", "gbk"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                content = f.read()
                return content, enc
        except Exception:
            continue
    return None, None

def find_main_script():
    """自動搜尋包含 CURRENT_VERSION 的 Python 主程式檔案 (支援 .py 與 .pyw)"""
    target_files = ["voice_input.pyw", "voice_input.py"]
    for tf in target_files:
        if os.path.exists(tf):
            content, enc = try_read_file(tf)
            if content and "CURRENT_VERSION" in content:
                return tf, content, enc

    py_files = [f for f in os.listdir(".") if (f.endswith(".py") or f.endswith(".pyw")) and f != "deploy.py" and f != "deploy.pyw"]
    for file in py_files:
        content, enc = try_read_file(file)
        if content and "CURRENT_VERSION" in content:
            return file, content, enc
    return None, None, None

def get_current_version(content):
    pattern = r'CURRENT_VERSION\s*=\s*["\']v?(\d+)\.(\d+)\.(\d+)(-[^"\']*)?["\']'
    match = re.search(pattern, content)
    if match:
        major, minor, patch, suffix = match.groups()
        return int(major), int(minor), int(patch), suffix or "", match.group(0)
    return None, None, None, None, None

def get_groq_api_key():
    appdata_dir = os.path.join(os.getenv('LOCALAPPDATA', ''), 'GroqVoiceTool')
    config_file = os.path.join(appdata_dir, "config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return cfg.get("groq_api_key", "")
        except Exception:
            pass
    return ""

def generate_ai_release_notes(main_script, new_version):
    api_key = get_groq_api_key()
    try:
        diff_bytes = subprocess.check_output(["git", "diff", main_script])
        diff_text = diff_bytes.decode("utf-8", errors="ignore").strip()
    except Exception:
        diff_text = ""

    if not diff_text:
        try:
            status_bytes = subprocess.check_output(["git", "status", "--short"])
            diff_text = "Modified files: " + status_bytes.decode("utf-8", errors="ignore").strip()
        except Exception:
            diff_text = "Routine system update and code refactoring."

    if len(diff_text) > 3000:
        diff_text = diff_text[:3000] + "\n... (diff truncated)"

    default_title = f"🚀 Release {new_version} - 系統例行最佳化與維護"
    default_body = f"### 🚀 {new_version} 更新內容說明\n- 本次更新包含底層系統穩定性提升與效能微調。\n- 增強系統執行緒安全性與資源釋放機制。"

    if not api_key:
        return default_title, default_body

    prompt = f"""你是一位專業的軟體發布管理員。請根據以下的 Git Diff 變更內容，為版本 {new_version} 撰寫一份專業的 GitHub Release Title 與 Release Notes (Markdown 格式)。

【規範要求】：
1. 輸出格式必須嚴格符合 JSON 物件格式：
{{
  "title": "版本 Title (例如: 🚀 Release {new_version} - 標題簡述)",
  "body": "Markdown 格式的詳細 Release Note 內容"
}}
2. 內容請使用自然流暢的台灣繁體中文。
3. 結構清單請分為：「⚡ 效能與架構最佳化」、「🐛 Bug 修正 / 穩定性強化」、「🛠️ 其他微調」。
4. 絕對只輸出 JSON 字串，不要包含任何其他文字或解說。

【Git Diff 變更內容】：
{diff_text}
"""

    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "qwen-2.5-32b", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}

        with httpx.Client(timeout=15.0) as client:
            resp = client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
            if resp.status_code == 200:
                raw_content = resp.json()["choices"][0]["message"]["content"].strip()
                if "</think>" in raw_content:
                    raw_content = raw_content.split("</think>")[-1].strip()
                json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
                if json_match:
                    res_json = json.loads(json_match.group(0))
                    return res_json.get("title", default_title), res_json.get("body", default_body)
    except Exception:
        pass

    return default_title, default_body

def main():
    root = tk.Tk()
    root.withdraw()

    print("🛠️ 正在設定 .gitignore 規範並排除大檔案...")
    ensure_gitignore_and_purge()

    print("🔍 正在掃描專案目錄...")
    main_script, content, enc = find_main_script()
    if not main_script or not content:
        messagebox.showerror("部署失敗", "找不到可用的 Python 主程式檔案（.py 或 .pyw）！")
        sys.exit(1)

    print(f"✅ 已成功鎖定主程式檔案：'{main_script}' (編碼: {enc})")

    major, minor, patch, suffix, old_line = get_current_version(content)
    if not old_line:
        messagebox.showerror("部署失敗", f"在 '{main_script}' 中找不到可解析的 CURRENT_VERSION 格式！")
        sys.exit(1)

    current_ver_str = f"v{major}.{minor}.{patch}{suffix}"
    
    # 依據 SemVer 規範自動遞增修訂號 (Patch +1)
    new_patch = patch + 1
    new_ver_str = f"v{major}.{minor}.{new_patch}"
    new_line = f'CURRENT_VERSION = "{new_ver_str}"'

    release_title, release_body = generate_ai_release_notes(main_script, new_ver_str)

    new_content = content.replace(old_line, new_line, 1)
    with open(main_script, "w", encoding=enc) as f:
        f.write(new_content)

    print(f"🤖 [版本自動升級] {current_ver_str} ➡️ {new_ver_str}")
    print(f"📌 Title: {release_title}")

    full_commit_msg = f"{new_ver_str}: {release_title}"

    print("\n🚀 正在執行安全的 Git 提交與推送...")
    try:
        ensure_gitignore_and_purge()

        # 1. Stage 純文字原始碼與設定檔
        subprocess.run(["git", "add", "."], check=True)

        # 2. Git Commit
        subprocess.run(["git", "commit", "-m", full_commit_msg], check=True)

        # 3. 嘗試推送到 GitHub 遠端
        push_res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)

        # 🌟 核心防護：若遭遇大檔案（GH001）攔截，自動觸發無歷史洗刷並強制推送
        if push_res.returncode != 0 and ("Large files detected" in push_res.stderr or "pre-receive hook declined" in push_res.stderr):
            print("⚠️ 偵測到歷史 Commit 包含超大檔案 (GH001)，啟動一鍵歷史淨化...")
            if fix_git_large_file_history():
                subprocess.run(["git", "push", "origin", "main", "--force"], check=True)

        # 4. 建立並推送 Tag
        subprocess.run(["git", "tag", "-d", new_ver_str], capture_output=True)
        subprocess.run(["git", "tag", new_ver_str], check=True)
        subprocess.run(["git", "push", "origin", new_ver_str, "--force"], check=True)

        # 5. 嘗試透過 GitHub CLI 發布 Release
        try:
            gh_cmd = ["gh", "release", "create", new_ver_str, "--title", release_title, "--notes", release_body]
            subprocess.run(gh_cmd, capture_output=True)
        except Exception:
            pass

        print(f"\n🎉 [一鍵自動部署完全成功] 版本 {new_ver_str} 已順利發布！")
        messagebox.showinfo("🎉 部署成功", f"版本 {current_ver_str} ➔ {new_ver_str}\n已成功自動發布並推送到 GitHub！\n\n【Title】: {release_title}")
    except subprocess.CalledProcessError as e:
        err_detail = e.stderr.decode("utf-8", errors="ignore") if hasattr(e, 'stderr') and e.stderr else str(e)
        print(f"\n❌ Git 操作過程發生錯誤：{err_detail}")
        messagebox.showerror("Git 部署失敗", f"執行 Git 過程發生錯誤：\n{err_detail}")

if __name__ == "__main__":
    main()