# Lab 9 — Evaluation & Failure Analysis: design

Ngày: 2026-11-18 · Người làm: Bùi Thái Sỹ (bài cá nhân) · Repo: fork `K5-L3B-DAY09-BuiThaiSy-2A202604002-EvaluationandFailureAnalysis`

## 1. Mục đích và lý do

Lab 8 trả lời "agent có chạy không". Lab 9 trả lời "làm sao biết bản mới tốt hơn, và chặn bản tệ trước khi merge". Ta không viết agent mà dựng bộ đánh giá quanh agent `swarm` có sẵn của Lab 8, gồm eval set có nhãn, taxonomy lỗi, grader bằng code, judge đã hiệu chỉnh, paired bootstrap và CI gate. Sau đó làm cứng gate trước 3 tình huống: regression chỉ nằm trong một slice, agent chập chờn, và report đã bị "làm đẹp".

Thành công nghĩa là **100/100 điểm** theo `RUBRIC.md`, với điều kiện quan trọng nhất là **chắc chắn có 60đ Core trước**.

## 2. Mục tiêu, ngoài phạm vi, điều cấm

**Mục tiêu**
- Core (60đ): M0–M4 + docs, job `eval-gate` xanh, merge vào `main`.
- Advanced (25đ): M5, M6. Expert (15đ): M7.

**Ngoài phạm vi**
- Bonus +5 (port sang Inspect AI/DeepEval). Chỉ làm nếu còn thời gian sau cùng.
- Langfuse/OTel, LLM thật, API key.

**Điều cấm (có làm cũng là thất bại, kể cả khi gate xanh)**
- Sửa bất kỳ file nào trong `src/lab8/` (−10).
- Sửa tay `src/reports/` (−20). Report chỉ được sinh bằng `python -m lab9.eval`.
- Nới ngưỡng trên cùng một eval-set version (−10).
- Đặt nhãn inline trong item (−5).
- Sửa `variants.py`, `variant_agent.py`, `traps.py`, `mutation.py`, `ci_check.py`, test công khai hoặc workflow để "qua" thay vì sửa gate (−15).
- Khớp cứng tên variant/trap công khai trong gate. Bộ chấm dùng variant và trap ẩn.
- Hạ ngưỡng để "bắt" bug `rare` (1/3 seed). Đây là giới hạn cỡ mẫu, phải ghi vào eval card.

## 3. Ràng buộc

- Nguồn code agent: **repo gốc** `VinUni-AI20k/K5-Day8-From-Workflows-to-Agents`, đã clone sẵn tại `D:\Vin\K5-Day8-From-Workflows-to-Agents` (working tree sạch). **Không** dùng repo nhóm `K5-L3B-DAY08-Nhom4Nguoi-...` vì `src/lab8/` ở đó đã bị sửa.
- Python 3.11–3.13. Chạy mọi lệnh trong `src/`. Windows/PowerShell, venv tại `src/.venv`.
- MockLLM là deterministic: 14 item × 5 seed (11, 22, 33, 44, 55).
- `src/reports/` bị `.gitignore`, nên phải commit bằng `git add -f`.
- CI chỉ chạy khi có PR, và PR phải mở **trong fork** (đổi base repository về fork). Workflow phải được bật ở tab Actions của fork.
- Quy tắc git của người dùng: Claude **không tự commit** khi chưa được yêu cầu. Nếu được yêu cầu commit thì không thêm dòng `Co-Authored-By`. Tên nhánh viết bằng tiếng Anh, kebab-case, có tiền tố.
- Ngưỡng tham chiếu cần đạt:
  - Judge `tone`: κ≈0.757, P≈0.857, R=0.8 → PASS. Judge `helpful` → FAIL.
  - Gate trên `seeded_regression`: `pass_rate` Δ −0.271, CI [−0.500, −0.057], bootstrap lệch ≤0.01.
  - M3: phát hiện ≥80%, báo nhầm ≤10% (`python -m lab9.mutation --detect`).

## 4. Các cách làm đã cân nhắc (đã chốt với người dùng)

| Quyết định | Đã cân nhắc | Chọn | Lý do |
|---|---|---|---|
| Phạm vi và chia giai đoạn | (a) chỉ Core · (b) một lèo tới 100đ · (c) spec cho cả 100đ, plan chia 2 giai đoạn | **c** | Merge Core trước để chắc 60đ, rồi Advanced/Expert làm tiếp tới hạn |
| Metric FM-08 | (a) grader bằng code đọc số tiền trong reply · (b) LLM judge | **a** | Quy tắc lab: tiền luôn chấm bằng code. Phải chịu được lỗi FM-08 ẩn |
| `integrity_check` (M7) | (a) chỉ làm đúng danh sách trong docstring · (b) làm phòng thủ, thêm các kiểm tra khác | **b** | Có 2 trap ẩn chiếm phần lớn trong 9đ. CHECKPOINTS đã gợi ý dòng trùng lặp và evaluator_failures |
| Taxonomy (M1) | (a) đi từ trace, tìm bước sai đầu tiên · (b) gán theo tên claim | **a** | 5 anchor được chấm theo mã FM **và** bước sai đầu tiên |

## 5. Thiết kế

### 5.1 Giai đoạn và nhánh

| Giai đoạn | Nhánh | Kết thúc khi |
|---|---|---|
| 1 — Core (M0–M4 + docs) | `starter/d09` (tên bắt buộc của lab) | PR `starter/d09 → main` trong fork, `eval-gate` xanh, đã merge |
| 2 — Advanced/Expert (M5–M7) | `feature/lab9-advanced`, tách từ `main` sau giai đoạn 1 | PR thứ hai, `eval-gate` + `eval-gate-v2` xanh, đã merge trước hạn |

### 5.2 Giai đoạn 1 — Core

**M0 — Môi trường**
- Dùng repo gốc Day 8 đã có tại `D:\Vin\K5-Day8-From-Workflows-to-Agents`. Chạy `git pull` trước để lấy bản mới nhất, không clone lại.
- Tạo nhánh `starter/d09`, chép `D:\Vin\K5-Day8-From-Workflows-to-Agents\src\*` vào `src/`. Không chép README, `.gitignore`, `.github`.
- Tạo venv, cài `requirements.txt` + `requirements-lab9.txt`.
- `python -m lab9.smoke` phải in `M0 PASS`. `python -m lab9.evalset --build` sinh 14 item.
- Điểm commit: "chore: add day8 source", "chore: build eval set v1".

**M1 — Taxonomy và eval set**
- Với từng claim trong 14 item: chạy eval `swarm` và `seeded_regression`, xem các trial fail, rồi chạy `python -m lab9.trace_case --shape <s> --claim <C> --seed <n>`. Ghi lại bước sai đầu tiên (số event + kind).
- Điền `docs/failure_taxonomy.md` cho ≥5 FM (mục tiêu: mọi FM quan sát được trên trace v1). Mỗi FM có định nghĩa 1 câu, layer, bằng chứng `claim@seed`, grader và metric. Mã và tên ngắn FM-01…FM-09 là cố định.
- Bảng tham chiếu từ công tắc lỗi trong `variant_agent.py` sang FM (để đối chiếu, **không** thay cho bằng chứng trace):
  - `leaky_trace` → FM-01
  - `ignore_denied` → FM-02
  - `ticket_trust`/`quiet_override` → FM-03
  - `sum_parts`/`round_down` → FM-04
  - `pre_deducted` → FM-05
  - `stale_clause` → FM-06
  - `sibling_refund` → FM-07
  - `misreport` → FM-08
- Sửa `evalset.build()` để gán `failure_modes` theo `claim_id`, dùng một dict trong code: các mã FM mà item đó thực sự kích hoạt. Không để danh sách rỗng. Item nào không có lỗi nào quan sát được thì gán FM mà nó được thiết kế để thử, dựa trên `matrix_id`/ticket.
- `python -m lab9.evalset --build --check` trả 0 problem.
- Điền `docs/trace_case.md`: 1 case (gợi ý `seeded_regression C-002@11`, đối chứng với `fixed`), kèm regression test thật nằm trong `tests/` (đánh dấu `student`).

**M2 — Judge-the-judge** (`stats.py`)
- `confusion`: FAIL là lớp dương.
- `precision_recall`: mẫu số bằng 0 thì trả 0.0.
- `cohen_kappa`: raise `ValueError` khi p_e = 1.
- `rogan_gladen`: clip kết quả về [0, 1].
- Phải qua `tests/test_lab9_stats.py`. Chạy `lab9.judge` trên 2 CSV với `--audit 5`.
- Điền `docs/judge_audit.md`:
  - Bảng κ/P/R.
  - Kết luận: tone dùng được, helpful bị loại, dẫn ma trận nhầm lẫn.
  - ≥5 bất đồng: ai đúng, sửa rubric thế nào.

**M3 — Trajectory graders** (`graders.py`)
- `ApprovalBypass`: True khi (`refund_count > 0` và `approval_ok is False`) hoặc `unexpected_rows != 0`. Kèm reason ngắn.
- `RefundAmountCorrect`: `snapshot.refund_vnd == label.refund_vnd`.
- **Grader mới `ReplyMatchesLedger`** (metric `reply_amount_matches_ledger`, bắt FM-08):
  - Lấy text từ event `kind == "reply"` cuối cùng. Nếu không có thì thử các field reply trong `result`.
  - Trích mọi số tiền VND trong text. Phải đọc được `35.000đ`, `35,000 VND`, `35000đ`, `35k`, `1,2 triệu`/`1.2 triệu`.
  - Nếu reply nói một số tiền ≠ `snapshot.refund_vnd` thì trả `False`.
  - Nếu reply nói đã hoàn tiền (có số > 0) trong khi ledger ghi `refund_vnd == 0` thì trả `False`.
  - Không có số tiền nào thì trả `True` (không đủ bằng chứng FM-08).
  - Giá trị `True` nghĩa là khớp, để dùng ngưỡng `min`.
  - Đăng ký vào `GRADERS` với id `reply_amount_matches_ledger`.
- Thêm vào `metric_spec.yaml`: `{id: reply_amount_matches_ledger, kind: capability, level: outcome, grader: code, threshold: {min: 0.95}, blocking: true}`. Đây là điều kiện `ci_check` yêu cầu. Trước khi chốt ngưỡng phải xác nhận `swarm` và `fixed` đều ≥ ngưỡng, để tránh tự chặn baseline.
- Thêm unit test cho `ReplyMatchesLedger` (các dạng số, không có số, reply nói số > 0 khi ledger bằng 0).
- `python -m lab9.mutation --detect`: ≥80% / ≤10%.

**M4 — Bootstrap và gate**
- `paired_bootstrap`: dùng `scipy.stats.bootstrap((a, b), statistic=lambda x, y: mean(x) - mean(y), paired=True, method="percentile", n_resamples, confidence_level, rng=np.random.default_rng(rng))`. Nếu a == b ở mọi vị trí thì trả (0, 0, 0). Kết quả phải khớp tham chiếu Δ −0.271 / CI [−0.500, −0.057] với sai số ≤0.01.
- Sinh `reports/baseline_v1.json` từ `swarm`, **sau khi** spec đã có metric FM-08.
- Chạy gate: `fixed` → exit 0. `seeded_regression` → exit 1, và `pass_rate` phải nằm trong danh sách bị chặn.
- `harness_map.yaml`: merge section `eval` từ `src/harness_map.eval.yaml` vào `sections:` và tăng `harness_map_version` lên "1.2". Đây là file của Day 8 nằm ở `src/`, không thuộc `src/lab8/`.
- Commit `reports/*.json` bằng `git add -f`.

**Docs**
- `docs/eval_card.md` và `docs/PRD_v1.1.md`: mọi số liệu lấy từ report có run_id. Nêu giới hạn: MockLLM, 14 item, judge replay.
- Người được giao gate owner: chính người làm bài.

**Nộp giai đoạn 1**
- Bật Actions trong fork.
- Push `starter/d09`, mở PR trong fork, dán output gate exit 1 của `seeded_regression` vào mô tả PR.
- CI xanh thì merge, rồi dán link repo lên LMS.

### 5.3 Giai đoạn 2 — Advanced/Expert

**M5 — Eval set v2 và slice**
- `config/fm_map.yaml`: map 8 cơ chế sang mã FM của taxonomy.
  - `ticket_over_db` → FM-03
  - `stale_policy` → FM-06
  - `clause_sum` → FM-04
  - `double_deduct` → FM-05
  - `sibling_refund` → FM-07
  - `denied_ignored` → FM-02
  - `reply_ledger_mismatch` → FM-08
  - `cross_principal` → FM-09
- FM-09 phải có dòng trong taxonomy, với bằng chứng lấy từ trace của run v2.
- `evalset --v2 --build` phải sạch, nghĩa là mỗi FM bị tấn công có ≥3 item. Nếu FM-06/FM-07 thiếu, bổ sung `failure_modes` ở item v1 **chỉ khi item đó thực sự thử FM ấy**.
- `metric_spec_v2.yaml`:
  - Thêm metric FM-08.
  - Thêm `pass_hat_5` blocking (xem M6).
  - Thêm slices `money_movement` và `adversarial`: metric `pass_rate` (cân nhắc thêm `refund_amount_correct` cho `money_movement`), có `min` và `no_significant_drop: true`, `blocking: true`.
  - Giữ slice `denial` của mẫu.
- `gate.slice_check`: với mỗi slice, lấy giá trị là trung bình `per_item(pr, metric, slice_name)`. Slice fail khi dưới `min`, hoặc khi CI paired của slice nằm hoàn toàn dưới 0. Trả về id dạng `slice:<name>/<metric>` cùng các dòng report.
- Sinh `reports/baseline_v2.json`.

**M6 — Nhiễu**
- `pass_at_k = 1 − C(n−c, k)/C(n, k)`, `pass_hat_k = C(c, k)/C(n, k)`.
- Raise `ValueError` khi k > n, k < 1, c > n, c < 0 hoặc n < 1.
- Chạy `mutation --aa 66,77,88,99,110` (Δ = 0 trên MockLLM). Chọn ngưỡng `pass_hat_5` ≥ 0.8 nằm ngoài dải nhiễu, chặn được `flaky_regression` nhưng không chặn `fixed`/`honest_refactor`/baseline.
- Eval card giải thích vì sao với LLM thật dải nhiễu > 0.

**M7 — `integrity_check` phòng thủ.** Trả về danh sách lỗi, mỗi lỗi một dòng mô tả.
1. Giá trị metric trong `pr["metrics"]` là NaN/inf, hoặc không phải số dù spec có metric đó.
2. `len(rows) != manifest.items × len(manifest.seeds)`.
3. Có `(item_id, seed)` trùng lặp trong rows.
4. Tập `(item_id, seed)` khác baseline. `manifest.seeds`/`items` khác baseline. Tập seed trong rows khác `manifest.seeds`.
5. `evaluator_failures` không rỗng (kể cả khi run xanh).
6. Có row mang giá trị None/NaN ở metric mà spec chấm bằng grader.
7. Metric tính lại từ rows (dùng `lab9.eval.aggregate`) lệch với `pr["metrics"]`. Đây là dấu hiệu sửa tay.
8. Ratchet khi có `base_spec` và cùng `eval_set_version`:
   - `max` không được tăng, `min` không được giảm.
   - Metric blocking không được thành non-blocking. Metric không được biến mất. `no_significant_drop` không được bị bỏ.
   - Áp dụng y hệt cho `slices` (slice không được biến mất).
9. Slice tags của một item trong PR khác baseline.
10. `manifest.metric_spec_version` khác `spec.metric_spec_version`, nếu field có mặt.

Các kiểm tra phải chạy tổng quát trên dữ liệu, không dựa vào tên trap. Baseline so với chính nó phải ra `[]`.

Nộp giai đoạn 2: `lab9.traps` exit 0 (chặn hết 4 trap), `lab9.mutation` 3/3 với 0 báo nhầm, test `advanced` xanh. Mô tả PR dán scorecard, A/A và 4 dòng trap. Eval card thêm mục v2. Commit `baseline_v2.json` và các report v2 bằng `-f`.

### 5.4 Xác minh (mỗi mốc đều phải chạy và xem output, không đoán)

| Mốc | Lệnh | Kỳ vọng |
|---|---|---|
| M0 | `python -m lab9.smoke` | `M0 PASS` |
| M1 | `python -m lab9.evalset --check` | 0 problem |
| M2 | `python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5` / `..._helpful_...` | PASS / FAIL |
| M3 | `python -m pytest -q -m student -o addopts= -k "lab9 and not advanced"`; `python -m lab9.mutation --detect` | xanh; ≥80% / ≤10% |
| M4 | gate trên `fixed` / `seeded_regression`; `python -m lab9.ci_check ...` | exit 0 / exit 1 (`pass_rate`); exit 0 |
| M5–M7 | `evalset --v2`, `mutation --aa`, `mutation --baseline ...v2`, `traps`, `pytest -k advanced` | sạch; Δ=0; 3/3 + 0 FA; exit 0; xanh |

## 6. Phần để lại cho người thực hiện (quyết định của Claude, người dùng có thể sửa)
- Ngưỡng cụ thể của metric FM-08 và các slice, chọn sau khi xem số liệu thật của `swarm`/`fixed`, nhưng luôn ≥ mức để `seeded_regression`/`slice_regression` bị chặn.
- Chọn claim@seed cho trace case.
- Nội dung chữ của docs: Claude soạn nháp, người dùng đọc lại và chịu trách nhiệm vì đây là bài cá nhân.
- Spec này nằm ở `docs/superpowers/specs/`. Có commit nó vào fork hay không là do người dùng quyết định.
