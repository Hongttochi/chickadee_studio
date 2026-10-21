import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { CircleAlert, ExternalLink, Maximize2, X } from "lucide-react";

function ScreenshotModal({ screenshot, onClose }) {
  const ref = useRef(null);
  useEffect(() => {
    const previous = document.activeElement;
    const dialog = ref.current;
    dialog.showModal();
    return () => {
      dialog.close();
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  return createPortal(<dialog ref={ref} className="screenshot-viewer" aria-label="스크린샷 확대"
    onCancel={(event) => { event.preventDefault(); onClose(); }}
    onKeyDown={(event) => event.stopPropagation()}
    onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="screenshot-viewer-content">
      <header><strong>스크린샷</strong><span>촬영 당시 화면</span><button type="button" autoFocus aria-label="스크린샷 닫기" onClick={onClose}><X size={18} /></button></header>
      <div className="screenshot-viewer-image"><img src={screenshot.data_url} alt="촬영한 스크린샷 확대 보기" /></div>
    </section>
  </dialog>, document.body);
}

// Only saved, inert JPEG data is rendered. Never load a page URL in the app.
export default function EvidenceScreenshot({ screenshot, hidden = false, caption = "스크린샷" }) {
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { setExpanded(false); setError(""); }, [screenshot?.data_url, hidden]);
  if (!screenshot || !/^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/.test(screenshot.data_url || "") || screenshot.data_url.length > 270000) {
    return <figure className="evidence-capture"><figcaption>{caption}</figcaption><p className="evidence-capture-note">저장된 스크린샷이 없습니다. 원문·CSS 근거를 확인하세요.</p></figure>;
  }
  let url = null;
  try {
    const parsed = new URL(screenshot.url);
    if (["http:", "https:"].includes(parsed.protocol) && !parsed.username && !parsed.password) url = parsed.href;
  } catch {}
  const date = new Date(screenshot.observed_at);
  const capturedAt = Number.isNaN(date.getTime()) ? "기록 없음" : new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "medium" }).format(date);
  const openURL = async (event) => {
    event.preventDefault();
    try { await window.chickadee.openExternal(url); setError(""); }
    catch { setError("앱을 재실행한 뒤 다시 시도해 주세요."); }
  };
  return <figure className="evidence-capture">
    <figcaption>{caption}</figcaption>
    <div className="evidence-capture-frame">
      <div className="evidence-capture-image"><img src={screenshot.data_url} alt="검사 브라우저에서 촬영한 스크린샷" /></div>
      <button className="evidence-capture-zoom" type="button" aria-label="확대" title="확대" aria-haspopup="dialog" onClick={() => setExpanded(true)}><Maximize2 size={16} aria-hidden="true" /></button>
    </div>
    <p className="evidence-capture-note">촬영 당시 화면</p>
    <details className="capture-metadata"><summary>촬영 정보</summary>
      <dl><div><dt>페이지</dt><dd>{url ? <a href={url} onClick={openURL} title="기본 브라우저에서 열기">{screenshot.url}<ExternalLink size={13} aria-hidden="true" /></a> : "주소 없음"}</dd></div>
        <div><dt>촬영 시각</dt><dd><time dateTime={screenshot.observed_at}>{capturedAt}</time></dd></div>
        <div><dt>SHA-256</dt><dd className="capture-hash">{screenshot.sha256 || "기록 없음"}</dd></div></dl>
      {error && <div className="capture-error" role="alert">
        <CircleAlert size={17} aria-hidden="true" />
        <div><strong>페이지를 열지 못했어요</strong><span>{error}</span></div>
        <button type="button" aria-label="오류 안내 닫기" onClick={() => setError("")}><X size={14} aria-hidden="true" /></button>
      </div>}
    </details>
    {expanded && !hidden && <ScreenshotModal screenshot={screenshot} onClose={() => setExpanded(false)} />}
  </figure>;
}
