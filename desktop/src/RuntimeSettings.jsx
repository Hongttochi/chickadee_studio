import React, { useEffect, useState } from "react";
import "./runtime-settings.css";

const names = { auto: "자동", standard: "표준", economy: "절약" };
const gb = value => Number.isFinite(value) ? `${(value / 1024**3).toFixed(1)} GB` : "확인 불가";
export default function RuntimeSettings({ disabled }) {
  const [data, setData] = useState(null), [busy, setBusy] = useState(false), [message, setMessage] = useState("");
  async function refresh() { setData(await window.chickadee.environment()); }
  useEffect(() => { refresh().catch(error => setMessage(error.message)); }, []);
  useEffect(() => {
    if (data?.ocr_check?.status !== "running") return;
    const timer = setInterval(() => refresh().catch(error => setMessage(error.message)), 600);
    return () => clearInterval(timer);
  }, [data?.ocr_check?.status]);
  async function action(fn) {
    setBusy(true); setMessage("");
    try { await fn(); await refresh(); } catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  }
  const checking = data?.ocr_check?.status === "running";
  const features = data?.features || {}, hardware = data?.hardware || {};
  const ocrStatus = checking ? "확인 중" : data?.ocr_check?.status === "completed" ? "구동 확인" : data?.ocr_check?.status === "failed" ? "확인 실패" : "모델 확인";
  return <details className="runtime-settings" aria-label="실행 환경">
    <summary>실행 환경<span>{data ? data.mode === 'auto' ? `자동 · ${names[data.effective_mode]}` : names[data.mode] : "확인 중"}</span></summary>
    {data && <>
      <dl className="runtime-hardware"><dt>CPU</dt><dd>논리 프로세서 {hardware.logical_cpus}개</dd><dt>메모리</dt><dd>{gb(hardware.total_bytes)} · 사용 가능 {gb(hardware.available_bytes)}</dd></dl>
      <div className="runtime-mode" role="group" aria-label="실행 모드">{Object.entries(names).map(([mode, name]) =>
        <button key={mode} type="button" aria-pressed={data.mode === mode} disabled={disabled || busy || checking}
          onClick={() => action(() => window.chickadee.configureRuntime({ mode }))}>{name}</button>)}</div>
      <p className="runtime-mode-description">{data.effective_mode === "economy" ? "이미지 OCR을 생략하고 문자·화면 AI를 사용합니다." : `이미지 OCR 처리 한도: ${data.ocr_max_images}장. 사용 가능한 기능은 아래에서 확인하세요.`}</p>
      <dl className="runtime-features"><dt>필수 탐지 4종</dt><dd>사용</dd>
        <dt>문자 AI</dt><dd>{features.text_ai ? "사용 가능" : "모델 확인 필요"}</dd>
        <dt>피싱 화면 AI</dt><dd>{features.visual_ai ? "사용 가능" : "모델 확인 필요"}</dd>
        <dt>이미지 OCR</dt><dd>{!features.ocr_available ? "모델·실행 파일 확인 필요" : !features.ocr_enabled ? "끔 · 절약 모드" : ocrStatus}</dd></dl>
      <div className="runtime-actions"><button type="button" disabled={disabled || busy || checking || !features.ocr_available}
        onClick={() => action(() => window.chickadee.testRuntime())}>{checking ? "기능 확인 중…" : "OCR 기능 확인"}</button>
        <button type="button" disabled={busy || checking} onClick={() => action(refresh)}>환경 새로고침</button></div>
      {data.reasons?.length > 0 && <p className="runtime-info">자동 권장: {names[data.recommended_mode]} · {data.reasons.join(" · ")}</p>}
      {data.ocr_check?.message && <p role="status">{data.ocr_check.message}</p>}
      <p className="runtime-info">{hardware.os} · {hardware.architecture} · {hardware.process_bits}비트 · CPU 실행</p>
    </>}
    {message && <p role="status">{message}</p>}
  </details>;
}
