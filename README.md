# Hệ Thống Dự Đoán Tiêu Thụ Nhiên Liệu Tàu Thủy với RAG và LLM

## Tổng Quan Dự Án

Hệ thống này là một giải pháp tích hợp Machine Learning và AI Chatbot để dự đoán và phân tích tiêu thụ nhiên liệu cho tàu thủy. Hệ thống giải quyết bài toán tối ưu hóa nhiên liệu trong ngành hàng hải bằng cách kết hợp mô hình dự đoán chuyên biệt với khả năng trả lời tự nhiên của Large Language Models (LLMs).

**Vấn đề cần giải quyết:** Việc dự đoán tiêu thụ nhiên liệu tàu thủy phụ thuộc vào nhiều yếu tố phức tạp (tốc độ, điều kiện thời tiết, loại tàu). Người dùng cần một hệ thống vừa có thể tính toán chính xác, vừa có thể giải thích và tư vấn bằng ngôn ngữ tự nhiên.

**Giải pháp:** Hệ thống sử dụng mô hình ML chuyên biệt cho từng loại tàu (CETO, POSEIDON, TRITON) để dự đoán chính xác, kết hợp với RAG (Retrieval-Augmented Generation) để cung cấp context từ knowledge base, và LLM để giải thích kết quả bằng tiếng Việt.

**Use case chính:** Người dùng có thể hỏi về các yếu tố ảnh hưởng đến nhiên liệu, cung cấp thông số chuyến đi để nhận dự đoán, hoặc so sánh nhiều phương án để tối ưu hóa chi phí nhiên liệu.

## Kiến Trúc Hệ Thống

### Input

Hệ thống nhận input từ người dùng qua hai kênh chính:

1. **Text Input:** Người dùng nhập câu hỏi hoặc mô tả bằng tiếng Việt/Anh. Hệ thống tự động trích xuất các tham số từ text sử dụng regex patterns (ví dụ: "tốc độ tàu: 10 m/s" → `Ship_SpeedOverGround: 10`).

2. **Structured Form Input:** Người dùng điền form với 8 features: tốc độ tàu, tốc độ gió, độ cao sóng, chu kỳ sóng, độ sâu đáy biển, nhiệt độ, tốc độ dòng chảy, và loại tàu.

### Processing

Hệ thống xử lý theo hai luồng chính:

**Luồng 1 - Có đủ tham số:** Khi hệ thống trích xuất được đủ 8 features từ input, nó sẽ:

- Chọn mô hình ML phù hợp dựa trên loại tàu (CETO/POSEIDON/TRITON)
- Thực hiện dự đoán tiêu thụ nhiên liệu (đơn vị: kg/s)
- Gọi LLM với kết quả dự đoán để tạo giải thích chi tiết bằng tiếng Việt

**Luồng 2 - Thiếu tham số hoặc câu hỏi chung:** Khi không đủ thông tin để dự đoán, hệ thống kích hoạt RAG:

- Chuyển đổi câu hỏi thành embedding vector (768 chiều) sử dụng model `text-embedding-nomic-embed-text-v1.5`
- Tìm kiếm trong database Supabase các document chunks có similarity ≥ 0.7
- Lấy top 3 chunks có similarity cao nhất
- Inject context vào LLM prompt dưới dạng system message
- LLM trả lời dựa trên context được cung cấp

### Output

Hệ thống trả về:

- **Text Response:** Câu trả lời bằng tiếng Việt, đã được chuẩn hóa (loại bỏ markdown characters)
- **Prediction Result (nếu có):** Giá trị dự đoán nhiên liệu (kg/s) kèm metadata
- **Dashboard Data:** Dữ liệu để hiển thị biểu đồ, thống kê, và so sánh

### Các Thành Phần Chính

**WHAT:** Hệ thống bao gồm:

- Backend Flask API xử lý logic nghiệp vụ
- React Frontend cung cấp giao diện chat và dashboard
- PostgreSQL/Supabase database lưu trữ conversations, messages, và document chunks
- LM Studio server chạy LLMs local (Qwen 2.5 VL 7B, Llama 3.1 8B)
- ML Models (.pkl files) cho 3 loại tàu

**WHY:**

- RAG được sử dụng để cung cấp context chính xác từ knowledge base, giảm hallucination và tăng độ tin cậy của LLM
- Đánh giá nhiều LLMs giúp so sánh hiệu năng và chọn model phù hợp nhất cho use case cụ thể

**WHERE:**

- Dữ liệu conversation và messages lưu trong Supabase (PostgreSQL)
- Document chunks với embeddings lưu trong bảng `fluxmare_chunks`
- ML models lưu local trong thư mục `models/`

**WHEN:**

- RAG được trigger khi không có đủ 8 features để dự đoán, hoặc khi user hỏi câu hỏi chung
- LLM được gọi sau khi có prediction (để giải thích) hoặc sau khi có RAG context (để trả lời câu hỏi)

## Module RAG (Retrieval-Augmented Generation)

RAG module là trái tim của hệ thống, đảm bảo LLM có thể trả lời chính xác dựa trên knowledge base thay vì chỉ dựa vào training data.

### Quy Trình Hoạt Động

**Bước 1 - Query Embedding:**
Khi user gửi câu hỏi, hệ thống gọi embedding model (`text-embedding-nomic-embed-text-v1.5`) qua LM Studio API để chuyển đổi text thành vector 768 chiều. Embedding này capture semantic meaning của câu hỏi.

**Bước 2 - Vector Search:**
Hệ thống lấy tất cả document chunks từ database và tính cosine similarity giữa query embedding và mỗi chunk embedding. Cosine similarity đo độ tương đồng semantic, giá trị từ -1 đến 1, với 1 là hoàn toàn giống nhau.

**Bước 3 - Relevance Filtering:**
Chỉ các chunks có similarity ≥ 0.7 được giữ lại. Ngưỡng này đảm bảo chỉ context thực sự liên quan mới được sử dụng, tránh nhiễu thông tin.

**Bước 4 - Top-K Retrieval:**
Hệ thống sắp xếp các chunks theo similarity giảm dần và lấy top 3. Số lượng này cân bằng giữa đủ context và không quá tải prompt.

**Bước 5 - Context Injection:**
Top 3 chunks được format thành system message với cấu trúc:

```
Dưới đây là các thông tin tham khảo để giúp bạn trả lời câu hỏi:
1. [Chunk content 1] (sim=0.85)
2. [Chunk content 2] (sim=0.78)
3. [Chunk content 3] (sim=0.72)
```

**Bước 6 - LLM Generation:**
LLM nhận được prompt gồm system message (chứa context) và user message (câu hỏi gốc). LLM sử dụng context này để tạo response chính xác và có căn cứ.

### Lưu Trữ Documents

Documents được lưu trữ dưới dạng chunks trong bảng `fluxmare_chunks`:

- Mỗi chunk có `content` (text), `embedding` (vector 768 chiều), và `meta` (metadata JSON)
- Embeddings được tạo tự động khi store chunk qua API `/chunk`
- Chunks có thể được thêm vào knowledge base bất kỳ lúc nào để cập nhật thông tin

## Tích Hợp LLM

Hệ thống hỗ trợ nhiều LLM models chạy local qua LM Studio, cho phép người dùng chọn model phù hợp.

### Models Được Hỗ Trợ

- **Qwen 2.5 VL 7B:** Model đa ngôn ngữ, đặc biệt tốt với tiếng Việt
- **Llama 3.1 8B:** Model instruction-tuned, có khả năng reasoning tốt

### Kết Nối và Cấu Hình

Hệ thống kết nối với LM Studio qua OpenAI-compatible API tại `http://localhost:1234/v1/chat/completions`. Mỗi request gồm:

- `model`: Tên model identifier
- `messages`: Array các messages với role (system/user/assistant) và content
- `temperature`: 0.6 (cân bằng giữa creativity và consistency)
- `max_tokens`: 1024 (giới hạn độ dài response)

### Xử Lý Response

LLM response được xử lý qua pipeline:

1. Nhận raw content từ API
2. Chuẩn hóa markdown: loại bỏ các ký tự `*`, `**`, `#`, `-`, `` ` ``, `_` để đảm bảo text sạch
3. Trả về text đã được normalize

### Execution Mode

Hệ thống hỗ trợ hai chế độ:

- **Sequential:** Chạy từng model một (giảm tải GPU, ít nóng máy)
- **Parallel:** Chạy nhiều models song song (nhanh hơn nhưng tốn tài nguyên)

## Phương Pháp Đánh Giá

Hệ thống có module evaluation tự động để đánh giá và so sánh hiệu năng của các LLM models trên tập test cases.

### Test Cases

Test cases được thiết kế trong file Excel với 6 categories:

- **RAG_Query:** Câu hỏi yêu cầu RAG retrieval
- **Parameter_Extract:** Test khả năng trích xuất tham số từ text
- **Hallucination:** Test cases được thiết kế để phát hiện hallucination
- **Language_Test:** Kiểm tra khả năng xử lý tiếng Việt
- **Multi_Turn:** Test hội thoại nhiều lượt
- **Edge_Case:** Test các trường hợp biên

Mỗi test case có: Question, Expected_Keywords, Expected_Behavior, và Source.

### Metrics Tự Động

Hệ thống tính toán 9 metrics cho mỗi response:

1. **Response_Time_Seconds:** Thời gian từ khi gửi request đến nhận response
2. **Is_Vietnamese:** Kiểm tra response có phải tiếng Việt không (≥15% ký tự Việt, <5 từ Anh phổ biến)
3. **Keywords_Found:** Số keywords tìm được / tổng số keywords (format: X/Y)
4. **Keyword_Coverage_Percent:** Tỷ lệ keywords được cover (0-100%)
5. **Has_Hallucination:** Phát hiện 4 patterns: fake citations, future dates, fake ships, unattributed numbers
6. **Response_Length_Words:** Số từ trong response
7. **Length_Score:** Điểm dựa trên độ dài (50-150 từ = 100 điểm, curve giảm dần)
8. **Manual_Quality_Score:** Điểm đánh giá thủ công (0-5, để trống ban đầu)
9. **Total_Score:** Tổng điểm weighted (0-100) với công thức:
   - Time Score (15%): max(0, 100 - time × 10)
   - Vietnamese Score (20%): 100 nếu YES, 0 nếu NO
   - Keyword Score (20%): Keyword coverage
   - No Hallucination Score (25%): 100 nếu NO, 0 nếu YES
   - Length Score (10%): Từ scoring curve
   - Manual Score (10%): Manual score × 20

### Quy Trình Đánh Giá

1. Đọc 50 test cases từ Excel
2. Với mỗi test case:
   - Gọi RAG để lấy context
   - Gửi đến các LLM models (tuần tự hoặc song song)
   - Đo response time
   - Tính 9 metrics tự động
3. Lưu kết quả vào CSV files (1 file/model)
4. Tính aggregate metrics: mean, std deviation, Vietnamese compliance rate, No hallucination rate
5. Thực hiện statistical tests: T-test và Cohen's d để so sánh models
6. Xuất comparison Excel với 5 sheets: raw results cho mỗi model, aggregate metrics, category breakdown

### Kết Quả Đánh Giá

Kết quả được lưu trong thư mục `evaluation_results/`:

- **CSV files:** Chi tiết từng test case với tất cả metrics
- **Excel file:** Tổng hợp với aggregate metrics và statistical analysis
- **Text report:** Executive summary với winner declaration và insights

## Luồng Dữ Liệu

**Step 1 - User Input:**
Người dùng gửi message qua frontend (text hoặc form). Frontend gửi POST request đến `/chat/chat` với messages array, model name, và language.

**Step 2 - Parameter Extraction:**
Backend sử dụng regex patterns để trích xuất 8 features từ user message. Nếu có structured input (form), ưu tiên sử dụng.

**Step 3 - Decision Point:**

- Nếu đủ 8 features → Luồng Prediction
- Nếu thiếu features → Luồng RAG

**Step 4a - Prediction Flow:**

- Load ML model tương ứng với ship_type
- Predict fuel consumption (kg/s)
- Gọi LLM với prediction và parameters để tạo explanation

**Step 4b - RAG Flow:**

- Tạo query embedding từ user message
- Search trong database với cosine similarity
- Filter chunks có similarity ≥ 0.7
- Lấy top 3 và format thành context
- Gọi LLM với context + question

**Step 5 - Response Generation:**
LLM tạo response dựa trên:

- System prompt (hướng dẫn trả lời tiếng Việt)
- Context từ RAG (nếu có)
- User question
- Prediction result (nếu có)

**Step 6 - Response Processing:**

- Normalize markdown từ LLM response
- Lưu message vào database
- Trả về JSON với response, prediction_result (nếu có), và metadata

**Step 7 - Frontend Display:**

- Hiển thị text response trong chat
- Nếu có prediction → Hiển thị dashboard với charts và statistics
- Lưu conversation vào state để hiển thị history

## Tính Năng Chính

1. **Auto Parameter Extraction:** Tự động trích xuất 8 features từ text tự nhiên, hỗ trợ cả tiếng Việt và tiếng Anh, không cần format cứng nhắc.

2. **RAG với Vector Search:** Tìm kiếm semantic trong knowledge base, chỉ sử dụng context có similarity ≥ 0.7, đảm bảo độ chính xác cao.

3. **Multi-Model LLM Support:** Cho phép người dùng chọn LLM model phù hợp, hỗ trợ so sánh hiệu năng giữa các models.

4. **Intelligent State Management:** Lưu trữ state của conversation, cho phép user cung cấp thông tin nhiều lượt, hệ thống tự động tích lũy và dự đoán khi đủ.

5. **Automated Evaluation System:** Module đánh giá tự động với 9 metrics, statistical analysis, và export kết quả đầy đủ cho research paper.

6. **Real-time Dashboard:** Hiển thị trực quan kết quả dự đoán với biểu đồ, thống kê, và khả năng so sánh nhiều phương án.

7. **Markdown Normalization:** Tự động làm sạch LLM responses, loại bỏ markdown characters để text dễ đọc hơn.

## Tech Stack

**Backend:**

- Python 3.8+
- Flask (web framework)
- SQLAlchemy (ORM)
- PostgreSQL/Supabase (database với pgvector support)
- httpx (async HTTP client)
- pandas, numpy, scikit-learn (data processing và ML)
- joblib (model loading)

**Frontend:**

- React + TypeScript
- Vite (build tool)
- Radix UI (component library)
- Axios (HTTP client)
- Recharts (data visualization)

**LLM & Embeddings:**

- LM Studio (local LLM server)
- Models: Qwen 2.5 VL 7B, Llama 3.1 8B
- Embedding model: text-embedding-nomic-embed-text-v1.5 (768 dimensions)

**ML Models:**

- Stacked ensemble models (.pkl) cho 3 loại tàu
- XGBoost, CatBoost, LightGBM (base models)

## Setup & Usage

### Prerequisites

- Python 3.8+
- Node.js 18+
- LM Studio đã cài đặt và có models đã download
- Supabase account hoặc PostgreSQL database

### Quick Start

1. **Clone repository và cài dependencies:**

   ```bash
   pip install -r requirements.txt
   cd frontend && npm install
   ```

2. **Cấu hình environment variables:**

   - Backend: Tạo `.env` với `SUPABASE_DB_URL`, `SECRET_KEY`, `LLM_API_URL`
   - Frontend: Tạo `.env` với `VITE_API_BASE_URL`

3. **Chạy hệ thống:**

   - Start LM Studio và load model
   - Start backend: `python main.py`
   - Start frontend: `npm run dev`

4. **Chạy evaluation (tùy chọn):**
   ```bash
   python evaluation/llm_evaluator.py eval_llms.xlsx evaluation_results 25
   ```

## Kết Quả Đánh Giá

Dựa trên 25 test cases, kết quả ban đầu cho thấy:

- **Qwen 2.5 VL 7B** đạt điểm trung bình 62.34/100, với Vietnamese compliance 100% và keyword coverage 90%
- **Llama 3.1 8B** đạt 61.61/100, với Vietnamese compliance 100% và keyword coverage 88.7%
- Cả hai models đều có vấn đề với hallucination (32-36% cases có hallucination)

## Hạn Chế và Hướng Phát Triển

**Hạn chế hiện tại:**

- RAG sử dụng brute-force search (tính similarity với tất cả chunks), chưa tối ưu cho database lớn
- Hallucination detection dựa trên pattern matching, có thể miss một số cases
- Models chạy local nên tốc độ phụ thuộc vào GPU

**Hướng phát triển:**

- Implement vector index (pgvector) để tăng tốc RAG search
- Cải thiện hallucination detection bằng LLM-based verification
- Thêm support cho streaming responses
- Mở rộng evaluation với human evaluation và A/B testing
