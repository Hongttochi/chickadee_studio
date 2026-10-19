import asyncio
from collections import Counter
from pathlib import Path
import queue
from threading import Event, Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .demo import DemoSite
from .detection import LABELS
from .scanner import ScanConfig, output_directory, scan

STATUS = {"completed": "점검 완료", "partial": "일부 결과 · 누락 항목 확인 필요", "cancelled": "사용자 중단 · 일부 결과", "failed": "실행 실패 · 결과를 신뢰하지 마세요"}


class Application:
    def __init__(self, root: tk.Tk, folder: Path | None = None, demo: bool = False):
        self.root = root
        self.folder = Path(folder or output_directory())
        self.events = queue.Queue()
        self.stop = Event()
        self.worker = None
        self.demo_site = None
        self.findings = []
        self.outcome = None
        self.closing = False
        self.url = tk.StringVar()
        self.page_limit = tk.StringVar(value="50")
        self.time_limit = tk.StringVar(value="300")
        self.filter = tk.StringVar(value="전체")
        self.status = tk.StringVar(value="URL을 입력하거나 로컬 데모를 준비하세요.")
        self.counts = tk.StringVar(value="검출 0건")
        self.path_label = tk.StringVar(value=f"저장 폴더: {self.folder}")
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self._poll)
        if demo:
            self.prepare_demo()

    def _build(self):
        self.root.title(f"Chickadee Bot {__version__} · 공공 웹사이트 광고 점검")
        self.root.geometry("1180x820")
        self.root.minsize(940, 680)
        self.root.configure(bg="#f2f6f5")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f2f6f5")
        style.configure("TLabel", background="#f2f6f5", foreground="#173f39", font=("맑은 고딕", 10))
        style.configure("Title.TLabel", font=("맑은 고딕", 23, "bold"))
        style.configure("Accent.TButton", background="#087e75", foreground="white", padding=9)
        style.configure("TButton", padding=7, font=("맑은 고딕", 10))
        style.configure("Treeview", rowheight=31, font=("맑은 고딕", 10), background="white", fieldbackground="white")
        style.configure("Treeview.Heading", font=("맑은 고딕", 10, "bold"), padding=8)
        main = ttk.Frame(self.root, padding=24)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="Chickadee Bot", style="Title.TLabel").pack(anchor="w")
        ttk.Label(main, text="문자 위장과 숨겨진 광고를 찾아, 원문과 위치를 확인합니다.  /  규칙 기반 데모").pack(anchor="w", pady=(2, 16))
        inputs = ttk.Frame(main)
        inputs.pack(fill="x")
        ttk.Label(inputs, text="점검 URL").pack(side="left", padx=(0, 12))
        self.entry = ttk.Entry(inputs, textvariable=self.url, font=("맑은 고딕", 11))
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.demo_button = ttk.Button(inputs, text="로컬 데모 준비", command=self.prepare_demo)
        self.demo_button.pack(side="left", padx=(8, 0))
        controls = ttk.Frame(main)
        controls.pack(fill="x", pady=12)
        ttk.Label(controls, text="최대 페이지").pack(side="left")
        self.pages_input = ttk.Entry(controls, textvariable=self.page_limit, width=7)
        self.pages_input.pack(side="left", padx=(8, 18))
        ttk.Label(controls, text="전체 제한(초)").pack(side="left")
        self.time_input = ttk.Entry(controls, textvariable=self.time_limit, width=7)
        self.time_input.pack(side="left", padx=(8, 18))
        self.folder_button = ttk.Button(controls, text="저장 폴더", command=self.choose_folder)
        self.folder_button.pack(side="left")
        self.cancel_button = ttk.Button(controls, text="중단", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="right")
        self.start_button = ttk.Button(controls, text="탐지 시작", style="Accent.TButton", command=self.start)
        self.start_button.pack(side="right", padx=8)
        ttk.Label(main, textvariable=self.path_label, wraplength=1050).pack(anchor="w", pady=(0, 8))
        self.progress = ttk.Progressbar(main, mode="indeterminate")
        self.progress.pack(fill="x")
        ttk.Label(main, textvariable=self.status, wraplength=1050).pack(anchor="w", pady=(8, 12))
        summary = ttk.Frame(main)
        summary.pack(fill="x", pady=(0, 8))
        ttk.Label(summary, textvariable=self.counts).pack(side="left")
        self.filter_box = ttk.Combobox(summary, textvariable=self.filter, values=["전체", *LABELS], state="readonly", width=18)
        self.filter_box.pack(side="right")
        self.filter_box.bind("<<ComboboxSelected>>", lambda _: self.refresh())
        columns = ("id", "type", "text", "url")
        table_frame = ttk.Frame(main)
        table_frame.pack(fill="both", expand=True)
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse", height=8)
        for name, title, width in zip(columns, ("항목", "탐지 유형", "검출 근거 원문", "페이지 URL"), (85, 165, 400, 280)):
            self.table.heading(name, text=title)
            self.table.column(name, width=width, minwidth=70, stretch=name in ("text", "url"))
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.table.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.show_detail)
        ttk.Label(main, text="선택한 항목의 원문·위치 / 실행 안내").pack(anchor="w", pady=(12, 5))
        self.detail = tk.Text(main, height=7, wrap="word", bg="white", fg="#173f39", relief="flat", padx=12, pady=10, font=("맑은 고딕", 10))
        self.detail.pack(fill="x")
        self._detail("필수 탐지 4종을 지원합니다. 탐지 결과는 규칙 기반 의심 항목이며 담당자의 확인이 필요합니다.\n이전 실행의 result.json은 새 실행 결과 저장 시 교체됩니다.")

    def _detail(self, text):
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", text)
        self.detail.configure(state="disabled")

    def prepare_demo(self):
        if self.worker and self.worker.is_alive():
            return
        if self.demo_site is None:
            self.demo_site = DemoSite().start()
        self.url.set(self.demo_site.url)
        self.status.set("로컬 데모 준비 완료 · 탐지 시작을 누르면 4개 페이지와 중첩 iframe을 점검합니다.")

    def choose_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.folder, title="result.json 저장 폴더")
        if chosen:
            self.folder = Path(chosen)
            self.path_label.set(f"저장 폴더: {self.folder}")

    def _busy(self, busy):
        for widget in (self.entry, self.pages_input, self.time_input, self.demo_button, self.folder_button, self.start_button):
            widget.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")
        if busy:
            self.progress.start(15)
        else:
            self.progress.stop()

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        try:
            config = ScanConfig(self.url.get().strip(), int(self.page_limit.get()), float(self.time_limit.get()))
        except ValueError as exc:
            messagebox.showerror("입력 확인", str(exc))
            return
        self.findings = []
        self.outcome = None
        self.filter.set("전체")
        self.refresh()
        self._detail("점검 중입니다. 현재 화면은 새 실행의 결과입니다. 파일은 실행 종료 시 저장합니다.")
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
        self.status.set("중단 요청을 처리하고 있습니다. 수집된 일부 결과를 저장합니다.")
        self.cancel_button.configure(state="disabled")

    def _poll(self):
        dirty = False
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            kind = event["kind"]
            if kind in ("status", "warning"):
                self.status.set(event["message"])
            elif kind == "finding":
                self.findings.append(event["finding"])
                dirty = True
            elif kind == "done":
                self.outcome = event["outcome"]
                report = self.outcome.report
                self._busy(False)
                self.status.set(f"{STATUS[report['status']]} · {len(report['pages_scanned'])}페이지 · {len(self.findings)}건 · {self.outcome.result['meta']['elapsed_sec']:.1f}초")
                errors = "\n".join(f"- {e['url']}: {e['message']}" for e in report["errors"])
                self._detail(f"{STATUS[report['status']]}\n저장 완료: {event['path']}\n실행 보고서: {self.folder / 'scan-report.json'}\n" + (errors or "누락·오류 보고 없음. 항목을 선택하면 원문과 위치를 확인할 수 있습니다."))
            elif kind == "error":
                self._busy(False)
                self.status.set("저장 또는 실행 실패 · 기존 파일을 이번 실행 결과로 사용하지 마세요.")
                self._detail(event["message"])
        if dirty:
            self.refresh()
        if self.closing and (self.worker is None or not self.worker.is_alive()):
            if self.demo_site:
                self.demo_site.close()
            self.root.destroy()
        else:
            self.root.after(100, self._poll)

    def refresh(self):
        self.table.delete(*self.table.get_children())
        for finding in self.findings:
            if self.filter.get() in ("전체", finding["technique"]):
                self.table.insert("", "end", iid=finding["id"], values=(finding["id"], LABELS[finding["technique"]], finding["evidence_text"], finding["url"]))
        counts = Counter(f["technique"] for f in self.findings)
        self.counts.set(f"검출 {len(self.findings)}건   " + "  ·  ".join(f"{LABELS[k]} {counts[k]}" for k in LABELS))

    def show_detail(self, _=None):
        selected = self.table.selection()
        if not selected:
            return
        finding = next(f for f in self.findings if f["id"] == selected[0])
        self._detail(f"{finding['id']} · {LABELS[finding['technique']]} ({finding['technique']})\n페이지: {finding['url']}\n위치: {finding['location']}\n원문:\n{finding['evidence_text']}")

    def close(self):
        self.closing = True
        if self.worker and self.worker.is_alive():
            self.cancel()
        self.status.set("진행 중인 작업을 정리한 후 종료합니다.")


def launch(folder=None, demo=False):
    root = tk.Tk()
    Application(root, folder, demo)
    root.mainloop()
