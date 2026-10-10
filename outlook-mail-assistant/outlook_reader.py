"""透過 Outlook COM（傳統版 Outlook）讀取信件。只在 Windows 上執行。"""

import re
from datetime import datetime, timedelta

import pythoncom
import win32com.client

OL_FOLDER_INBOX = 6
OL_MAIL = 43
OL_MEETING_REQUEST = 53
OL_SENSITIVITY = {0: "一般", 1: "個人", 2: "私人", 3: "機密"}
OL_IMPORTANCE = {0: "低", 1: "一般", 2: "高"}

PR_INTERNET_MESSAGE_ID = "http://schemas.microsoft.com/mapi/proptag/0x1035001F"
PR_LAST_VERB_EXECUTED = "http://schemas.microsoft.com/mapi/proptag/0x10810003"
REPLY_VERBS = {102, 103, 104}  # 回覆、全部回覆、轉寄

# 引用的舊信從這些行開始，之後的內容不送去分析
QUOTE_MARKERS = re.compile(
    r"^\s*(From:|寄件者:|寄件者：|-----Original Message-----|-----原始郵件-----|_{20,}|On .+ wrote:)",
    re.MULTILINE,
)


def strip_quoted(body: str) -> str:
    body = body.replace("\r\n", "\n")
    m = QUOTE_MARKERS.search(body)
    if m and m.start() > 0:
        body = body[: m.start()]
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def to_local_naive(dt) -> datetime:
    # pywin32 回傳的時間帶有不正確的時區標記，實際值是本機時間
    return datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


def smtp_of(address_entry) -> str:
    if address_entry is None:
        return ""
    try:
        if address_entry.Type == "EX":
            user = address_entry.GetExchangeUser()
            if user is not None:
                return (user.PrimarySmtpAddress or "").lower()
            dl = address_entry.GetExchangeDistributionList()
            if dl is not None:
                return (dl.PrimarySmtpAddress or "").lower()
        return (address_entry.Address or "").lower()
    except pythoncom.com_error:
        return ""


class OutlookEvents:
    pending_ids: list = []

    def OnNewMailEx(self, received_item_ids):
        OutlookEvents.pending_ids.extend(i for i in received_item_ids.split(",") if i)


class OutlookReader:
    def __init__(self, cfg: dict, use_events: bool = True):
        self.cfg = cfg
        self.events_enabled = False
        if use_events:
            try:
                self.app = win32com.client.DispatchWithEvents("Outlook.Application", OutlookEvents)
                self.events_enabled = True
            except Exception:  # 型別庫產生失敗等狀況，退回純輪詢
                self.app = win32com.client.Dispatch("Outlook.Application")
        else:
            self.app = win32com.client.Dispatch("Outlook.Application")
        self.ns = self.app.GetNamespace("MAPI")
        self.my_addresses = {a.lower() for a in cfg["me"].get("addresses", [])}
        try:
            self.my_addresses.add(smtp_of(self.ns.CurrentUser.AddressEntry))
        except pythoncom.com_error:
            pass
        self.my_addresses.discard("")

    # ---------- 新信事件 ----------

    def pump_events(self):
        pythoncom.PumpWaitingMessages()

    def take_pending_ids(self) -> list:
        ids = OutlookEvents.pending_ids[:]
        OutlookEvents.pending_ids.clear()
        return ids

    def get_item(self, entry_id):
        try:
            return self.ns.GetItemFromID(entry_id)
        except pythoncom.com_error:
            return None

    # ---------- 輪詢掃描 ----------

    def resolve_folder(self, path: str):
        parts = [p for p in path.split("/") if p]
        inbox = self.ns.GetDefaultFolder(OL_FOLDER_INBOX)
        if parts[0].lower() == "inbox":
            folder = inbox
        else:
            folder = inbox.Parent.Folders[parts[0]]
        for name in parts[1:]:
            folder = folder.Folders[name]
        return folder

    def scan_since(self, since: datetime):
        """依收件時間由新到舊走訪，遇到早於 since 的信就停止（避開 Restrict 的地區日期格式問題）。"""
        max_scan = self.cfg["outlook"].get("max_scan", 200)
        for path in self.cfg["outlook"].get("folders", ["Inbox"]):
            items = self.resolve_folder(path).Items
            items.Sort("[ReceivedTime]", True)
            item = items.GetFirst()
            count = 0
            while item is not None and count < max_scan:
                count += 1
                if item.Class in (OL_MAIL, OL_MEETING_REQUEST):
                    if to_local_naive(item.ReceivedTime) < since:
                        break
                    yield item
                item = items.GetNext()

    # ---------- 信件轉換 ----------

    def is_supported(self, item) -> bool:
        return item is not None and item.Class in (OL_MAIL, OL_MEETING_REQUEST)

    def message_key(self, item) -> str:
        try:
            mid = item.PropertyAccessor.GetProperty(PR_INTERNET_MESSAGE_ID)
            if mid:
                return mid
        except pythoncom.com_error:
            pass
        return item.EntryID

    def has_replied(self, item) -> bool:
        try:
            return item.PropertyAccessor.GetProperty(PR_LAST_VERB_EXECUTED) in REPLY_VERBS
        except pythoncom.com_error:
            return False

    def to_dict(self, item) -> dict:
        to, cc, my_role = [], [], "未在收件者中（可能是群組信）"
        for r in item.Recipients:
            addr = smtp_of(r.AddressEntry)
            label = f"{r.Name} <{addr}>" if addr else r.Name
            if r.Type == 2:
                cc.append(label)
            else:
                to.append(label)
            if addr in self.my_addresses:
                my_role = "副本 CC" if r.Type == 2 else "收件者 To"

        sender_email = ""
        if getattr(item, "SenderEmailType", "") == "EX":
            sender_email = smtp_of(getattr(item, "Sender", None))
        if not sender_email:
            sender_email = (getattr(item, "SenderEmailAddress", "") or "").lower()

        meeting_start = ""
        if item.Class == OL_MEETING_REQUEST:
            try:
                appt = item.GetAssociatedAppointment(False)
                meeting_start = to_local_naive(appt.Start).strftime("%Y-%m-%d %H:%M")
            except (pythoncom.com_error, AttributeError):
                pass

        return {
            "key": self.message_key(item),
            "entry_id": item.EntryID,
            "subject": item.Subject or "",
            "sender_name": item.SenderName or "",
            "sender_email": sender_email,
            "to": to,
            "cc": cc,
            "my_role": my_role,
            "received": to_local_naive(item.ReceivedTime).strftime("%Y-%m-%d %H:%M"),
            "importance": OL_IMPORTANCE.get(item.Importance, "一般"),
            "sensitivity": OL_SENSITIVITY.get(item.Sensitivity, "一般"),
            "attachments": [a.FileName for a in item.Attachments],
            "body": strip_quoted(item.Body or ""),
            "meeting_start": meeting_start,
        }

    # ---------- 寫回 Outlook ----------

    def set_category(self, item, category: str):
        existing = [c.strip() for c in (item.Categories or "").split(",") if c.strip()]
        existing = [c for c in existing if not re.match(r"^P[1-4]-", c)]
        item.Categories = ", ".join(existing + [category])
        item.Save()

    def create_reply_draft(self, item, draft: str):
        reply = item.Reply()
        reply.Body = f"{draft}\n\n{reply.Body}"
        reply.Save()  # 只存到草稿匣，不寄出

    def send_to_self(self, subject: str, html: str):
        if not self.my_addresses:
            raise RuntimeError("找不到你的信箱，請在 config 的 me.addresses 設定")
        mail = self.app.CreateItem(0)
        mail.To = sorted(self.my_addresses)[0]
        mail.Subject = subject
        mail.HTMLBody = html
        mail.Send()


def since_hours_ago(hours: float) -> datetime:
    return datetime.now() - timedelta(hours=hours)
