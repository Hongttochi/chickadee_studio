"""Package the already built Windows app, documentation and license notices."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DESKTOP = ROOT / 'desktop'
VERSION = json.loads((DESKTOP / 'package.json').read_text(encoding='utf-8'))['version']
APP = ROOT / 'artifacts' / f'electron-{VERSION}' / 'win-unpacked'


def frontend_licenses():
    modules = DESKTOP / 'node_modules'
    pending = ['react', 'react-dom', '@xyflow/react', 'lucide-react', 'use-sync-external-store']
    visited, notices = set(), []
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        folder = modules / name
        package = json.loads((folder / 'package.json').read_text(encoding='utf-8'))
        files = [p for p in folder.iterdir() if p.is_file() and p.name.upper().startswith(('LICENSE', 'COPYING', 'NOTICE'))]
        if not files:
            raise RuntimeError(f'License text missing: {name}')
        notices.append(f"\n{'=' * 72}\n{name} {package['version']} ({package.get('license', '')})\n" +
                       '\n'.join(p.read_text(encoding='utf-8', errors='replace') for p in sorted(files)))
        pending.extend(package.get('dependencies', {}))
    target = DESKTOP / 'licenses' / 'Frontend-Third-Party.txt'
    target.write_text('Bundled frontend dependencies and their license notices.\n' + '\n'.join(notices), encoding='utf-8')
    return len(visited)


def main():
    required = [APP / 'Chickadee.exe', APP / 'resources/engine/ChickadeeEngine.exe']
    if not all(p.is_file() for p in required):
        raise RuntimeError('Build scripts/build-desktop.ps1 first.')
    count = frontend_licenses()
    shutil.copytree(DESKTOP / 'licenses', APP / 'licenses', dirs_exist_ok=True)
    for name in ['quickstart-windows.md', 'desktop.md', 'result-format.md', 'third-party-notices.md', 'validation.md', 'manual.md', 'agent-extension.md', 'inspection-agent.md']:
        target = APP / 'docs' / name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(ROOT / 'docs' / name, target)
    shutil.copy2(ROOT / 'DESIGN.md', APP / 'DESIGN.md')
    (APP / 'README_FIRST.txt').write_text(
        f'Chickadee Studio {VERSION} / Windows x64\n\n'
        'ZIP 전체를 압축 해제한 다음 Chickadee.exe를 실행하세요.\n'
        'resources 등 함께 있는 폴더를 유지하세요. Python/Node.js/Docker 설치는 필요하지 않습니다.\n'
        'URL 입력 → 검사 실행. 로컬 예제는 실행 옆 화살표 메뉴 → 데모 검사.\n'
        '일시정지·재개, 검토 상태·메모·일괄 처리, Ctrl K 빠른 명령을 지원합니다.\n'
        '기본 저장: 문서/Chickadee/results/실행별 폴더\n'
        '검사 구성의 포트를 연결하면 실제 실행 단계가 변경됩니다.\n'
        '사용 안내: docs/quickstart-windows.md, docs/desktop.md\n'
        '이 프리릴리스는 인증서 서명이 없습니다. 0.6.0 재빌드본이 개발 PC의 Device Guard에 차단됐습니다.\n'
        'Windows CI 실행 검증 결과와 사용자 PC별 검증 한계는 docs/validation.md를 확인하세요.\n'
        'https://github.com/orqan137/chickadee_Bot\n', encoding='utf-8-sig')
    output = ROOT / 'artifacts' / f'Chickadee-Studio-{VERSION}-win-x64.zip'
    temporary = output.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for file in sorted(APP.rglob('*')):
            if file.is_file():
                archive.write(file, str(Path(f'Chickadee-{VERSION}') / file.relative_to(APP)))
    with zipfile.ZipFile(temporary) as archive:
        invalid = archive.testzip()
        if invalid:
            raise RuntimeError(f'ZIP checksum failed: {invalid}')
    temporary.replace(output)
    digest = sha256()
    with output.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    output.with_suffix('.zip.sha256').write_text(f'{digest.hexdigest()}  {output.name}\n', encoding='ascii')
    print(json.dumps({'archive': str(output), 'bytes': output.stat().st_size, 'sha256': digest.hexdigest(), 'frontend_license_count': count}))


if __name__ == '__main__':
    main()
