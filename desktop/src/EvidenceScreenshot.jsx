import React, { useState } from "react";
import { Maximize2, Minimize2 } from "lucide-react";

// Only saved, inert JPEG data is rendered. Never load a page URL in the app.
export default function EvidenceScreenshot({ screenshot, hidden = false, caption = "스크린샷" }) {
  const [expanded, setExpanded] = useState(false);
  if (!screenshot || !/^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/.test(screenshot.data_url || "") || screenshot.data_url.length > 270000) {
    return <figure className="evidence-capture"><figcaption>{caption}</figcaption><p className="evidence-capture-note">저장된 스크린샷이 없습니다. 원문·CSS 근거를 확인하세요.</p></figure>;
  }
  return <figure className="evidence-capture">
    <figcaption>{caption}</figcaption>
    <div className="evidence-capture-frame">
    <div className={expanded ? "evidence-capture-image expanded" : "evidence-capture-image"}>
      <img src={screenshot.data_url} alt="검사 브라우저에서 촬영한 스크린샷" />
    </div>
    <button className="evidence-capture-zoom" type="button" aria-label={expanded ? "축소" : "확대"} title={expanded ? "축소" : "확대"} aria-pressed={expanded} onClick={() => setExpanded(!expanded)}>
      {expanded ? <Minimize2 size={16} aria-hidden="true" /> : <Maximize2 size={16} aria-hidden="true" />}
    </button>
    </div>
    <p className="evidence-capture-note">{hidden ? "숨김·화면 밖 요소는 이미지에 보이지 않을 수 있습니다. 원문·CSS와 함께 확인하세요. " : "촬영 당시 보이는 영역입니다. "}외부 이미지·글꼴 로딩은 제한됩니다.</p>
    <details><summary>촬영 정보</summary><p>{screenshot.url}</p><time>{screenshot.observed_at}</time><p className="mono">SHA-256 {screenshot.sha256}</p></details>
  </figure>;
}
