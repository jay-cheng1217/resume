@echo off
chcp 65001 >nul
title Outlook 連線檢查
echo === 1/2 安裝 pywin32 ===
py -m pip install pywin32 --quiet 2>nul || python -m pip install pywin32 --quiet
if errorlevel 1 (
    echo.
    echo [失敗] 找不到 Python。請到 Microsoft Store 搜尋 "Python 3.12" 安裝後再執行一次。
    pause
    exit /b 1
)
echo.
echo === 2/2 讀取 Outlook 帳號（請先打開 Outlook）===
py "%~dp0check_outlook.py" 2>nul || python "%~dp0check_outlook.py"
echo.
echo 請把上面的畫面全部複製貼給 Claude。
pause
