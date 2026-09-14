#!/usr/bin/env python3
"""Reproducible, provider-neutral evaluation harness for korean-plain-writer.

The harness deliberately does not call an LLM provider. It prepares versioned runs,
performs deterministic preservation checks, creates blinded pairwise ballots, and
aggregates votes under a promotion policy. Generation and model grading can happen
in any environment as long as they emit the documented JSONL records.

Also reused (via --skill-root) by korean-writing-orchestrator/eval/ for its
composition-quality evaluation -- this script has no korean-plain-writer-specific
paths baked in, so pointing --skill-root/--cases/--policy at a sibling skill is
the intended way to share it rather than forking a copy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable


SYSTEMS = ("source", "naive", "champion", "challenger")
NUMBER_RE = re.compile(r"(?<!\w)\d[\d,]*(?:\.\d+)?(?:%|퍼센트)?")
QUOTE_RE = re.compile(r'["“”]([^"“”]+)["“”]')

# Deterministic, code-level Korean AI-tell / grammar checks. Each pattern is
# taken as-is from vendor/humanizer/references (translation-ese-patterns.md,
# punctuation-patterns.md) rather than invented here -- see that catalog for
# the evidence, exceptions, and rationale behind each one. Only patterns with
# a narrow, well-documented "자연스러운 경우" exception list are included, to
# keep the false-positive rate low enough to run unattended in a harness.
# "이중피동" is a genuine grammar error (비문); the rest are style/translation-ese
# signals, which is why they stay advisory (see GRAMMAR_PATTERNS[*].severity)
# rather than counting as a critical_failure.
GRAMMAR_PATTERNS: dict[str, dict[str, Any]] = {
    "이중피동": {
        # "지다"가 뒤에 오는 어미의 받침을 흡수하며 지/진/질/집/졌/져로 표면형이
        # 바뀌므로(생성되어진다, 분석되어집니다 등) 순수 "되어지" 부분 문자열만으로는
        # 활용형 대부분을 놓친다. 흔한 활용 음절을 문자 클래스로 함께 잡는다.
        "regex": re.compile(r"되어[지진질집졌져]"),
        "severity": "S1",
        "threshold": 1,
        "note": "패턴 31: '~되다'에 '~어지다'를 다시 붙인 이중 피동. 표준 문법상 비문.",
    },
    "에_있어서": {
        "regex": re.compile(r"에\s*있어서?"),
        "severity": "S1",
        "threshold": 1,
        "note": "패턴 27: 일본어 차용 격식투. 거의 모든 경우 '~에서'로 환원 가능.",
    },
    "가지고_있다": {
        "regex": re.compile(r"가지고\s*있"),
        "severity": "S1",
        "threshold": 1,
        "note": "패턴 30: 영어 have의 직역. 형용사나 '~이/가 있다'로 환원 가능한 경우가 대부분.",
    },
    "에_대해_남발": {
        "regex": re.compile(r"에\s*대해서?"),
        "severity": "S2",
        "threshold": 3,
        "note": "패턴 25: 영어 about/regarding 직역. 목적격 조사로 직결 가능한 경우가 많음.",
    },
    "통해_남발": {
        "regex": re.compile(r"[을를]\s*통(?:해|하여)"),
        "severity": "S2",
        "threshold": 3,
        "note": "패턴 26: 영어 through/via 직역. '~로', '~해서' 등으로 분산 가능.",
    },
    "관련하여_남발": {
        "regex": re.compile(r"[와과]\s*관련(?:하여|된|하는)"),
        "severity": "S2",
        "threshold": 3,
        "note": "패턴 28: 영어 in relation to 직역. 직접 결합('교육 정책')으로 환원 가능.",
    },
    "기반_바탕_남발": {
        "regex": re.compile(r"에\s*기반(?:하여|한|해)|을\s*바탕으로"),
        "severity": "S2",
        "threshold": 2,
        "note": "패턴 29: 영어 based on 직역. '~로', '~을 보고' 등으로 분산 가능.",
    },
    "에_의해_피동": {
        "regex": re.compile(r"에\s*의(?:해|하여)"),
        "severity": "S2",
        "threshold": 3,
        "note": "패턴 32: 영어 수동태 by 직역. 행위자를 주어로 한 능동이 대개 더 자연스러움.",
    },
    "라는_점에서": {
        "regex": re.compile(r"라는\s*점에서"),
        "severity": "S2",
        "threshold": 3,
        "note": "패턴 36: 영어 in that 직역. 연결어미 '~서'로 환원 가능한 경우가 많음.",
    },
    "연결어미_뒤_쉼표": {
        "regex": re.compile(r"(?:고|아서|어서|지만|면서|며|는데|ㄴ데),"),
        "severity": "S2",
        "threshold": 3,
        "note": "패턴 3 (KatFishNet 94.88% AUC): 한국어 연결어미는 이미 절 관계를 나타내 쉼표가 불필요.",
    },
    "줄표_과다": {
        "regex": re.compile(r"—"),
        "severity": "S2",
        "threshold": 1,
        "note": "패턴 6: 영어식 강조 줄표. 한국어 글쓰기에서는 드묾, 괄호나 문장 나누기가 대안.",
    },
}


def scan_grammar_patterns(text: str) -> dict[str, Any]:
    """Deterministically count vendor/humanizer AI-tell patterns in `text`.

    Returns per-pattern counts plus which ones cross their documented
    threshold (S1: any occurrence, S2: 3+ unless noted otherwise). This is a
    diagnostic signal, not a preservation check, so callers should treat it
    as advisory rather than folding it into critical_failures -- the source
    catalog itself lists narrow "자연스러운 경우" exceptions a regex can't see.
    """
    findings: dict[str, Any] = {}
    triggered: list[str] = []
    for name, spec in GRAMMAR_PATTERNS.items():
        count = len(spec["regex"].findall(text))
        hit = count >= spec["threshold"]
        findings[name] = {
            "count": count, "severity": spec["severity"],
            "threshold": spec["threshold"], "hit": hit, "note": spec["note"],
        }
        if hit:
            triggered.append(name)
    return {"advisory": True, "triggered": triggered, "patterns": findings}


# Structural/rhythm signals for composition-quality evaluation (used by
# korean-writing-orchestrator/eval/, opt-in via policy.json's
# "scan_composition_patterns" so korean-plain-writer's existing checks are
# unaffected). These target a different axis than GRAMMAR_PATTERNS: not "is
# this phrase translation-ese" but "does this read with a human's uneven
# rhythm, or a model's metronomic one." See
# korean-writing-orchestrator/eval/product-contract.md for the reasoning.
SENTENCE_SPLIT_RE = re.compile(r"[.!?]+(?:\s|$)")
CLICHE_OPENERS = [
    re.compile(r"^\s*오늘날\s*우리는"),
    re.compile(r"^\s*현대\s*사회에서는"),
    re.compile(r"^\s*바야흐로"),
]
CLICHE_CLOSERS = [
    re.compile(r"이처럼[^.!?]*(?:알\s*수\s*있었다|볼\s*수\s*있었다)\s*\.?\s*$"),
    re.compile(r"이렇듯[^.!?]*(?:알\s*수\s*있었다|볼\s*수\s*있었다)\s*\.?\s*$"),
]


def sentence_lengths(text: str) -> list[int]:
    """Word count (어절, whitespace-delimited tokens) per sentence.

    AI-text-detection writeups on "burstiness" (e.g. GPTZero-style tools)
    measure sentence length in words, not characters -- a human academic
    sample reported sentence-length stdev of 8.2 words vs 4.1 for GPT-4o
    output. 어절 count is the standard proxy for "words" in Korean when no
    real morphological tokenizer is available.
    """
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
    return [len(normalize_text(s).split()) for s in sentences]


def rhythm_stats(text: str) -> dict[str, Any]:
    """Sentence-length variation across a text (a burstiness proxy).

    No pass/fail threshold yet -- this is diagnostic only, like change_ratio
    was before change-rate-baseline.md calibrated it against 45 real
    examples.

    Reports two related numbers:
    - coefficient_of_variation (stdev/mean): easy to read, but unbounded and
      conflates "evenly short" with "evenly medium" -- the
      2026-09-14-champion-vs-naive orchestrator pilot hit exactly this: a
      terse, well-written champion output scored LOWER CV than a padded
      naive one, the opposite of what "AI is more metronomic" predicts.
    - burstiness (Goh & Barabási 2008, Phys. Rev. E 94, 032311):
      B = (stdev - mean) / (stdev + mean), bounded to [-1, 1]. B -> -1 for
      perfectly regular spacing, B = 0 for Poisson-random, B -> 1 for
      extremely bursty. Originally defined for inter-event time gaps, not
      sentence lengths within one short document -- applying it here is our
      own adaptation, not itself a validated Korean-AI-text signal the way
      the vendor/humanizer punctuation patterns are (those cite a measured
      94.88% AUC; this doesn't). Report `mean_length` alongside both numbers
      so a reader isn't left guessing whether a low burstiness score means
      "suspiciously uniform" or just "consistently short and fine."
    """
    lengths = sentence_lengths(text)
    if len(lengths) < 3:
        return {
            "sentence_count": len(lengths), "mean_length": None, "stdev": None,
            "coefficient_of_variation": None, "burstiness": None,
            "note": "문장이 3개 미만이라 리듬 변동을 측정하기엔 표본이 너무 작음",
        }
    mean = statistics.mean(lengths)
    stdev = statistics.stdev(lengths)
    return {
        "sentence_count": len(lengths),
        "mean_length": round(mean, 1),
        "stdev": round(stdev, 1),
        "coefficient_of_variation": round(stdev / mean, 3) if mean else None,
        "burstiness": round((stdev - mean) / (stdev + mean), 3) if (stdev + mean) else None,
    }


def scan_composition_cliches(text: str) -> dict[str, Any]:
    """Flag stock essay openers/closers already named in genre-rules.md.

    Narrow, fixed-phrase matches only (no general "is this a cliche" NLP) to
    keep false positives low. Advisory, same reasoning as GRAMMAR_PATTERNS.
    """
    opener_hit = any(pattern.search(text) for pattern in CLICHE_OPENERS)
    closer_hit = any(pattern.search(text.strip()) for pattern in CLICHE_CLOSERS)
    triggered = [name for name, hit in (("상투적_도입", opener_hit), ("상투적_마무리", closer_hit)) if hit]
    return {"advisory": True, "triggered": triggered, "opener_hit": opener_hit, "closer_hit": closer_hit}


class HarnessError(ValueError):
    pass


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise HarnessError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise HarnessError(f"{path}:{line_number}: each row must be an object")
            rows.append(value)
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root)
        if relative.parts[:2] == ("eval", "runs") or "__pycache__" in relative.parts:
            continue
        digest.update(str(relative).encode())
        digest.update(sha256_file(path).encode())
    return digest.hexdigest()


def git_revision(cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cwd, check=True,
            capture_output=True, text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def validate_cases(rows: list[dict[str, Any]], expected_split: str | None = None) -> None:
    required = {
        "id", "split", "genre", "register", "source_quality",
        "instruction", "input", "must_preserve", "risk_tags",
    }
    allowed_quality = {"ai_heavy", "mixed", "natural"}
    seen: set[str] = set()
    errors: list[str] = []
    for index, row in enumerate(rows, 1):
        missing = sorted(required - row.keys())
        if missing:
            errors.append(f"row {index}: missing {', '.join(missing)}")
            continue
        case_id = row["id"]
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"row {index}: id must be a non-empty string")
        elif case_id in seen:
            errors.append(f"row {index}: duplicate id {case_id}")
        seen.add(case_id)
        if expected_split and row["split"] != expected_split:
            errors.append(f"{case_id}: expected split {expected_split}, got {row['split']}")
        if row["source_quality"] not in allowed_quality:
            errors.append(f"{case_id}: invalid source_quality {row['source_quality']}")
        for field in ("instruction", "input", "genre", "register"):
            if not isinstance(row[field], str) or not row[field].strip():
                errors.append(f"{case_id}: {field} must be a non-empty string")
        for field in ("must_preserve", "risk_tags"):
            if not isinstance(row[field], list) or not all(isinstance(x, str) for x in row[field]):
                errors.append(f"{case_id}: {field} must be a list of strings")
        ratio = row.get("max_change_ratio")
        if ratio is not None and (not isinstance(ratio, (int, float)) or not 0 <= ratio <= 1):
            errors.append(f"{case_id}: max_change_ratio must be between 0 and 1")
    if errors:
        raise HarnessError("case validation failed:\n- " + "\n- ".join(errors))


def validate_outputs(
    rows: list[dict[str, Any]], case_ids: set[str], required_systems: Iterable[str] | None = None,
) -> None:
    seen: set[tuple[str, str, int]] = set()
    errors: list[str] = []
    coverage: dict[str, set[str]] = defaultdict(set)
    for index, row in enumerate(rows, 1):
        required = {"case_id", "system", "trial", "output"}
        missing = required - row.keys()
        if missing:
            errors.append(f"row {index}: missing {', '.join(sorted(missing))}")
            continue
        case_id, system, trial, output = (
            row["case_id"], row["system"], row["trial"], row["output"]
        )
        if case_id not in case_ids:
            errors.append(f"row {index}: unknown case_id {case_id}")
        if not isinstance(system, str) or not system:
            errors.append(f"row {index}: system must be a non-empty string")
        if not isinstance(trial, int) or trial < 1:
            errors.append(f"row {index}: trial must be a positive integer")
            continue
        if not isinstance(output, str) or not output.strip():
            errors.append(f"row {index}: output must be a non-empty string")
        key = (case_id, system, trial)
        if key in seen:
            errors.append(f"row {index}: duplicate output {key}")
        seen.add(key)
        coverage[case_id].add(system)
    if required_systems:
        wanted = set(required_systems)
        for case_id in sorted(case_ids):
            missing_systems = wanted - coverage.get(case_id, set())
            if missing_systems:
                errors.append(f"{case_id}: missing systems {sorted(missing_systems)}")
    if errors:
        raise HarnessError("output validation failed:\n- " + "\n- ".join(errors))


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def change_ratio(original: str, revised: str) -> float:
    return 1.0 - SequenceMatcher(
        a=normalize_text(original), b=normalize_text(revised), autojunk=False
    ).ratio()


def quoted_spans(text: str) -> list[str]:
    return [match.group(1) for match in QUOTE_RE.finditer(text)]


def static_grade(case: dict[str, Any], output: str, policy: dict[str, Any]) -> dict[str, Any]:
    original = case["input"]
    checks: dict[str, Any] = {}
    required_missing = [item for item in case["must_preserve"] if item not in output]
    checks["required_strings"] = {"pass": not required_missing, "missing": required_missing}

    if policy["static_checks"].get("preserve_numbers", True):
        original_numbers = NUMBER_RE.findall(original)
        missing_numbers = [item for item in original_numbers if item not in output]
        checks["numbers"] = {"pass": not missing_numbers, "missing": missing_numbers}

    if policy["static_checks"].get("preserve_quotes", True):
        original_quotes = quoted_spans(original)
        missing_quotes = [item for item in original_quotes if item not in output]
        checks["quotes"] = {"pass": not missing_quotes, "missing": missing_quotes}

    ratio = change_ratio(original, output)
    limit = case.get("max_change_ratio")
    checks["change_ratio"] = {
        "value": round(ratio, 6),
        "limit": limit,
        "pass": limit is None or ratio <= limit,
        "advisory": True,
    }

    if policy["static_checks"].get("scan_grammar_patterns", True):
        checks["ai_grammar_patterns"] = scan_grammar_patterns(output)

    if policy["static_checks"].get("scan_composition_patterns", False):
        checks["rhythm"] = {"advisory": True, "pass": True, **rhythm_stats(output)}
        checks["composition_cliches"] = scan_composition_cliches(output)

    advisory_checks = {"change_ratio", "ai_grammar_patterns", "rhythm", "composition_cliches"}
    critical_failures = [
        name for name, result in checks.items()
        if name not in advisory_checks and isinstance(result, dict) and not result.get("pass", True)
    ]
    return {
        "critical_pass": not critical_failures,
        "critical_failures": critical_failures,
        "checks": checks,
    }


def command_validate(args: argparse.Namespace) -> None:
    total = 0
    all_ids: set[str] = set()
    for raw_path in args.cases:
        path = Path(raw_path)
        rows = read_jsonl(path)
        validate_cases(rows, args.expected_split)
        duplicates = all_ids.intersection(row["id"] for row in rows)
        if duplicates:
            raise HarnessError(f"duplicate ids across files: {sorted(duplicates)}")
        all_ids.update(row["id"] for row in rows)
        total += len(rows)
    print(f"validated {total} cases across {len(args.cases)} file(s)")


def command_scaffold(args: argparse.Namespace) -> None:
    cases_path = Path(args.cases)
    cases = read_jsonl(cases_path)
    validate_cases(cases)
    policy = read_json(Path(args.policy))
    systems = policy.get("required_systems", list(SYSTEMS))
    if args.trials < 1:
        raise HarnessError("trials must be at least 1")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=False)
    rows = []
    for case in cases:
        for trial in range(1, args.trials + 1):
            for system in systems:
                rows.append({
                    "case_id": case["id"],
                    "system": system,
                    "trial": trial,
                    "output": case["input"] if system == "source" else None,
                    "metadata": {},
                })
    write_jsonl(out_dir / "outputs.template.jsonl", rows)
    skill_root = Path(args.skill_root).resolve()
    artifacts: dict[str, dict[str, str]] = {}
    for specification in args.artifact:
        if "=" not in specification:
            raise HarnessError(f"artifact must use name=path: {specification}")
        name, raw_path = specification.split("=", 1)
        artifact_path = Path(raw_path).resolve()
        if not name or not artifact_path.exists():
            raise HarnessError(f"invalid artifact: {specification}")
        digest = tree_digest(artifact_path) if artifact_path.is_dir() else sha256_file(artifact_path)
        artifacts[name] = {"path": str(artifact_path), "sha256": digest}
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "case_file": str(cases_path.resolve()),
        "case_sha256": sha256_file(cases_path),
        "policy_file": str(Path(args.policy).resolve()),
        "policy_sha256": sha256_file(Path(args.policy)),
        "skill_root": str(skill_root),
        "skill_tree_sha256": tree_digest(skill_root),
        "git_revision": git_revision(skill_root),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "trials": args.trials,
        "systems": systems,
        "artifacts": artifacts,
        "notes": args.notes,
    }
    write_json(out_dir / "manifest.json", manifest)
    print(f"created run scaffold at {out_dir}")


def command_static(args: argparse.Namespace) -> None:
    cases = read_jsonl(Path(args.cases))
    validate_cases(cases)
    by_id = {case["id"]: case for case in cases}
    outputs = read_jsonl(Path(args.outputs))
    validate_outputs(outputs, set(by_id))
    policy = read_json(Path(args.policy))
    grades = []
    for row in outputs:
        result = static_grade(by_id[row["case_id"]], row["output"], policy)
        grades.append({
            "case_id": row["case_id"], "system": row["system"],
            "trial": row["trial"], "genre": by_id[row["case_id"]]["genre"],
            "source_quality": by_id[row["case_id"]]["source_quality"],
            "metadata": row.get("metadata", {}), **result,
        })
    write_jsonl(Path(args.out), grades)
    failures = sum(not row["critical_pass"] for row in grades)
    warnings = sum(not row["checks"]["change_ratio"]["pass"] for row in grades)
    grammar_hits = sum(
        bool(row["checks"].get("ai_grammar_patterns", {}).get("triggered"))
        for row in grades
    )
    print(
        f"graded {len(grades)} outputs: {failures} critical failures, "
        f"{warnings} over-edit warnings, {grammar_hits} with a flagged grammar/AI-tell pattern"
    )


def command_import_batch(args: argparse.Namespace) -> None:
    cases = read_jsonl(Path(args.cases))
    validate_cases(cases)
    case_ids = {case["id"] for case in cases}
    rows = [
        {
            "case_id": case["id"], "system": "source", "trial": args.trial,
            "output": case["input"], "metadata": {},
        }
        for case in cases
    ]
    for specification in args.batch:
        if "=" not in specification:
            raise HarnessError(f"batch must use system=path: {specification}")
        system, raw_path = specification.split("=", 1)
        payload = read_json(Path(raw_path))
        outputs = payload.get("outputs") if isinstance(payload, dict) else None
        if not isinstance(outputs, list):
            raise HarnessError(f"{raw_path}: expected an outputs array")
        seen: set[str] = set()
        for item in outputs:
            if not isinstance(item, dict) or not isinstance(item.get("output"), str):
                raise HarnessError(f"{raw_path}: invalid output item")
            case_id = item.get("case_id")
            if case_id not in case_ids or case_id in seen:
                raise HarnessError(f"{raw_path}: unknown or duplicate case_id {case_id}")
            seen.add(case_id)
            rows.append({
                "case_id": case_id, "system": system, "trial": args.trial,
                "output": item["output"], "metadata": payload.get("metadata", {}),
            })
        missing = case_ids - seen
        if missing:
            raise HarnessError(f"{raw_path}: missing cases {sorted(missing)}")
    validate_outputs(rows, case_ids)
    write_jsonl(Path(args.out), rows)
    print(f"imported {len(rows)} outputs for trial {args.trial}")


def stable_id(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:20]


def command_blind(args: argparse.Namespace) -> None:
    cases = read_jsonl(Path(args.cases))
    validate_cases(cases)
    by_id = {case["id"]: case for case in cases}
    outputs = read_jsonl(Path(args.outputs))
    validate_outputs(outputs, set(by_id), [args.system_a, args.system_b])
    indexed = {(r["case_id"], r["system"], r["trial"]): r["output"] for r in outputs}
    pairs = sorted({(r["case_id"], r["trial"]) for r in outputs if r["system"] == args.system_a})
    rng = random.Random(args.seed)
    ballots: list[dict[str, Any]] = []
    key_rows: list[dict[str, Any]] = []
    for case_id, trial in pairs:
        a_key = (case_id, args.system_a, trial)
        b_key = (case_id, args.system_b, trial)
        if a_key not in indexed or b_key not in indexed:
            raise HarnessError(f"missing paired output for {case_id}, trial {trial}")
        comparison_id = stable_id(case_id, str(trial), args.system_a, args.system_b, str(args.seed))
        orders = [(args.system_a, args.system_b)]
        if rng.random() < 0.5:
            orders[0] = (args.system_b, args.system_a)
        if args.mirror:
            orders.append((orders[0][1], orders[0][0]))
        for order_index, (left_system, right_system) in enumerate(orders, 1):
            pair_id = stable_id(comparison_id, str(order_index))
            case = by_id[case_id]
            ballots.append({
                "pair_id": pair_id,
                "comparison_id": comparison_id,
                "input": case["input"],
                "instruction": case["instruction"],
                "left": indexed[(case_id, left_system, trial)],
                "right": indexed[(case_id, right_system, trial)],
            })
            key_rows.append({
                "pair_id": pair_id, "comparison_id": comparison_id,
                "case_id": case_id, "trial": trial,
                "genre": case["genre"], "source_quality": case["source_quality"],
                "left_system": left_system, "right_system": right_system,
            })
    write_jsonl(Path(args.ballots), ballots)
    write_jsonl(Path(args.key), key_rows)
    print(f"created {len(ballots)} blinded ballots and a separate answer key")


def wilson_interval(wins: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return (0.0, 0.0)
    p = wins / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def operational_summary(rows: list[dict[str, Any]], system: str) -> dict[str, float | int | None]:
    metadata_rows = [
        row.get("metadata", {}) for row in rows
        if row.get("system") == system and isinstance(row.get("metadata", {}), dict)
    ]

    def values(name: str) -> list[float]:
        return [
            float(row[name]) for row in metadata_rows
            if isinstance(row.get(name), (int, float)) and not isinstance(row.get(name), bool)
        ]

    latency = values("latency_ms")
    input_tokens = values("input_tokens")
    output_tokens = values("output_tokens")
    cost = values("cost_usd")
    return {
        "samples_with_metadata": sum(bool(row) for row in metadata_rows),
        "mean_latency_ms": sum(latency) / len(latency) if latency else None,
        "total_input_tokens": int(sum(input_tokens)) if input_tokens else None,
        "total_output_tokens": int(sum(output_tokens)) if output_tokens else None,
        "total_cost_usd": sum(cost) if cost else None,
    }


def aggregate_preferences(
    votes: list[dict[str, Any]], key_rows: list[dict[str, Any]], candidate: str,
) -> tuple[list[dict[str, Any]], int]:
    key_by_pair = {row["pair_id"]: row for row in key_rows}
    grouped: dict[str, list[str]] = defaultdict(list)
    unknown = 0
    seen_votes: set[tuple[str, str]] = set()
    for vote in votes:
        pair_id = vote.get("pair_id")
        winner = vote.get("winner")
        judge_id = vote.get("judge_id")
        vote_key = (str(pair_id), str(judge_id))
        if (
            pair_id not in key_by_pair or winner not in {"left", "right", "tie"}
            or not isinstance(judge_id, str) or not judge_id.strip()
            or vote_key in seen_votes
        ):
            unknown += 1
            continue
        seen_votes.add(vote_key)
        key = key_by_pair[pair_id]
        system = "tie" if winner == "tie" else key[f"{winner}_system"]
        grouped[key["comparison_id"]].append(system)
    comparisons = []
    comparison_meta = {row["comparison_id"]: row for row in key_rows}
    for comparison_id, choices in grouped.items():
        counts = Counter(choices)
        non_tie = {name: count for name, count in counts.items() if name != "tie"}
        if not non_tie:
            winner = "tie"
        else:
            top = max(non_tie.values())
            winners = [name for name, count in non_tie.items() if count == top]
            winner = winners[0] if len(winners) == 1 else "tie"
        meta = comparison_meta[comparison_id]
        comparisons.append({
            "comparison_id": comparison_id,
            "case_id": meta["case_id"], "trial": meta["trial"],
            "genre": meta["genre"], "source_quality": meta["source_quality"],
            "winner": winner,
            "candidate_won": winner == candidate,
            "vote_counts": dict(counts),
        })
    return comparisons, unknown


def markdown_report(report: dict[str, Any]) -> str:
    preference = report["pairwise_preference"]
    case_preference = report["case_preference"]
    gate = report["critical_gate"]
    lines = [
        f"# 평가 보고서: {report['decision']}", "",
        f"- 비교: `{report['baseline']}` vs `{report['candidate']}`",
        f"- 유효 비교: {preference['decisions']}건 (무승부 {preference['ties']}건)",
        f"- 후보 승률: {preference['candidate_win_rate']:.1%}",
        f"- 사례 단위 후보 승률: {case_preference['candidate_win_rate']:.1%} "
        f"({case_preference['decided_cases']}개 사례)",
        f"- 사례 단위 95% Wilson 구간: {case_preference['confidence_interval'][0]:.1%}~"
        f"{case_preference['confidence_interval'][1]:.1%}",
        f"- 후보 중대 실패: {gate['challenger_critical_failures']}건",
        "", "## 장르별 결과", "",
        "| 장르 | 후보 승 | 기준 승 | 무승부 | 후보 승률 |", "|---|---:|---:|---:|---:|",
    ]
    for genre, row in sorted(report["by_genre"].items()):
        lines.append(
            f"| {genre} | {row['candidate_wins']} | {row['baseline_wins']} | "
            f"{row['ties']} | {row['candidate_win_rate']:.1%} |"
        )
    operational = report.get("operational", {})
    if any(row.get("samples_with_metadata", 0) for row in operational.values()):
        lines.extend(["", "## 운영 지표", ""])
        for label in ("baseline", "candidate"):
            row = operational[label]
            lines.append(
                f"- {label}: 평균 지연 {row['mean_latency_ms']}ms, "
                f"입력/출력 토큰 {row['total_input_tokens']}/{row['total_output_tokens']}, "
                f"총비용 ${row['total_cost_usd']}"
            )
    lines.extend(["", "## 판정 근거", ""])
    lines.extend(f"- {reason}" for reason in report["reasons"])
    lines.extend([
        "", "> 이 판정은 자동 배포 승인이 아니다. `eligible_for_human_review`는 사람이",
        "> 경계 사례와 변경 diff를 확인할 수 있다는 뜻이다.", "",
    ])
    return "\n".join(lines)


def command_report(args: argparse.Namespace) -> None:
    policy = read_json(Path(args.policy))
    votes = read_jsonl(Path(args.votes))
    key_rows = read_jsonl(Path(args.key))
    baseline = getattr(args, "baseline_system", None) or policy["champion_system"]
    candidate = getattr(args, "candidate_system", None) or policy["challenger_system"]
    expected_pair = {baseline, candidate}
    for row in key_rows:
        actual_pair = {row.get("left_system"), row.get("right_system")}
        if actual_pair != expected_pair:
            raise HarnessError(
                f"answer key contains {sorted(str(x) for x in actual_pair)}; "
                f"expected {sorted(expected_pair)}"
            )
    comparisons, invalid_votes = aggregate_preferences(votes, key_rows, candidate)

    decisions = [row for row in comparisons if row["winner"] != "tie"]
    candidate_wins = sum(row["candidate_won"] for row in decisions)
    baseline_wins = len(decisions) - candidate_wins
    ties = len(comparisons) - len(decisions)
    rate = candidate_wins / len(decisions) if decisions else 0.0
    interval = wilson_interval(candidate_wins, len(decisions))

    case_votes: dict[str, Counter[str]] = defaultdict(Counter)
    for row in decisions:
        case_votes[row["case_id"]][row["winner"]] += 1
    case_outcomes: dict[str, str] = {}
    for case_id, counts in case_votes.items():
        candidate_count = counts[candidate]
        baseline_count = counts[baseline]
        if candidate_count == baseline_count:
            case_outcomes[case_id] = "tie"
        else:
            case_outcomes[case_id] = candidate if candidate_count > baseline_count else baseline
    decided_cases = [winner for winner in case_outcomes.values() if winner != "tie"]
    candidate_case_wins = sum(winner == candidate for winner in decided_cases)
    case_rate = candidate_case_wins / len(decided_cases) if decided_cases else 0.0
    case_interval = wilson_interval(candidate_case_wins, len(decided_cases))

    by_genre: dict[str, dict[str, Any]] = {}
    for genre in sorted({row["genre"] for row in key_rows}):
        subset = [row for row in comparisons if row["genre"] == genre]
        decided = [row for row in subset if row["winner"] != "tie"]
        wins = sum(row["candidate_won"] for row in decided)
        by_genre[genre] = {
            "candidate_wins": wins,
            "baseline_wins": len(decided) - wins,
            "ties": len(subset) - len(decided),
            "candidate_win_rate": wins / len(decided) if decided else 0.0,
            "decisions": len(decided),
        }

    expected_trials = {(row["case_id"], row["trial"]) for row in comparisons}
    scores = read_jsonl(Path(args.static_scores))
    static_by_trial = {
        (row.get("case_id"), row.get("trial")): row
        for row in scores if row.get("system") == candidate
    }
    missing_static = sorted(expected_trials - static_by_trial.keys())
    failed_trials = {
        (row.get("case_id"), row.get("trial"))
        for row in scores
        if row.get("system") == candidate and not row.get("critical_pass", False)
    }
    missing_semantic: list[tuple[str, int]] = []
    if args.semantic_scores:
        semantic_scores = read_jsonl(Path(args.semantic_scores))
        semantic_by_trial = {
            (row.get("case_id"), row.get("trial")): row
            for row in semantic_scores if row.get("system") == candidate
        }
        missing_semantic = sorted(expected_trials - semantic_by_trial.keys())
        failed_trials.update(
            key for key, row in semantic_by_trial.items() if row.get("pass") is not True
        )
    elif policy.get("require_semantic_scores", False):
        missing_semantic = sorted({(row["case_id"], row["trial"]) for row in comparisons})
    critical_failures = len(failed_trials)
    overedit_rates: dict[str, float | None] = {}
    for system in (baseline, candidate):
        natural_rows = [
            row for row in scores
            if row.get("system") == system and row.get("source_quality") == "natural"
        ]
        overedit_rates[system] = (
            sum(
                not row.get("checks", {}).get("change_ratio", {}).get("pass", True)
                for row in natural_rows
            ) / len(natural_rows)
            if natural_rows else None
        )

    promotion = policy["promotion"]
    reasons: list[str] = []
    insufficient = False
    rejected = False
    if len(decisions) < promotion["minimum_pairwise_decisions"]:
        insufficient = True
        reasons.append(
            f"유효 비교 {len(decisions)}건으로 최소 {promotion['minimum_pairwise_decisions']}건에 못 미친다."
        )
    if len(decided_cases) < promotion.get("minimum_cases", 0):
        insufficient = True
        reasons.append(
            f"유효 사례 {len(decided_cases)}개로 최소 {promotion.get('minimum_cases', 0)}개에 못 미친다."
        )
    if missing_static:
        insufficient = True
        reasons.append(f"후보 결정적 검사 점수가 {len(missing_static)}개 trial에서 비어 있다.")
    if missing_semantic:
        insufficient = True
        reasons.append(f"후보 의미 게이트 점수가 {len(missing_semantic)}개 trial에서 비어 있다.")
    if promotion.get("require_all_strata_represented", False):
        minimum = promotion.get("minimum_decisions_per_stratum", 1)
        thin = [genre for genre, row in by_genre.items() if row["decisions"] < minimum]
        if thin:
            insufficient = True
            reasons.append(f"장르별 최소 비교 수가 부족하다: {', '.join(thin)}")
    if critical_failures > promotion["maximum_critical_failures"]:
        rejected = True
        reasons.append(
            f"후보의 중대 실패 {critical_failures}건이 허용치 "
            f"{promotion['maximum_critical_failures']}건을 넘었다."
        )
    if decisions and rate < promotion["minimum_challenger_win_rate"]:
        rejected = True
        reasons.append(
            f"후보 승률 {rate:.1%}가 기준 {promotion['minimum_challenger_win_rate']:.1%}보다 낮다."
        )
    lower_bound = case_interval[0]
    if decisions and lower_bound < promotion.get("minimum_lower_confidence_bound", 0.0):
        insufficient = True
        reasons.append(
            f"사례 단위 후보 승률의 95% 하한 {lower_bound:.1%}가 기준 "
            f"{promotion.get('minimum_lower_confidence_bound', 0.0):.1%}보다 낮다."
        )
    minimum_stratum_rate = promotion.get("minimum_stratum_win_rate")
    if minimum_stratum_rate is not None:
        regressed = [
            genre for genre, row in by_genre.items()
            if row["decisions"] >= promotion.get("minimum_decisions_per_stratum", 1)
            and row["candidate_win_rate"] < minimum_stratum_rate
        ]
        if regressed:
            rejected = True
            reasons.append(f"후보 승률이 장르 하한보다 낮다: {', '.join(regressed)}")
    baseline_overedit = overedit_rates[baseline]
    candidate_overedit = overedit_rates[candidate]
    allowed_overedit_delta = promotion.get("maximum_overedit_rate_regression")
    if (
        allowed_overedit_delta is not None and baseline_overedit is not None
        and candidate_overedit is not None
        and candidate_overedit > baseline_overedit + allowed_overedit_delta
    ):
        rejected = True
        reasons.append(
            f"자연 원문 과잉 수정 경보율이 {baseline_overedit:.1%}에서 "
            f"{candidate_overedit:.1%}로 악화했다."
        )
    if invalid_votes:
        reasons.append(f"형식이 잘못되었거나 키에 없는 투표 {invalid_votes}건은 제외했다.")

    labels = policy["decision_labels"]
    is_promotion_comparison = (
        baseline == policy["champion_system"] and candidate == policy["challenger_system"]
    )
    if not is_promotion_comparison:
        decision = "comparison_only"
        reasons.append("현재 버전과 후보의 승격 비교가 아니므로 참고 비교로만 기록한다.")
    elif rejected:
        decision = labels["rejected"]
    elif insufficient:
        decision = labels["insufficient"]
    else:
        decision = labels["eligible"]
        reasons.append("자동 기준을 통과했다. 변경 diff와 경계 사례를 사람이 검토해야 한다.")

    report = {
        "schema_version": 1,
        "decision": decision,
        "baseline": baseline,
        "candidate": candidate,
        "pairwise_preference": {
            "comparisons": len(comparisons), "decisions": len(decisions), "ties": ties,
            "candidate_wins": candidate_wins, "baseline_wins": baseline_wins,
            "candidate_win_rate": rate, "confidence_interval": interval,
        },
        "case_preference": {
            "cases": len(case_outcomes), "decided_cases": len(decided_cases),
            "ties": len(case_outcomes) - len(decided_cases),
            "candidate_wins": candidate_case_wins,
            "baseline_wins": len(decided_cases) - candidate_case_wins,
            "candidate_win_rate": case_rate,
            "confidence_interval": case_interval,
        },
        "critical_gate": {
            "challenger_critical_failures": critical_failures,
            "missing_static_scores": len(missing_static),
            "missing_semantic_scores": len(missing_semantic),
        },
        "overediting": {
            "baseline_warning_rate": baseline_overedit,
            "candidate_warning_rate": candidate_overedit,
        },
        "operational": {
            "baseline": operational_summary(scores, baseline),
            "candidate": operational_summary(scores, candidate),
        },
        "by_genre": by_genre,
        "reasons": reasons,
    }
    out_path = Path(args.out)
    write_json(out_path.with_suffix(".json"), report)
    out_path.with_suffix(".md").write_text(markdown_report(report), encoding="utf-8")
    print(f"decision: {decision}; wrote {out_path.with_suffix('.json')} and {out_path.with_suffix('.md')}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate one or more case files")
    validate.add_argument("cases", nargs="+")
    validate.add_argument("--expected-split")
    validate.set_defaults(func=command_validate)

    scaffold = subparsers.add_parser("scaffold", help="create a versioned run scaffold")
    scaffold.add_argument("--cases", required=True)
    scaffold.add_argument("--policy", required=True)
    scaffold.add_argument("--skill-root", required=True)
    scaffold.add_argument("--out", required=True)
    scaffold.add_argument("--trials", type=int, default=1)
    scaffold.add_argument("--model", default="record-exact-model-id")
    scaffold.add_argument("--reasoning-effort", default="record-exact-setting")
    scaffold.add_argument("--notes", default="")
    scaffold.add_argument(
        "--artifact", action="append", default=[], metavar="NAME=PATH",
        help="record an exact prompt or skill artifact; may be repeated",
    )
    scaffold.set_defaults(func=command_scaffold)

    static = subparsers.add_parser("static-grade", help="run deterministic preservation checks")
    static.add_argument("--cases", required=True)
    static.add_argument("--outputs", required=True)
    static.add_argument("--policy", required=True)
    static.add_argument("--out", required=True)
    static.set_defaults(func=command_static)

    import_batch = subparsers.add_parser(
        "import-batch", help="merge structured batch generations into outputs JSONL"
    )
    import_batch.add_argument("--cases", required=True)
    import_batch.add_argument("--batch", action="append", required=True, metavar="SYSTEM=PATH")
    import_batch.add_argument("--trial", type=int, default=1)
    import_batch.add_argument("--out", required=True)
    import_batch.set_defaults(func=command_import_batch)

    blind = subparsers.add_parser("make-blind", help="create randomized pairwise ballots")
    blind.add_argument("--cases", required=True)
    blind.add_argument("--outputs", required=True)
    blind.add_argument("--system-a", default="champion")
    blind.add_argument("--system-b", default="challenger")
    blind.add_argument("--ballots", required=True)
    blind.add_argument("--key", required=True)
    blind.add_argument("--seed", type=int, default=20260913)
    blind.add_argument("--mirror", action=argparse.BooleanOptionalAction, default=True)
    blind.set_defaults(func=command_blind)

    report = subparsers.add_parser("report", help="aggregate votes and apply promotion policy")
    report.add_argument("--policy", required=True)
    report.add_argument("--votes", required=True)
    report.add_argument("--key", required=True)
    report.add_argument("--static-scores", required=True)
    report.add_argument("--semantic-scores")
    report.add_argument("--baseline-system")
    report.add_argument("--candidate-system")
    report.add_argument("--out", required=True, help="output path without extension")
    report.set_defaults(func=command_report)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except (HarnessError, OSError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
