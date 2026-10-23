"""Create looping service demos from the actual desktop recording, without adding UI frames."""
import argparse
import json
from pathlib import Path
import shutil

import cv2
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def read_frames(video, start, end, width=1120):
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        raise ValueError(f'Cannot read recording: {video}')
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(start * fps))
    frames = []
    for _ in range(max(1, round((end - start) * fps))):
        ok, frame = cap.read()
        if not ok:
            break
        height = round(frame.shape[0] * width / frame.shape[1])
        frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
        frames.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
    cap.release()
    if not frames:
        raise ValueError(f'Empty recording interval: {start}..{end}')
    return frames, round(1000 / fps)


def animated_webp(frames, duration, target):
    frames[0].save(target, save_all=True, append_images=frames[1:], duration=duration,
                   loop=0, quality=85, method=4)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recording', type=Path, default=ROOT / 'artifacts/service-recording')
    args = parser.parse_args()
    source = args.recording
    output = ROOT / 'docs/assets/demos'
    data = json.loads((source / 'recording.json').read_text(encoding='utf-8'))
    if data['status'] != 'passed' or data['laya']['analyzed'] < 1 or data['paid_requests']:
        raise ValueError('A successful local pipeline recording is required')
    intervals = {segment['name']: segment for segment in data['segments']}
    plan = [('stage-01-target', '01-target'), ('stage-02-exploration', '06-graph'),
            ('stage-03-detection', '03-detection'), ('stage-04-ocr', '04-ocr'),
            ('stage-05-analysis', '05-analysis'), ('stage-06-groq', '07-groq'),
            ('stage-07-report', '08-report')]
    clips, manifest = {}, []
    for filename, name in plan:
        segment = intervals[name]
        frames, duration = read_frames(source / 'service.webm', segment['start'], segment['end'])
        animated_webp(frames, duration, output / (filename + '.webp'))
        clips[filename] = frames
        manifest.append({'asset': filename + '.webp', 'source_segment': name, 'frames': len(frames),
                         'duration_ms': duration, 'loop': 0})
    overview = []
    for name in ('stage-04-ocr', 'stage-05-analysis', 'stage-03-detection',
                 'stage-02-exploration', 'stage-06-groq', 'stage-07-report'):
        overview.extend(frame.copy() for frame in clips[name][2:14])
    animated_webp(overview, 250, output / 'overview.webp')
    palette = [frame.quantize(colors=128, method=Image.Quantize.FASTOCTREE) for frame in overview]
    palette[0].save(output / 'overview.gif', save_all=True, append_images=palette[1:], duration=250,
                    loop=0, disposal=2, optimize=True)
    for filename in ('01-pipeline.png','02-statistics.png','03-groq-report.png','05-report-saved.png',
                     '22-four-techniques.png','23-ocr-boxes.png','24-ocr-line.png'):
        shutil.copy2(source / filename, output / filename)
    shutil.copy2(source / '02-statistics.png', output / '25-ocr-statistics.png')
    shutil.copy2(source / 'service.webm', output / 'service.webm')
    (output / 'service-media.json').write_text(json.dumps({'source':'service.webm','fps':4,
        'local_verification':{k:data[k] for k in ['ocr','laya','mandatory_techniques','delayed_comment_detected','paid_requests']},
        'clips':manifest}, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    print('Generated seven stage clips, overview.webp, overview.gif and matched screenshots.')


if __name__ == '__main__':
    main()
