import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Maximize2, X } from "lucide-react";
import startScreen from "../assets/guide/start.png";
import reviewScreen from "../assets/guide/review.png";
import historyScreen from "../assets/guide/history.png";

const STORAGE_KEY = "chickadee.guide.v1.seen";
export function shouldShowTutorial() {
  try {
    return localStorage.getItem(STORAGE_KEY) !== "true";
  } catch {
    return true;
  }
}
export function rememberTutorial() {
  try {
    localStorage.setItem(STORAGE_KEY, "true");
  } catch {
    // The guide remains usable even when browser storage is unavailable.
  }
}

const steps = [
  {
    label: "검사 시작",
    title: "주소를 넣고 검사를 시작하세요",
    description: "검사 대상에서 주소를 입력한 뒤, 화면 맨 위의 검사 실행을 누릅니다.",
    image: startScreen,
    caption: "검사 대상 선택 → 오른쪽 패널에서 주소 입력",
    instructions: [
      ["주소 입력", "왼쪽 검사 구성 → 위치 핀 아이콘의 검사 대상 노드를 누릅니다. 오른쪽 ‘검사 대상 URL’에 사이트 주소를 입력하세요."],
      ["검사 실행", "상단의 검사 실행을 누릅니다. 검사 범위를 바꾸려면 왼쪽 검사 설정에서 최대 페이지와 전체 제한시간을 먼저 조정하세요."],
      ["진행 확인", "오른쪽 가장자리 패널 버튼으로 브라우저 미리보기를 엽니다. 탐색 경로에서는 방문·대기 주소를, 진행 기록에서는 단계별 작업을 확인할 수 있습니다."],
    ],
    note: "주소는 https:// 또는 http://로 시작해야 합니다.",
    example: "https://example.go.kr",
  },
  {
    label: "결과 확인",
    title: "발견한 항목의 근거를 확인하세요",
    description: "탐지 내역에서 항목을 선택하고, 오른쪽 상세 패널에서 근거를 읽습니다.",
    image: reviewScreen,
    caption: "탐지 항목 선택 → 오른쪽에서 원문과 근거 확인",
    instructions: [
      ["항목 찾기", "전체·필수 탐지·광고 의심 탭으로 범위를 좁힙니다. 검색창에는 문구나 URL을 입력하고, 검토 필터에서 미검토 항목만 볼 수도 있습니다."],
      ["근거 확인", "행을 누른 뒤 ‘발견한 문구’와 ‘탐지 이유’를 확인하세요. ‘페이지 · 기술 정보’를 펼치면 원본 URL과 DOM 위치를 확인하고 복사할 수 있습니다."],
      ["검토 저장", "검토 확인 또는 제외를 누르면 상태가 저장됩니다. 검토 메모를 입력한 뒤에도 이 버튼을 사용하세요. ⋯ 메뉴에서는 메모만 저장하거나 미검토로 되돌릴 수 있습니다."],
    ],
    note: "탐지된 항목이 모두 불법 광고인 것은 아닙니다. 원문과 근거를 함께 확인하세요.",
  },
  {
    label: "결과 저장",
    title: "결과는 자동으로 저장됩니다",
    description: "지난 검사를 다시 열거나, 필요한 결과를 파일로 내보낼 수 있습니다.",
    image: historyScreen,
    caption: "검사 기록 선택 → 저장된 탐지 내역 열기",
    instructions: [
      ["이전 결과 열기", "왼쪽 검사 기록에서 대상·상태·완료 시간을 확인하고 원하는 행을 누릅니다. 별도로 보관한 result.json은 ‘결과 불러오기’로 열 수 있습니다."],
      ["파일 확인", "상단 결과 폴더를 누르면 저장 위치가 열립니다. 저장 위치는 검사 설정에서 바꿀 수 있으며, 각 검사는 별도 폴더에 보관됩니다."],
      ["CSV 내보내기", "탐지 내역 오른쪽 위의 CSV 저장을 누릅니다. 저장된 CSV 파일은 스프레드시트에서 열어 확인할 수 있습니다."],
    ],
    note: "잘 모르겠다면 데모로 연습해 보세요. 내장 예제를 검사합니다.",
  },
];

export default function Tutorial({ onClose, onDemo, onInspect, canDemo }) {
  const [step, setStep] = useState(0);
  const [zoomed, setZoomed] = useState(false);
  const dialog = useRef(null);
  const heading = useRef(null);
  const tabs = useRef(null);
  const current = steps[step];
  const last = step === steps.length - 1;
  useEffect(() => {
    const previous = document.activeElement;
    const element = dialog.current;
    element.showModal();
    return () => {
      element.close();
      if (previous instanceof HTMLElement && previous.isConnected) previous.focus();
    };
  }, []);
  useEffect(() => {
    heading.current?.focus();
  }, [step]);
  useLayoutEffect(() => {
    const list = tabs.current;
    const measure = () => {
      const active = list.querySelector('[aria-current="step"]');
      if (!active) return;
      list.style.setProperty("--tab-left", `${active.offsetLeft}px`);
      list.style.setProperty("--tab-top", `${active.offsetTop + active.offsetHeight - 2}px`);
      list.style.setProperty("--tab-width", `${active.offsetWidth}px`);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(list);
    list.querySelectorAll("button").forEach(button => observer.observe(button));
    return () => observer.disconnect();
  }, [step]);

  return (
    <dialog
      ref={dialog}
      className="tutorial-dialog"
      aria-labelledby="tutorial-label"
      onCancel={(event) => { event.preventDefault(); onClose(); }}
      onKeyDown={(event) => event.stopPropagation()}
    >
      <header className="tutorial-header">
        <h2 id="tutorial-label">사용 가이드</h2>
        <button type="button" className="tutorial-close" aria-label="사용 가이드 닫기" onClick={onClose}>닫기 <X size={18} aria-hidden="true" /></button>
      </header>
      <nav className="tutorial-steps" aria-label="안내 순서">
        <ol ref={tabs}>
          {steps.map((item, index) => (
            <li key={item.label}>
              <button
                type="button"
                aria-label={`${index + 1}단계: ${item.label}`}
                aria-current={index === step ? "step" : undefined}
                onClick={() => setStep(index)}
              >{item.label}</button>
            </li>
          ))}
          <li className="tab-indicator" aria-hidden="true" />
        </ol>
      </nav>
      <div className="tutorial-content">
        <h3 id="tutorial-title" tabIndex={-1} ref={heading} aria-describedby="tutorial-step-count">{current.title}</h3>
        <span id="tutorial-step-count" className="tutorial-sr-only">{steps.length}단계 중 {step + 1}단계</span>
        <p id="tutorial-description">{current.description}</p>
        <div className="tutorial-walkthrough">
        <figure className="tutorial-screen">
          <button className="tutorial-screen-button" type="button" aria-label="화면 크게 보기" title="화면 크게 보기" onClick={() => setZoomed(true)}>
            <img src={current.image} alt={current.caption} />
            <span className="tutorial-zoom-icon" aria-hidden="true"><Maximize2 size={14} /></span>
          </button>
          <figcaption>{current.caption}</figcaption>
        </figure>
        <dl className="tutorial-instructions">
          {current.instructions.map(([label, description], index) => (
            <div key={label}><dt><span className="tutorial-number" aria-hidden="true">{index + 1}</span>{label}</dt><dd>{description}</dd></div>
          ))}
        </dl>
        </div>
        {current.example && <p className="tutorial-address">주소 예시 <code>{current.example}</code></p>}
        <p className="tutorial-hint">{current.note}</p>
        {last && !canDemo && <p id="tutorial-demo-unavailable" className="tutorial-unavailable" role="status">지금은 데모를 시작할 수 없습니다. 검사 엔진이 준비되고 진행 중인 검사가 끝난 뒤 다시 시도하세요.</p>}
      </div>
      <footer className="tutorial-footer">
          <button type="button" className="button button-secondary" disabled={step === 0} onClick={() => setStep(step - 1)}><ArrowLeft size={18} aria-hidden="true" /> 이전</button>
          <div>
          {last ? (
            <>
              <button type="button" className="button button-secondary" disabled={!canDemo} aria-describedby={!canDemo ? "tutorial-demo-unavailable" : undefined} onClick={onDemo}>데모로 연습하기</button>
              <button type="button" className="button button-primary" onClick={onInspect}>직접 검사하기</button>
            </>
          ) : (
            <button type="button" className="button button-primary" onClick={() => setStep(step + 1)}>다음 <ArrowRight size={18} aria-hidden="true" /></button>
          )}
        </div>
      </footer>
      <p className="tutorial-reopen">닫아도 왼쪽 메뉴의 <strong>사용 가이드</strong>에서 다시 볼 수 있습니다.</p>
      {zoomed && <ScreenPreview image={current.image} caption={current.caption} onClose={() => setZoomed(false)} />}
    </dialog>
  );
}

function ScreenPreview({ image, caption, onClose }) {
  const ref = useRef(null);
  useEffect(() => {
    const previous = document.activeElement;
    const element = ref.current;
    element.showModal();
    return () => { element.close(); if (previous?.isConnected) previous.focus(); };
  }, []);
  return <dialog ref={ref} className="tutorial-image-dialog" aria-label="가이드 화면 확대"
    onCancel={(event) => { event.preventDefault(); event.stopPropagation(); onClose(); }}
    onKeyDown={(event) => event.stopPropagation()}>
    <header><span>{caption}</span><button type="button" aria-label="확대 화면 닫기" onClick={onClose}><X size={18} /></button></header>
    <img src={image} alt={caption} />
  </dialog>;
}
