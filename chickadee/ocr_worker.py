"""Offline PaddleOCR PP-OCRv5 CPU inference in a disposable child process.

Implements the official DB detector / CTC recognizer inference transforms.
Models are immutable official PaddlePaddle assets, never downloaded at runtime.
"""
import base64
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


class PaddleTextReader:
    def __init__(self):
        import cv2
        import numpy as np
        import paddle.inference as inference
        import yaml
        self.cv, self.np = cv2, np
        models = ROOT / 'ocr-models' if getattr(sys, 'frozen', False) else ROOT / 'artifacts/ocr-models'
        manifest = json.loads((ROOT / 'chickadee/data/ocr-models.json').read_text(encoding='utf-8'))
        for item in manifest['files']:
            file = models / item['path']
            if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('OCR 모델 파일 검증 실패. scripts/prepare_ocr_models.py를 실행하세요.')
        def predictor(name):
            folder = models / name
            config = inference.Config(str(folder / 'inference.json'), str(folder / 'inference.pdiparams'))
            config.disable_gpu()
            config.set_cpu_math_library_num_threads(2)
            config.disable_mkldnn()
            config.disable_glog_info()
            return inference.create_predictor(config)
        self.det = predictor('PP-OCRv5_mobile_det')
        self.rec = predictor('korean_PP-OCRv5_mobile_rec')
        config = yaml.safe_load((models / 'korean_PP-OCRv5_mobile_rec/inference.yml').read_text(encoding='utf-8'))
        self.chars = [''] + config['PostProcess']['character_dict'] + [' ']

    def run(self, model, value):
        model.get_input_handle(model.get_input_names()[0]).copy_from_cpu(value)
        model.run()
        return model.get_output_handle(model.get_output_names()[0]).copy_to_cpu()

    def read(self, data):
        from PIL import Image
        import pyclipper
        np, cv = self.np, self.cv
        Image.MAX_IMAGE_PIXELS = 8_000_000
        with Image.open(io.BytesIO(data)) as source:
            w, h = source.size
            image_format = source.format
            if w * h > 8_000_000 or min(w, h) < 8 or source.format not in ('PNG', 'JPEG', 'WEBP', 'GIF'):
                raise ValueError('지원하지 않는 이미지 형식·해상도')
            image = np.asarray(source.convert('RGB'))[:, :, ::-1].copy()
        ratio = min(1., 960 / max(w, h))
        dw, dh = max(32, round(w * ratio / 32) * 32), max(32, round(h * ratio / 32) * 32)
        resized = cv.resize(image, (dw, dh)).astype('float32') / 255.
        tensor = ((resized - np.array([.485, .456, .406], dtype='float32')) /
                  np.array([.229, .224, .225], dtype='float32')).transpose(2, 0, 1)[None].copy()
        scores = self.run(self.det, tensor)[0, 0]
        contours, _ = cv.findContours((scores > .3).astype('uint8') * 255, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)
        boxes = []
        for contour in contours[:1000]:
            rect = cv.minAreaRect(contour)
            if min(rect[1]) < 3:
                continue
            poly = cv.boxPoints(rect)
            mask = np.zeros(scores.shape, dtype='uint8')
            cv.fillPoly(mask, [poly.astype('int32')], 1)
            if cv.mean(scores, mask)[0] < .6:
                continue
            distance = cv.contourArea(poly) * 1.5 / max(cv.arcLength(poly, True), 1)
            offset = pyclipper.PyclipperOffset()
            offset.AddPath(poly.astype('int32').tolist(), pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)
            grown = offset.Execute(distance)
            if len(grown) != 1:
                continue
            box = cv.boxPoints(cv.minAreaRect(np.asarray(grown[0], dtype='float32')))
            box[:, 0] = np.clip(box[:, 0] * w / dw, 0, w - 1)
            box[:, 1] = np.clip(box[:, 1] * h / dh, 0, h - 1)
            ordered = box[np.argsort(box[:, 0])]
            left, right = ordered[:2], ordered[2:]
            left = left[np.argsort(left[:, 1])]; right = right[np.argsort(right[:, 1])]
            boxes.append(np.array([left[0], right[0], right[1], left[1]], dtype='float32'))
        boxes.sort(key=lambda b: (round(float(b[:, 1].min()) / 15), float(b[:, 0].min())))
        lines = []
        for box in boxes[:80]:
            bw = max(1, int(max(np.linalg.norm(box[0] - box[1]), np.linalg.norm(box[2] - box[3]))))
            bh = max(1, int(max(np.linalg.norm(box[0] - box[3]), np.linalg.norm(box[1] - box[2]))))
            transform = cv.getPerspectiveTransform(box, np.array([[0, 0], [bw, 0], [bw, bh], [0, bh]], dtype='float32'))
            crop = cv.warpPerspective(image, transform, (bw, bh), borderMode=cv.BORDER_REPLICATE)
            if bh / bw > 1.5:
                crop = np.rot90(crop)
            rh, rw = crop.shape[:2]
            width = min(1600, max(320, int(48 * rw / rh)))
            actual = min(width, max(1, int(48 * rw / rh)))
            rec = np.zeros((3, 48, width), dtype='float32')
            rec[:, :, :actual] = (cv.resize(crop, (actual, 48)).astype('float32') / 127.5 - 1).transpose(2, 0, 1)
            output = self.run(self.rec, rec[None])[0]
            indices, confidence = output.argmax(axis=1), output.max(axis=1)
            keep = (indices != 0) & np.concatenate(([True], indices[1:] != indices[:-1]))
            text = ''.join(self.chars[int(index)] for index in indices[keep] if index < len(self.chars)).strip()
            score = float(confidence[keep].mean()) if keep.any() else 0.
            if text and np.isfinite(score):
                lines.append({'text': text[:1000], 'confidence': round(score, 4), 'box': [[round(float(v), 1) for v in point] for point in box]})
        preview = Image.fromarray(image[:, :, ::-1])
        preview.thumbnail((1600, 1600))
        buffer = io.BytesIO()
        preview.save(buffer, format='JPEG', quality=65)
        while buffer.tell() > 200_000:
            preview.thumbnail((max(64, preview.width // 2), max(64, preview.height // 2)))
            buffer = io.BytesIO(); preview.save(buffer, format='JPEG', quality=45)
        return {'engine': 'PaddleOCR', 'model': 'PP-OCRv5 mobile / Korean', 'width': w, 'height': h,
                'image_format': image_format,
                'preview_data_url': 'data:image/jpeg;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii'),
                'preview_sha256': hashlib.sha256(buffer.getvalue()).hexdigest(),
                'lines': lines, 'truncated': len(boxes) > 80, 'status': 'completed'}


def main():
    # Native libraries log to stdout. Keep the private protocol on its original
    # descriptor and redirect all library chatter to stderr before importing.
    import os
    protocol = os.fdopen(os.dup(sys.stdout.fileno()), 'w', encoding='utf-8', buffering=1)
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    reader = None
    for line in sys.stdin:
        try:
            if len(line) > 2_800_000:
                raise ValueError('OCR 입력 크기 초과')
            value = json.loads(line)
            data = base64.b64decode(value['image'], validate=True)
            if len(data) > 2_000_000:
                raise ValueError('OCR 이미지 크기 초과')
            if reader is None:
                reader = PaddleTextReader()
            result = reader.read(data)
        except Exception as error:
            result = {'status': 'failed', 'fatal': reader is None, 'message': str(error)[:300], 'lines': []}
        protocol.write(json.dumps(result, ensure_ascii=True) + '\n')


if __name__ == '__main__': main()
