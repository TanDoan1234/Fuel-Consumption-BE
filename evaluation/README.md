# LLM Evaluation Module

Module đánh giá tự động 3 LLMs (Gemma 2 9B, Qwen 2.5 7B, Llama 3 8B) trên 50 test cases với RAG system.

## 📋 Yêu Cầu

1. **LM Studio đang chạy** trên port 1234
2. **Database (Supabase/PostgreSQL)** đã được cấu hình và có dữ liệu RAG
3. **File Excel** `eval_llms.xlsx` với 50 test cases

## 🚀 Cách Sử Dụng

### Bước 1: Tạo Template Excel (Nếu chưa có)

```bash
python evaluation/create_template.py eval_llms.xlsx
```

File Excel sẽ có sheet `TEST_CASES` với các columns:
- `ID`: 1-50
- `Category`: RAG_Query, Parameter_Extract, Hallucination, Language_Test, Multi_Turn, Edge_Case
- `Question`: Câu hỏi tiếng Việt
- `Expected_Keywords`: Từ khóa cách nhau bằng dấu phẩy (vd: "tốc độ,gió,sóng")
- `Expected_Behavior`: Mô tả hành vi mong đợi
- `Source`: Citation của test case

### Bước 2: Chỉnh Sửa Test Cases (Tùy chọn)

Mở file `eval_llms.xlsx` và chỉnh sửa các test cases theo nhu cầu của bạn.

### Bước 3: Đảm Bảo LM Studio Đang Chạy

1. Mở LM Studio
2. Load 3 models:
   - `google/gemma-2-9b-it` (hoặc `gemma-2-9b-it`)
   - `qwen/qwen2.5-7b-instruct` (hoặc `qwen2.5-7b-instruct`)
   - `meta-llama-3.1-8b-instruct` (hoặc `llama-3.2-3b-instruct`)
3. Start local server (port 1234)

**Lưu ý:** Tên model trong code phải khớp với tên model trong LM Studio. Nếu khác, sửa trong `evaluation/llm_evaluator.py` tại class `Config`, phần `MODELS`.

### Bước 4: Chạy Evaluation

```bash
python evaluation/llm_evaluator.py eval_llms.xlsx evaluation_results
```

Hoặc chỉ định file và thư mục output:

```bash
python evaluation/llm_evaluator.py <excel_file> <output_dir>
```

### Bước 5: Xem Kết Quả

Kết quả sẽ được lưu trong thư mục `evaluation_results/`:

1. **CSV Files** (3 files):
   - `results_gemma.csv`
   - `results_qwen.csv`
   - `results_llama.csv`

2. **Excel File**: `comparison_summary.xlsx` (5 sheets):
   - `Gemma_Results`: Raw data
   - `Qwen_Results`: Raw data
   - `Llama_Results`: Raw data
   - `Aggregate_Metrics`: So sánh metrics và statistical tests
   - `Category_Breakdown`: Performance theo categories

3. **Text Report**: `summary_report.txt`
   - Executive summary
   - Detailed metrics
   - Winner declaration

4. **Log File**: `llm_evaluation.log`
   - Timestamp mỗi test
   - Errors và retries
   - Warnings

## 📊 Metrics Tự Động (9 Metrics)

1. **Response_Time_Seconds**: Thời gian response (giây)
2. **Is_Vietnamese**: Có phải tiếng Việt không (YES/NO)
3. **Keywords_Found**: Số keywords tìm được (X/Y)
4. **Keyword_Coverage_Percent**: Tỷ lệ keywords (0-100%)
5. **Has_Hallucination**: Có hallucination không (YES/NO)
6. **Response_Length_Words**: Số từ trong response
7. **Length_Score**: Điểm độ dài (0-100)
8. **Manual_Quality_Score**: Điểm đánh giá thủ công (0-5, để trống ban đầu)
9. **Total_Score**: Tổng điểm weighted (0-100)

## ⚙️ Cấu Hình

Có thể chỉnh sửa các thông số trong `evaluation/llm_evaluator.py`:

- **API Settings**: `TIMEOUT`, `MAX_RETRIES`, `TEMPERATURE`, `MAX_TOKENS`
- **Model Names**: Sửa trong `Config.MODELS` nếu tên model khác
- **Scoring Weights**: Sửa trong `Config.WEIGHTS`
- **Hallucination Patterns**: Sửa trong `Config.HALLUCINATION_PATTERNS`

## 🔧 Troubleshooting

### Lỗi: "Không thể kết nối LM Studio"
- Kiểm tra LM Studio đang chạy trên port 1234
- Kiểm tra model đã được load chưa
- Kiểm tra tên model trong code có khớp với LM Studio không

### Lỗi: "RAG error"
- Kiểm tra database connection
- Kiểm tra có dữ liệu trong bảng `fluxmare_chunks` không
- Kiểm tra Flask app context đã được khởi tạo đúng chưa

### Lỗi: "File không tồn tại"
- Đảm bảo file `eval_llms.xlsx` tồn tại
- Hoặc tạo template bằng `create_template.py`

### Timeout
- Tăng `TIMEOUT` trong `Config` nếu model chạy chậm
- Kiểm tra LM Studio có đang xử lý request khác không

## 📝 Lưu Ý

- Script chạy song song 3 models để tiết kiệm thời gian
- Mỗi test case sẽ gọi RAG trước, sau đó gọi 3 models
- Tổng thời gian: ~50 test cases × (RAG time + max(model times)) × 3 models
- Nếu một model fail, script sẽ tiếp tục với các model khác
- Manual_Quality_Score có thể được điền sau vào CSV files

## 🎯 Output Format

### CSV Columns:
- Test_ID
- Category
- Question
- Response
- Response_Time_Seconds
- Is_Vietnamese
- Keywords_Found
- Keyword_Coverage_Percent
- Has_Hallucination
- Response_Length_Words
- Length_Score
- Manual_Quality_Score
- Total_Score
- Notes

### Excel Sheets:
1. **Raw Results**: 3 sheets với đầy đủ data
2. **Aggregate_Metrics**: So sánh mean ± std, t-test, Cohen's d
3. **Category_Breakdown**: Performance theo 6 categories

