from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "eval_harness.py"
SPEC = importlib.util.spec_from_file_location("eval_harness", SCRIPT)
assert SPEC and SPEC.loader
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


def case(**updates):
    value = {
        "id": "case-1",
        "split": "dev",
        "genre": "notice",
        "register": "formal",
        "source_quality": "mixed",
        "instruction": "쉽게 고쳐 주세요.",
        "input": "신청은 2027년 3월 1일까지입니다. 담당자는 \"연장할 수 없습니다\"라고 말했다.",
        "must_preserve": ["2027년 3월 1일"],
        "risk_tags": ["number", "quote"],
    }
    value.update(updates)
    return value


class CaseValidationTests(unittest.TestCase):
    def test_rejects_duplicate_ids(self):
        with self.assertRaises(HARNESS.HarnessError):
            HARNESS.validate_cases([case(), case()])

    def test_accepts_valid_case(self):
        HARNESS.validate_cases([case()])


class StaticGraderTests(unittest.TestCase):
    def setUp(self):
        self.policy = {"static_checks": {"preserve_numbers": True, "preserve_quotes": True}}

    def test_detects_missing_number_and_quote(self):
        result = HARNESS.static_grade(case(), "신청 기한이 끝났습니다.", self.policy)
        self.assertFalse(result["critical_pass"])
        self.assertIn("numbers", result["critical_failures"])
        self.assertIn("quotes", result["critical_failures"])

    def test_passes_preserved_literals(self):
        result = HARNESS.static_grade(case(), case()["input"], self.policy)
        self.assertTrue(result["critical_pass"])

    def test_flags_overediting_as_advisory(self):
        result = HARNESS.static_grade(
            case(input="비가 왔다.", must_preserve=[], max_change_ratio=0.1),
            "햇빛이 눈부시게 내리쬐었다.", self.policy,
        )
        self.assertTrue(result["critical_pass"])
        self.assertFalse(result["checks"]["change_ratio"]["pass"])
        self.assertTrue(result["checks"]["change_ratio"]["advisory"])

    def test_static_command_writes_case_metadata(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            root = Path(raw_dir)
            cases_path = root / "cases.jsonl"
            outputs_path = root / "outputs.jsonl"
            policy_path = root / "policy.json"
            scores_path = root / "scores.jsonl"
            HARNESS.write_jsonl(cases_path, [case(source_quality="natural")])
            HARNESS.write_jsonl(outputs_path, [{
                "case_id": "case-1", "system": "challenger", "trial": 1,
                "output": case()["input"],
            }])
            HARNESS.write_json(policy_path, self.policy)
            args = type("Args", (), {
                "cases": str(cases_path), "outputs": str(outputs_path),
                "policy": str(policy_path), "out": str(scores_path),
            })()
            HARNESS.command_static(args)
            score = HARNESS.read_jsonl(scores_path)[0]
            self.assertEqual(score["source_quality"], "natural")
            self.assertEqual(score["genre"], "notice")


class BatchImportTests(unittest.TestCase):
    def test_imports_complete_batch_and_source(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            root = Path(raw_dir)
            cases_path = root / "cases.jsonl"
            batch_path = root / "challenger.json"
            output_path = root / "outputs.jsonl"
            HARNESS.write_jsonl(cases_path, [case()])
            HARNESS.write_json(batch_path, {
                "outputs": [{"case_id": "case-1", "output": "후보 결과"}],
                "metadata": {"latency_ms": 100},
            })
            args = type("Args", (), {
                "cases": str(cases_path), "batch": [f"challenger={batch_path}"],
                "trial": 1, "out": str(output_path),
            })()
            HARNESS.command_import_batch(args)
            rows = HARNESS.read_jsonl(output_path)
            self.assertEqual({row["system"] for row in rows}, {"source", "challenger"})
            challenger = next(row for row in rows if row["system"] == "challenger")
            self.assertEqual(challenger["metadata"]["latency_ms"], 100)

    def test_rejects_incomplete_batch(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            root = Path(raw_dir)
            cases_path = root / "cases.jsonl"
            batch_path = root / "challenger.json"
            HARNESS.write_jsonl(cases_path, [case(), case(id="case-2")])
            HARNESS.write_json(batch_path, {
                "outputs": [{"case_id": "case-1", "output": "후보 결과"}]
            })
            args = type("Args", (), {
                "cases": str(cases_path), "batch": [f"challenger={batch_path}"],
                "trial": 1, "out": str(root / "outputs.jsonl"),
            })()
            with self.assertRaises(HARNESS.HarnessError):
                HARNESS.command_import_batch(args)


class BlindAndReportTests(unittest.TestCase):
    def test_ballot_hides_system_names_and_report_maps_votes(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            root = Path(raw_dir)
            cases_path = root / "cases.jsonl"
            outputs_path = root / "outputs.jsonl"
            ballots_path = root / "ballots.jsonl"
            key_path = root / "key.jsonl"
            policy_path = root / "policy.json"
            votes_path = root / "votes.jsonl"
            static_path = root / "static.jsonl"
            semantic_path = root / "semantic.jsonl"
            report_path = root / "report"
            HARNESS.write_jsonl(cases_path, [case()])
            HARNESS.write_jsonl(outputs_path, [
                {"case_id": "case-1", "system": "champion", "trial": 1, "output": "현재 결과"},
                {"case_id": "case-1", "system": "challenger", "trial": 1, "output": "후보 결과"},
            ])
            args = type("Args", (), {
                "cases": str(cases_path), "outputs": str(outputs_path),
                "system_a": "champion", "system_b": "challenger",
                "ballots": str(ballots_path), "key": str(key_path),
                "seed": 1, "mirror": True,
            })()
            HARNESS.command_blind(args)
            ballots = HARNESS.read_jsonl(ballots_path)
            self.assertEqual(len(ballots), 2)
            self.assertNotIn("champion", ballots_path.read_text(encoding="utf-8"))
            self.assertNotIn("challenger", ballots_path.read_text(encoding="utf-8"))

            keys = HARNESS.read_jsonl(key_path)
            votes = []
            for key in keys:
                side = "left" if key["left_system"] == "challenger" else "right"
                votes.append({"pair_id": key["pair_id"], "judge_id": "test", "winner": side})
            HARNESS.write_jsonl(votes_path, votes)
            policy = {
                "champion_system": "champion", "challenger_system": "challenger",
                "promotion": {
                    "minimum_pairwise_decisions": 1,
                    "minimum_challenger_win_rate": 0.55,
                    "maximum_critical_failures": 0,
                    "require_all_strata_represented": True,
                    "minimum_decisions_per_stratum": 1,
                },
                "decision_labels": {
                    "eligible": "eligible_for_human_review",
                    "rejected": "rejected", "insufficient": "insufficient_evidence",
                },
                "require_semantic_scores": True,
            }
            HARNESS.write_json(policy_path, policy)
            HARNESS.write_jsonl(static_path, [{
                "case_id": "case-1", "system": "challenger", "trial": 1,
                "critical_pass": True,
            }])
            HARNESS.write_jsonl(semantic_path, [{
                "case_id": "case-1", "system": "challenger", "trial": 1, "pass": True,
            }])
            report_args = type("Args", (), {
                "policy": str(policy_path), "votes": str(votes_path), "key": str(key_path),
                "static_scores": str(static_path), "semantic_scores": str(semantic_path),
                "out": str(report_path),
            })()
            HARNESS.command_report(report_args)
            report = json.loads(report_path.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(report["decision"], "eligible_for_human_review")
            self.assertEqual(report["pairwise_preference"]["candidate_win_rate"], 1.0)

    def test_default_policy_accepts_strong_six_case_result(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            root = Path(raw_dir)
            policy_path = Path(__file__).parents[1] / "eval" / "policy.json"
            key_path = root / "key.jsonl"
            votes_path = root / "votes.jsonl"
            static_path = root / "static.jsonl"
            semantic_path = root / "semantic.jsonl"
            report_path = root / "report"
            keys = []
            votes = []
            static_scores = []
            semantic_scores = []
            genres = ["informational", "essay", "notice", "article", "email", "message"]
            for case_index, genre in enumerate(genres, 1):
                case_id = f"case-{case_index}"
                for trial in range(1, 5):
                    comparison_id = f"comparison-{case_index}-{trial}"
                    pair_id = f"pair-{case_index}-{trial}"
                    keys.append({
                        "pair_id": pair_id, "comparison_id": comparison_id,
                        "case_id": case_id, "trial": trial, "genre": genre,
                        "source_quality": "mixed", "left_system": "champion",
                        "right_system": "challenger",
                    })
                    votes.append({"pair_id": pair_id, "judge_id": "judge-1", "winner": "right"})
                    static_scores.append({
                        "case_id": case_id, "system": "challenger", "trial": trial,
                        "critical_pass": True, "genre": genre, "source_quality": "mixed",
                        "checks": {"change_ratio": {"pass": True}},
                    })
                    semantic_scores.append({
                        "case_id": case_id, "system": "challenger", "trial": trial, "pass": True,
                    })
            HARNESS.write_jsonl(key_path, keys)
            HARNESS.write_jsonl(votes_path, votes)
            HARNESS.write_jsonl(static_path, static_scores)
            HARNESS.write_jsonl(semantic_path, semantic_scores)
            args = type("Args", (), {
                "policy": str(policy_path), "votes": str(votes_path), "key": str(key_path),
                "static_scores": str(static_path), "semantic_scores": str(semantic_path),
                "baseline_system": None, "candidate_system": None, "out": str(report_path),
            })()
            HARNESS.command_report(args)
            report = json.loads(report_path.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(report["decision"], "eligible_for_human_review")
            self.assertGreater(report["case_preference"]["confidence_interval"][0], 0.5)


if __name__ == "__main__":
    unittest.main()
