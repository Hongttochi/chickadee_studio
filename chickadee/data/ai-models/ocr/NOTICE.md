Korean OCR recognizer

Base: PaddlePaddle korean_PP-OCRv5_mobile_rec, Apache-2.0.
Fine-tuned on synthetic Korean text with separated text, font and template groups.
The detector remains the official PP-OCRv5 mobile detector. Runtime is offline CPU.

Two candidates were selected using 2,000 validation samples. On a small real Korean
recognition audit (20 text regions, 8 images, 287 reference characters), the same
inference pipeline produced 30 character errors with the official recognizer and
10 with this recognizer. This is not a general Korean OCR accuracy estimate or a
detector recall measurement. The full detector/recognizer pipeline also passed
two Korean fixtures and two previously collected page images.

Exact inference file hashes, training summary and audit scope: manifest.json.
No raw research images or training corpora are redistributed here.
