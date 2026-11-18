# Judge audit

Chạy (trong `src/`):

```bash
python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 10
python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 21
```

Lớp dương là `FAIL`, vì việc của judge là **tìm ra lỗi**. Judge chạy ở chế độ replay: verdict đã lưu sẵn trong CSV, không gọi model.

| Tiêu chí | n | Confusion (tp/fp/fn/tn) | κ | Precision | Recall | Specificity | Tỉ lệ FAIL quan sát → sau Rogan-Gladen | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|---|---|---|
| tone_ok | 100 | 24 / 4 / 6 / 66 | 0.757 | 0.857 | 0.800 | 0.943 | 0.28 → 0.30 | **PASS** | **dùng** (chỉ để theo dõi giọng văn, không đụng tới tiền) |
| helpful | 100 | 9 / 0 / 21 / 70 | 0.375 | 1.000 | 0.300 | 1.000 | 0.09 → 0.30 | **FAIL** (κ, R dưới floor) | **loại** |

## Case audit thủ công (10 bất đồng của tone + 5 đại diện của helpful)

| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú / sửa rubric |
|---|---|---|---|---|---|
| 1 | H-008 "Em đã hoàn tiền cho anh rồi nha, anh check giúp em." | PASS | FAIL | Người | Xưng "em", thêm "nha" là quá suồng sã với khách đang khiếu nại. Rubric thêm: *"Xưng hô bắt buộc LogiX ↔ anh/chị; 'em', 'bạn', 'nha', 'nhé' ⇒ FAIL."* |
| 2 | H-017 "Dạ, bạn ơi LogiX đã hoàn 25.000đ … rồi nha." | PASS | FAIL | Người | Cùng lỗi xưng hô như #1, quy tắc xưng hô ở #1 bắt được. |
| 3 | H-029 "Dạ, vui lòng chờ. … không cần nhắn thêm." | PASS | FAIL | Người | Judge chỉ thấy "Dạ, vui lòng". Rubric thêm: *"Câu mệnh lệnh hoặc chặn khách liên hệ ('không cần nhắn thêm') ⇒ FAIL, dù có từ lịch sự."* |
| 4 | H-042 "Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ." | FAIL | PASS | Người | Judge phạt vì thiếu lời xin lỗi. Rubric thêm: *"Không bắt buộc xin lỗi; ngắn mà đủ ý và lễ phép ⇒ PASS."* |
| 5 | H-051 "… đã refund 90.000đ …" | FAIL | PASS | Người | Style guide CS cho phép từ "refund". Rubric thêm danh sách từ tiếng Anh được phép: refund, voucher, ship. |
| 6 | H-063 "… đã hoàn 20.000đ và sẽ hoàn thêm …" | PASS | FAIL | Người, nhưng **không phải lỗi tone** | Hứa "sẽ hoàn thêm" ngoài kết quả của hệ thống là lỗi nội dung hoặc tiền (gần FM-08), phải chấm bằng code, không qua judge tone. Rubric tone ghi rõ: *"không chấm số tiền hay cam kết"*. Chuyển sang grader `reply_amount_matches_ledger`. |
| 7 | H-070 "… ạ 😂😂" | PASS | FAIL | Người | Rubric thêm: *"Emoji trong trả lời khiếu nại ⇒ FAIL."* |
| 8 | H-081 "Dạ, đơn O-107 chưa đủ điều kiện hoàn …" | FAIL | PASS | **Judge** (theo note, người đọc nhầm ticket) | **Sửa nhãn người** thành FAIL trong bản CSV kế tiếp. Không sửa rubric. |
| 9 | H-088 "Dạ, dạ, LogiX đã hoàn …" | FAIL | PASS | Người, ở mức chấp nhận được | Lỗi gõ lặp từ không làm hỏng giọng văn. Rubric thêm: *"Lỗi gõ nhỏ không đổi nghĩa ⇒ PASS."* |
| 10 | H-094 "Da, LogiX da hoan 40.000đ …" (mất dấu) | PASS | FAIL | Người | Rubric thêm: *"Tiếng Việt không dấu hoặc văn dịch máy ⇒ FAIL."* |
| 11 | HL-015 "Dạ, LogiX đã hoàn 55.000đ cho đơn O-112 ạ." (ledger 40.000đ) | PASS | FAIL | Người | Judge không thấy ledger nên không thể biết số tiền sai. Đây là lỗi FM-08, phải chấm bằng code. |
| 12 | HL-016 xin lỗi dài, "đã hoàn 55.000đ" (ledger 35.000đ) | PASS | FAIL | Người | Judge bị lời xin lỗi dài "mua chuộc" (thiên vị độ dài và độ lịch sự), bỏ qua số tiền sai. |
| 13 | HL-043 xin lỗi lặp, "đã hoàn 35.000đ" (ledger 20.000đ) | PASS | FAIL | Người | Cùng kiểu với #12: câu văn lặp lại vẫn được PASS. |
| 14 | HL-047 "Ok bạn, đơn O-515 xử lý rồi nhé." | PASS | FAIL | Người | Không nói kết quả hay số tiền, xưng hô sai. Rubric helpful cần: *"phải nêu kết quả cụ thể (hoàn bao nhiêu / vì sao từ chối / cần gì thêm)"*. |
| 15 | HL-100 "Dạ, LogiX đã hoàn 55.000đ cho đơn O-112 ạ." (ledger 35.000đ) | PASS | FAIL | Người | Lỗi FM-08. Judge thấy câu trả lời trôi chảy nên cho PASS. |

## Kết luận

- **tone_ok: dùng được** (κ 0.757, P 0.857, R 0.80 đều trên floor). Judge này chỉ được dùng để theo dõi giọng văn, **không** dùng làm gate tiền hay approval. Tỉ lệ FAIL quan sát 0.28 sau hiệu chỉnh Rogan-Gladen là 0.30, nghĩa là judge đếm thiếu khoảng 2 điểm phần trăm.
- **helpful: loại, không được dùng làm gate.** Ma trận nhầm lẫn 9/0/21/70 cho thấy precision 1.0 là ảo: judge gần như chỉ nói PASS, bỏ sót **21/30 reply người dùng đánh FAIL** (R = 0.30, κ = 0.375). Tỉ lệ FAIL thật khoảng 0.30, nhưng judge chỉ thấy 0.09. Dùng judge này làm gate thì gate sẽ xanh đúng lúc agent nói sai số tiền với khách. 17/21 ca bỏ sót có note "ledger ghi …" (sai số tiền, tức FM-08). Judge chỉ đọc reply, không thấy ledger, và bị câu xin lỗi dài, lặp lại đánh lừa. Hướng xử lý:
  1. Phần "nói đúng số tiền" tách ra thành grader code `reply_amount_matches_ledger` (đọc số tiền trong reply so với ledger).
  2. Phần "có nêu kết quả cụ thể không" viết lại rubric như #14, rồi gán nhãn lại và hiệu chỉnh lại trước khi dùng.
- **Rủi ro còn lại:** judge mới chỉ được kiểm trên dữ liệu replay đã công khai (cũng chính là dữ liệu dùng để sửa rubric). Cần một tập nhãn người mới, chưa ai nhìn thấy, làm held-out, rồi đo lại κ/P/R trên tập đó. Nhãn H-081 cần sửa trước khi dùng CSV này làm chuẩn.
