"""Download pinned official PaddleOCR inference assets for offline CPU use."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'chickadee/data/ocr-models.json'
DESTINATION = ROOT / 'artifacts/ocr-models'
MODELS = ('PP-OCRv5_mobile_det', 'korean_PP-OCRv5_mobile_rec')
FILES = ('inference.json', 'inference.pdiparams', 'inference.yml')


def download(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(30_000_001)
    if len(data) > 30_000_000:
        raise ValueError('OCR asset exceeds download limit')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pin', action='store_true', help='Explicitly refresh official model revisions and SHA256 pins')
    args = parser.parse_args()
    if args.pin:
        manifest = {'version': 'PP-OCRv5', 'license': 'Apache-2.0', 'files': []}
        for model in MODELS:
            meta = json.loads(download('https://huggingface.co/api/models/PaddlePaddle/' + model))
            revision = meta['sha']
            for name in FILES:
                url = f'https://huggingface.co/PaddlePaddle/{model}/resolve/{revision}/{name}'
                data = download(url)
                path = DESTINATION / model / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                manifest['files'].append({'path': model + '/' + name, 'url': url, 'bytes': len(data),
                                          'sha256': hashlib.sha256(data).hexdigest(), 'revision': revision})
        MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    else:
        manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
        for item in manifest['files']:
            path = DESTINATION / item['path']
            data = path.read_bytes() if path.exists() else b''
            if hashlib.sha256(data).hexdigest() != item['sha256']:
                data = download(item['url'])
                if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                    raise ValueError('OCR model SHA256 mismatch: ' + item['path'])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
    print('Verified official offline PaddleOCR assets:', len(manifest['files']))


if __name__ == '__main__': main()
