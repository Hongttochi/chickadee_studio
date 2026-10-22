"""Register a verified local Laya bundle for the desktop app. No downloads or API calls."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chickadee.laya_worker import verified_bundle
from chickadee.exports import atomic_write


def default_config():
    if sys.platform == 'win32':
        return Path(os.environ['APPDATA']) / 'Chickadee/laya.json'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/Chickadee/laya.json'
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'Chickadee/laya.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True, help='Local Python with laya, torch and safetensors installed')
    parser.add_argument('--config', type=Path, default=default_config())
    args = parser.parse_args()
    folder, manifest = verified_bundle(args.bundle)
    executable = args.python.resolve(strict=True)
    if not executable.is_file():
        parser.error('Python 실행 파일이 필요합니다.')
    env = {**os.environ, 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'USE_TF': '0'}
    subprocess.run([str(executable), '-c', 'import laya,torch,safetensors; print("Local Laya runtime ready")'],
                   env=env, check=True, timeout=30)
    target = args.config.resolve()
    atomic_write(target, json.dumps({'format': 1, 'model_dir': str(folder), 'python': str(executable)}, indent=2).encode('utf-8'))
    print(f'Laya 활성화: {manifest["version"]}')
    print(f'앱을 다시 실행하면 적용됩니다. 설정 파일: {target}')


if __name__ == '__main__':
    main()
