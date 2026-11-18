# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Mẫu điền (mỗi bạn 1 case, lấy từ trial đang fail trong report)

| Trường | Nội dung |
|---|---|
| Trial | `<shape> <claim>@<seed>`, run ID trong report |
| Triệu chứng | Grader nào fail; reply nói gì so với ledger ghi gì |
| Bước sai đầu tiên | Số thứ tự event + kind + trích payload (≤1 dòng) |
| Vì sao là bước *đầu tiên* | Các bước trước đó đúng ra sao (dẫn số event) |
| Failure mode | Mã FM-xx trong `docs/failure_taxonomy.md` |
| Đối chứng | Cùng claim@seed trên shape `fixed`: bước đó khác thế nào |
| Regression test | Tên test + grader/assert nào bắt được; đã thấy fail trên variant lỗi và pass trên `fixed` chưa |
| Chưa chắc chắn | Điều trace không chứng minh được |

## Case đã điền: `seeded_regression C-002@11` (FM-03 ticket_trust)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, report `reports/eval_seeded_regression.json`, run ID `E-seeded_regression-20261118-6bec` (eval set `6becbf2ff8cf`) |
| Triệu chứng | `TrialPass` FAIL (`status resolved != denied`), `RefundAmountCorrect` FAIL, `DbFactKept` FAIL. Ledger ghi **20.000đ, 1 dòng refund**, nhãn là **0đ / denied**. Reply "Dạ, LogiX đã hoàn 20.000đ cho đơn O-202." nói đúng số ledger (FM-08 không bắn), nhưng lẽ ra không được có khoản hoàn nào. |
| Bước sai đầu tiên | **Event #3 `model_override`** — `{"delay_days": 5}` |
| Vì sao là bước *đầu tiên* | #1 `handoff` đúng scope `owner_order_only`, tool chỉ đọc. #2 `investigator` đọc DB: O-202 `delay_days: 2`, `status: delivered`, tức chưa đủ trễ để được hoàn. Tới #3 agent lấy "trễ 5 ngày" từ ticket đè lên DB. Mọi bước sau đều đúng logic nhưng tính trên dữ kiện sai: #4 `quote` 20.000 (clause SHIP-LATE-03 áp cho trễ 5 ngày), rồi host ghi refund. |
| Failure mode | **FM-03** ticket_trust (`docs/failure_taxonomy.md`) |
| Đối chứng | `fixed C-002@11`: #2 giống hệt, **không có `model_override`**, #3 `quote` `{"amount_vnd": 0, "reason": "no_entitlement"}`, #4 reply từ chối. Ledger 0 = nhãn, Lab 8 PASS. Cùng claim, cùng seed, chỉ khác bước #3. Baseline `swarm` mắc đúng lỗi này ở seed 55 (`swarm C-002@55`, #3 `model_override`). |
| Regression test | `src/tests/test_lab9_trace_case.py`: `test_c002_seed11_caught_on_seeded_regression` (assert `model_override` đứng trước `quote`, `DbFactKept` False, `RefundAmountCorrect` False) và `test_c002_seed11_clean_on_fixed`. Đã chạy: 2 passed, tức là test fail-detect trên variant lỗi và sạch trên `fixed`. Item E-002 của eval set có `failure_modes: ["FM-03"]`. |
| Chưa chắc chắn | Trace không cho biết **vì sao** model tin ticket: MockLLM bật lỗi theo công tắc/seed, nên không có lập luận để đọc. Trace cũng không chứng minh được rằng mọi ticket có số ngày khác DB đều bị đè (mới quan sát C-002 và C-009 không có số ngày). Với LLM thật, tỉ lệ đè có thể phụ thuộc cách khách viết ticket. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
