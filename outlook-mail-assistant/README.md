# Outlook 信件助理

在 Windows 本機監看傳統版 Outlook，新信寄到時用 Claude 摘要、分級（P1–P4），並給出建議回覆、要準備的資料、要找誰協助；每天定時產生彙整報告寄給自己。

> ⚠️ **使用前請先確認公司政策**：信件內容會傳送到 Anthropic（Claude）分析。若公司的 Entra ID 已封鎖 Claude 的 M365 連接器，代表 IT 有管控這類資料流向。請先確認 AI 工具使用規範，以及你用的是公司授權的 Claude 帳號。

## 運作流程

| 階段 | 做法 | 資料是否離開本機 |
|---|---|---|
| 1. 收信 | Outlook `NewMailEx` 事件即時觸發；每 N 分鐘輪詢補抓漏掉的信 | 否 |
| 2. 規則過濾 | 電子報、系統通知直接記為 P4；含機密關鍵字或 Outlook 標示「私人／機密」的信**不送出**，只提醒你人工處理 | 否 |
| 3. 精簡內容 | 移除引用的舊信、截斷過長內文；附件只送檔名 | 否 |
| 4. Claude 分析 | 摘要、等級、分類、期限、建議動作、準備資料、找誰、建議回覆、風險 | **是** |
| 5. 規則保底 | 重要寄件者或急件關鍵字至少 P2（防止模型低估） | 否 |
| 6. 輸出 | 每日 Markdown 紀錄、桌面通知、（選用）Outlook 分類標籤、（選用）回覆草稿 | 否 |
| 7. 定時彙整 | 依設定時間產生報告：新信總表＋「P1/P2 需回覆但還沒回」清單，寄給自己 | 否（在 Outlook 內寄給自己） |

## 優先等級

| 等級 | 定義 |
|---|---|
| 🔴 P1 | 今天內處理：主管或客戶直接要求、阻擋他人工作、量產或出貨風險、當日期限 |
| 🟠 P2 | 1–2 個工作天內：需要你回覆、決策或提供資料 |
| 🟡 P3 | 本週內：一般溝通、你只在 CC |
| ⚪ P4 | 參考：通知、電子報 |

## 環境需求

| 項目 | 需求 |
|---|---|
| 作業系統 | Windows 10/11 |
| Outlook | **傳統版 Outlook**（新版 Outlook 不支援 COM） |
| Python | 3.11 以上 |
| Claude | 二擇一：本機 Claude Code（用你登入的 Claude 帳號），或 Anthropic API Key |

## 安裝

```powershell
# 1. 安裝 Claude Code（原生版，產生 claude.exe），安裝後執行 claude 完成登入
irm https://claude.ai/install.ps1 | iex
claude

# 2. 安裝 Python 套件
cd outlook-mail-assistant
py -m pip install -r requirements.txt

# 3. 建立設定檔
copy config.example.toml config.toml
notepad config.toml
```

### 設定檔重點

| 區塊 | 要改什麼 |
|---|---|
| `[me]` | `role` 寫你的職務、`addresses` 填你的公司信箱 |
| `[priority]` | `vip_senders` 填主管、重要客戶網域；`urgent_keywords` 依產品線調整 |
| `[filters]` | `sensitive_keywords` 依公司機密分級補充 |
| `[[directory]]` | 「主題 → 窗口」對照表。Claude 只會從這裡推薦人選，不會自己編名字 |
| `[actions]` | 是否加 Outlook 分類標籤、是否自動建立回覆草稿（只存草稿，**絕不自動寄出**） |
| `[digest]` | 彙整時間、是否寄給自己 |
| `[analyzer]` | `backend`、`model`，詳見下表 |

### 分析後端

| backend | 認證 | 計費 | 備註 |
|---|---|---|---|
| `claude_cli`（預設） | 本機 `claude` 已登入的帳號 | 計入你的 Claude 方案額度 | 執行時不載入任何工具、MCP，也不保存對話 |
| `api` | 環境變數 `ANTHROPIC_API_KEY` | 依 token 計費 | 已啟用 `fallbacks: "default"`：模型拒答時自動改用 Anthropic 建議的備援模型 |

預設模型是 `claude-opus-5-5`。信件量大、想省額度或加快速度，可以把 `model` 改成 `claude-sonnet-5-5` 或 `claude-haiku-5-5`（`claude_cli` 也接受 `sonnet`、`haiku` 這類別名）。

## 使用

| 指令 | 用途 |
|---|---|
| `py mail_assistant.py once --hours 4 --dry-run` | **第一次先跑這個**：只印出將送給 Claude 的內容，不呼叫 Claude、不寫回 Outlook |
| `py mail_assistant.py once --hours 4` | 分析最近 4 小時的信後結束 |
| `py mail_assistant.py watch` | 持續監看（新信即時分析＋定時彙整） |
| `py mail_assistant.py digest` | 立即產生一份彙整報告 |

### 輸出位置

| 檔案 | 內容 |
|---|---|
| `reports/YYYY-MM-DD.md` | 當天每封信的完整分析（含建議回覆） |
| `reports/digest-*.md` | 每次的彙整報告 |
| `data/mails.db` | SQLite，記錄已處理的信（避免重複分析） |
| `data/assistant.log` | 執行紀錄 |

`config.toml`、`data/`、`reports/` 已列入 `.gitignore`，**不要提交到 Git**。

## 開機自動執行（工作排程器）

```powershell
$py = (Get-Command pythonw).Source
$script = (Resolve-Path .\mail_assistant.py).Path
schtasks /Create /TN "OutlookMailAssistant" /SC ONLOGON /RL LIMITED `
  /TR "`"$py`" `"$script`" watch"
```

用 `pythonw` 執行不會出現視窗，執行狀況請看 `data/assistant.log`。停用：`schtasks /Delete /TN "OutlookMailAssistant" /F`。

## 疑難排解

| 狀況 | 原因與處理 |
|---|---|
| `找不到 claude 執行檔` | Claude Code 不在 PATH 中，在 `config.toml` 的 `claude_path` 填入完整路徑（通常是 `%USERPROFILE%\.local\bin\claude.exe`） |
| `claude.cmd 是批次檔` | 你用的是 npm 安裝版。請改裝原生版（見安裝步驟） |
| Outlook 跳出「有程式嘗試存取電子郵件地址」之類的安全性警告 | 公司 GPO 或防毒狀態觸發的 Outlook 安全性提示。**不要嘗試繞過**，請洽 IT，或改用手動匯出 |
| 啟動時建立 `Outlook.Application` 失敗 | 多半是只裝了新版 Outlook，或傳統版未安裝。請切回或安裝傳統版 Outlook |
| 新信事件沒反應 | 程式會自動退回輪詢模式（每 `poll_minutes` 分鐘），log 開頭會寫出「新信事件：停用」 |
| 分析失敗 | 記為「⚠️ 分析失敗」並列在彙整報告中；每次輪詢會自動重試，同一封信最多 3 次 |
| 子資料夾的信沒被抓到 | Outlook 規則把信移走了。在 `folders` 加上 `"Inbox/子資料夾名稱"` |
