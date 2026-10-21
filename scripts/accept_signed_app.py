"""Accept the enrolled signing service's directory; keep all non-native bytes identical.

Windows Authenticode verification must still run before executing or publishing it.
No certificate trust or OS security configuration is changed by this helper.
"""
import argparse
from hashlib import file_digest
from pathlib import Path
import shutil

NATIVE = {'.exe', '.dll', '.pyd', '.node'}


def files(root):
    result = {}
    for path in root.rglob('*'):
        if path.is_symlink(): raise ValueError('Symbolic links are not accepted in signed artifacts')
        if path.is_file(): result[path.relative_to(root).as_posix()] = path
    return result


def accept(original, signed):
    original, signed = original.resolve(), signed.resolve()
    if original == signed or original in signed.parents or signed in original.parents:
        raise ValueError('Original and signed application directories must be separate')
    before, after = files(original), files(signed)
    if set(before) != set(after): raise ValueError('The signed artifact file list differs from the build')
    for name, path in before.items():
        if path.suffix.lower() in NATIVE:
            if after[name].stat().st_size < 64 or after[name].stat().st_size > path.stat().st_size + 1024*1024:
                raise ValueError('Signed native file size is invalid: ' + name)
        else:
            with path.open('rb') as a, after[name].open('rb') as b:
                if file_digest(a, 'sha256').digest() != file_digest(b, 'sha256').digest():
                    raise ValueError('Signing changed application code or data: ' + name)
    for name, path in after.items():
        if path.suffix.lower() in NATIVE: shutil.copy2(path, before[name])
    print('Signed native files restored. Application code, design and model bytes match the original build.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--signed', type=Path, required=True)
    args = parser.parse_args()
    accept(args.original, args.signed)
