@echo off
chcp 65001 > nul
title 🚀 GroqVoiceTool 全自動 GitHub 部署中...
cd /d "%~dp0"
python deploy.py
pause