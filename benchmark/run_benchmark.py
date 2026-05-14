"""
Benchmark runner. Loads each transcript + ground-truth label pair, runs the
full pipeline, fuzzy-matches extracted items against ground truth, and
reports per-stage precision / recall / F1, plus hallucination rate, schema
compliance, and average latency.

Usage:
    .venv/bin/python benchmark/run_benchmark.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Allow running as a script from anywhere.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rapidfuzz import fuzz  # noqa: E402

from app.llm import LLMClient  # noqa: E402
from app.pipeline import Pipeline  # noqa: E402

MATCH_THRESHOLD = 80  # %
TRANSCRIPTS_DIR = Path(__file__).parent / "transcripts"
LABELS_DIR = Path(__file__).parent / "labels"
RESULTS_PATH = Path(__file__).parent / "results.json"


def fuzzy_in(needle: str, haystack: list[str], threshold: int = MATCH_THRESHOLD) -> bool:
    if not needle:
        return False
    n = needle.strip().lower()
    for h in haystack:
        if fuzz.token_set_ratio(n, h.strip().lower()) >= threshold:
            return True
    return False


def prf(true_positives: int, predicted: int, actual: int) -> tuple[float, float, float]:
    precision = (true_positives / predicted) if predicted else 1.0 if actual == 0 else 0.0
    recall = (true_positives / actual) if actual else 1.0 if predicted == 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


def evaluate_one(pred_descriptions: list[str], gt_descriptions: list[str]) -> dict[str, Any]:
    """Symmetric fuzzy matching: TP = predictions matching any gt description."""
    tp = sum(1 for p in pred_descriptions if fuzzy_in(p, gt_descriptions))
    # Recall: gt items matched by any prediction
    matched_gt = sum(1 for g in gt_descriptions if fuzzy_in(g, pred_descriptions))
    precision, _, _ = prf(tp, len(pred_descriptions), len(gt_descriptions))
    recall_value = (matched_gt / len(gt_descriptions)) if gt_descriptions else (1.0 if not pred_descriptions else 0.0)
    f1 = (2 * precision * recall_value / (precision + recall_value)) if (precision + recall_value) else 0.0
    return {
        "tp": tp,
        "matched_gt": matched_gt,
        "predicted": len(pred_descriptions),
        "actual": len(gt_descriptions),
        "precision": round(precision, 3),
        "recall": round(recall_value, 3),
        "f1": round(f1, 3),
    }


async def run_one(pipeline: Pipeline, tid: str) -> dict[str, Any]:
    tdata = json.loads((TRANSCRIPTS_DIR / f"{tid}.json").read_text())
    gt = json.loads((LABELS_DIR / f"{tid}.json").read_text())

    meeting_date = datetime.fromisoformat(tdata["meeting_date"])
    t0 = time.perf_counter()
    report = await pipeline.run(
        tdata["transcript"],
        meeting_date=meeting_date,
    )
    elapsed = time.perf_counter() - t0

    pred_actions = [it.description for it in report.action_items.items]
    pred_decisions = [d.decision for d in report.decisions.items]
    gt_actions = [a["description"] for a in gt["action_items"]]
    gt_decisions = [d["decision"] for d in gt["decisions"]]

    return {
        "id": tid,
        "category": tdata["category"],
        "action_items": evaluate_one(pred_actions, gt_actions),
        "decisions": evaluate_one(pred_decisions, gt_decisions),
        "hallucination_rate": report.validation.hallucination_rate,
        "flagged_fields": report.validation.flagged_fields,
        "fields_checked": report.validation.total_fields_checked,
        "latency_seconds": elapsed,
        "tokens": report.total_tokens_used,
        "stage_errors": len(report.stage_errors),
        "schema_first_try_success": (len(report.stage_errors) == 0),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    def _macro(stage: str) -> dict[str, float]:
        precisions = [r[stage]["precision"] for r in results]
        recalls = [r[stage]["recall"] for r in results]
        f1s = [r[stage]["f1"] for r in results]
        return {
            "precision": round(sum(precisions) / len(precisions), 3),
            "recall": round(sum(recalls) / len(recalls), 3),
            "f1": round(sum(f1s) / len(f1s), 3),
        }

    def _micro(stage: str) -> dict[str, float]:
        tp = sum(r[stage]["tp"] for r in results)
        predicted = sum(r[stage]["predicted"] for r in results)
        matched_gt = sum(r[stage]["matched_gt"] for r in results)
        actual = sum(r[stage]["actual"] for r in results)
        p = (tp / predicted) if predicted else 1.0
        r = (matched_gt / actual) if actual else 1.0
        f1 = (2 * p * r / (p + r)) if (p + r) else 0.0
        return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3),
                "tp": tp, "predicted": predicted, "actual": actual}

    total_flagged = sum(r["flagged_fields"] for r in results)
    total_checked = sum(r["fields_checked"] for r in results)
    return {
        "n_transcripts": len(results),
        "action_items": {"macro": _macro("action_items"), "micro": _micro("action_items")},
        "decisions": {"macro": _macro("decisions"), "micro": _micro("decisions")},
        "hallucination_rate": round(total_flagged / total_checked, 4) if total_checked else 0.0,
        "fields_flagged_total": total_flagged,
        "fields_checked_total": total_checked,
        "schema_compliance_rate": round(
            sum(1 for r in results if r["schema_first_try_success"]) / len(results), 3
        ),
        "avg_latency_seconds": round(sum(r["latency_seconds"] for r in results) / len(results), 2),
        "max_latency_seconds": round(max(r["latency_seconds"] for r in results), 2),
        "total_tokens_used": sum(r["tokens"] for r in results),
    }


def print_report(results: list[dict[str, Any]], agg: dict[str, Any]) -> None:
    print("\n" + "=" * 78)
    print("PER-TRANSCRIPT RESULTS")
    print("=" * 78)
    print(f"{'id':>4} {'category':<18} {'AI-F1':>6} {'DEC-F1':>7} {'halluc':>7} {'lat(s)':>7} {'tok':>6}")
    print("-" * 78)
    for r in results:
        print(f"{r['id']:>4} {r['category']:<18} "
              f"{r['action_items']['f1']:>6.2f} "
              f"{r['decisions']['f1']:>7.2f} "
              f"{r['hallucination_rate']*100:>6.1f}% "
              f"{r['latency_seconds']:>7.2f} "
              f"{r['tokens']:>6}")
    print("\n" + "=" * 78)
    print("AGGREGATE METRICS")
    print("=" * 78)
    ai = agg["action_items"]
    de = agg["decisions"]
    print(f"Transcripts:              {agg['n_transcripts']}")
    print(f"Action items (macro):     P={ai['macro']['precision']:.2f}  R={ai['macro']['recall']:.2f}  F1={ai['macro']['f1']:.2f}")
    print(f"Action items (micro):     P={ai['micro']['precision']:.2f}  R={ai['micro']['recall']:.2f}  F1={ai['micro']['f1']:.2f}   (TP={ai['micro']['tp']} / Pred={ai['micro']['predicted']} / Actual={ai['micro']['actual']})")
    print(f"Decisions   (macro):      P={de['macro']['precision']:.2f}  R={de['macro']['recall']:.2f}  F1={de['macro']['f1']:.2f}")
    print(f"Decisions   (micro):      P={de['micro']['precision']:.2f}  R={de['micro']['recall']:.2f}  F1={de['micro']['f1']:.2f}   (TP={de['micro']['tp']} / Pred={de['micro']['predicted']} / Actual={de['micro']['actual']})")
    print(f"Hallucination rate:       {agg['hallucination_rate']*100:.2f}%   ({agg['fields_flagged_total']}/{agg['fields_checked_total']} fields)")
    print(f"Schema compliance:        {agg['schema_compliance_rate']*100:.1f}%  (runs with 0 stage errors)")
    print(f"Avg / max latency:        {agg['avg_latency_seconds']}s / {agg['max_latency_seconds']}s")
    print(f"Total tokens consumed:    {agg['total_tokens_used']:,}")
    print()


async def main() -> int:
    transcript_ids = sorted(p.stem for p in TRANSCRIPTS_DIR.glob("*.json"))
    if not transcript_ids:
        print("No transcripts found. Run benchmark/_build_dataset.py first.")
        return 1
    print(f"Benchmarking {len(transcript_ids)} transcripts...")

    llm = LLMClient()
    pipeline = Pipeline(llm)

    results: list[dict[str, Any]] = []
    for tid in transcript_ids:
        print(f"  running {tid}...", end="", flush=True)
        try:
            r = await run_one(pipeline, tid)
            results.append(r)
            print(f" ok ({r['latency_seconds']:.1f}s, {r['tokens']} tok)")
        except Exception as e:  # noqa: BLE001
            print(f" FAILED: {type(e).__name__}: {e}")

    if not results:
        return 1

    agg = aggregate(results)
    print_report(results, agg)

    RESULTS_PATH.write_text(json.dumps({"per_transcript": results, "aggregate": agg}, indent=2))
    print(f"Results written to {RESULTS_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))