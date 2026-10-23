"""Local resource recommendations and an offline OCR capability probe."""
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import platform
import struct
import sys
import zlib
from .image_ocr import MAX_UNIQUE_IMAGES

MODES = ('auto', 'standard', 'economy')
GIB = 1024**3


def memory_info():
    if sys.platform == 'win32':
        import ctypes
        class Status(ctypes.Structure):
            _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                        *[(n, ctypes.c_ulonglong) for n in ('total', 'available', 'page_total', 'page_available', 'virtual_total', 'virtual_available', 'extended')]]
        status = Status(); status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return {'total_bytes': status.total, 'available_bytes': status.available}
    try:
        size = os.sysconf('SC_PAGE_SIZE')
        return {'total_bytes': size * os.sysconf('SC_PHYS_PAGES'), 'available_bytes': size * os.sysconf('SC_AVPHYS_PAGES')}
    except (AttributeError, OSError, ValueError):
        return {'total_bytes': None, 'available_bytes': None}


def available_features():
    from .local_ai import model
    features = {}
    for kind in ('text', 'visual'):
        try: model(kind); features[kind] = True
        except Exception: features[kind] = False
    root = Path(__file__).resolve().parents[1]
    models = root / ('ocr-models' if getattr(sys, 'frozen', False) else 'artifacts/ocr-models')
    try:
        manifest = json.loads((root / 'chickadee/data/ocr-models.json').read_text(encoding='utf-8'))
        features['ocr'] = bool(importlib.util.find_spec('paddle')) and all(
            (models / f['path']).is_file() and (models / f['path']).stat().st_size == f['bytes'] for f in manifest['files'])
    except (OSError, ValueError, KeyError, ImportError): features['ocr'] = False
    return features


def environment(mode='auto'):
    if mode not in MODES: raise ValueError('실행 모드는 auto, standard, economy 중 하나입니다.')
    memory = memory_info(); cores = os.cpu_count() or 1
    reasons = []
    if cores < 2: reasons.append('논리 CPU 2개 미만')
    if memory['total_bytes'] is not None and memory['total_bytes'] < 4 * GIB: reasons.append('전체 메모리 4GB 미만')
    if memory['available_bytes'] is not None and memory['available_bytes'] < 1.5 * GIB: reasons.append('사용 가능 메모리 1.5GB 미만')
    recommended = 'economy' if reasons else 'standard'
    effective = recommended if mode == 'auto' else mode
    features = available_features()
    return {'mode': mode, 'effective_mode': effective, 'recommended_mode': recommended, 'reasons': reasons,
            'checked_at': datetime.now().astimezone().isoformat(),
            'hardware': {'os': platform.system(), 'architecture': platform.machine(), 'process_bits': struct.calcsize('P')*8,
                         'logical_cpus': cores, **memory},
            'features': {'required_detection': True, 'text_ai': features['text'], 'visual_ai': features['visual'],
                         'ocr_available': features['ocr'], 'ocr_enabled': effective == 'standard' and features['ocr']},
            # Images are processed sequentially. A smaller count does not reduce
            # model resident memory, but silently drops later post attachments.
            'ocr_max_images': MAX_UNIQUE_IMAGES if effective == 'standard' else 10,
            'inference_device': 'cpu', 'paid_requests': 0}


def probe_png():
    """Own 64px blank image; capability check without files, sites or user content."""
    def chunk(kind, value):
        return struct.pack('!I', len(value)) + kind + value + struct.pack('!I', zlib.crc32(kind+value))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 64, 64, 8, 2, 0, 0, 0)) + chunk(
        b'IDAT', zlib.compress((b'\0'+b'\xff'*64*3)*64)) + chunk(b'IEND', b'')
