import React from "react";

const labels = { ad_context: "광고 문맥 유사", phishing_pattern: "피싱 화면 유사", review: "추가 신호 미확인", no_features: "일치 특징 없음" };
export default function LocalAIAnalysis({ analysis }) {
  if (!analysis) return null;
  return <section className="local-ai-analysis" aria-label="로컬 AI 분석">
    <label>AI 분석</label>
    <dl>{[["text", "문자 문맥"], ["visual", "피싱 화면"]].map(([kind, title]) => {
      const item = analysis[kind];
      if (!item) return null;
      return <React.Fragment key={kind}><dt>{title}</dt><dd>
        <strong>{item.status === "completed" ? labels[item.label] || "분석 완료" : "분석 미완료"}</strong>
        {Number.isFinite(item.score) && <span title="보정되지 않은 학습 모델의 분류 점수입니다. 확률이나 안전 점수가 아닙니다.">모델 점수 {item.score.toFixed(3)}</span>}
      </dd></React.Fragment>;
    })}</dl>
    <details><summary>분석 정보</summary>
      {Object.values(analysis).map((item, i) => <p key={i}>{item.model || item.message} · {item.version}</p>)}
      {analysis.text?.matched_features?.length > 0 && <p>일치 특징: {analysis.text.matched_features.join(" · ")}</p>}
      <p>로컬 처리 · API 사용 없음</p>
    </details>
  </section>;
}
