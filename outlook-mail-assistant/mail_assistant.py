"""Outlook 信件助理：新信即時分析、分級、建議回覆，並定時寄出彙整報告。

用法：
    python mail_assistant.py watch              持續監看（預設）
    python mail_assistant.py once --hours 24    分析最近 24 小時的信後結束
    python mail_assistant.py digest             立即產生一份彙整報告
    加上 --dry-run：不呼叫 Claude、不寫回 Outlook，只印出將送出的內容
"""

import argparse
import logging
import sys
import time
import tomllib
from datetime import datetime, timedelta
from pathlib import Path

import pythoncom

import report
from analyzer import PRIORITIES, AnalysisError, build_user_message, make_analyzer
from outlook_reader import OutlookReader, since_hours_ago
from store import Store

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
REPORTS = BASE / "reports"
log = logging.getLogger("mail_assistant")


def contains_any(text: str, needles: list) -> bool:
    text = text.lower()
    return any(n.lower() in text for n in needles if n)


def higher(p1: str, p2: str) -> str:
    return p1 if PRIORITIES.index(p1) <= PRIORITIES.index(p2) else p2


class Assistant:
    def __init__(self, cfg: dict, dry_run: bool = False, use_events: bool = True):
        self.cfg = cfg
        self.dry_run = dry_run
        self.use_events = use_events
        self.reader = OutlookReader(cfg, use_events=use_events)
        self.store = Store(DATA / "mails.db")
        self.analyzer = None if dry_run else make_analyzer(cfg, DATA)
        REPORTS.mkdir(exist_ok=True)

    # ---------- 單封信處理 ----------

    def classify_without_llm(self, mail: dict):
        f = self.cfg.get("filters", {})
        if contains_any(mail["sender_email"], f.get("skip_senders", [])) or contains_any(
            mail["subject"], f.get("skip_subject_keywords", [])
        ):
            return "skipped"
        if contains_any(mail["subject"] + "\n" + mail["body"], f.get("sensitive_keywords", [])):
            return "sensitive"
        if f.get("treat_outlook_sensitivity_as_sensitive", True) and mail["sensitivity"] in ("私人", "機密"):
            return "sensitive"
        return None

    def priority_floor(self, mail: dict) -> str | None:
        p = self.cfg.get("priority", {})
        if contains_any(mail["sender_email"], p.get("vip_senders", [])):
            return "P2"
        if contains_any(mail["subject"] + "\n" + mail["body"], p.get("urgent_keywords", [])):
            return "P2"
        return None

    def process_item(self, item):
        if not self.reader.is_supported(item):
            return
        mail = self.reader.to_dict(item)
        if not self.store.should_process(mail["key"]):
            return

        status = self.classify_without_llm(mail)
        if status == "skipped":
            self.save_simple(mail, "skipped", "P4")
            return
        if status == "sensitive":
            self.save_simple(mail, "sensitive", "P2", "信件含機密關鍵字或標示為機密，未送給 Claude，請自行處理。")
            self.notify("P2", f"🔒 機密信件：{mail['subject']}", mail["sender_name"])
            return

        if self.dry_run:
            print("=" * 60)
            print(build_user_message(mail, self.cfg["analyzer"].get("max_body_chars", 6000)))
            return

        log.info("分析中：%s｜%s", mail["sender_name"], mail["subject"])
        try:
            a = self.analyzer.analyze(mail)
        except (AnalysisError, OSError, ValueError) as e:
            log.error("分析失敗：%s｜%s", mail["subject"], e)
            self.store.save(mail, "failed", "P3", error=str(e))
            return

        floor = self.priority_floor(mail)
        if floor and higher(floor, a["priority"]) != a["priority"]:
            a["priority_reason"] += f"（規則：重要寄件者或急件關鍵字，提升為 {floor}）"
            a["priority"] = floor

        self.store.save(mail, "analyzed", a["priority"], a)
        self.append_daily(report.mail_entry_md(mail, a))
        log.info("%s｜%s｜%s", a["priority"], mail["subject"], a["summary"])
        self.apply_actions(item, mail, a)

    def save_simple(self, mail: dict, status: str, priority: str, note: str = ""):
        log.info("%s｜%s", report.STATUS_LABEL[status], mail["subject"])
        if not self.dry_run:
            self.store.save(mail, status, priority)
            self.append_daily(report.simple_entry_md(mail, status, note))

    def apply_actions(self, item, mail: dict, a: dict):
        act = self.cfg.get("actions", {})
        p = a["priority"]
        try:
            if act.get("set_outlook_category"):
                self.reader.set_category(item, report.PRIORITY_LABEL[p].split(" ", 1)[1].replace(" ", "-"))
            if (
                act.get("create_reply_draft")
                and a["reply_needed"]
                and a["reply_draft"]
                and higher(p, act.get("draft_min_priority", "P2")) == p
            ):
                self.reader.create_reply_draft(item, a["reply_draft"])
        except pythoncom.com_error as e:
            log.warning("寫回 Outlook 失敗：%s", e)
        self.notify(p, f"{report.PRIORITY_LABEL[p]}｜{mail['subject']}", a["summary"])

    def notify(self, priority: str, title: str, body: str):
        min_p = self.cfg.get("actions", {}).get("notify_min_priority", "P2")
        if self.dry_run or higher(priority, min_p) != priority:
            return
        try:
            from win11toast import notify
        except ImportError:
            return
        try:
            notify(title, body[:200])
        except Exception as e:  # 通知失敗不影響主流程
            log.warning("桌面通知失敗：%s", e)

    def append_daily(self, text: str):
        path = REPORTS / f"{datetime.now():%Y-%m-%d}.md"
        new = not path.exists()
        with path.open("a", encoding="utf-8") as f:
            if new:
                f.write(f"# 信件分析紀錄 {datetime.now():%Y-%m-%d}\n\n")
            f.write(text)

    # ---------- 輪詢補抓 ----------

    def catch_up(self, since: datetime | None = None):
        started = datetime.now()
        if since is None:
            last = self.store.get_meta("last_scan_at")
            since = (
                datetime.fromisoformat(last) - timedelta(minutes=5)
                if last
                else since_hours_ago(self.cfg["outlook"].get("lookback_hours", 24))
            )
        for item in list(self.reader.scan_since(since)):
            self.process_item(item)
        for entry_id in self.store.retryable_entry_ids():
            self.process_item(self.reader.get_item(entry_id))
        if not self.dry_run:
            self.store.set_meta("last_scan_at", started.isoformat(timespec="seconds"))

    def process_new_mail_events(self):
        self.reader.pump_events()
        for entry_id in self.reader.take_pending_ids():
            self.process_item(self.reader.get_item(entry_id))

    # ---------- 彙整報告 ----------

    def latest_digest_slot(self, now: datetime) -> datetime | None:
        slots = []
        for t in self.cfg.get("digest", {}).get("times", []):
            h, m = map(int, t.split(":"))
            for day in (now.date(), now.date() - timedelta(days=1)):
                slot = datetime.combine(day, datetime.min.time()).replace(hour=h, minute=m)
                if slot <= now:
                    slots.append(slot)
        return max(slots) if slots else None

    def digest_due(self) -> bool:
        last = self.store.get_meta("last_digest_at")
        if not last:
            self.store.set_meta("last_digest_at", datetime.now().isoformat(timespec="seconds"))
            return False
        slot = self.latest_digest_slot(datetime.now())
        return slot is not None and datetime.fromisoformat(last) < slot

    def run_digest(self):
        now = datetime.now()
        since = self.store.get_meta("last_digest_at") or (now - timedelta(days=1)).isoformat(timespec="seconds")
        rows = self.store.processed_since(since)
        days = self.cfg.get("digest", {}).get("followup_days", 3)
        followups = []
        for r in self.store.open_followups((now - timedelta(days=days)).strftime("%Y-%m-%d %H:%M")):
            item = self.reader.get_item(r["entry_id"])
            if item is not None and not self.reader.has_replied(item):
                followups.append(r)

        title = f"信件彙整 {now:%Y-%m-%d %H:%M}（自 {since.replace('T', ' ')[:16]} 起）"
        path = REPORTS / f"digest-{now:%Y%m%d-%H%M}.md"
        path.write_text(report.digest_md(title, rows, followups), encoding="utf-8")
        log.info("彙整報告：%s（新信 %d 封，待回覆 %d 封）", path, len(rows), len(followups))

        if self.cfg.get("digest", {}).get("email_to_self") and not self.dry_run:
            try:
                self.reader.send_to_self(f"[信件助理] {title}", report.digest_html(title, rows, followups))
            except (pythoncom.com_error, RuntimeError) as e:
                log.warning("寄送彙整報告失敗：%s", e)
        if not self.dry_run:
            self.store.set_meta("last_digest_at", now.isoformat(timespec="seconds"))

    # ---------- 主迴圈 ----------

    def watch(self):
        poll = timedelta(minutes=self.cfg["outlook"].get("poll_minutes", 5))
        log.info("開始監看（新信事件：%s，輪詢間隔：%s）", "啟用" if self.reader.events_enabled else "停用", poll)
        self.catch_up()
        next_poll = datetime.now() + poll
        while True:
            try:
                self.process_new_mail_events()
                if datetime.now() >= next_poll:
                    self.catch_up()
                    next_poll = datetime.now() + poll
                if self.digest_due():
                    self.run_digest()
            except pythoncom.com_error as e:
                log.error("Outlook 連線錯誤（Outlook 是否已關閉？）30 秒後重試：%s", e)
                time.sleep(30)
                self.reader = OutlookReader(self.cfg, use_events=self.use_events)
            time.sleep(1)


def main():
    ap = argparse.ArgumentParser(description="Outlook 信件助理")
    ap.add_argument("command", nargs="?", default="watch", choices=["watch", "once", "digest"])
    ap.add_argument("--config", default=str(BASE / "config.toml"))
    ap.add_argument("--hours", type=float, help="once 模式：分析最近幾小時的信")
    ap.add_argument("--dry-run", action="store_true", help="不呼叫 Claude、不寫回 Outlook")
    args = ap.parse_args()

    DATA.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(DATA / "assistant.log", encoding="utf-8")],
    )
    config_path = Path(args.config)
    if not config_path.exists():
        sys.exit(f"找不到 {config_path}，請先複製 config.example.toml 成 config.toml 並修改")
    cfg = tomllib.loads(config_path.read_text(encoding="utf-8"))

    try:
        assistant = Assistant(cfg, dry_run=args.dry_run, use_events=args.command == "watch")
    except AnalysisError as e:
        sys.exit(str(e))

    if args.command == "watch":
        assistant.watch()
    elif args.command == "once":
        assistant.catch_up(since_hours_ago(args.hours) if args.hours else None)
    else:
        assistant.run_digest()


if __name__ == "__main__":
    main()
