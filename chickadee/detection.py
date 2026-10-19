"""Explainable, deliberately small rule set. No remote inference or credentials."""

import re
import unicodedata

LABELS = {
    "HOMOGLYPH": "닮은꼴 글자 위장",
    "JAMO": "자모 분해",
    "TRANSPARENT": "투명 텍스트",
    "OFFSCREEN": "화면 밖 은닉",
}

# Canonical compatibility jamo lets decomposed syllables and typed jamo compare
# equally, including final consonants (e.g. 슬롯 -> ㅅㅡㄹㄹㅗㅅ).
LEADS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
VOWELS = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
TAILS = "ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"
JAMO_MAP = dict(zip(map(chr, range(0x1100, 0x1113)), LEADS))
JAMO_MAP.update(zip(map(chr, range(0x1161, 0x1176)), VOWELS))
JAMO_MAP.update(zip(map(chr, range(0x11A8, 0x11C3)), TAILS))
LOOKALIKES = str.maketrans({
    "а": "a", "А": "A", "е": "e", "Е": "E", "о": "o", "О": "O",
    "р": "p", "Р": "P", "с": "c", "С": "C", "у": "y", "У": "Y",
    "х": "x", "Х": "X", "і": "i", "І": "I", "ј": "j", "Ј": "J",
    "ѕ": "s", "Ѕ": "S", "к": "k", "К": "K", "м": "m", "М": "M",
    "т": "t", "Т": "T", "в": "b", "В": "B", "н": "h", "Н": "H",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I",
    "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T",
    "Υ": "Y", "Χ": "X", "ο": "o", "ι": "i", "ϲ": "c",
})
DIGITS = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t"})


def skeleton(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text).casefold()
    return "".join(JAMO_MAP.get(c, c) for c in decomposed if c.isalnum())


KEYWORDS = tuple(map(skeleton, (
    "카지노", "casino", "슬롯", "slot", "토토", "toto", "바카라", "baccarat",
    "먹튀검증", "안전놀이터", "도박", "성인방송", "성인사이트", "성인물", "야동", "porn", "betting", "mega bet",
)))
PREVENTION = tuple(map(skeleton, ("예방", "신고", "주의", "근절", "금지", "단속", "차단", "피해상담")))
PROMOTION = tuple(map(skeleton, (
    "가입", "보너스", "첫충", "충전", "입금", "지급", "추천코드", "바로가기", "무료", "텔레그램",
    "bonus", "signup", "join", "free", "bet now",
)))
JAMO_RE = re.compile(r"[\u1100-\u11ff\u3130-\u318f\ua960-\ua97f\ud7b0-\ud7ff]")


def is_advertisement(text: str) -> bool:
    normalized = skeleton(unicodedata.normalize("NFKC", text).translate(LOOKALIKES))
    variants = (normalized, skeleton(unicodedata.normalize("NFKC", text).translate(LOOKALIKES).translate(DIGITS)))
    if not any(term in variant for variant in variants for term in KEYWORDS):
        return False
    # Educational/warning text is common on public sites. These are heuristic
    # exclusions, not a legal judgement or a comprehensive semantic classifier.
    if any(term in normalized for term in PREVENTION):
        return False
    return any(term in normalized for term in PROMOTION) or len(normalized) < 160


def techniques(text: str, transparent: bool = False, offscreen: bool = False) -> list[str]:
    if not is_advertisement(text):
        return []
    normalized = unicodedata.normalize("NFKC", text)
    changed_letters = any(
        c.translate(LOOKALIKES) != c or
        (unicodedata.normalize("NFKC", c) != c and not JAMO_RE.match(c)
         and any("a" <= t.casefold() <= "z" for t in unicodedata.normalize("NFKC", c)))
        for c in text
    )
    digits_needed = not any(k in skeleton(normalized.translate(LOOKALIKES)) for k in KEYWORDS)
    codes = []
    if changed_letters or (digits_needed and any(c in "013457" for c in normalized)):
        codes.append("HOMOGLYPH")
    if JAMO_RE.search(text):
        codes.append("JAMO")
    if transparent:
        codes.append("TRANSPARENT")
    if offscreen:
        codes.append("OFFSCREEN")
    return codes


def classify_elements(elements: list[dict], inherited: dict | None = None) -> list[dict]:
    inherited = inherited or {}
    hits = []
    by_id = {e["node_id"]: e for e in elements}
    for element in elements:
        transparent = element["transparent"] or inherited.get("transparent", False)
        offscreen = element["offscreen"] or inherited.get("offscreen", False)
        for code in techniques(element["text"], transparent, offscreen):
            hits.append({**element, "technique": code})
    # Prefer the smallest owner of the evidence. A wrapper containing several
    # independently classified descendants must not inflate the finding count.
    ancestors_with_hit = set()
    for hit in hits:
        parent = hit["parent_id"]
        while parent is not None and parent in by_id:
            ancestors_with_hit.add((parent, hit["technique"]))
            parent = by_id[parent]["parent_id"]
    return [h for h in hits if (h["node_id"], h["technique"]) not in ancestors_with_hit
            or h["technique"] in techniques(h["direct_text"],
                h["transparent"] or inherited.get("transparent", False),
                h["offscreen"] or inherited.get("offscreen", False))]
