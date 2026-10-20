// Independent feature surface. Existing app layout/theme stays owned by its designer.
import React, { useEffect, useMemo, useState } from "react";
import { ReactFlow, Controls, Background } from "@xyflow/react";
import { explorationFlow, CHANGE_LABELS } from "./inspection-model.mjs";
import "./inspection.css";

const api = window.chickadee;
const EMPTY = { graph: { nodes: [], edges: [] }, packets: [], agent: { assessments: [], ledger: {} } };

export default function InspectionInsights() {
  const [data, setData] = useState(EMPTY), [run, setRun] = useState(null), [history, setHistory] = useState([]);
  const [tab, setTab] = useState("graph"), [selected, setSelected] = useState(null), [packetId, setPacketId] = useState("");
  const [baseline, setBaseline] = useState(""), [message, setMessage] = useState(""), [working, setWorking] = useState(false);
  const [key, setKey] = useState(""), [model, setModel] = useState("openai/gpt-oss-20b");
  const [tokenLimit, setTokenLimit] = useState(24000), [callLimit, setCallLimit] = useState(6);
  async function refresh() {
    const state = await api.state();
    setRun(state.run_id); setHistory(state.history || []);
    if (state.run_id) setData(await api.inspection({ run_id: state.run_id }));
    else setData(EMPTY);
  }
  async function action(fn) {
    setWorking(true); setMessage("");
    try { await fn(); await refresh(); } catch (error) { setMessage(error.message); }
    finally { setWorking(false); }
  }
  useEffect(() => {
    refresh().catch((error) => setMessage(error.message));
    return api.onEvent((event) => {
      if (event.kind === "started") { setData(EMPTY); setRun(event.run_id); setSelected(null); setPacketId(""); }
      if (event.kind === "exploration") {
        setData((previous) => {
          const nodes = new Map(previous.graph.nodes.map((node) => [node.id, node]));
          const edges = new Map(previous.graph.edges.map((edge) => [edge.id, edge]));
          nodes.set(event.node.id, event.node); if (event.edge) edges.set(event.edge.id, event.edge);
          return { ...previous, graph: { ...previous.graph, nodes: [...nodes.values()], edges: [...edges.values()] } };
        });
      }
      if (event.kind === "agent_started") setData((previous) => ({ ...previous, agent: { ...previous.agent, running: true } }));
      if (["done", "agent_done", "agent_failed"].includes(event.kind)) {
        if (event.kind === "agent_failed") setMessage(event.message);
        refresh().catch((error) => setMessage(error.message));
      }
    });
  }, []);
  useEffect(() => {
    if (!data.agent?.running) return;
    const id = setInterval(() => refresh().catch((error) => setMessage(error.message)), 1000);
    return () => clearInterval(id);
  }, [data.agent?.running]);
  const flow = useMemo(() => explorationFlow(data.graph), [data.graph]);
  const packet = data.packets.find((item) => item.id === packetId);
  const changes = data.comparison?.changes?.filter((item) => item.status !== "unchanged") || [];
  const ledger = data.agent?.ledger || {};
  const busy = working || data.agent?.running;
  return <section className="inspection-extension" aria-label="검사 분석">
    <div className="inspection-actions" role="tablist" aria-label="분석 보기">
      {[["graph", "탐색 그래프"], ["comparison", "변경 비교"], ["agent", "Groq 검토"]].map(([id, label]) =>
        <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}>{label}</button>)}
      <button onClick={() => action(refresh)} disabled={working}>새로고침</button>
    </div>
    {message && <p role="status">{message}</p>}
    {!run && <p>검사를 실행하거나 검사 기록을 여세요.</p>}
    {tab === "graph" && <>
      <div className="inspection-graph" data-testid="exploration-graph">
        <ReactFlow nodes={flow.nodes} edges={flow.edges} fitView nodesDraggable={false} nodesConnectable={false}
          onNodeClick={(_event, node) => {
            const observed = data.graph.nodes.find((item) => item.id === node.id);
            setSelected(observed); if (observed?.packet_ids?.[0]) setPacketId(observed.packet_ids[0]);
          }}><Background /><Controls /></ReactFlow>
      </div>
      {(flow.omitted > 0 || data.graph.truncated) && <p>화면 표시 {flow.nodes.length}개 / 관측 {data.graph.nodes.length}개. 수집 한도: {data.graph.truncated ? "도달" : "미도달"}.</p>}
      {selected && <div className="inspection-detail"><strong>{selected.label}</strong><p>{selected.url}</p>
        <p>{selected.kind === "state" ? `${selected.packet_ids?.length || 0}개 영역 관측` : selected.status}</p>
        {packet && <pre>{packet.text}</pre>}</div>}
    </>}
    {tab === "comparison" && <>
      <div className="inspection-actions"><label>이전 검사 <select aria-label="비교 기준" value={baseline} onChange={(event) => setBaseline(event.target.value)}>
        <option value="">검사 선택</option>{history.filter((item) => item.id !== run).map((item) => <option key={item.id} value={item.id}>{item.finished_at} · {item.url}</option>)}
      </select></label><button disabled={!baseline || working} onClick={() => action(() => api.compare({ run_id: run, baseline_id: baseline }))}>비교</button></div>
      {data.comparison ? <>
        <p>{Object.entries(data.comparison.counts).map(([name, count]) => `${CHANGE_LABELS[name]} ${count}`).join(" · ")}</p>
        <p>{data.comparison.warning}{!data.comparison.coverage_complete && " 일부 수집 범위입니다."}</p>
        <div className="inspection-changes">{changes.map((change) => <article key={change.identity}>
          <strong>{CHANGE_LABELS[change.status]}</strong><p>{(change.after || change.before).url} · {(change.after || change.before).location}</p>
          <div className="inspection-pair"><div><b>이전</b><pre>{change.before?.text || "관측 없음"}</pre><pre>{JSON.stringify({ links: change.before?.link_targets, style: change.before?.computed_style || null }, null, 2)}</pre></div>
            <div><b>현재</b><pre>{change.after?.text || "관측 없음"}</pre><pre>{JSON.stringify({ links: change.after?.link_targets, style: change.after?.computed_style || null }, null, 2)}</pre></div></div>
        </article>)}{changes.length === 0 && <p>비교 범위에서 변경된 관측이 없습니다.</p>}</div>
      </> : <p>같은 시작 URL의 이전 검사와 비교합니다. 첫 검사나 이전 버전 기록에는 비교 근거가 없을 수 있습니다.</p>}
    </>}
    {tab === "agent" && <>
      <div className="inspection-actions">
        <label>Groq API 키 <input aria-label="Groq API 키" type="password" autoComplete="off" value={key} onChange={(event) => setKey(event.target.value)} placeholder="GROQ_API_KEY 또는 세션 입력" /></label>
        <label>모델 <input aria-label="Groq 모델" value={model} onChange={(event) => setModel(event.target.value)} /></label>
        <label>누적 토큰 <input aria-label="Groq 토큰 한도" type="number" min="1000" max="60000" value={tokenLimit} onChange={(event) => setTokenLimit(Number(event.target.value))} /></label>
        <label>누적 호출 <input aria-label="Groq 호출 한도" type="number" min="1" max="12" value={callLimit} onChange={(event) => setCallLimit(Number(event.target.value))} /></label>
        <button disabled={busy} onClick={() => action(async () => {
          await api.configureAgent({ api_key: key, model, token_limit: tokenLimit, call_limit: callLimit }); setKey("");
        })}>설정 적용</button>
      </div>
      <p>외부 API는 Groq만 사용합니다. 키는 메모리에만 보관합니다. 선택한 근거의 일부 문구·관측값을 전송하며 URL·이메일·전화번호는 마스킹합니다. 자유 서술의 개인정보까지 모두 제거되는 것은 아닙니다.</p>
      <p>현재 검사 누적 호출 {ledger.calls || 0}/{ledger.call_limit || callLimit} · 예산 사용 {ledger.charged_tokens || 0}/{ledger.token_limit || tokenLimit}토큰 · 제공자 보고 {ledger.usage_tokens || 0}토큰</p>
      <label>검토 영역 <select aria-label="검토 영역" value={packetId} onChange={(event) => setPacketId(event.target.value)}><option value="">영역 선택</option>
        {data.packets.map((item) => <option key={item.id} value={item.id}>{item.text.slice(0, 60)} · {item.location}</option>)}
      </select></label>
      {packet && <div className="inspection-detail"><pre>{packet.text}</pre><p>스타일: {packet.computed_style ? "관측" : "미확인"} · {packet.truncated ? "일부 문맥" : "수집 문맥"}</p></div>}
      <div className="inspection-actions"><button disabled={!packet || busy} onClick={() => action(() => api.runAgent({ run_id: run, evidence_id: packetId }))}>Groq 분석</button>
        <button disabled={!data.agent?.running} onClick={() => action(() => api.stopAgent())}>분석 중단</button></div>
      {data.agent?.assessments?.slice().reverse().map((item, index) => <article className="inspection-detail" key={index}>
        <strong>{{ ad_suspected: "광고 의심", benign_context: "정상 문맥 제안", uncertain: "보류" }[item.assessment]}</strong><p>{item.summary}</p>
        <p>{item.reads.map((read) => read.tool).join(" → ")} · {item.provider} / {item.model}</p>
        {item.missing_evidence.length > 0 && <p>미확인: {item.missing_evidence.join(", ")}</p>}
      </article>)}
    </>}
  </section>;
}
