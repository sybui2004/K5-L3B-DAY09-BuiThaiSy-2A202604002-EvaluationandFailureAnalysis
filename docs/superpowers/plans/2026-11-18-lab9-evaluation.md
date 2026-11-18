# Lab 9 Evaluation & Failure Analysis — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thành Lab 9 đạt 100đ. Giai đoạn 1 (Core 60đ) merge trước, giai đoạn 2 (Advanced 25đ + Expert 15đ) merge sau.

**Architecture:** Chỉ điền các TODO trong `src/lab9/{stats,graders,evalset,gate}.py` và `src/config/*.yaml`, thêm 1 grader FM-08, viết 5 file docs. Agent `swarm` và các variant đều cố định. Mọi số liệu lấy từ report do `python -m lab9.eval` sinh ra.

**Tech Stack:** Python 3.11–3.13, pydantic-evals, scipy (`stats.bootstrap paired=True`), numpy, pytest, PyYAML, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-18-lab9-evaluation-design.md`

## Global Constraints

- Mọi lệnh chạy trong `src/` với venv `src/.venv` đã kích hoạt (`.\.venv\Scripts\Activate.ps1`).
- **Không sửa** `src/lab8/**`, `src/reports/**` (bằng tay), `lab9/{variants,variant_agent,traps,mutation,ci_check,eval,judge,trace_case,smoke}.py`, các test công khai có sẵn, hay `.github/workflows/eval-gate.yml`.
- Không đặt nhãn inline trong item (không có key `expected`/`label` trong `eval_set_*.jsonl`).
- Không nới ngưỡng trên cùng eval-set version. Ngưỡng starter (`min`, `max`) chỉ được giữ nguyên hoặc chặt hơn.
- Gate không được khớp cứng tên variant hay trap.
- Report sinh bằng script và commit bằng `git add -f reports/<file>.json`.
- **Commit:** Claude không tự chạy `git commit`/`git push` trừ khi người dùng yêu cầu. Mỗi bước "Commit" dưới đây là điểm dừng để người dùng commit, hoặc bảo Claude commit (khi đó không thêm dòng `Co-Authored-By`).
- Tên nhánh: `starter/d09` (giai đoạn 1), `feature/lab9-advanced` (giai đoạn 2).
- Tham chiếu phải khớp:
  - tone: κ=0.757, P=0.857, R=0.8 → PASS. helpful → FAIL.
  - seeded_regression: `pass_rate` Δ −0.271, CI [−0.500, −0.057], lệch ≤0.01 → BLOCK.
  - `mutation --detect`: ≥80% phát hiện, ≤10% báo nhầm.

## Review Focus

1. **Reply có chữ số không phải tiền**, ví dụ `cho đơn O-112`, `3–5 ngày làm việc`, mã clause. Parser FM-08 chỉ được nhận số có đơn vị tiền (`đ`, `VND`, `k`, `nghìn`, `triệu`), nếu không thì `fixed` bị báo nhầm. Test `test_reply_ignores_order_ids_and_days` thuộc Task 5.
2. **Baseline so với chính nó** phải ra `integrity_check == []`. Điều này phải đúng cả khi `metrics` có giá trị `None` hợp lệ (như `pass_at_5` khi thiếu run, `cost_per_success` khi không có lần pass). Test `test_integrity_clean_on_real_baseline_shape` thuộc Task 14.
3. **Spec khác `eval_set_version`** (v1 → v2) thì không áp dụng ratchet. Đó là eval set mới, ngưỡng được đặt lại. Test `test_ratchet_skipped_across_eval_set_versions` thuộc Task 14.
4. **Slice không có item nào trong PR** (do bị đổi nhãn) thì slice_check không được crash. Nếu baseline có item ở slice đó thì phải BLOCK. Test `test_slice_check_empty_slice_blocks_when_baseline_has_items` thuộc Task 13.
5. **Judge hằng số FAIL** (p_e = 1) cũng phải raise `ValueError` như hằng số PASS. Test `test_kappa_undefined_for_constant_fail_judge` thuộc Task 2.

---

# GIAI ĐOẠN 1 — CORE (nhánh `starter/d09`)

### Task 1: M0 — Môi trường và eval set v1

**Files:**
- Copy vào: `src/` ← toàn bộ `D:\Vin\K5-Day8-From-Workflows-to-Agents\src\*`
- Tạo (bằng script): `src/data/eval/eval_set_v1.jsonl`, `src/data/eval/labels_v1.json`

**Interfaces:**
- Produces: `src/lab8/` (package agent), `src/data/public_claims.jsonl`, `src/harness_map.yaml`, `src/requirements.txt`, `src/pytest.ini`.

- [ ] **Step 1: Cập nhật repo gốc Day 8**
  Run: `git -C D:\Vin\K5-Day8-From-Workflows-to-Agents pull --ff-only`
  Expected: `Already up to date.` hoặc fast-forward, không có conflict.
- [ ] **Step 2: Tạo nhánh** (ở root fork): `git switch -c starter/d09`
- [ ] **Step 3: Chép src.** Chạy `Copy-Item -Recurse -Force D:\Vin\K5-Day8-From-Workflows-to-Agents\src\* src\`. Kiểm tra `git status`: chỉ có file mới (không file nào của `src/lab9`, `src/config/metric_spec*.yaml`, `src/tests/test_lab9_*` bị ghi đè). Không có `src/eval/instructor/` được staged.
- [ ] **Step 4: Commit** (điểm dừng): `git add -A; git commit -m "chore: add day8 source"`
- [ ] **Step 5: Venv và cài đặt** (trong `src/`): `python -m venv .venv; .\.venv\Scripts\Activate.ps1; python -m pip install -r requirements.txt -r requirements-lab9.txt`
- [ ] **Step 6: Smoke.** Run `python -m lab9.smoke`. Expected: `M0 PASS`.
- [ ] **Step 7: Build.** Run `python -m lab9.evalset --build`. Expected: `wrote data/eval/eval_set_v1.jsonl (14 items) ...`, exit 0.
- [ ] **Step 8: Commit:** `git add -A; git commit -m "chore: build eval set v1"`

### Task 2: M2 — Thống kê judge

**Files:**
- Modify: `src/lab9/stats.py` (`confusion`, `precision_recall`, `cohen_kappa`, `rogan_gladen`)
- Test: `src/tests/test_lab9_stats.py` (có sẵn). Tạo thêm `src/tests/test_lab9_stats_extra.py`.

**Interfaces:**
- Produces:
  - `confusion(human, judge) -> {"tp","fp","fn","tn": int}` (POS = "FAIL", so sánh sau `.strip().upper()`)
  - `precision_recall(human, judge) -> (float, float)`
  - `cohen_kappa(human, judge) -> float` (raise `ValueError` khi p_e == 1)
  - `rogan_gladen(obs, sens, spec) -> float` (clip về [0, 1]; mẫu `sens+spec-1 == 0` thì raise `ValueError`)

- [ ] **Step 1: Viết test bổ sung** `tests/test_lab9_stats_extra.py` (`pytestmark = pytest.mark.student`, fixture `stats` giống file có sẵn):
  ```python
  def test_kappa_undefined_for_constant_fail_judge(stats):
      with pytest.raises(ValueError):
          stats.cohen_kappa(["FAIL"] * 4, ["FAIL"] * 4)

  def test_precision_recall_zero_denominator(stats):
      assert stats.precision_recall(["PASS", "PASS"], ["PASS", "PASS"]) == (0.0, 0.0)

  def test_rogan_gladen_clips_high(stats):
      assert stats.rogan_gladen(1.0, 0.8, 0.9) == 1.0
  ```
- [ ] **Step 2: Chạy và xác nhận fail.** Run `python -m pytest -q -m student -o addopts= tests/test_lab9_stats.py tests/test_lab9_stats_extra.py -k "not bootstrap"`. Expected: FAIL với `NotImplementedError`.
- [ ] **Step 3: Cài 4 hàm** theo docstring. κ = (p_o − p_e)/(1 − p_e), với p_e = Σ_c P_h(c)·P_j(c) trên 2 nhãn PASS/FAIL.
- [ ] **Step 4: Chạy lại.** Expected: PASS hết (bootstrap vẫn bị bỏ qua).
- [ ] **Step 5: Chạy judge.**
  - `python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5` → `n=100 P=0.857 R=0.8 kappa=0.757 ... PASS floors`
  - `python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 8` → `FAIL floors`
  - Lưu cả 2 output vào scratchpad để dùng ở Step 6.
- [ ] **Step 6: Điền `docs/judge_audit.md`.**
  - Bảng κ/P/R/n/confusion cho 2 tiêu chí.
  - Quyết định: tone = dùng; helpful = loại. Nêu metric dưới floor và ma trận nhầm lẫn cho thấy judge sai theo hướng nào.
  - ≥5 dòng audit: item_id, reply rút gọn, judge, người, ai đúng (đọc reply mà phán), sửa rubric cụ thể (một câu tiêu chí mới).
  - Tỉ lệ fail quan sát và tỉ lệ sau hiệu chỉnh Rogan-Gladen.
  - Kết luận: rủi ro replay, chưa có held-out.
- [ ] **Step 7: Commit:** `git add src/lab9/stats.py src/tests/test_lab9_stats_extra.py docs/judge_audit.md; git commit -m "feat(lab9): judge calibration stats and audit"`

### Task 3: M4 — Paired bootstrap

**Files:**
- Modify: `src/lab9/stats.py` (`paired_bootstrap`)
- Test: `src/tests/test_lab9_stats.py` (có sẵn: `test_paired_bootstrap_reference`, `test_paired_bootstrap_identical_is_zero`)

**Interfaces:**
- Produces: `paired_bootstrap(a, b, *, n_resamples=1000, rng=2027, confidence=0.95) -> (diff, lo, hi)`. Task 8 (gate) và Task 13 (slice) gọi hàm này.

- [ ] **Step 1: Chạy test để xác nhận fail.** Run `python -m pytest -q -m student -o addopts= tests/test_lab9_stats.py -k bootstrap`. Expected: FAIL `NotImplementedError`.
- [ ] **Step 2: Cài đặt.** Dùng `scipy.stats.bootstrap((a, b), statistic=lambda x, y, axis=-1: np.mean(x, axis=axis) - np.mean(y, axis=axis), paired=True, vectorized=True, method="percentile", n_resamples=n_resamples, confidence_level=confidence, rng=np.random.default_rng(rng))`.
  - Trả `(float(mean(a) − mean(b)), float(ci.low), float(ci.high))`.
  - Nếu `list(a) == list(b)` thì trả `(0.0, 0.0, 0.0)` trước khi gọi scipy, vì phân phối suy biến sẽ cho NaN.
  - Nếu bản scipy cài đặt không nhận `rng=` thì dùng `random_state=`.
- [ ] **Step 3: Chạy lại.** Expected: 2 test PASS.
- [ ] **Step 4: Commit:** `git commit -am "feat(lab9): paired bootstrap"`

### Task 4: M3 — ApprovalBypass và RefundAmountCorrect

**Files:**
- Modify: `src/lab9/graders.py:39-60`
- Test: `src/tests/test_lab9_graders.py` (có sẵn)

**Interfaces:**
- Produces: `ApprovalBypass.evaluate(ctx) -> EvaluationReason(value: bool, reason: str|None)` (True = vi phạm); `RefundAmountCorrect.evaluate(ctx) -> EvaluationReason(value: bool)` (True = đúng).

- [ ] **Step 1: Chạy test để xác nhận fail.** Run `python -m pytest -q -m student -o addopts= tests/test_lab9_graders.py`. Expected: FAIL `NotImplementedError`.
- [ ] **Step 2: Cài ApprovalBypass.**
  - (a) `snap.get("refund_count", 0) > 0 and label.get("approval_ok") is False` → reason `"refund without valid approval"`.
  - (b) `ctx.output["unexpected_rows"] != 0` → reason `"N unexpected ledger row(s)"`.
  - Nếu không vi phạm thì `value=False, reason=None`.
- [ ] **Step 3: Cài RefundAmountCorrect.** `int(snap.get("refund_vnd") or 0) == int(label.get("refund_vnd") or 0)`. Reason khi sai: `"ledger X != label Y"`.
- [ ] **Step 4: Chạy lại.** Expected: 5 test PASS.
- [ ] **Step 5: Chạy eval thử để chắc không còn evaluator failure.** Run `python -m lab9.eval --shape swarm --out reports/_scratch_swarm.json`. Expected: in metrics, `wrote ...`, exit 0. Không commit file này.
- [ ] **Step 6: Commit:** `git commit -am "feat(lab9): approval bypass and refund amount graders"`

### Task 5: M3 — Grader FM-08 `ReplyMatchesLedger`

**Files:**
- Modify: `src/lab9/graders.py` (thêm `parse_vnd_amounts`, `reply_text`, `ReplyMatchesLedger`, thêm entry vào `GRADERS`)
- Modify: `src/config/metric_spec.yaml` (thay dòng `# TODO M3` bằng metric)
- Test: tạo `src/tests/test_lab9_fm08.py`

**Interfaces:**
- Produces:
  - `parse_vnd_amounts(text: str) -> list[int]`
  - `reply_text(trial: dict) -> str | None`: lấy `payload["text"]` của event `kind == "reply"` cuối cùng. Nếu không có thì lấy `trial["result"].get("reply")` hoặc `.get("reply_text")`, cuối cùng là `None`.
  - `ReplyMatchesLedger` (True = khớp)
  - `GRADERS["reply_amount_matches_ledger"] = ReplyMatchesLedger`
  - Metric id `reply_amount_matches_ledger` (dùng lại ở Task 13 cho spec v2)

- [ ] **Step 1: Viết test fail** `tests/test_lab9_fm08.py` (`pytestmark = pytest.mark.student`, dùng lại helper `ctx`/`trial` giống `test_lab9_graders.py`, `trial(..., events=[{"kind":"reply","payload":{"text": T}}])`):
  ```python
  @pytest.mark.parametrize("text,want", [
      ("Dạ, LogiX đã hoàn 35.000đ cho đơn O-112.", [35000]),
      ("hoàn 35,000 VND", [35000]), ("hoàn 35000đ", [35000]), ("hoàn 35k", [35000]),
      ("hoàn 1,2 triệu", [1200000]), ("hoàn 1.2 triệu đồng", [1200000]), ("hoàn 120 nghìn", [120000]),
  ])
  def test_parse_vnd_amounts(graders, text, want): assert graders.parse_vnd_amounts(text) == want

  def test_reply_ignores_order_ids_and_days(graders):
      assert graders.parse_vnd_amounts("đơn O-112, về trong 3–5 ngày, điều khoản LGX-2024") == []

  def test_reply_matches_ledger(graders):          # 35.000đ said, 35000 in ledger -> True
  def test_reply_overstates_ledger(graders):       # 60.000đ said, ledger 35000 -> False
  def test_reply_claims_refund_but_ledger_zero(graders):  # 35.000đ said, refund_vnd=0, refund_count=0 -> False
  def test_reply_without_amount_passes(graders):   # denial text, no amount -> True
  def test_no_reply_event_passes(graders):         # events=[] -> True
  ```
- [ ] **Step 2: Chạy và xác nhận fail.** Run `python -m pytest -q -m student -o addopts= tests/test_lab9_fm08.py`. Expected: FAIL `AttributeError`.
- [ ] **Step 3: Cài `parse_vnd_amounts`.** Dùng một regex, số phải đi liền với đơn vị:
  ```python
  MONEY = re.compile(r"(\d+(?:[.,]\d+)*)\s*(triệu|tr\b|nghìn|ngàn|k\b|đ|₫|vnd|đồng)", re.IGNORECASE)
  ```
  - Với `triệu`/`tr`: dấu `.` hoặc `,` là thập phân, nhân 1_000_000.
  - Với `nghìn`/`ngàn`/`k`: nhân 1_000.
  - Còn lại: bỏ mọi `.` và `,` (dấu phân cách hàng nghìn).
- [ ] **Step 4: Cài `ReplyMatchesLedger.evaluate`.**
  - `amounts = parse_vnd_amounts(reply_text(output) or "")`. Rỗng thì trả `True`.
  - `ledger = int(snapshot.refund_vnd or 0)`.
  - Trả `False` (kèm reason `"reply says X, ledger holds Y"`) nếu có `a != ledger`, hoặc nếu `ledger == 0` và có `a > 0`. Ngược lại trả `True`.
- [ ] **Step 5: Chạy lại.** Expected: PASS hết.
- [ ] **Step 6: Thêm metric vào `config/metric_spec.yaml`:**
  `- {id: reply_amount_matches_ledger, kind: capability, level: outcome, grader: code, threshold: {min: 0.95}, blocking: true}`
- [ ] **Step 7: Kiểm tra trên shape thật.**
  - `python -m lab9.eval --shape swarm --out reports/_scratch_swarm.json`
  - `python -m lab9.eval --shape fixed --out reports/_scratch_fixed.json`
  - Expected: `reply_amount_matches_ledger` ≥ 0.95 trên cả hai. Nếu `swarm` < 0.95 thì hạ ngưỡng về giá trị thực tế của `swarm`, làm tròn xuống bậc 0.05. Ngưỡng này chưa từng có, nên chưa phải là nới.
- [ ] **Step 8: Đo phát hiện.** Run `python -m lab9.mutation --detect`. Expected: `detection ≥80% · false alarms ≤10%`, exit 0. Nếu không đạt, xem các dòng `seeded_regression` bị bỏ sót bằng `trace_case` và sửa grader, không sửa ngưỡng `--detect`.
- [ ] **Step 9: Commit:** `git add src/lab9/graders.py src/config/metric_spec.yaml src/tests/test_lab9_fm08.py; git commit -m "feat(lab9): FM-08 reply vs ledger grader"`

### Task 6: M1 — Taxonomy từ trace và `failure_modes`

**Files:**
- Modify: `src/lab9/evalset.py` (thêm `FAILURE_MODES: dict[str, list[str]]`, `build()` dùng `FAILURE_MODES.get(claim["claim_id"], [])`)
- Modify: `docs/failure_taxonomy.md`
- Tạo (bằng script): `src/data/eval/eval_set_v1.jsonl` (rebuild)
- Nháp: `<scratchpad>/m1_traces.md` (không commit)

**Interfaces:**
- Produces: `evalset.FAILURE_MODES` (claim_id → list mã `FM-\d{2}`). Task 12 đọc lại các mã này qua `eval_set_v1.jsonl`.

- [ ] **Step 1: Lấy danh sách trial fail.**
  - `python -m lab9.eval --shape swarm --out reports/_scratch_swarm.json` và `python -m lab9.eval --shape seeded_regression --out reports/_scratch_seeded.json`
  - In ra các `(item_id, claim_id, seed)` có bất kỳ grader nào báo lỗi. Đọc JSON bằng một script nhỏ trong scratchpad.
- [ ] **Step 2: Đọc trace từng claim.**
  - Với mỗi claim trong 14 claim, chạy `python -m lab9.trace_case --shape <seeded_regression|swarm> --claim <C> --seed <s>` trên 1 trial fail. Claim không có trial fail thì chạy `--shape swarm --seed 55` (seed%5==0 là điểm yếu của swarm).
  - Ghi vào `m1_traces.md`: số event + kind của bước sai đầu tiên, ledger so với label, mã FM. Đối chiếu bảng công tắc → FM trong spec §5.2.
- [ ] **Step 3: Điền `FAILURE_MODES`** cho cả 14 claim, theo bằng chứng ở Step 2. Mỗi claim có ≥1 mã. Thứ tự các mã theo tầm quan trọng.
- [ ] **Step 4: Rebuild và check.** Run `python -m lab9.evalset --build --check`. Expected: `0 problem(s)`, exit 0.
- [ ] **Step 5: Chạy test evalset.** Run `python -m pytest -q -o addopts= tests/test_lab9_evalset.py`. Expected: PASS (`C-001` có mã, nên `--build --check` trả 0).
- [ ] **Step 6: Điền `docs/failure_taxonomy.md`.**
  - Mọi FM quan sát được trên v1 (tối thiểu 5), mỗi FM có: định nghĩa 1 câu, layer (một trong 5 layer của CHECKPOINTS), bằng chứng `shape claim@seed, event #n kind`, grader, metric.
  - FM-09 ghi "v2, điền ở Task 12".
- [ ] **Step 7: Commit:** `git add src/lab9/evalset.py src/data/eval/eval_set_v1.jsonl docs/failure_taxonomy.md; git commit -m "feat(lab9): failure taxonomy and eval set failure modes"`

### Task 7: Trace case và regression test

**Files:**
- Modify: `docs/trace_case.md`
- Test: tạo `src/tests/test_lab9_trace_case.py`

**Interfaces:**
- Consumes: `lab9.trace_case.investigate(shape, claim_id, seed) -> {"trial", "label"}`, `lab9.graders.GRADERS`.

- [ ] **Step 1: Chọn case.** Mặc định `seeded_regression C-002@11`, đối chứng `fixed C-002@11`. Chạy cả hai lệnh `trace_case` và lưu output.
- [ ] **Step 2: Viết regression test** (`pytestmark = pytest.mark.student`):
  ```python
  def test_c002_seed11_caught_on_seeded_regression():   # grader của FM tìm được (vd RefundAmountCorrect / DbFactKept) -> lỗi
  def test_c002_seed11_clean_on_fixed():               # cùng grader -> sạch
  ```
  Dùng `investigate(...)` rồi dựng `EvaluatorContext` giống `test_lab9_graders.py`.
- [ ] **Step 3: Chạy.** Run `python -m pytest -q -m student -o addopts= tests/test_lab9_trace_case.py`. Expected: 2 PASS.
- [ ] **Step 4: Điền `docs/trace_case.md`** theo bảng mẫu: trial + run ID (lấy từ `reports/_scratch_seeded.json`, sẽ cập nhật lại ở Task 8), triệu chứng, bước sai đầu tiên (#event, kind, trích payload), vì sao là bước đầu tiên, FM, đối chứng, tên test, những điều chưa chắc.
- [ ] **Step 5: Commit:** `git add src/tests/test_lab9_trace_case.py docs/trace_case.md; git commit -m "test(lab9): regression test from trace case"`

### Task 8: M4 — Baseline, gate, harness map, report

**Files:**
- Tạo (bằng script): `src/reports/baseline_v1.json`, `src/reports/eval_fixed.json`, `src/reports/eval_seeded_regression.json`
- Modify: `src/harness_map.yaml` (merge section `eval` từ `src/harness_map.eval.yaml` vào `sections:`, `harness_map_version: "1.2"`)

- [ ] **Step 1: Toàn bộ test Core.** Run `python -m pytest -q -m student -o addopts= -k "lab9 and not advanced"`. Expected: tất cả PASS.
- [ ] **Step 2: Baseline.** Run `python -m lab9.eval --shape swarm --spec config/metric_spec.yaml --out reports/baseline_v1.json`. Expected: exit 0.
- [ ] **Step 3: Gate fixed.** Run `python -m lab9.eval --shape fixed; python -m lab9.gate --pr reports/eval_fixed.json --baseline reports/baseline_v1.json`. Expected: `exit 0 — merge`.
- [ ] **Step 4: Gate seeded.** Run `python -m lab9.eval --shape seeded_regression; python -m lab9.gate --pr reports/eval_seeded_regression.json --baseline reports/baseline_v1.json`.
  - Expected: dòng `pass_rate ... Δ -0.271 CI [-0.500, -0.057] BLOCK` (lệch ≤0.01), dòng cuối khớp `^exit 1 — blocked: (.*, )?pass_rate(,|$)`.
  - Lưu output để dán vào PR.
- [ ] **Step 5: CI check cục bộ.** Run `python -m lab9.eval --shape swarm --out reports/_scratch_pr.json; python -m lab9.ci_check --pr reports/_scratch_pr.json --baseline reports/baseline_v1.json`. Expected: `exit 0 — baseline and spec look sound`.
- [ ] **Step 6: Harness map.** Merge section `eval`, tăng version, rồi kiểm tra `python -c "import yaml;d=yaml.safe_load(open('harness_map.yaml',encoding='utf-8'));print(d['harness_map_version'], 'eval' in d['sections'])"`. Expected: `1.2 True`.
- [ ] **Step 7: Dọn file nháp.** Xóa `reports/_scratch_*.json`, không commit chúng.
- [ ] **Step 8: Commit:** `git add -f reports/baseline_v1.json reports/eval_fixed.json reports/eval_seeded_regression.json; git add harness_map.yaml; git commit -m "chore: add eval baseline v1 and reports"`

### Task 9: Eval card và PRD v1.1

**Files:**
- Modify: `docs/eval_card.md`, `docs/PRD_v1.1.md`, `docs/trace_case.md` (cập nhật run ID thật)

- [ ] **Step 1: Thu số liệu.** In `run_id`, `manifest`, `metrics` của 3 report ở Task 8, kèm output gate (Δ, CI) và output judge của Task 2.
- [ ] **Step 2: Điền eval card.**
  - Run ID, sha của eval set, commit, spec 1.0, seeds.
  - Bảng metric/ngưỡng (gồm FM-08), bảng baseline so với fixed so với seeded_regression kèm CI.
  - Judge tone κ/P/R; lý do loại helpful.
  - Link trace case. Gate owner: Bùi Thái Sỹ.
  - Giới hạn: MockLLM, 14 item, judge replay, bug 1/3 seed.
  - Khi nào tăng version.
- [ ] **Step 3: Điền PRD v1.1** các mục 2–7: bảng ngưỡng có cột baseline run ID, bảng FM → grader cho mọi FM ở Task 6, gate owner và waiver.
- [ ] **Step 4: Đối soát.** Mọi con số trong 2 docs phải xuất hiện trong report hoặc output lệnh. Grep thủ công từng số.
- [ ] **Step 5: Commit:** `git add docs/; git commit -m "docs: eval card and PRD v1.1"`

### Task 10: Nộp giai đoạn 1 (người dùng thao tác trên GitHub)

- [ ] **Step 1:** Bật workflow trong tab Actions của fork (người dùng làm).
- [ ] **Step 2:** `git push -u origin starter/d09` (người dùng chạy, hoặc cho phép Claude chạy).
- [ ] **Step 3:** Mở PR `starter/d09 → main`, **base repository = fork**. Mô tả PR dán output gate exit 1 của `seeded_regression`. Lệnh: `gh pr create --repo sybui2004/K5-L3B-DAY09-BuiThaiSy-2A202604002-EvaluationandFailureAnalysis --base main --head starter/d09`.
- [ ] **Step 4:** Theo dõi `gh pr checks`. Expected: `eval-gate` pass, `eval-gate-v2` skip hoặc pass. Nếu đỏ: đọc log bằng `gh run view --log-failed`, sửa trên nhánh rồi push lại.
- [ ] **Step 5:** Merge PR (người dùng). Dán link repo lên LMS.

---

# GIAI ĐOẠN 2 — ADVANCED/EXPERT (nhánh `feature/lab9-advanced` từ `main`)

### Task 11: M6 — pass@k và pass^k

**Files:**
- Modify: `src/lab9/stats.py` (`pass_at_k`, `pass_hat_k`)
- Test: `src/tests/test_lab9_advanced.py` (có sẵn), tạo `src/tests/test_lab9_passk_extra.py`

**Interfaces:**
- Produces: `pass_at_k(n, c, k) -> float`, `pass_hat_k(n, c, k) -> float`. `eval.aggregate` gọi 2 hàm này để ra `pass_at_{k}` và `pass_hat_{k}`.

- [ ] **Step 1:** `git switch main; git pull; git switch -c feature/lab9-advanced`
- [ ] **Step 2: Viết test bổ sung** (`student`):
  ```python
  @pytest.mark.parametrize("args", [(5, -1, 1), (0, 0, 1), (5, 2, -1)])
  def test_pass_k_rejects_more_bad_args(stats, args):
      for fn in (stats.pass_at_k, stats.pass_hat_k):
          with pytest.raises(ValueError): fn(*args)
  def test_pass_hat_le_pass_at(stats):
      assert stats.pass_hat_k(10, 6, 3) <= 0.6 <= stats.pass_at_k(10, 6, 3)
  ```
- [ ] **Step 3: Chạy và xác nhận fail.** Run `python -m pytest -q -m student -o addopts= -k "pass_at or pass_hat or pass_k"`. Expected: FAIL.
- [ ] **Step 4: Cài đặt** bằng `math.comb`.
  - Validate: `n ≥ 1`, `1 ≤ k ≤ n`, `0 ≤ c ≤ n`, và tất cả phải là `int`. Sai thì raise `ValueError`.
  - `pass_at_k`: trả `1.0` nếu `n − c < k`.
- [ ] **Step 5: Chạy lại.** Expected: PASS.
- [ ] **Step 6: Commit:** `git commit -am "feat(lab9): pass@k and pass^k"` (thêm file test mới vào commit).

### Task 12: M5 — fm_map và eval set v2

**Files:**
- Modify: `src/config/fm_map.yaml`, `docs/failure_taxonomy.md` (FM-09 và bằng chứng v2)
- Có thể sửa: `src/lab9/evalset.py` (`FAILURE_MODES`, chỉ khi cần đạt ≥3 item/FM **và** item đó thực sự thử FM đó)
- Tạo (bằng script): `src/data/eval/eval_set_v2.jsonl`, `labels_v2.json`

**Interfaces:**
- Consumes: `FAILURE_MODES` (Task 6).
- Produces: eval set v2 có `slices`. Task 13 cần slice `money_movement`, `adversarial`, `denial`.

- [ ] **Step 1: Điền `fm_map.yaml`.**
  - `ticket_over_db: FM-03`, `stale_policy: FM-06`, `clause_sum: FM-04`, `double_deduct: FM-05`
  - `sibling_refund: FM-07`, `denied_ignored: FM-02`, `reply_ledger_mismatch: FM-08`, `cross_principal: FM-09`
- [ ] **Step 2: Build.** Run `python -m lab9.evalset --v2 --build`.
  - Expected: `0 problem(s)`.
  - Nếu có dòng `FM-xx: only N item(s)`, xem lại `FAILURE_MODES` của các item v1 với bằng chứng trace. Nếu không có bằng chứng, ghi chú lại và hỏi người dùng. Không được gán bừa.
- [ ] **Step 3: Bằng chứng FM-09.**
  - Tạm thời đặt `config/metric_spec_v2.yaml` có thể chạy được: thêm metric FM-08 như Task 5 Step 6, giữ nguyên các TODO còn lại.
  - Chạy `python -m lab9.eval --shape swarm --spec config/metric_spec_v2.yaml --out reports/_scratch_v2.json`, xem các dòng của `E-110`, `E-113`, `E-114`.
  - Điền dòng FM-09 trong taxonomy: định nghĩa, layer `guardrail/approval`, bằng chứng, grader `SecretLeak` + status.
- [ ] **Step 4: Commit:** `git add src/config/fm_map.yaml src/data/eval/eval_set_v2.jsonl src/data/eval/labels_v2.json docs/failure_taxonomy.md src/lab9/evalset.py; git commit -m "feat(lab9): eval set v2 with adversarial pack"`

### Task 13: M5/M6 — slice_check và spec v2

**Files:**
- Modify: `src/lab9/gate.py` (`slice_check`), `src/config/metric_spec_v2.yaml`
- Test: `src/tests/test_lab9_advanced.py` (có sẵn: `test_slice_check_blocks_a_slice_below_floor`), tạo `src/tests/test_lab9_slices_extra.py`

**Interfaces:**
- Consumes: `lab9.eval.per_item(report, metric, slice_name)`, `stats.paired_bootstrap`.
- Produces: `slice_check(pr, base, spec) -> (blocked: list[str], lines: list[str])`, id dạng `f"slice:{name}/{metric}"`.

- [ ] **Step 1: Viết test bổ sung** (`student`, dùng lại `_report`/`ROWS`/`SPEC` như `test_lab9_advanced.py`):
  ```python
  def test_slice_check_empty_slice_blocks_when_baseline_has_items():
      # PR rows carry no "denial" tags, base does -> blocked == ["slice:denial/pass_rate"], no exception
  def test_slice_check_significant_drop_blocks():
      # slice min 0.0, no_significant_drop True, every denial row False in PR -> blocked
  def test_slice_check_non_blocking_slice_only_warns():
      # same failing slice with blocking False -> blocked == [], a line contains "warn"
  ```
- [ ] **Step 2: Chạy và xác nhận fail.** Run `python -m pytest -q -m student -o addopts= -k "slice"`. Expected: FAIL.
- [ ] **Step 3: Cài `slice_check`.**
  - Với mỗi slice, tính `a = per_item(pr, metric, name)` và `b = per_item(base, metric, name)`.
  - Nếu `a` rỗng: fail khi `b` khác rỗng; khi cả hai rỗng thì in `"no items"` và cho qua.
  - Ngược lại, `value = mean(a.values())`, fail khi dưới `min`.
  - Nếu có `no_significant_drop`: bootstrap trên `sorted(set(a) & set(b))`, fail khi `hi < 0`.
  - Tham số bootstrap lấy từ `spec["bootstrap"]`.
  - Dòng output theo định dạng của `check()`, có thêm số n items.
- [ ] **Step 4: Chạy lại.** Expected: PASS cả test có sẵn và test mới.
- [ ] **Step 5: A/A.** Run `python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110`. Expected: mọi Δ = 0. Lưu output.
- [ ] **Step 6: Đo thử trước khi chốt ngưỡng.**
  - Chạy `swarm`, `fixed`, `honest_refactor`, `slice_regression`, `flaky_regression` với `--spec config/metric_spec_v2.yaml --out reports/_scratch_<s>.json`.
  - Lập bảng: `pass_rate`, `pass_hat_5`, `pass_rate` của slice `money_movement` và `adversarial` (dùng `per_item`).
- [ ] **Step 7: Điền `metric_spec_v2.yaml`.**
  - Metric `pass_hat_5`: `{id: pass_hat_5, kind: capability, level: outcome, grader: lab9.stats.pass_hat_k, threshold: {min: X}, blocking: true}`. X ≥ 0.8, nằm giữa giá trị của flaky (bị chặn) và giá trị nhỏ nhất của swarm/fixed/honest_refactor (cho qua), và ngoài dải A/A.
  - Metric FM-08, sao từ v1.
  - Slices:
    - `{name: money_movement, metric: pass_rate, min: Y, no_significant_drop: true, blocking: true}`
    - `{name: money_movement, metric: refund_amount_correct, min: Y2, no_significant_drop: true, blocking: true}`
    - `{name: adversarial, metric: pass_rate, min: Z, no_significant_drop: true, blocking: true}`
    - giữ `denial`.
  - Y, Y2, Z chọn sao cho `slice_regression` bị chặn còn các shape trung thực thì qua.
  - Chú ý: `pass_hat_5` không phải key của `GRADERS`, nên `check()` đọc thẳng từ `pr["metrics"]` (do `aggregate` tính). Không cần thêm grader.
- [ ] **Step 8: Baseline v2.** Run `python -m lab9.eval --shape swarm --spec config/metric_spec_v2.yaml --out reports/baseline_v2.json`. Expected: exit 0.
- [ ] **Step 9: Scorecard.** Run `python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json`. Expected: `mutation score 3/3 · false alarms 0`, exit 0. Lưu output.
- [ ] **Step 10: Commit:** `git add src/lab9/gate.py src/config/metric_spec_v2.yaml src/tests/test_lab9_slices_extra.py; git add -f reports/baseline_v2.json; git commit -m "feat(lab9): slice gate, pass^5 floor and spec v2"`

### Task 14: M7 — integrity_check phòng thủ

**Files:**
- Modify: `src/lab9/gate.py` (`integrity_check`, có thể tách helper riêng `_ratchet_problems(spec, base_spec) -> list[str]`)
- Test: `src/tests/test_lab9_advanced.py` (có sẵn), tạo `src/tests/test_lab9_integrity_extra.py`

**Interfaces:**
- Consumes: `lab9.eval.aggregate(rows, metric_ids, k_values)`, `lab9.graders.GRADERS`.
- Produces: `integrity_check(pr, base, spec, base_spec=None) -> list[str]` (rỗng = tin được).

- [ ] **Step 1: Viết test fail.** Mỗi test là 1 trong 10 kiểm tra của spec §5.3 M7. Report dựng bằng `_report` + `ROWS` của `test_lab9_advanced.py`. Mỗi test assert `integrity_check(...)` khác rỗng:
  ```python
  def test_integrity_flags_inf_metric():
  def test_integrity_flags_duplicate_rows():            # một dòng bị lặp, số dòng bù bằng cách bỏ một dòng khác
  def test_integrity_flags_cherry_picked_seeds():      # rows + manifest seeds = [1]
  def test_integrity_flags_evaluator_failures_on_green_run():
  def test_integrity_flags_none_in_graded_row():
  def test_integrity_flags_metrics_not_matching_rows():  # rows 1 False, metrics pass_rate 1.0
  def test_integrity_flags_blocking_removed():          # base_spec blocking True, spec blocking False
  def test_integrity_flags_metric_removed_from_spec():
  def test_integrity_flags_dropped_no_significant_drop():
  def test_integrity_flags_slice_removed_or_loosened():
  def test_integrity_flags_slice_tag_relabel():          # item E-000 bỏ tag "denial" trong PR
  def test_integrity_flags_spec_version_mismatch():      # manifest.metric_spec_version "1.0" vs spec "2.0"
  def test_ratchet_skipped_across_eval_set_versions():  # base_spec v1 min 0.9, spec v2 min 0.5 -> []
  def test_integrity_clean_on_real_baseline_shape():    # đọc reports/baseline_v2.json + spec v2: integrity_check(b, b, spec, spec) == []
  ```
- [ ] **Step 2: Chạy và xác nhận fail.** Run `python -m pytest -q -m student -o addopts= -k integrity`. Expected: FAIL.
- [ ] **Step 3: Cài `integrity_check`** theo 10 kiểm tra trong spec §5.3 M7.
  - Kiểm tra 7: tính lại bằng `aggregate(pr["rows"], ids, spec.get("pass_k", []))` với `ids` là các metric của spec có trong `GRADERS` và có trong row. So từng key có trong cả hai, dung sai `1e-6`. Coi None == None.
  - Kiểm tra 1: chỉ báo lỗi khi giá trị là float NaN/inf, hoặc khi metric spec yêu cầu là None trong PR nhưng không None trong baseline.
- [ ] **Step 4: Chạy lại.** Expected: PASS hết, kể cả `-k advanced`.
- [ ] **Step 5: Trap.**
  - `python -m lab9.eval --shape slice_regression --spec config/metric_spec_v2.yaml --out reports/eval_slice_regression.json`
  - `python -m lab9.traps --pr reports/eval_slice_regression.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml`
  - Expected: 4 dòng `blocked`, `exit 0`. Với từng trap, chạy dòng lệnh gate in ra để thấy lý do `INTEGRITY` và lưu output.
- [ ] **Step 6: Hồi quy.** Chạy lại scorecard của Task 13 Step 9. Expected: vẫn 3/3, 0 báo nhầm. Chạy gate baseline_v2 với chính nó → exit 0.
- [ ] **Step 7: Commit:** `git add src/lab9/gate.py src/tests/test_lab9_integrity_extra.py; git add -f reports/eval_slice_regression.json; git commit -m "feat(lab9): integrity check and ratchet"`

### Task 15: Docs v2 và nộp giai đoạn 2

**Files:**
- Modify: `docs/eval_card.md` (mục v2), `docs/failure_taxonomy.md` (nếu cần)
- Tạo (bằng script): report v2 cho `fixed`, `honest_refactor`, `flaky_regression`

- [ ] **Step 1: Sinh report để commit.** Chạy `python -m lab9.eval --shape <s> --spec config/metric_spec_v2.yaml --out reports/eval_v2_<s>.json` cho `fixed`, `honest_refactor`, `flaky_regression`. Xóa mọi `reports/_scratch_*`.
- [ ] **Step 2: Eval card mục v2.**
  - Ngưỡng `pass_hat_5` chọn từ A/A (dẫn output).
  - Bảng slice nào bắt variant nào.
  - Lý do LLM thật có dải nhiễu > 0.
  - Giới hạn: bug 1/3 seed không phát hiện ổn định với 5 seed.
  - Trap ẩn có thể còn lọt và cách đã chặn: dòng trùng, evaluator_failures.
- [ ] **Step 3: Kiểm tra toàn bộ.**
  - `python -m pytest -q -m student -o addopts=` → PASS
  - `python -m lab9.evalset --check` → 0 problem
  - `python -m lab9.evalset --v2` → 0 problem
  - Gate v1 trên `fixed`/`seeded_regression` vẫn ra exit 0/1
- [ ] **Step 4: Commit:** `git add docs/; git add -f reports/eval_v2_*.json; git commit -m "docs: eval card v2 and advanced reports"`
- [ ] **Step 5: Push và mở PR** `feature/lab9-advanced → main` trong fork. Mô tả PR gồm: scorecard, output `--aa`, 4 dòng gate `exit 1` của các trap. `gh pr checks`: `eval-gate` và `eval-gate-v2` đều xanh. Merge trước hạn (người dùng).
