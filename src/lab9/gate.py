"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item
from lab9.graders import GRADERS


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)
    Also caught: duplicated (item, seed) rows, rows whose seeds differ from the manifest, metrics
    that do not match a recomputation from the rows (hand-edited numbers), and a report produced
    under a different metric_spec_version than the spec it is judged by."""
    problems: list[str] = []
    rows, base_rows = pr.get("rows") or [], base.get("rows") or []
    man, base_man = pr.get("manifest") or {}, base.get("manifest") or {}
    spec_ids = [m["id"] for m in spec.get("metrics") or []]
    graded = [m for m in spec_ids if m in GRADERS]

    # 1. metric values must be finite numbers; None only where the baseline is None too
    for mid, val in (pr.get("metrics") or {}).items():
        if isinstance(val, float) and not math.isfinite(val):
            problems.append(f"metric {mid} is {val}")
    # Graded metrics only: derived ones (cost_per_success, pass_k) are legitimately None, e.g. with 0 passes.
    for mid in graded:
        if (pr.get("metrics") or {}).get(mid) is None and (base.get("metrics") or {}).get(mid) is not None:
            problems.append(f"metric {mid} missing in PR but present in baseline")

    # 2-4. row count, duplicates, (item, seed) coverage, seeds
    seeds = list(man.get("seeds") or [])
    want = (man.get("items") or 0) * len(seeds)
    if len(rows) != want:
        problems.append(f"{len(rows)} rows, manifest says {man.get('items')} items x {len(seeds)} seeds = {want}")
    keys = [(r.get("item_id"), r.get("seed")) for r in rows]
    dups = sorted({k for k in keys if keys.count(k) > 1}, key=str)
    if dups:
        problems.append(f"duplicate (item, seed) rows: {dups[:5]}")
    base_keys = {(r.get("item_id"), r.get("seed")) for r in base_rows}
    if set(keys) != base_keys:
        miss, extra = base_keys - set(keys), set(keys) - base_keys
        problems.append(f"(item, seed) set differs from baseline: {len(miss)} missing, {len(extra)} extra")
    if sorted(seeds) != sorted(base_man.get("seeds") or []):
        problems.append(f"seeds {seeds} differ from baseline {base_man.get('seeds')}")
    if man.get("items") != base_man.get("items"):
        problems.append(f"items {man.get('items')} differ from baseline {base_man.get('items')}")
    if {r.get("seed") for r in rows} - set(seeds):
        problems.append("rows carry seeds not listed in the manifest")

    # 5-6. crashed graders, missing grades
    if pr.get("evaluator_failures"):
        problems.append(f"{len(pr['evaluator_failures'])} evaluator failure(s): {pr['evaluator_failures'][0]}")
    for mid in graded:
        bad = [f"{r.get('item_id')}@{r.get('seed')}" for r in rows if r.get(mid) is None
               or (isinstance(r.get(mid), float) and math.isnan(r[mid]))]
        if bad:
            problems.append(f"{len(bad)} row(s) without a {mid} grade, first {bad[0]}")

    # 7. reported metrics must equal a recomputation from the rows
    for mid in graded:
        vals = [r[mid] for r in rows if r.get(mid) is not None]
        if not vals or mid not in (pr.get("metrics") or {}):
            continue
        safety = mid in ("secret_leak", "approval_bypass")
        recomputed = sum(bool(v) for v in vals) if safety else round(sum(bool(v) for v in vals) / len(vals), 4)
        got = pr["metrics"][mid]
        if not isinstance(got, (int, float)) or abs(float(got) - recomputed) > 1e-6:
            problems.append(f"metric {mid} = {got} but recomputed from rows = {recomputed}")
    # ... including the pass_k family (pass_hat_5 is blocking in v2) and pass_5, from per-item pass_rate.
    by_item: dict[str, list[bool]] = {}
    for r in rows:
        by_item.setdefault(r.get("item_id"), []).append(bool(r.get("pass_rate")))
    derived: dict[str, float | None] = {}
    if by_item:
        derived["pass_5"] = round(sum(all(v) for v in by_item.values()) / len(by_item), 4)
        for k in spec.get("pass_k") or []:
            if min(len(v) for v in by_item.values()) >= k:
                for name, fn in (("pass_at", stats.pass_at_k), ("pass_hat", stats.pass_hat_k)):
                    est = [fn(len(v), sum(v), k) for v in by_item.values()]
                    derived[f"{name}_{k}"] = round(sum(est) / len(est), 4)
    for mid, want_v in derived.items():
        got = (pr.get("metrics") or {}).get(mid)
        if mid in (pr.get("metrics") or {}) and got is not None and (
                not isinstance(got, (int, float)) or abs(float(got) - want_v) > 1e-6):
            problems.append(f"metric {mid} = {got} but recomputed from rows = {want_v}")

    # 8. ratchet: same eval set => thresholds only get stricter. "Same" = same version label OR the
    # same eval-set file: bumping eval_set_version without changing the set is a ratchet dodge.
    if base_spec is not None:
        same_version = spec.get("eval_set_version") == base_spec.get("eval_set_version")
        same_file = spec.get("eval_set") is not None and spec.get("eval_set") == base_spec.get("eval_set")
        if same_file and not same_version:
            problems.append(f"eval_set_version {base_spec.get('eval_set_version')} -> {spec.get('eval_set_version')} "
                            f"but the eval set file {spec.get('eval_set')} is unchanged")
        if same_version or same_file:
            problems += _ratchet_problems(spec, base_spec)

    # 9. slice tags are part of the eval set, not of the PR: compare row by row with the baseline
    # (untagging only the failing seeds keeps the per-item union and still hides them), and every
    # row of one item must carry the same tags.
    base_tags = {(r.get("item_id"), r.get("seed")): sorted(r.get("slices") or []) for r in base_rows}
    relabelled = sorted({r.get("item_id") for r in rows
                         if (r.get("item_id"), r.get("seed")) in base_tags
                         and sorted(r.get("slices") or []) != base_tags[(r.get("item_id"), r.get("seed"))]}, key=str)
    if relabelled:
        problems.append(f"slice tags differ from baseline for {relabelled[:5]}")
    per_item_tags: dict[str, set] = {}
    for r in rows:
        per_item_tags.setdefault(r.get("item_id"), set()).add(tuple(sorted(r.get("slices") or [])))
    mixed = sorted((i for i, t in per_item_tags.items() if len(t) > 1), key=str)
    if mixed:
        problems.append(f"slice tags differ between seeds of the same item: {mixed[:5]}")

    # 10. the report must come from the spec it is judged by
    msv, ssv = man.get("metric_spec_version"), spec.get("metric_spec_version")
    if msv is not None and ssv is not None and str(msv) != str(ssv):
        problems.append(f"report metric_spec_version {msv} != spec {ssv}")
    return problems


def _ratchet_problems(spec: dict, base_spec: dict) -> list[str]:
    """Looser-than-base thresholds on the same eval-set version (metrics and slices)."""
    out: list[str] = []

    def compare(label: str, new: dict | None, old: dict, th_new: dict, th_old: dict) -> None:
        if new is None:
            out.append(f"ratchet: {label} removed")
            return
        if old.get("blocking") and not new.get("blocking"):
            out.append(f"ratchet: {label} no longer blocking")
        for k in ("max", "max_increase"):
            if k in th_old and (k not in th_new or th_new[k] > th_old[k]):
                out.append(f"ratchet: {label} {k} {th_old[k]} -> {th_new.get(k)}")
        if "min" in th_old and ("min" not in th_new or th_new["min"] < th_old["min"]):
            out.append(f"ratchet: {label} min {th_old['min']} -> {th_new.get('min')}")
        if th_old.get("no_significant_drop") and not th_new.get("no_significant_drop"):
            out.append(f"ratchet: {label} dropped no_significant_drop")

    new_m = {m["id"]: m for m in spec.get("metrics") or []}
    for m in base_spec.get("metrics") or []:
        n = new_m.get(m["id"])
        compare(f"metric {m['id']}", n, m, (n or {}).get("threshold") or {}, m.get("threshold") or {})
    new_s = {(s["name"], s["metric"]): s for s in spec.get("slices") or []}
    for s in base_spec.get("slices") or []:
        n = new_s.get((s["name"], s["metric"]))
        compare(f"slice {s['name']}/{s['metric']}", n, s, n or {}, s)
    return out


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for sl in spec.get("slices") or []:
        name, metric = sl["name"], sl["metric"]
        sid = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, slice_name=name), per_item(base, metric, slice_name=name)
        verdict, note, val = "ok", "", None
        if not a:
            # A slice that empties out in the PR (relabelled items) is a hidden regression, not a pass.
            verdict = "fail" if b else "ok"
            note = "no items in PR slice" if b else "no items"
        else:
            val = round(sum(a.values()) / len(a), 4)
            if "min" in sl and val < sl["min"]:
                verdict = "fail"
            keys = sorted(set(a) & set(b))
            if sl.get("no_significant_drop") and keys:
                d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                                   n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"
        if verdict != "ok" and sl.get("blocking"):
            blocked.append(sid)
        label = "ok" if verdict == "ok" else ("BLOCK" if sl.get("blocking") else "warn")
        th = {k: sl[k] for k in ("min", "no_significant_drop") if k in sl}
        lines.append(f"  {sid:<34} {val!s:<8} n={len(a):<3} {json.dumps(th):<40} {note:<28} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
