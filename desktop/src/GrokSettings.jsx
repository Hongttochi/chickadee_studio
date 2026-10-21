import React, { useState } from "react";
import { Plus, ChevronDown } from "lucide-react";
import grokLogo from "../assets/groq-logo.png";

export default function GrokSettings({ config, onConfigured }) {
  const [editing, setEditing] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const [keyAdded, setKeyAdded] = useState(false);
  const [key, setKey] = useState("");
  const [draft, setDraft] = useState(config);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const update = (name, value) => setDraft((previous) => ({ ...previous, [name]: value }));
  async function apply() {
    setBusy(true); setMessage("");
    try {
      const result = await window.chickadee.configureAgent({ model: draft.model,
        token_limit: draft.token_limit, call_limit: draft.call_limit, api_key: key });
      onConfigured({ model: result.model, token_limit: result.token_limit, call_limit: result.call_limit, sessionKey: Boolean(key) || config.sessionKey });
      setKeyAdded(Boolean(key) || config.sessionKey); setKey(""); setEditing(false); setMessage("Groq 설정을 적용했습니다.");
    } catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  }
  return <section className="grok-settings" aria-label="Groq 설정">
    <div className="grok-settings-heading">
      <img src={grokLogo} alt="Groq" />
    </div>
    <p className="grok-intro">선택한 탐지 근거를 AI로 추가 검토합니다. 분석을 실행할 때만 Groq에 요청합니다.</p>
    <div className="grok-connection-heading"><div><strong>API 연결</strong><p>현재 앱에서 사용할 키를 설정합니다.</p></div>
      <button type="button" className="grok-add-key" onClick={() => setEditing(!editing)} aria-expanded={editing} aria-controls="grok-key-editor" disabled={busy}><Plus size={13} aria-hidden="true" />{editing ? "닫기" : "API 키 등록"}</button>
    </div>
    <div className="grok-connection-card"><div><strong>{config.sessionKey || keyAdded ? "현재 세션 키" : "Groq API 키"}</strong><span>{config.sessionKey || keyAdded ? "등록됨" : "미등록"}</span></div>
      <p>{config.sessionKey || keyAdded ? "등록한 키는 앱을 종료하면 삭제됩니다. 서버 연결은 분석 실행 시 확인합니다." : "AI 검토를 사용하려면 본인의 Groq API 키를 등록하세요."}</p>
    </div>
    {editing && <div id="grok-key-editor" className="grok-key-editor">
      <label>API 키<input aria-label="Groq API 키" type="password" autoComplete="off" spellCheck={false} value={key} onChange={(event) => setKey(event.target.value)} placeholder="API 키 입력" disabled={busy} autoFocus /></label>
      <p>키는 파일에 저장하지 않습니다. 입력 후 아래 설정 적용을 눌러주세요.</p>
    </div>}
    <button type="button" className="grok-advanced-toggle" onClick={() => setAdvanced(!advanced)} aria-expanded={advanced} aria-controls="grok-advanced"><ChevronDown size={14} aria-hidden="true" />모델 및 사용 한도</button>
    {advanced && <div id="grok-advanced">
    <label>모델<input aria-label="Groq 모델" value={draft.model} onChange={(event) => update("model", event.target.value)} disabled={busy} /></label>
    <div className="form-row">
      <label>누적 토큰 한도<input aria-label="Groq 토큰 한도" type="number" min="1000" max="60000" value={draft.token_limit} onChange={(event) => update("token_limit", Number(event.target.value))} disabled={busy} /></label>
      <label>누적 호출 한도<input aria-label="Groq 호출 한도" type="number" min="1" max="12" value={draft.call_limit} onChange={(event) => update("call_limit", Number(event.target.value))} disabled={busy} /></label>
    </div>
    </div>}
    <div className="grok-settings-actions"><p role="status">{message}</p><button type="button" onClick={apply} disabled={busy}>{busy ? "적용 중…" : "설정 적용"}</button></div>
  </section>;
}
