#!/usr/bin/env python3
"""LLM 채점자의 점수가 전문가 점수와 얼마나 맞는지 재는 스크립트.

사람 채점자를 늘리기 어려우니 LLM 채점자를 쓰되, 그 채점자를 믿어도 되는지는 전문가가
이미 채점해 둔 글로 먼저 확인한다(`eval/related-work.md` 3절, van der Lee 외 2019의
"일치도를 실제로 계산해 보고하라"). 지표는 국립국어원 2026 AI 언어 평가 "글쓰기 채점
능력 평가" 과제가 쓰는 RMSE·Spearman에, 서열 척도 채점에서 표준인 QWK(quadratic
weighted kappa)를 더했다.

입력 JSONL 한 줄 = 글 하나의 한 채점 항목:
    {"id": "essay-001", "item": "exp_grammar",
     "experts": [2, 3, 2],   # 전문가별 점수(1명 이상)
     "judge": 2}             # LLM 채점자 점수

전문가가 2명 이상이면 "전문가끼리의 일치도"도 계산한다. LLM 채점자가 이 값에 가까우면
사람 한 명을 더 쓴 것만큼 믿을 만하다는 뜻이고, 이 값을 넘는 걸 기대하면 안 된다.

사용법:
    python judge_agreement.py scores.jsonl
    python judge_agreement.py scores.jsonl --min-score 0 --max-score 3 --json
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        average = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = average
        i = j + 1
    return ranks


def pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) < 2:
        return None
    mx, my = statistics.mean(x), statistics.mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if not sx or not sy:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def spearman(x: list[float], y: list[float]) -> float | None:
    """동순위를 평균 순위로 처리한 Spearman 상관(순위에 대한 Pearson)."""
    return pearson(_ranks(x), _ranks(y))


def rmse(x: list[float], y: list[float]) -> float | None:
    if not x:
        return None
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(x, y)) / len(x))


def qwk(x: list[int], y: list[int], low: int, high: int) -> float | None:
    """Quadratic weighted kappa (Cohen 1968). 점수는 [low, high] 정수여야 한다."""
    n = high - low + 1
    if not x or n < 2:
        return None
    observed = [[0.0] * n for _ in range(n)]
    for a, b in zip(x, y):
        observed[a - low][b - low] += 1
    total = len(x)
    row = [sum(r) for r in observed]
    col = [sum(observed[i][j] for i in range(n)) for j in range(n)]
    numerator = denominator = 0.0
    for i in range(n):
        for j in range(n):
            weight = (i - j) ** 2 / (n - 1) ** 2
            numerator += weight * observed[i][j]
            denominator += weight * row[i] * col[j] / total
    return 1 - numerator / denominator if denominator else None


def _agreement(x: list[float], y: list[float], low: int, high: int) -> dict[str, Any]:
    xi = [min(high, max(low, round(v))) for v in x]
    yi = [min(high, max(low, round(v))) for v in y]
    values = {"spearman": spearman(x, y), "rmse": rmse(x, y), "qwk": qwk(xi, yi, low, high)}
    return {key: (round(v, 3) if v is not None else None) for key, v in values.items()}


def evaluate(rows: list[dict[str, Any]], low: int, high: int) -> dict[str, Any]:
    by_item: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_item[row["item"]].append(row)
    by_item["(전체)"] = rows

    result: dict[str, Any] = {}
    for item, subset in by_item.items():
        expert_mean = [statistics.mean(r["experts"]) for r in subset]
        judge = [float(r["judge"]) for r in subset]
        entry = {"n": len(subset), "judge_vs_expert_mean": _agreement(expert_mean, judge, low, high)}
        # 전문가끼리: 가능한 모든 전문가 쌍의 일치도 평균. LLM 채점자의 현실적 상한선이다.
        rater_count = min(len(r["experts"]) for r in subset)
        if rater_count >= 2:
            pair_scores = [
                _agreement([r["experts"][a] for r in subset], [r["experts"][b] for r in subset], low, high)
                for a, b in itertools.combinations(range(rater_count), 2)
            ]
            entry["expert_vs_expert"] = {
                key: round(statistics.mean(p[key] for p in pair_scores if p[key] is not None), 3)
                if any(p[key] is not None for p in pair_scores) else None
                for key in ("spearman", "rmse", "qwk")
            }
        result[item] = entry
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scores", help="채점 JSONL")
    parser.add_argument("--min-score", type=int, default=0)
    parser.add_argument("--max-score", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    rows = [json.loads(line) for line in Path(args.scores).read_text(encoding="utf-8").splitlines() if line.strip()]
    result = evaluate(rows, args.min_score, args.max_score)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"{'항목':<18} {'n':>5}   {'LLM↔전문가 Spearman/RMSE/QWK':<32} {'전문가↔전문가 Spearman/RMSE/QWK'}")
    for item, entry in result.items():
        j = entry["judge_vs_expert_mean"]
        e = entry.get("expert_vs_expert")
        judge_text = f"{j['spearman']} / {j['rmse']} / {j['qwk']}"
        expert_text = f"{e['spearman']} / {e['rmse']} / {e['qwk']}" if e else "-"
        print(f"{item:<18} {entry['n']:>5}   {judge_text:<32} {expert_text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
