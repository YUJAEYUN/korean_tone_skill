#!/usr/bin/env python3
"""서로 다른 원문들이 재작성 뒤 서로 더 비슷해지는지(문체 획일화)를 재는 스크립트.

Padmakumar & He, "Does Writing with Language Models Reduce Content Diversity?"
(ICLR 2024)는 LLM과 함께 쓴 글들이 서로 더 비슷해진다는 것을 보였다. 이 스크립트는 그
생각을 문체에 적용한다. 설계 원칙 6("글쓴이의 목소리를 평준화하지 않는다")을 수치로
확인하려는 것이다.

측정 방법(우리 자체 설계이며 한국어 문체 획일화 지표로 검증된 것은 아니다):

- 글마다 문법 형태소(조사 J*, 연결어미 EC, 종결어미 EF, 선어말어미 EP, 전성어미 ET*)의
  "형태/품사" 상대빈도 벡터를 만든다. 실질 형태소(명사·동사 어간)를 빼서 주제 차이가
  유사도에 섞이지 않게 한다. 반말 "~거든", 해요체 "~요", 합쇼체 "~습니다"처럼 말투는
  이 벡터에 그대로 드러난다.
- 원문들끼리의 평균 쌍별 코사인 유사도(source_similarity)와, 같은 시스템이 고친 글들끼리의
  평균 쌍별 유사도(output_similarity)를 비교한다.
- homogenization = output_similarity - source_similarity. 0보다 크면 재작성 뒤 글들이
  서로 더 비슷해졌다는 뜻이다. 시스템끼리(naive vs champion 등) 비교하는 용도다.

사용법:
    python homogenization.py --cases eval/cases/validation.jsonl \\
        --outputs eval/runs/<run>/outputs.jsonl
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from text_metrics import _kiwi  # noqa: E402  (같은 Kiwi 인스턴스를 재사용)

GRAMMATICAL_PREFIXES = ("J", "EC", "EF", "EP", "ET")


def style_profile(text: str) -> Counter[str]:
    tokens = _kiwi().tokenize(text)
    grams = [f"{t.form}/{t.tag}" for t in tokens if t.tag.startswith(GRAMMATICAL_PREFIXES)]
    total = len(grams) or 1
    return Counter({key: count / total for key, count in Counter(grams).items()})


def cosine(a: Counter[str], b: Counter[str]) -> float:
    dot = sum(a[key] * b[key] for key in a.keys() & b.keys())
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return dot / norm if norm else 0.0


def mean_pairwise(profiles: list[Counter[str]]) -> float | None:
    pairs = list(itertools.combinations(profiles, 2))
    if not pairs:
        return None
    return statistics.mean(cosine(a, b) for a, b in pairs)


def homogenization(cases: dict[str, str], outputs: list[dict[str, Any]]) -> dict[str, Any]:
    """시스템·trial별로 원문 대비 쌍별 문체 유사도 변화를 계산한다.

    trial마다 따로 계산한 뒤 평균낸다. 같은 사례의 다른 trial끼리는 비교하지 않는다.
    """
    source_profiles = {case_id: style_profile(text) for case_id, text in cases.items()}
    grouped: dict[tuple[str, int], dict[str, str]] = defaultdict(dict)
    for row in outputs:
        if row["system"] != "source" and row["case_id"] in cases and row.get("output"):
            grouped[(row["system"], row["trial"])][row["case_id"]] = row["output"]

    per_system: dict[str, list[dict[str, float]]] = defaultdict(list)
    for (system, trial), texts in sorted(grouped.items()):
        ids = sorted(texts)
        source_sim = mean_pairwise([source_profiles[i] for i in ids])
        output_sim = mean_pairwise([style_profile(texts[i]) for i in ids])
        if source_sim is None or output_sim is None:
            continue
        per_system[system].append({
            "trial": trial, "cases": len(ids),
            "source_similarity": source_sim, "output_similarity": output_sim,
            "homogenization": output_sim - source_sim,
        })

    summary = {}
    for system, rows in per_system.items():
        summary[system] = {
            "trials": len(rows),
            "cases": rows[0]["cases"],
            "source_similarity": round(statistics.mean(r["source_similarity"] for r in rows), 4),
            "output_similarity": round(statistics.mean(r["output_similarity"] for r in rows), 4),
            "homogenization": round(statistics.mean(r["homogenization"] for r in rows), 4),
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", required=True, help="사례 JSONL (id, input)")
    parser.add_argument("--outputs", required=True, help="하네스 outputs.jsonl")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cases = {}
    for line in Path(args.cases).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            cases[row["id"]] = row["input"]
    outputs = [json.loads(line) for line in Path(args.outputs).read_text(encoding="utf-8").splitlines() if line.strip()]
    summary = homogenization(cases, outputs)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    print(f"{'시스템':<12} {'사례':>4} {'원문끼리':>8} {'결과끼리':>8} {'획일화':>8}")
    for system, row in sorted(summary.items()):
        print(f"{system:<12} {row['cases']:>4} {row['source_similarity']:>8.3f} "
              f"{row['output_similarity']:>8.3f} {row['homogenization']:>+8.3f}")
    print("\n획일화 > 0: 고친 글끼리 원문끼리보다 말투가 더 비슷해짐(목소리 평준화 신호).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
