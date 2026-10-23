from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

root = Path(SPECPATH).parent
data = collect_data_files('laya')
for package in ('torch', 'laya', 'transformers', 'safetensors', 'tokenizers', 'huggingface-hub', 'regex', 'numpy', 'packaging', 'tqdm', 'pyyaml', 'filelock'):
    data += copy_metadata(package)
a = Analysis([str(root/'run_laya.py')], pathex=[str(root)], datas=data,
    hiddenimports=['laya.agent', 'laya.common', 'transformers.models.modernbert.modeling_modernbert',
                   'transformers.models.modernbert.configuration_modernbert', 'transformers.models.bert.tokenization_bert',
                   'transformers.models.auto.tokenization_auto', 'transformers.models.auto.configuration_auto',
                   'safetensors.torch'],
    excludes=['tkinter', 'paddle', 'tensorflow', 'torchvision', 'torchaudio', 'matplotlib', 'scipy', 'sklearn', 'pandas', 'IPython', 'pytest', 'triton', 'cv2'],
    binaries=[], hookspath=[], hooksconfig={}, runtime_hooks=[], noarchive=False, optimize=0)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ChickadeeLaya',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='ChickadeeLaya')
