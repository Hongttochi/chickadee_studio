import React, { useMemo, useRef, useState } from "react";
import { Search, ListFilter, ScanSearch, FileText, Image } from "lucide-react";
import LocalAIAnalysis from "./LocalAIAnalysis.jsx";

const PAGE_SIZE = 20;
function hasSignal(packet) {
  return Object.values(packet.local_ai || {}).some(item => item?.status === "completed" && ["ad_context", "phishing_pattern"].includes(item.label));
}

export default function LocalAIResults({ packets }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [page, setPage] = useState(1);
  const browserRef = useRef(null);
  const rows = useMemo(() => packets.filter(p => !p.supplemental).map((packet, index) => ({ packet, index, signal: hasSignal(packet) })), [packets]);
  const counts = {
    all: rows.length,
    signal: rows.filter(row => row.signal).length,
    text: rows.filter(row => row.packet.source_kind !== "image_ocr").length,
    image: rows.filter(row => row.packet.source_kind === "image_ocr").length,
  };
  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return rows.filter(({ packet, signal }) =>
      (filter === "all" || (filter === "signal" && signal) || (filter === "image" && packet.source_kind === "image_ocr") || (filter === "text" && packet.source_kind !== "image_ocr")) &&
      (!needle || (packet.text || "").toLocaleLowerCase().includes(needle))
    ).sort((a, b) => Number(b.signal) - Number(a.signal) || a.index - b.index);
  }, [rows, query, filter]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const start = (currentPage - 1) * PAGE_SIZE;
  function changePage(next) {
    setPage(next);
    browserRef.current?.scrollIntoView({ block: "start" });
  }
  return <div className="local-ai-browser" ref={browserRef}>
    <div className="local-ai-list-tools">
      <div className="local-ai-filters" role="group" aria-label="분석 결과 필터">
        {[["all", "전체", ListFilter], ["signal", "유사 신호", ScanSearch], ["text", "웹페이지 문구", FileText], ["image", "이미지 문구", Image]].map(([id, label, FilterIcon]) =>
          <button key={id} type="button" aria-pressed={filter === id} onClick={() => { setFilter(id); setPage(1); }}><FilterIcon size={14} aria-hidden="true" />{label}<span>{counts[id].toLocaleString()}</span></button>)}
      </div>
      <label className="local-ai-search"><Search size={14} aria-hidden="true" /><input aria-label="분석 문구 검색" placeholder="문구 검색" value={query} onChange={event => { setQuery(event.target.value); setPage(1); }} /></label>
    </div>
    <p className="local-ai-list-hint">유사 신호 먼저 표시 · 항목을 누르면 원문과 분석을 볼 수 있습니다.</p>
    <div className="local-ai-row-list">
      {filtered.slice(start, start + PAGE_SIZE).map(({ packet, index, signal }) => <details className="local-ai-row" key={packet.id}>
        <summary><span className="local-ai-row-number">{String(index + 1).padStart(2, "0")}</span><span className="local-ai-row-source">{packet.source_kind === "image_ocr" ? "이미지 문구" : "웹페이지 문구"}</span><span className="local-ai-row-preview">{packet.text || "인식된 문구 없음"}</span><span className="local-ai-row-status" data-signal={signal}>{signal ? "유사 신호" : Object.values(packet.local_ai || {}).some(item => item?.status === "completed") ? "추가 신호 미확인" : "분석 미완료"}</span></summary>
        <div className="local-ai-result-card"><div className="local-ai-row-text">{packet.text || "인식된 문구 없음"}</div><LocalAIAnalysis analysis={packet.local_ai} /></div>
      </details>)}
      {!filtered.length && <p className="local-ai-no-results">조건에 맞는 분석 결과가 없습니다.</p>}
    </div>
    <div className="local-ai-pagination"><span>{filtered.length ? `${start + 1}–${Math.min(start + PAGE_SIZE, filtered.length)}` : "0"} / {filtered.length.toLocaleString()}개</span><div><button type="button" disabled={currentPage === 1} onClick={() => changePage(currentPage - 1)}>이전</button><span>{currentPage} / {pageCount}</span><button type="button" disabled={currentPage === pageCount} onClick={() => changePage(currentPage + 1)}>다음</button></div></div>
  </div>;
}
