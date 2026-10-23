"""Render the public evaluation figures from metrics.json using Pretendard.

Run after `npm --prefix desktop ci`: python scripts/render_evaluation_charts.py
Requires Pillow (also used by the local OCR/image pipeline).
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
INK = '#26323D'
MUTED = '#64748B'
GRID = '#E7ECF1'
TRACK = '#F1F4F7'
COLORS = ['#6B7C8F', '#46566A', '#2563EB', '#13836D']
SCALE = 2


class Figure:
    def __init__(self, width, height, fonts):
        self.image = Image.new('RGB', (width * SCALE, height * SCALE), 'white')
        self.draw = ImageDraw.Draw(self.image)
        self.width, self.height, self.fonts = width, height, fonts

    def text(self, x, y, value, size=22, bold=False, color=INK, anchor='lt'):
        name = 'Pretendard-Bold.ttf' if bold else 'Pretendard-Regular.ttf'
        font = ImageFont.truetype(str(self.fonts / name), size * SCALE)
        self.draw.text((x * SCALE, y * SCALE), value, font=font, fill=color, anchor=anchor)

    def line(self, x1, y1, x2, y2, color=GRID):
        self.draw.line((x1 * SCALE, y1 * SCALE, x2 * SCALE, y2 * SCALE), fill=color, width=SCALE)

    def rect(self, x, y, w, h, color):
        self.draw.rectangle((x * SCALE, y * SCALE, (x + w) * SCALE, (y + h) * SCALE), fill=color)

    def save(self, path):
        self.image.resize((self.width, self.height), Image.Resampling.LANCZOS).save(path, optimize=True)


def text_models(metrics, fonts, destination):
    fig = Figure(1600, 750, fonts)
    fig.text(64, 48, '한국어 광고 문맥 분류', 36, True)
    fig.text(64, 104, '정상 댓글과 홍보성 봇 댓글 구분  /  고정 평가셋 118건', 22, color=MUTED)
    rows = [
        ('rf', 'RF', '기본 학습'),
        ('rf_augmented', 'RF', '데이터 보강'),
        ('bert_full_augmented', 'BERT', '본체 미세조정'),
        ('laya_full_augmented', 'Laya', '본체 미세조정'),
    ]
    panels = [(300, 490, 'Macro F1', 'macro_f1', False),
              (930, 490, '홍보 문맥 재현율', 'positive_recall', True)]
    for x, width, title, key, percent in panels:
        fig.text(x, 180, title, 24, True)
        for tick in range(6):
            px = x + width * tick / 5
            fig.line(px, 230, px, 562)
            label = f'{tick * 20}%' if percent else f'{tick / 5:.1f}'
            fig.text(px, 581, label, 18, color=MUTED, anchor='mt')
        for i, (model, _, _) in enumerate(rows):
            y = 248 + 82 * i
            value = metrics['text_comparison']['models'][model][key]
            fig.rect(x, y, width, 28, TRACK)
            fig.rect(x, y, width * value, 28, COLORS[i])
            label = f'{value * 100:.2f}%' if percent else f'{value:.4f}'
            fig.text(x + width + 18, y + 14, label, 22, True, anchor='lm')
    for i, (_, label, detail) in enumerate(rows):
        y = 244 + 82 * i
        fig.text(64, y, label, 25, True)
        fig.text(64, y + 34, detail, 18, color=MUTED)
    fig.line(64, 638, 1536, 638)
    fig.text(64, 663, '학습 문구: 실제 440건 + 합성 49건. 한국어 홍보 댓글 분류 지표입니다.', 21, color=MUTED)
    fig.text(64, 701, '서비스 구성: RF 문자 분류 + 한국어 Laya 문맥 분석. 14종 전체의 판별 성능과 구분합니다.', 21, color=MUTED)
    fig.save(destination / 'model-comparison.png')


def ocr_models(metrics, fonts, destination):
    fig = Figure(1600, 650, fonts)
    fig.text(64, 48, '라틴 문자 인식 지표', 36, True)
    fig.text(64, 104, '실제 이미지 16장  /  문자 영역 43개  /  정답 문구 1,229자', 22, color=MUTED)
    fig.text(390, 180, '문자 오류율 CER (낮을수록 우수)', 24, True)
    x, width, maximum = 390, 940, 0.04
    for tick in range(5):
        px = x + width * tick / 4
        fig.line(px, 230, px, 408)
        fig.text(px, 431, f'{tick:.0f}%', 20, color=MUTED, anchor='mt')
    for i, (key, label, color) in enumerate([
        ('baseline', '기존 OCR', '#13836D'),
        ('trained', '추가 학습 OCR', '#6B7C8F'),
    ]):
        y = 260 + i * 100
        value = metrics['ocr_comparison'][key]['cer']
        fig.text(64, y + 18, label, 25, True, anchor='lm')
        fig.rect(x, y, width, 36, TRACK)
        fig.rect(x, y, width * value / maximum, 36, color)
        fig.text(x + width * value / maximum + 20, y + 18, f'{value * 100:.2f}%', 28, True, anchor='lm')
    fig.line(64, 494, 1536, 494)
    fig.text(64, 519, '라틴 문자 인식 지표로, 한국어 성능 표는 아닙니다.', 21, color=MUTED)
    fig.text(64, 558, '정답 문구를 직접 읽어 작성한 자료입니다. 기존 모델 13자, 추가 학습 모델 36자 오류.', 21, color=MUTED)
    fig.text(64, 597, '서비스의 이미지 문자 추출에는 한국어 PaddleOCR를 사용합니다.', 21, color=MUTED)
    fig.save(destination / 'ocr-comparison.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font-dir', type=Path, default=ROOT / 'desktop/node_modules/pretendard/dist/public/static/alternative')
    args = parser.parse_args()
    for filename in ('Pretendard-Regular.ttf', 'Pretendard-Bold.ttf'):
        if not (args.font_dir / filename).is_file():
            parser.error(f'Missing font: {filename}. Run npm --prefix desktop ci or pass --font-dir.')
    destination = ROOT / 'docs/assets/evaluation'
    metrics = json.loads((destination / 'metrics.json').read_text(encoding='utf-8'))
    text_models(metrics, args.font_dir, destination)
    ocr_models(metrics, args.font_dir, destination)
    print('Rendered model-comparison.png and ocr-comparison.png with Pretendard.')


if __name__ == '__main__':
    main()
