#!/usr/bin/env python3
"""원문과 재작성본의 읽기 쉬움 지표를 형태소 분석으로 재는 스크립트.

`change_rate_check.py`는 "원문과 얼마나 다른가"만 잰다. 이 스크립트는 "재작성본이
실제로 더 쉬워졌는가"를 잰다(`eval/related-work.md` 6절: 쉬운 말 규칙을 적용했다고
실제로 쉬워지는 건 아니므로 결과물을 직접 재야 한다).

지표(모두 참고 수치이며 통과/실패 기준이 아니다. 기준값은 `eval/text-metrics-baseline.md`
참고):

- 평균·최대 문장 길이(어절): 국립국어원 공공언어 진단 "용이성: 문장을 적절한 길이로
  작성하였는가"(related-work.md 7.1절)
- 적·의·것·들 빈도(100어절당): 김정선 『내 문장이 그렇게 이상한가요?』의 "적의를
  보이는 것들"
- 피동 빈도(100어절당): 동사+어지다("만들어지다", "쓰여지다"). 형용사+어지다("많아지다")는
  상태 변화라 세지 않고, 명사+되다("시작되다")는 표준 동사가 많아 세지 않는다. 명사+되어지다
  ("해결되어지다", 이중 피동)는 센다
- 명사형 어미(-기, -음) 빈도(100어절당): 명사화 문장("~함", "~하기")
- 다절 문장 수: 절을 잇는 연결어미("-고", "-는데", "-면", "-지만", "-거나" 등)가 3개 이상인
  문장 수. "-어/-아/-게/-지"와 보조용언 앞 어미는 절 연결로 보지 않는다. 자연스러운 구어체
  글에도 이런 문장이 있으므로 문장 길이와 함께 본다
- 어휘 다양성 MATTR: 생성형 AI 글이 사람 글보다 어휘 다양성이 낮다는 KCI 연구.
  떨어지지 않는지 보는 용도다
- 어려운 표현 잔존: `references/plain-vocabulary-map.md` 1열 표현의 등장 횟수
- 맞춤법 오류: 어떤 문맥에서도 틀린 표기만 모은 목록(아래 MISSPELLINGS)

Kiwi의 오타·띄어쓰기 교정 기능은 쓰지 않는다. 직접 시험해 보니 "됬다", "몇일",
"않된다"를 하나도 못 잡았고, 제대로 쓴 재작성본 172어절에서 띄어쓰기 "교정" 2건이
모두 오탐이었다("이끌어낼"→"이끌어 낼", "두어야 합니다"→"두어야합니다").

필요 패키지: kiwipiepy (pip install kiwipiepy)

사용법:
    python text_metrics.py revised.txt                # 한 글만 측정
    python text_metrics.py original.txt revised.txt   # 원문 대비 변화량
    python text_metrics.py original.txt revised.txt --json
    또는 파이썬에서 직접:
        from text_metrics import measure, compare
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

VOCAB_MAP_PATH = Path(__file__).resolve().parent.parent / "references" / "plain-vocabulary-map.md"

# 어휘 다양성은 실질 형태소로만 센다. 조사·어미까지 넣으면 문법 형태소 반복이 값을 좌우한다.
CONTENT_TAGS = {"NNG", "NNP", "VV", "VA", "MAG", "XR"}
MATTR_WINDOW = 50
# 절을 잇지 않고 동사를 가볍게 붙이는 연결어미("막아 두다", "크게", "먹지 않다").
LIGHT_CONNECTIVES = {"어", "아", "게", "지"}
MULTICLAUSE_MIN = 3

# 어떤 문맥에서도 표준 표기가 아닌 것만 넣는다. "금새"(물건값), "바램"(색이 바램)처럼
# 맞는 뜻이 따로 있는 표기는 오탐이 나므로 넣지 않는다.
MISSPELLINGS = {
    "됬": (re.compile(r"됬"), "됐"),
    "되요": (re.compile(r"되요"), "돼요"),
    "몇일": (re.compile(r"몇\s?일(?![본꾼손])"), "며칠"),
    # "하지 않되 기록은 남긴다"의 연결어미 "-되"는 맞으므로 활용형만 잡는다.
    "않되": (re.compile(r"않\s?(?:돼|된|되[는지고면어요었])"), "안 되"),
    "읍니다": (re.compile(r"읍니다"), "습니다"),
    "오랫만": (re.compile(r"오랫만"), "오랜만"),
    "왠만": (re.compile(r"왠만"), "웬만"),
    "왠(지 외)": (re.compile(r"왠(?![지만])"), "웬"),
    "어떻해": (re.compile(r"어떻해"), "어떡해 / 어떻게 해"),
    "뵈요": (re.compile(r"뵈요"), "봬요"),
    "ㄹ께": (re.compile(r"[할될줄갈올볼][께]요?(?=[\s.!?,]|$)"), "~ㄹ게"),
    "역활": (re.compile(r"역활"), "역할"),
    "희안": (re.compile(r"희안"), "희한"),
    "설겆이": (re.compile(r"설겆이"), "설거지"),
    "일일히": (re.compile(r"일일히"), "일일이"),
    "금새(곧)": (re.compile(r"금새\s?(?:끝|사라|잊|지나|잠들)"), "금세"),
}

_TRAILING_RE = re.compile(r"(?:하다|되다|이다|하는|한|의)$")
# 매핑표에 있어도 개수로 세면 오탐이 나는 것. "~바람", "~할 것"은 문장 끝 서식 표현이라
# 본문에서 세면 "바람이 분다", "할 것이다"까지 잡힌다. 영문 약어(AI, IoT 등)는 매핑표 규칙이
# "처음 나올 때 한글 풀이 병기"라서 "인공지능[AI]"처럼 바르게 쓴 경우도 잡힌다.
_UNCOUNTABLE_TERMS = {"바람", "할 것"}
_ASCII_ONLY_RE = re.compile(r"^[\x00-\x7f]+$")
_WORD_RE = re.compile(r"[가-힣A-Za-z0-9]")


@lru_cache(maxsize=1)
def _kiwi():
    try:
        from kiwipiepy import Kiwi
    except ImportError as error:
        raise RuntimeError("kiwipiepy가 없습니다. `pip install kiwipiepy`로 설치하세요.") from error
    return Kiwi()


@lru_cache(maxsize=1)
def hard_terms() -> tuple[str, ...]:
    """plain-vocabulary-map.md 매핑표 1열을 본문 검색용 어간으로 바꾼다.

    "제고하다" → "제고", "상당수의" → "상당수"처럼 활용 어미를 떼어 활용형("제고할",
    "제고해야")도 잡히게 한다. 괄호 설명과 "~"는 지운다.
    """
    if not VOCAB_MAP_PATH.exists():
        return ()
    terms: set[str] = set()
    in_table = False
    for line in VOCAB_MAP_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("| 어려운 표현"):
            in_table = True
            continue
        if not in_table or not line.startswith("|") or line.startswith("|---"):
            continue
        first = line.split("|")[1]
        for variant in first.split("/"):
            term = re.sub(r"\([^)]*\)|~", "", variant).strip()
            term = _TRAILING_RE.sub("", term).strip()
            if len(term) >= 2 and term not in _UNCOUNTABLE_TERMS and not _ASCII_ONLY_RE.match(term):
                terms.add(term)
    return tuple(sorted(terms, key=len, reverse=True))


def _eojeol_count(text: str) -> int:
    return sum(1 for token in text.split() if _WORD_RE.search(token))


def _per_100(count: int, eojeol: int) -> float:
    return round(count * 100 / eojeol, 2) if eojeol else 0.0


def mattr(lemmas: list[str], window: int = MATTR_WINDOW) -> float | None:
    """Moving-Average Type-Token Ratio (Covington & McFall 2010).

    글 길이에 따라 값이 크게 흔들리는 TTR 대신 창을 한 칸씩 밀며 TTR을 평균낸다.
    실질 형태소가 창 크기보다 적으면 그냥 TTR을 돌려준다.
    """
    if not lemmas:
        return None
    if len(lemmas) <= window:
        return round(len(set(lemmas)) / len(lemmas), 3)
    ratios = [len(set(lemmas[i:i + window])) / window for i in range(len(lemmas) - window + 1)]
    return round(statistics.mean(ratios), 3)


def connective_count(tokens: list[Any]) -> int:
    """절을 잇는 연결어미 수. 보조용언(VX) 앞의 연결어미와 LIGHT_CONNECTIVES는 뺀다."""
    return sum(
        1 for i, t in enumerate(tokens)
        if t.tag == "EC" and t.form not in LIGHT_CONNECTIVES
        and not (i + 1 < len(tokens) and tokens[i + 1].tag.startswith("VX"))
    )


def measure(text: str) -> dict[str, Any]:
    kiwi = _kiwi()
    eojeol = _eojeol_count(text)
    sentences = [s.text for s in kiwi.split_into_sents(text) if _WORD_RE.search(s.text)]
    lengths = [_eojeol_count(s) for s in sentences]
    multiclause = sum(1 for s in sentences if connective_count(kiwi.tokenize(s)) >= MULTICLAUSE_MIN)
    tokens = kiwi.tokenize(text)

    jeok = sum(1 for t in tokens if t.tag == "XSN" and t.form == "적")
    ui = sum(1 for t in tokens if t.tag == "JKG")
    geot = sum(1 for t in tokens if t.tag == "NNB" and t.form == "것")
    deul = sum(1 for t in tokens if t.tag == "XSN" and t.form == "들")
    etn = sum(1 for t in tokens if t.tag == "ETN")
    passive = sum(
        1 for stem, ending, aux in zip(tokens, tokens[1:], tokens[2:])
        if stem.tag.split("-")[0] in {"VV", "XSV"} and ending.tag == "EC" and ending.form in {"어", "아"}
        and aux.tag == "VX" and aux.form == "지"
    )
    lemmas = [t.form for t in tokens if t.tag in CONTENT_TAGS]

    # 형태소 경계에서 시작하는 것만 센다("이야기" 안의 "야기"는 제외). 긴 표현부터 세고
    # 그 구간을 표시해 "함에 있어서" 안의 "에 있어서"를 두 번 세지 않는다.
    starts = {t.start for t in tokens}
    consumed = [False] * len(text)
    hard_hits: dict[str, int] = {}
    for term in hard_terms():
        count = 0
        for match in re.finditer(re.escape(term), text):
            if match.start() in starts and not any(consumed[match.start():match.end()]):
                consumed[match.start():match.end()] = [True] * len(term)
                count += 1
        if count:
            hard_hits[term] = count

    spelling_hits: dict[str, dict[str, Any]] = {}
    for name, (pattern, fix) in MISSPELLINGS.items():
        count = len(pattern.findall(text))
        if count:
            spelling_hits[name] = {"count": count, "fix": fix}

    return {
        "eojeol": eojeol,
        "sentences": len(lengths),
        "mean_sentence_length": round(statistics.mean(lengths), 1) if lengths else None,
        "max_sentence_length": max(lengths) if lengths else None,
        "multiclause_sentences": multiclause,
        "jeok_ui_geot_deul_per_100": _per_100(jeok + ui + geot + deul, eojeol),
        "jeok_ui_geot_deul": {"적": jeok, "의": ui, "것": geot, "들": deul},
        "passive_per_100": _per_100(passive, eojeol),
        "nominal_ending_per_100": _per_100(etn, eojeol),
        "mattr": mattr(lemmas),
        "hard_terms": sum(hard_hits.values()),
        "hard_term_hits": hard_hits,
        "misspellings": sum(hit["count"] for hit in spelling_hits.values()),
        "misspelling_hits": spelling_hits,
    }


# 원문 대비 변화량을 계산할 수치 지표와, 쉬운 글이 되려면 어느 쪽으로 움직여야 하는지.
# "down": 줄어야 좋음, "keep": 크게 떨어지지만 않으면 됨.
DIRECTIONS = {
    "mean_sentence_length": "down",
    "max_sentence_length": "down",
    "multiclause_sentences": "down",
    "jeok_ui_geot_deul_per_100": "down",
    "passive_per_100": "down",
    "nominal_ending_per_100": "down",
    "mattr": "keep",
    "hard_terms": "down",
    "misspellings": "down",
}

LABELS = {
    "mean_sentence_length": "평균 문장 길이(어절)",
    "max_sentence_length": "최대 문장 길이(어절)",
    "multiclause_sentences": "다절 문장 수(연결어미 3+)",
    "jeok_ui_geot_deul_per_100": "적·의·것·들 (100어절당)",
    "passive_per_100": "피동 -어지다 (100어절당)",
    "nominal_ending_per_100": "명사형 어미 -기/-음 (100어절당)",
    "mattr": "어휘 다양성 MATTR",
    "hard_terms": "어려운 표현 잔존",
    "misspellings": "맞춤법 오류",
}


def compare(original: str, revised: str) -> dict[str, Any]:
    before = measure(original)
    after = measure(revised)
    deltas: dict[str, Any] = {}
    for key, direction in DIRECTIONS.items():
        a, b = before[key], after[key]
        if a is None or b is None:
            continue
        deltas[key] = {"before": a, "after": b, "delta": round(b - a, 3), "direction": direction}
    return {"before": before, "after": after, "deltas": deltas}


def _format_single(result: dict[str, Any]) -> str:
    lines = [f"어절 {result['eojeol']}, 문장 {result['sentences']}"]
    for key in DIRECTIONS:
        lines.append(f"{LABELS[key]}: {result[key]}")
    if result["hard_term_hits"]:
        lines.append("  어려운 표현: " + ", ".join(f"{k}×{v}" for k, v in result["hard_term_hits"].items()))
    if result["misspelling_hits"]:
        lines.append("  맞춤법: " + ", ".join(
            f"{k}×{v['count']}(→{v['fix']})" for k, v in result["misspelling_hits"].items()))
    return "\n".join(lines)


def _format_compare(result: dict[str, Any]) -> str:
    lines = [f"{'지표':<28} {'원문':>7} {'수정본':>7} {'변화':>8}"]
    for key, row in result["deltas"].items():
        delta = row["delta"]
        if row["direction"] == "down":
            mark = "좋아짐" if delta < 0 else ("같음" if delta == 0 else "나빠짐")
        else:
            mark = "유지" if delta >= -0.05 else "떨어짐"
        lines.append(f"{LABELS[key]:<28} {row['before']:>7} {row['after']:>7} {delta:>+8} {mark}")
    after = result["after"]
    if after["hard_term_hits"]:
        lines.append("남은 어려운 표현: " + ", ".join(f"{k}×{v}" for k, v in after["hard_term_hits"].items()))
    if after["misspelling_hits"]:
        lines.append("남은 맞춤법 오류: " + ", ".join(
            f"{k}×{v['count']}(→{v['fix']})" for k, v in after["misspelling_hits"].items()))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+", help="측정할 파일 1개, 또는 원문·재작성본 2개")
    parser.add_argument("--json", action="store_true", help="JSON으로 출력")
    args = parser.parse_args()
    if len(args.files) > 2:
        parser.error("파일은 1개 또는 2개만 받습니다.")

    texts = [Path(path).read_text(encoding="utf-8") for path in args.files]
    if len(texts) == 1:
        result = measure(texts[0])
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else _format_single(result))
    else:
        result = compare(*texts)
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else _format_compare(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
