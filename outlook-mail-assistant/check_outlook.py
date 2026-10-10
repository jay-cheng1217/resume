"""檢查這台電腦能否透過 COM 讀取 Outlook。只讀取帳號與數量，不讀信件內容，不會把任何資料送出去。"""

import platform
import sys

print(f"Python {sys.version.split()[0]}  Windows {platform.release()}")

try:
    import pythoncom
    import win32com.client
except ImportError:
    print("[失敗] 沒有安裝 pywin32。請執行：py -m pip install pywin32")
    sys.exit(1)

try:
    app = win32com.client.Dispatch("Outlook.Application")
except pythoncom.com_error as e:
    print("[失敗] 無法連接 Outlook：", e)
    print("可能原因：只安裝了新版 Outlook（COM 不支援），或傳統版 Outlook 沒有安裝。")
    sys.exit(1)

try:
    print("Outlook 版本:", app.Version)
    ns = app.GetNamespace("MAPI")
    print("目前使用者:", ns.CurrentUser.Name)
    for acct in ns.Accounts:
        print("帳號:", acct.DisplayName, "|", acct.SmtpAddress)
    inbox = ns.GetDefaultFolder(6)
    print("收件匣:", inbox.FolderPath, "| 信件數:", inbox.Items.Count)
    print()
    print("[成功] 可以讀取 Outlook，下一步可以執行 mail_assistant.py")
except pythoncom.com_error as e:
    print("[失敗] 讀取 Outlook 資料時發生錯誤：", e)
    print("如果剛才有跳出 Outlook 安全性警告，代表公司政策有限制，請勿按允許，將畫面提供給 IT 或 Claude。")
    sys.exit(1)
