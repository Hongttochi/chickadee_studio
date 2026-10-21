import React, { useState } from "react";

export default function ImageOCR({ image }) {
  const [selected, setSelected] = useState(-1);
  if (!image) return null;
  const source = /^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/.test(image.preview_data_url || "") && image.preview_data_url.length < 270000 ? image.preview_data_url : null;
  return <section className="image-ocr-evidence" aria-label="이미지 OCR 근거">
    <label>이미지 OCR</label>
    {source && <div className="image-ocr-preview">
      <img src={source} alt="OCR로 검사한 게시글 이미지" />
      <svg viewBox={`0 0 ${image.width} ${image.height}`} aria-hidden="true">
        {(image.lines || []).map((line, index) => <polygon key={index} points={line.box.map(([x, y]) => `${x},${y}`).join(" ")} className={selected === index ? "selected" : ""} />)}
      </svg>
    </div>}
    <div className="image-ocr-lines">{(image.lines || []).map((line, index) => <button type="button" key={index} aria-pressed={selected === index} onClick={() => setSelected(index)}>
      <span>{line.text}</span><small>{Math.round(line.confidence * 100)}%</small>
    </button>)}</div>
    <details><summary>이미지 정보</summary><p>{image.source_url}</p><p>{image.model} · {image.width} × {image.height}</p><p className="mono">SHA-256 {image.image_sha256}</p></details>
  </section>;
}
