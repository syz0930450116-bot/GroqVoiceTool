import os
import re
import sys
import subprocess

TARGET_FILE = "voice_input.pyw"

def get_current_version():
    if not os.path.exists(TARGET_FILE):
        print(f"❌ 錯誤：找不到 {TARGET_FILE}，請確認程式碼位於專案根目錄！")
        sys.exit(1)
    
    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        match = re.search(r'CURRENT_VERSION\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
    
    print("❌ 錯誤：無法在檔案中找到 CURRENT_VERSION 變數！")
    sys.exit(1)

def run_cmd(cmd, desc):
    print(f"\n🚀 [執行中] {desc}...")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"⚠️ {desc} 執行失敗！")
        return False
    return True

def main():
    ver = get_current_version()
    print("=" * 60)
    print(f"📦 Groq Voice Tool 自動打包與發布助手 (偵測到版本：{ver})")
    print("=" * 60)

    # 1. 自動打 Tag 並推送至 Git
    print("\n[Step 1/3] 正在處理 Git 提交與 Tag...")
    run_cmd(f'git add {TARGET_FILE}', "新增 Git 修改")
    run_cmd(f'git commit -m "bump: 發布新版本 {ver}"', "Git Commit")
    run_cmd(f'git tag -d {ver}', f"清理本地舊 Tag {ver} (若存在)")
    run_cmd(f'git tag {ver}', f"建立新 Tag {ver}")
    run_cmd('git push origin main --force', "推送到 Git 主分支")
    run_cmd(f'git push origin {ver} --force', f"強制推送 Tag {ver} 至雲端")

    # 2. 執行打包
    print("\n[Step 2/3] 開始使用 PyInstaller 打包程式...")
    build_cmd = f"{sys.executable} -m PyInstaller --noconsole --onefile {TARGET_FILE}"
    if not run_cmd(build_cmd, "PyInstaller 打包"):
        print("❌ 打包中斷，請檢查錯誤日誌！")
        return

    exe_path = os.path.join("dist", "voice_input.exe")
    if not os.path.exists(exe_path):
        print("❌ 打包完成但找不到 dist/voice_input.exe！")
        return

    print(f"\n✅ 打包成功！EXE 路徑：{os.path.abspath(exe_path)}")

    # 3. 發布選擇
    print("\n[Step 3/3] 請選擇 Release 發布方式：")
    print(" 1️⃣ 自動透過 GitHub CLI 發布 Release 並上傳 EXE")
    print(" 2️⃣ 完成！我會手動拖曳 EXE 到 GitHub 網頁")
    
    choice = input("\n請輸入選擇 (1 或 2，預設 2): ").strip()

    if choice == "1":
        gh_cmd = f'gh release create {ver} .\\dist\\voice_input.exe --title "{ver} 自動修復更新" --notes "版本 {ver} 已發布，包含最新修復與優化。"'
        if not run_cmd(gh_cmd, "GitHub CLI 發布"):
            print("\n⚠️ CLI 自動上傳失敗，已備用切換為網頁上傳模式。")
            upload_cmd = f'gh release upload {ver} .\\dist\\voice_input.exe --clobber'
            run_cmd(upload_cmd, "嘗試覆蓋上傳 EXE")

    print("\n" + "=" * 60)
    print(f"🎉 版本 {ver} 打包作業順利完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()