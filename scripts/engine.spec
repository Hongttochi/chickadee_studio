# PyInstaller desktop worker. The scanner only launches Chromium headless shell.
from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis(
    [str(root / 'run_bridge.py')], pathex=[str(root)], binaries=[],
    datas=[(str(root / 'chickadee/extract.js'), 'chickadee'),
           (str(root / 'chickadee/rules.json'), 'chickadee'),
           (str(root / 'chickadee/data'), 'chickadee/data'),
           (str(root / 'schemas/result.schema.json'), 'schemas'),
           (str(root / 'chickadee/demo_site'), 'chickadee/demo_site'),
           (str(root / 'profiles'), 'profiles')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['tkinter'], noarchive=False, optimize=0,
)
# Do not ship the second, unused headed browser. Keep headless shell, ffmpeg,
# and WinDLL diagnostics. This filters build data; installed browsers stay intact.
def required_browser(entry):
    return '.local-browsers/chromium-' not in entry[0].replace(chr(92), '/')
a.datas = [entry for entry in a.datas if required_browser(entry)]
a.binaries = [entry for entry in a.binaries if required_browser(entry)]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ChickadeeEngine',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=True, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='ChickadeeEngine')
