"""Explainable, deliberately small rule set. No remote inference or credentials."""

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path

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


JAMO_RE = re.compile(r"[\u1100-\u11ff\u3130-\u318f\ua960-\ua97f\ud7b0-\ud7ff]")


@dataclass(frozen=True)
class Rules:
    version: str
    keywords: tuple[str, ...]
    prevention: tuple[str, ...]
    promotion: tuple[str, ...]

    @classmethod
    def load(cls, path: Path | None = None):
        path = Path(path or Path(__file__).with_name("rules.json"))
        if path.stat().st_size > 1_000_000:
            raise ValueError("탐지 규칙 파일은 1MB 이하여야 합니다.")
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or set(data) != {"version", "keywords", "prevention", "promotion"}:
            raise ValueError("규칙 파일에는 version, keywords, prevention, promotion이 필요합니다.")
        if not isinstance(data["version"], str):
            raise ValueError("규칙 version은 문자열이어야 합니다.")
        for key in ("keywords", "prevention", "promotion"):
            if not isinstance(data[key], list) or len(data[key]) > 1000 or not all(isinstance(t, str) and 0 < len(t) <= 100 and skeleton(t) for t in data[key]):
                raise ValueError(f"{key}는 100자 이하 문자열의 배열(최대 1000개)이어야 합니다.")
        if not data["keywords"]:
            raise ValueError("keywords는 비워둘 수 없습니다.")
        return cls(data["version"], *(tuple(data[k]) for k in ("keywords", "prevention", "promotion")))


DEFAULT_RULES = Rules.load()


def _canonical(text, digits=False):
    result, flags = [], []
    # A Latin r resembles the vowel in ㅋr/ㅂr only in this Hangul context.
    # Do not globally turn an ordinary English r into a Hangul vowel.
    mixed = set()
    for i in range(len(text) - 2):
        if text[i] in LEADS and text[i + 1] in "rR" and (JAMO_RE.match(text[i + 2]) or '\uac00' <= text[i + 2] <= '\ud7a3'):
            mixed.update((i, i + 1))
    for index, char in enumerate(text):
        mapped = unicodedata.normalize("NFKC", char).translate(LOOKALIKES)
        if index in mixed and char in "rR":
            mapped = "ㅏ"
        if digits:
            mapped = mapped.translate(DIGITS)
        fragment = skeleton(mapped)
        is_jamo = index not in mixed and bool(JAMO_RE.match(char))
        is_glyph = index in mixed or (not is_jamo and mapped.casefold() != char.casefold() and any('a' <= c <= 'z' for c in mapped.casefold()))
        result.extend(fragment)
        flags.extend([(is_glyph, is_jamo, index)] * len(fragment))
    return "".join(result), flags


@lru_cache(maxsize=256)
def analyze(text: str, rules: Rules | None = None) -> dict:
    """Attach obfuscation only to characters inside an actual keyword match."""
    rules = rules or DEFAULT_RULES
    matches, contexts = [], []
    boundaries = [m.start() for m in re.finditer(r"[\n!?;。！？]|\.(?=\s|$)", text)]
    for digits in (False, True):
        normalized, flags = _canonical(text, digits)
        for keyword in rules.keywords:
            needle = skeleton(keyword)
            for match in re.finditer(re.escape(needle), normalized):
                start, end = match.span()
                first, last = flags[start][2], flags[end - 1][2]
                # Avoid matching English keywords in ordinary words (timeslot).
                if needle.isascii() and ((first and 'a' <= text[first - 1].casefold() <= 'z') or (last + 1 < len(text) and 'a' <= text[last + 1].casefold() <= 'z')):
                    continue
                before = max((n for n in boundaries if n < first), default=-1)
                after = min((n for n in boundaries if n > last), default=len(text))
                before, after = max(before, first - 161), min(after, last + 161)
                context = skeleton(text[before + 1:after].translate(LOOKALIKES))
                if any(skeleton(term) in context for term in rules.prevention):
                    continue
                # A topic alone is also a book title, place name, brand or lesson.
                # Require a local promotional signal, even for short text.
                if not any(skeleton(term) in context for term in rules.promotion):
                    continue
                contexts.append((before + 1, after))
                matches.append({"keyword": keyword, "source_span": [first, last + 1],
                                "homoglyph": any(f[0] for f in flags[start:end]),
                                "jamo": any(f[1] for f in flags[start:end])})
    unique = {tuple(m["source_span"]) + (m["keyword"],): m for m in reversed(matches)}
    contextual = []
    for token in re.finditer(r"[^\W_]+", text):
        raw = token.group()
        if skeleton(raw.translate(LOOKALIKES)) != 'com' or raw.isascii():
            continue
        if any(start <= token.start() and token.end() <= end for start, end in contexts):
            contextual.append({"source_span": list(token.span()), "original": raw,
                               "canonical": "com", "reason": "같은 문장 내 광고 키워드·권유 문맥의 닮은꼴 COM 표기"})
    return {"is_advertisement": bool(matches), "matches": list(unique.values()),
            "contextual_homoglyphs": contextual, "rules_version": rules.version}


def is_advertisement(text: str) -> bool:
    return analyze(text)["is_advertisement"]


def techniques(text: str, transparent: bool = False, offscreen: bool = False, rules: Rules | None = None) -> list[str]:
    analysis = analyze(text, rules)
    if not analysis["is_advertisement"]:
        return []
    codes = []
    if any(m["homoglyph"] for m in analysis["matches"]) or analysis["contextual_homoglyphs"]:
        codes.append("HOMOGLYPH")
    if any(m["jamo"] for m in analysis["matches"]):
        codes.append("JAMO")
    if transparent:
        codes.append("TRANSPARENT")
    if offscreen:
        codes.append("OFFSCREEN")
    return codes


def classify_elements(elements: list[dict], inherited: dict | None = None, rules: Rules | None = None) -> list[dict]:
    inherited = inherited or {}
    hits = []
    by_id = {e["node_id"]: e for e in elements}
    for element in elements:
        transparent = element["transparent"] or inherited.get("transparent", False)
        offscreen = element["offscreen"] or inherited.get("offscreen", False)
        for code in techniques(element["text"], transparent, offscreen, rules):
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
                h["offscreen"] or inherited.get("offscreen", False), rules)]
