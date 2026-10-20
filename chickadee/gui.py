import asyncio
from collections import Counter
from datetime import datetime
from pathlib import Path
import json
import queue
from threading import Event, Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .demo import DemoSite
from .detection import LABELS, Rules
from .candidates import CATEGORY_LABELS
from .profiles import SiteProfile
from .scanner import ScanConfig, ScanOutcome, output_directory, scan

STATUS = {"completed": "점검 완료", "partial": "일부 결과 · 누락 확인 필요",
          "cancelled": "사용자 중단 · 일부 결과", "failed": "점검 실패"}
BG, NAV, INK, MUTED, ACCENT = "#f3f6fb", "#14283f", "#182b44", "#67788c", "#087f80"


class Application:
    def __init__(self, root, folder=None, demo=False, allow_network=True, rules_path=None, profile_path=None, initial_url=None):
        self.root, self.folder = root, Path(folder or output_directory())
        self.allow_network, self.rules_path, self.profile_path = allow_network, rules_path, profile_path
        self.events, self.stop = queue.Queue(), Event()
        self.worker = self.demo_site = self.outcome = None
        self.findings, self.candidates = [], []
        self.closing, self.sort_reverse = False, False
        self.sort_key = "id"
        self.url, self.search = tk.StringVar(value=initial_url or ""), tk.StringVar()
        self.page_limit, self.time_limit = tk.StringVar(value="100"), tk.StringVar(value="300")
        self.filter = tk.StringVar(value="전체")
        self.status = tk.StringVar(value="URL을 입력하고 점검을 시작하세요.")
        self.counts, self.metrics = tk.StringVar(), tk.StringVar(value="준비 완료")
        self.path_label = tk.StringVar(value=str(self.folder))
        self._build()
        self.search.trace_add("write", lambda *_: self.refresh())
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self._poll)
        self.refresh()
        if demo:
            self.prepare_demo()

    def _build(self):
        self.root.title(f"Chickadee Bot {__version__} · 웹사이트 광고 점검")
        width = min(1440, self.root.winfo_screenwidth() - 60)
        height = min(920, self.root.winfo_screenheight() - 70)
        self.root.geometry(f"{width}x{height}+20+10")
        self.root.minsize(1080, 680)
        self.root.configure(bg=BG)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=INK, font=("맑은 고딕", 10))
        style.configure("Title.TLabel", font=("맑은 고딕", 22, "bold"))
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("TButton", padding=(12, 8), font=("맑은 고딕", 10))
        style.configure("Accent.TButton", background=ACCENT, foreground="white", padding=(22, 10))
        style.map("Accent.TButton", background=[("active", "#096b72"), ("disabled", "#afc4cb")])
        style.configure("Treeview", rowheight=37, font=("맑은 고딕", 10), background="white", fieldbackground="white", borderwidth=0)
        style.configure("Treeview.Heading", font=("맑은 고딕", 9, "bold"), foreground=MUTED, padding=(8, 12), background="#edf2f8")
        style.map("Treeview", background=[("selected", "#dcefeb")], foreground=[("selected", INK)])
        style.configure("TNotebook", background="white", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(14, 9), font=("맑은 고딕", 9))
        style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor="#dfe7f0", borderwidth=0)

        sidebar = tk.Frame(self.root, bg=NAV, width=204, padx=20, pady=28)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="CHICKADEE", bg=NAV, fg="#71d2c7", font=("맑은 고딕", 16, "bold")).pack(anchor="w")
        tk.Label(sidebar, text="웹사이트 광고 점검", bg=NAV, fg="#c3d1e1", font=("맑은 고딕", 10)).pack(anchor="w", pady=(5, 32))
        def nav_button(text, command, primary=False):
            button = tk.Button(sidebar, text=text, command=command, anchor="w", relief="flat", bd=0,
                               bg="#24445e" if primary else NAV, fg="white", activebackground="#2c4b66",
                               activeforeground="white", font=("맑은 고딕", 10), padx=12, pady=12, cursor="hand2")
            button.pack(fill="x", pady=3)
            return button
        nav_button("대시보드", lambda: self.entry.focus_set(), True)
        self.load_button = nav_button("결과 불러오기", self.open_result)
        self.demo_button = nav_button("로컬 데모 준비", self.prepare_demo)
        tk.Frame(sidebar, height=1, bg="#30445c").pack(fill="x", pady=24)
        self.folder_button = nav_button("저장 폴더 설정", self.choose_folder)
        self.rules_button = nav_button("탐지 규칙 선택", lambda: self.choose_settings("rules"))
        self.profile_button = nav_button("사이트 설정 선택", lambda: self.choose_settings("profile"))
        tk.Label(sidebar, text=f"v{__version__}\n\n필수 4종 + 광고 의심 후보\n원문과 판정 근거 보존", justify="left", bg=NAV, fg="#a3b5c8", font=("맑은 고딕", 9)).pack(side="bottom", anchor="w", pady=12)

        main = ttk.Frame(self.root, padding=(24, 22))
        main.pack(fill="both", expand=True)
        heading = ttk.Frame(main)
        heading.pack(fill="x")
        ttk.Label(heading, text="웹사이트 점검", style="Title.TLabel").pack(side="left")
        tk.Label(heading, text="외부 검사 허용" if self.allow_network else "로컬 전용", bg="#e0f1ed", fg="#187269", font=("맑은 고딕", 9, "bold"), padx=12, pady=7).pack(side="right")
        ttk.Label(main, text="위장·은닉 광고를 찾고, 원문과 판정 근거를 한 곳에서 확인하세요.", style="Muted.TLabel").pack(anchor="w", pady=(4, 16))

        card = tk.Frame(main, bg="white", highlightbackground="#e0e7f0", highlightthickness=1, padx=18, pady=14)
        card.pack(fill="x")
        tk.Label(card, text="점검 대상 URL", bg="white", fg=INK, font=("맑은 고딕", 10, "bold")).pack(anchor="w")
        row = tk.Frame(card, bg="white")
        row.pack(fill="x", pady=(8, 12))
        self.entry = ttk.Entry(row, textvariable=self.url, font=("맑은 고딕", 12))
        self.entry.pack(side="left", fill="x", expand=True, ipady=7)
        self.start_button = ttk.Button(row, text="점검 시작 →", style="Accent.TButton", command=self.start)
        self.start_button.pack(side="left", padx=(12, 0))
        self.cancel_button = ttk.Button(row, text="중단", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=(6, 0))
        options = tk.Frame(card, bg="white")
        options.pack(fill="x")
        for title, value, name in (("최대 페이지", self.page_limit, "pages_input"), ("제한 시간(초)", self.time_limit, "time_input")):
            tk.Label(options, text=title, bg="white", fg=MUTED, font=("맑은 고딕", 9)).pack(side="left", padx=(0, 7))
            widget = ttk.Entry(options, textvariable=value, width=7)
            widget.pack(side="left", padx=(0, 18))
            setattr(self, name, widget)
        self.export_button = ttk.Button(options, text="CSV 내보내기", command=self.export_csv, state="disabled")
        self.export_button.pack(side="right")
        self.progress = ttk.Progressbar(main, mode="indeterminate", maximum=100)
        self.progress.pack(fill="x", pady=(12, 6))
        status_row = ttk.Frame(main)
        status_row.pack(fill="x")
        ttk.Label(status_row, textvariable=self.status, wraplength=760).pack(side="left")
        ttk.Label(status_row, textvariable=self.metrics, style="Muted.TLabel").pack(side="right")

        cards = ttk.Frame(main)
        cards.pack(fill="x", pady=(16, 14))
        self.stat_values = {}
        definitions = [("전체", "필수 기법 전체", ACCENT), ("HOMOGLYPH", "닮은꼴 문자", "#7253aa"),
                       ("JAMO", "자모 분해", "#3374ad"), ("TRANSPARENT", "투명 텍스트", "#229688"),
                       ("OFFSCREEN", "화면 밖 은닉", "#c17b27"), ("광고 의심", "추가 검토 후보", "#ba5b55")]
        for index, (code, title, color) in enumerate(definitions):
            cards.columnconfigure(index, weight=1)
            frame = tk.Frame(cards, bg="white", padx=12, pady=10, highlightbackground="#e0e7f0", highlightthickness=1, cursor="hand2")
            frame.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 7, 0))
            value = tk.StringVar(value="0")
            self.stat_values[code] = value
            top = tk.Label(frame, text=title, bg="white", fg=MUTED, font=("맑은 고딕", 9))
            top.pack(anchor="w")
            number = tk.Label(frame, textvariable=value, bg="white", fg=color, font=("맑은 고딕", 23, "bold"))
            number.pack(anchor="w")
            for widget in (frame, top, number):
                widget.bind("<Button-1>", lambda _, code=code: self.set_filter(code))

        toolbar = ttk.Frame(main)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Label(toolbar, textvariable=self.counts).pack(side="left")
        self.filter_box = ttk.Combobox(toolbar, textvariable=self.filter, values=["전체", *LABELS, "광고 의심"], state="readonly", width=15)
        self.filter_box.pack(side="right")
        self.filter_box.bind("<<ComboboxSelected>>", lambda _: self.refresh())
        ttk.Entry(toolbar, textvariable=self.search, width=25).pack(side="right", padx=8)
        ttk.Label(toolbar, text="원문·URL 검색", style="Muted.TLabel").pack(side="right")
        split = tk.PanedWindow(main, orient="horizontal", sashwidth=9, bg=BG, bd=0)
        split.pack(fill="both", expand=True)
        table_frame = tk.Frame(split, bg="white")
        split.add(table_frame, minsize=420, stretch="always")
        columns = ("id", "type", "text", "url")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse", height=4)
        for name, title, width in zip(columns, ("항목", "분류", "검출 근거 원문", "페이지 URL"), (85, 140, 300, 210)):
            self.table.heading(name, text=title, command=lambda key=name: self.sort_by(key))
            self.table.column(name, width=width, minwidth=70, stretch=name in ("text", "url"))
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        horizontal = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=scrollbar.set, xscrollcommand=horizontal.set)
        scrollbar.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        self.table.pack(fill="both", expand=True)
        self.table.tag_configure("even", background="#f8fafc")
        self.table.tag_configure("candidate", foreground="#9b5840")
        self.table.bind("<<TreeviewSelect>>", self.show_detail)
        self.empty_label = tk.Label(table_frame, text="결과가 여기에 표시됩니다.\n로컬 데모로 먼저 확인해 보세요.", bg="white", fg=MUTED, font=("맑은 고딕", 11), justify="center")
        detail_frame = tk.Frame(split, bg="white", padx=10, pady=6)
        split.add(detail_frame, width=375, minsize=280)
        self.tabs = ttk.Notebook(detail_frame)
        self.tabs.pack(fill="both", expand=True)
        self.detail = self._text_tab("판정 근거")
        self.raw_detail = self._text_tab("원시 JSON", monospace=True)
        self.log_detail = self._text_tab("실행 기록")
        copy_row = tk.Frame(detail_frame, bg="white")
        copy_row.pack(fill="x", pady=(8, 0))
        ttk.Button(copy_row, text="원문 복사", command=lambda: self.copy_selected("evidence_text")).pack(side="left")
        ttk.Button(copy_row, text="위치 복사", command=lambda: self.copy_selected("location")).pack(side="left", padx=6)
        ttk.Label(main, textvariable=self.path_label, style="Muted.TLabel", wraplength=1050).pack(anchor="w", pady=(8, 0))
        self._detail("점검 흐름\n\n1. 검사할 웹사이트 URL을 입력하세요.\n2. 점검 시작을 누르세요.\n3. 항목을 선택해 원문과 판정 근거를 검토하세요.\n\n필수 4종과 일반 광고 의심 후보는 구분해 저장합니다.\n\nJSON·CSV 결과는 저장 폴더에서 확인할 수 있습니다.")

    def _text_tab(self, title, monospace=False):
        frame = tk.Frame(self.tabs, bg="white")
        self.tabs.add(frame, text=title)
        text = tk.Text(frame, height=8, wrap="word", bg="white", fg=INK, relief="flat", padx=10, pady=12,
                       font=("Consolas" if monospace else "맑은 고딕", 10), state="disabled")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        return text

    @staticmethod
    def _write(widget, value):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")

    def _detail(self, text):
        self._write(self.detail, text)

    def _log(self, text):
        self.log_detail.configure(state="normal")
        self.log_detail.insert("end", datetime.now().strftime("%H:%M:%S") + "  " + text + "\n")
        if int(self.log_detail.index("end-1c").split('.')[0]) > 400:
            self.log_detail.delete("1.0", "2.0")
        self.log_detail.see("end")
        self.log_detail.configure(state="disabled")

    def prepare_demo(self):
        if self.worker and self.worker.is_alive():
            return
        if self.demo_site is None:
            self.demo_site = DemoSite().start()
        self.url.set(self.demo_site.url)
        self.status.set("로컬 데모 준비 완료 · 점검 시작을 누르세요.")

    def choose_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.folder, title="결과 저장 폴더")
        if chosen:
            self.folder = Path(chosen)
            self.path_label.set(str(self.folder))

    def choose_settings(self, kind):
        chosen = filedialog.askopenfilename(title="탐지 규칙" if kind == "rules" else "사이트별 읽기 설정", filetypes=[("JSON", "*.json")])
        if not chosen:
            return
        try:
            config = Rules.load(Path(chosen)) if kind == "rules" else SiteProfile.load(Path(chosen))
            if kind == "rules":
                self.rules_path = Path(chosen)
            else:
                self.profile_path = Path(chosen)
            self._detail(f"선택한 설정\n\n{chosen}\n\n{config}")
        except Exception as exc:
            messagebox.showerror("설정 파일 확인", str(exc))

    def open_result(self):
        chosen = filedialog.askopenfilename(title="result.json 불러오기", filetypes=[("JSON", "*.json")])
        if not chosen:
            return
        try:
            self.outcome = ScanOutcome.load(Path(chosen))
            self.findings = self.outcome.result["findings"]
            self.candidates = self.outcome.report.get("ad_candidates", [])
            self.filter.set("전체")
            self.search.set("")
            self.refresh()
            self.export_button.configure(state="normal")
            self.status.set(f"결과 불러옴 · {STATUS.get(self.outcome.report['status'], '보고서 없는 결과')}")
            self.metrics.set(f"{len(self.outcome.report['pages_scanned'])}페이지")
            self._detail(f"불러온 결과\n\n{chosen}\n\n원본 URL: {self.outcome.result['meta']['entry_url']}\n\n항목을 선택하면 원문과 근거를 확인할 수 있습니다.")
            self._log("결과 파일 불러오기 · 웹 접속 없음")
        except Exception as exc:
            messagebox.showerror("결과 파일 확인", str(exc))

    def export_csv(self):
        if self.outcome is None:
            return
        chosen = filedialog.asksaveasfilename(title="고정 칼럼 CSV 내보내기", initialdir=self.folder, initialfile="result.csv", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if chosen:
            try:
                self.outcome.save_csv(Path(chosen))
                self.status.set(f"CSV 저장 완료 · {chosen}")
            except Exception as exc:
                messagebox.showerror("CSV 저장 실패", str(exc))

    def _busy(self, busy):
        for widget in (self.entry, self.pages_input, self.time_input, self.demo_button, self.folder_button,
                       self.start_button, self.load_button, self.rules_button, self.profile_button):
            widget.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")
        self.export_button.configure(state="disabled" if busy or self.outcome is None else "normal")
        if busy:
            self.progress.configure(mode="indeterminate")
            self.progress.start(15)
        else:
            self.progress.stop()
            completed = self.outcome is not None and self.outcome.report.get('status') == 'completed'
            self.progress.configure(mode="determinate", value=100 if completed else 0)

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        try:
            url = self.url.get().strip()
            if '://' not in url and url:
                import ipaddress
                try:
                    ipaddress.ip_address(url.split(':')[0])
                    url = 'http://' + url
                except ValueError:
                    url = 'http://' + url if url.startswith('localhost') else 'https://' + url
            config = ScanConfig(url, int(self.page_limit.get()), float(self.time_limit.get()),
                                allow_network=self.allow_network, rules_path=self.rules_path, profile_path=self.profile_path)
        except (ValueError, OSError) as exc:
            messagebox.showerror("입력 확인", str(exc))
            return
        self.url.set(url)
        self.findings, self.candidates, self.outcome = [], [], None
        self.filter.set("전체")
        self.search.set("")
        self.refresh()
        self._detail("점검 중입니다.\n\n항목이 발견되면 목록에 표시됩니다. 파일은 점검 종료 시 저장됩니다.")
        self._write(self.raw_detail, "")
        self._write(self.log_detail, "")
        self.stop = Event()
        self._busy(True)
        def work():
            try:
                outcome = asyncio.run(scan(config, self.stop, self.events.put))
                path = outcome.save(self.folder)
                self.events.put({"kind": "done", "outcome": outcome, "path": path})
            except Exception as exc:
                self.events.put({"kind": "error", "message": str(exc)})
        self.worker = Thread(target=work, daemon=True)
        self.worker.start()

    def cancel(self):
        self.stop.set()
        self.status.set("중단 처리 중 · 수집된 결과를 저장합니다.")
        self.cancel_button.configure(state="disabled")

    def _poll(self):
        dirty = False
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            kind = event["kind"]
            if kind in ("status", "warning", "error"):
                self.status.set(event["message"])
                self._log(event["message"])
                if kind == "error":
                    self._busy(False)
                    self._detail("실행 또는 저장 실패\n\n" + event["message"] + "\n\n기존 결과 파일을 이번 실행 결과로 사용하지 마세요.")
            elif kind == "progress":
                self.metrics.set(f"수집 {event['pages_scanned']} · 대기 {event['queue_remaining']}")
            elif kind == "page_complete":
                page = event['page']
                self.metrics.set(f"방문 {event['pages_scanned']} · 발견 URL {event['discovered_urls']} · 대기 {event['queue_remaining']}")
                self._log(f"{page['url']}\n  링크 {page['links_discovered']}개 · 새 대기 {page['links_queued']}개 · 요소 {page['elements_examined']}개 · 후보 +{page['candidates_added']} · {page['elapsed_sec']:.1f}초")
                if page.get('content_selector') and not page.get('content_roots_matched'):
                    self._log(f"  본문 선택자 미일치: {page['content_selector']} (링크 탐색은 계속합니다.)")
            elif kind == "finding":
                self.findings.append(event["finding"])
                dirty = True
            elif kind == "candidate":
                self.candidates.append(event["candidate"])
                dirty = True
            elif kind == "done":
                self.outcome = event["outcome"]
                self.findings, self.candidates = self.outcome.result["findings"], self.outcome.report.get("ad_candidates", [])
                report = self.outcome.report
                self._busy(False)
                self.status.set(STATUS[report['status']])
                self.metrics.set(f"{len(report['pages_scanned'])}페이지 · {self.outcome.result['meta']['elapsed_sec']:.1f}초")
                errors = "\n".join(f"• {e['url']}\n  {e['message']}" for e in report["errors"])
                self._detail(f"{STATUS[report['status']]}\n\n필수 기법 {len(self.findings)}건\n광고 의심 후보 {len(self.candidates)}건\n\n저장 완료\n{event['path']}\n{self.folder / 'result.csv'}\n\n" + (errors or "누락·오류 보고 없음.\n항목을 선택해 근거를 검토하세요."))
                self._log(f"{STATUS[report['status']]} · JSON/CSV 저장 완료")
                dirty = True
        if dirty:
            self.refresh()
        if self.closing and (self.worker is None or not self.worker.is_alive()):
            if self.demo_site:
                self.demo_site.close()
            self.root.destroy()
        else:
            self.root.after(100, self._poll)

    def set_filter(self, code):
        self.filter.set(code)
        self.refresh()

    def sort_by(self, key):
        self.sort_reverse = not self.sort_reverse if self.sort_key == key else False
        self.sort_key = key
        self.refresh()

    def _records(self):
        return [*self.findings, *self.candidates]

    @staticmethod
    def _label(record):
        return LABELS.get(record.get("technique"), CATEGORY_LABELS.get(record.get("category"), "광고 의심"))

    def refresh(self):
        selection = self.table.selection()
        self.table.delete(*self.table.get_children())
        query = self.search.get().casefold().strip()
        records = [r for r in self._records() if (self.filter.get() == "전체" or self.filter.get() == r.get("technique") or
                   self.filter.get() == "광고 의심" and "category" in r) and
                   (not query or query in (r['evidence_text'] + ' ' + r['url'] + ' ' + r['location'] + ' ' + self._label(r)).casefold())]
        keys = {"id": lambda r: r['id'], "type": self._label, "text": lambda r: r['evidence_text'], "url": lambda r: r['url']}
        records.sort(key=keys[self.sort_key], reverse=self.sort_reverse)
        for index, record in enumerate(records):
            tags = (["even"] if index % 2 == 0 else []) + (["candidate"] if 'category' in record else [])
            self.table.insert("", "end", iid=record['id'], values=(record['id'], self._label(record), record['evidence_text'].replace('\n', '  '), record['url']), tags=tags)
        if selection and self.table.exists(selection[0]):
            self.table.selection_set(selection[0])
        counts = Counter(r['technique'] for r in self.findings)
        self.stat_values['전체'].set(str(len(self.findings)))
        for code in LABELS:
            self.stat_values[code].set(str(counts[code]))
        self.stat_values['광고 의심'].set(str(len(self.candidates)))
        self.counts.set(f"필수 {len(self.findings)} · 후보 {len(self.candidates)}   /   표시 {len(records)}")
        if records:
            self.empty_label.place_forget()
        else:
            self.empty_label.configure(text="검색·필터에 맞는 결과가 없습니다." if query or self.filter.get() != '전체' else "결과가 여기에 표시됩니다.\n로컬 데모로 먼저 확인해 보세요.")
            self.empty_label.place(relx=.5, rely=.45, anchor='center')

    def _selected(self):
        selection = self.table.selection()
        return next((r for r in self._records() if selection and r['id'] == selection[0]), None)

    def show_detail(self, _=None):
        record = self._selected()
        if record is None:
            return
        evidence = self.outcome.report.get('evidence_details', {}).get(record['id'], {}) if self.outcome else {}
        if 'category' in record:
            evidence = record
        analysis = evidence.get('analysis', {})
        keywords = evidence.get('matched_keywords', list(dict.fromkeys(m['keyword'] for m in analysis.get('matches', []))))
        reasons = evidence.get('style_reasons', evidence.get('reasons', []))
        self._detail(f"{record['id']} · {self._label(record)}\n" + ("광고 의심 후보 · 추가 검토 필요\n" if 'category' in record else "필수 기법 탐지 · 의심 항목\n") +
                     f"\n페이지:\n{record['url']}\n\n위치:\n{record['location']}\n\n원문:\n{record['evidence_text']}\n\n일치 키워드:\n{', '.join(keywords) or '수집 중'}\n\n판정 근거:\n" + ('\n'.join('• '+r for r in reasons) or '문자 변형 및 광고 문맥 분석') +
                     f"\n\n관찰 시각:\n{evidence.get('observed_at', '이전 결과에 시각 정보 없음')}")
        self._write(self.raw_detail, json.dumps({'record': record, 'evidence': evidence}, ensure_ascii=False, indent=2))

    def copy_selected(self, key):
        record = self._selected()
        if record:
            self.root.clipboard_clear()
            self.root.clipboard_append(record[key])

    def close(self):
        self.closing = True
        if self.worker and self.worker.is_alive():
            self.cancel()
        self.status.set("작업을 정리한 후 종료합니다.")


def launch(folder=None, demo=False, allow_network=True, rules_path=None, profile_path=None, initial_url=None):
    root = tk.Tk()
    Application(root, folder, demo, allow_network, rules_path, profile_path, initial_url)
    root.mainloop()
