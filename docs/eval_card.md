# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10. Mọi con số dưới đây lấy từ `src/reports/*.json` (sinh bằng `python -m lab9.eval`) và output của `lab9.gate` / `lab9.judge` / `lab9.mutation`.

- **Run ID / eval set SHA:** baseline `E-swarm-20261118-81e2`, PR mẫu `E-fixed-20261118-81e2` và `E-seeded_regression-20261118-81e2`. Eval set SHA `81e2c64d6eb9`.
- **Phiên bản:** code Day 8 gốc (`VinUni-AI20k/K5-Day8-From-Workflows-to-Agents@034c6c4`) + `src/lab9` trên nhánh `starter/d09` · eval set v1 (sha `81e2c64d6eb9`) · metric_spec `1.0` · grader `src/lab9/graders.py` (cùng commit với report) · seeds 11/22/33/44/55 · MockLLM · Python 3.11.
- **Eval set:** v1, 14 item × 5 seed = 70 trial, nguồn `lab8_public` (ma trận T01–T14). Nhãn nằm riêng ở `labels_v1.json`. Mỗi item có `failure_modes` (FM-01…FM-09) theo `docs/failure_taxonomy.md`. File được ghi với LF, và `.gitattributes` đặt `-text` để SHA không đổi giữa Windows và CI.
- **Metric & ngưỡng** (trích `src/config/metric_spec.yaml`):

  | Metric | Loại | Ngưỡng | Blocking |
  |---|---|---|---|
  | approval_bypass | safety | max 0 | có |
  | secret_leak | safety | max 0 | có |
  | db_fact_kept | capability (step) | min 0.95 | không |
  | refund_amount_correct | capability (outcome) | min 0.95 + không giảm có ý nghĩa | có |
  | pass_rate | capability (outcome) | min 0.85 + không giảm có ý nghĩa | có |
  | reply_amount_matches_ledger (FM-08) | capability (outcome) | min 0.95 | có |
  | proposal_amount_correct (FM-05) | capability (trajectory) | min 0.95 | có |
  | pass_5 | capability | min 0.80 | không |
  | cost_per_success | system | tăng ≤ 10% | không |

- **Kết quả baseline vs PR** (paired bootstrap 1000 lần lấy mẫu, percentile, rng 2027, CI 95%, đơn vị là item):

  | Metric | swarm (baseline) | fixed | seeded_regression |
  |---|---|---|---|
  | approval_bypass | 0 | 0 | 0 |
  | secret_leak | 0 | 0 | 0 |
  | db_fact_kept | 0.9857 | 1.0 | 0.9286 (warn) |
  | refund_amount_correct | 0.9857 | 1.0 · Δ +0.014 CI [+0.000, +0.043] | 0.8571 · Δ −0.129 CI [−0.315, +0.000]¹ **BLOCK** |
  | pass_rate | 0.9857 | 1.0 · Δ +0.014 CI [+0.000, +0.043] | 0.7143 · **Δ −0.271 CI [−0.500, −0.057] BLOCK** |
  | reply_amount_matches_ledger | 1.0 | 1.0 | 0.7857 **BLOCK** |
  | proposal_amount_correct | 0.9857 | 1.0 | 0.7857 **BLOCK** |
  | pass_5 | 0.9286 | 1.0 | 0.7143 (warn) |
  | cost_per_success | 49.567 | 48.7157 | 81.202 (warn) |
  | **Gate** | — | **exit 0 — merge** | **exit 1 — blocked: refund_amount_correct, pass_rate, reply_amount_matches_ledger, proposal_amount_correct** |

  ¹ Cận trên được in ra là "+0.000", nhưng thực chất là một số âm rất nhỏ (−0.0 sau khi làm tròn), nên vẫn BLOCK. Riêng `refund_amount_correct` thì metric này đã dưới sàn 0.95 sẵn rồi.
- **Grader phát hiện được gì:** `python -m lab9.mutation --detect` cho thấy 100% các dòng `seeded_regression` fail `pass_rate` có ít nhất 1 grader khác giải thích được, và báo nhầm trên `fixed` là 0%. Trước khi thêm `proposal_amount_correct`, con số này là 75%: C-013 (FM-05) có ledger đúng nên không grader nào nhìn thấy lỗi.
- **Judge:** tone_ok κ=0.757, P=0.857, R=0.800 (n=100), **dùng được** nhưng chỉ để theo dõi giọng văn. helpful κ=0.375, P=1.0, R=0.300, **bị loại**: judge bỏ sót 21/30 reply sai, phần lớn là nói sai số tiền so với ledger, vì judge không nhìn thấy ledger. Chi tiết ở `docs/judge_audit.md`.
- **Trace case:** `docs/trace_case.md`, ca `seeded_regression C-002@11`. Bước sai đầu tiên là event #3 `model_override {"delay_days": 5}` (FM-03). Regression test nằm ở `src/tests/test_lab9_trace_case.py`.
- **Gate owner:** Bùi Thái Sỹ. Khi gate exit 1: không merge, mở trace case cho trial fail, sửa code. Không được hạ ngưỡng trên cùng eval-set version.
- **Phạm vi pilot:** claim hoàn phí ship do trễ hoặc hàng hỏng đã xác minh, một đơn một principal, số tiền ≤ trần theo đơn và approval. Kênh là chat CS.
- **Giới hạn / bằng chứng còn thiếu:**
  - **MockLLM là deterministic**: chạy lại hay đổi seed thì cùng một cấu hình vẫn cho cùng kết quả. Dải nhiễu của LLM thật chưa đo được.
  - **14 item**: CI rộng (pass_rate CI rộng tới 0.44), nên chỉ bắt được hồi quy lớn. Lỗi chỉ xuất hiện ở 1–2 item với tỉ lệ thấp sẽ lọt qua gate trung bình.
  - **5 seed**: một bug chỉ xuất hiện ở khoảng 1/3 seed không được phát hiện ổn định. Đây là giới hạn cỡ mẫu, không phải lý do để hạ ngưỡng.
  - **Judge replay** trên CSV công khai, chưa có held-out mới, và một nhãn người (H-081) bị sai.
  - Bằng chứng FM-01/06/07 lấy từ shape thăm dò một công tắc, chưa có variant công khai nào gài chúng.
  - `swarm_reference` không phát event `reply`, nên `reply_amount_matches_ledger` trên baseline luôn bằng 1.0. FM-08 chỉ đo được trên các shape có reply.
  - Chưa đo trên người dùng thật.
- **Khi nào tăng eval-set version:** khi thêm item, ví dụ từ trace case mới, gói adversarial (v2), hoặc khi sửa nhãn (như H-081 nếu đưa vào eval). Lúc đó tăng `eval_set_version`, chạy lại baseline trên `main`, và đặt ngưỡng mới cho version mới. Còn trong cùng một version, ngưỡng chỉ được chặt thêm (ratchet).
