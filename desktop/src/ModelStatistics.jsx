import React from 'react';
import { modelStatistics } from './model-statistics.mjs';

function Bars({ values, labels }) {
  const maximum = Math.max(1, ...values);
  return <div className="model-stat-bars" role="img" aria-label={labels.map((label, i) => `${label} ${values[i]}개`).join(', ')}>
    {values.map((value, i) => <div key={labels[i]} title={`${labels[i]}: ${value}개`}><span>{value}</span><i style={{ height: `${Math.max(value ? 4 : 1, value / maximum * 36)}px` }} /><small>{labels[i]}</small></div>)}
  </div>;
}
export default function ModelStatistics({ data }) {
  const stats = modelStatistics(data), bands = ['0~0.2', '0.2~0.4', '0.4~0.6', '0.6~0.8', '0.8~1'];
  return <section className="model-statistics" aria-label="모델 처리 통계">
    <header><strong>이번 검사 통계</strong><span>실제 처리 건수와 저장된 분석 점수</span></header>
    <div className="model-statistics-scroll"><table><thead><tr><th>기능</th><th>상태</th><th>처리</th><th>분포</th></tr></thead><tbody>
      <tr><th>ML</th><td>{stats.ml.analyzed ? '적용' : '입력 없음'}</td><td>{stats.ml.analyzed.toLocaleString()}개 영역</td><td>{stats.ml.samples ? <Bars values={stats.ml.bins} labels={bands} /> : '점수 없음'}</td></tr>
      <tr><th>Laya</th><td>{stats.laya.status}</td><td>{stats.laya.analyzed.toLocaleString()}개 영역</td><td>{stats.laya.samples ? <Bars values={stats.laya.bins} labels={bands} /> : '적용된 분석 결과 없음'}</td></tr>
      <tr><th>OCR</th><td>{stats.ocr.status}</td><td>{stats.ocr.analyzed.toLocaleString()} / {stats.ocr.total.toLocaleString()}개 이미지 영역</td><td>{stats.ocr.total ? <Bars values={stats.ocr.values} labels={['문자 인식', '읽기 어려움', '오류', '생략']} /> : '이미지 없음'}</td></tr>
    </tbody></table></div>
    <p>ML과 Laya의 점수는 모델의 분류 점수입니다. 정확도나 위법 확률이 아닙니다. OCR은 이미지에서 글자를 읽은 결과입니다.</p>
  </section>;
}
