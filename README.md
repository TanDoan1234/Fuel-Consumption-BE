# Fuel Consumption Prediction System

Hệ thống dự đoán tiêu thụ nhiên liệu tàu thủy sử dụng Machine Learning và AI Chatbot.

## 📁 Cấu trúc Mã Nguồn

### Backend (Python/Flask)

```
├── api/                    # API endpoints
│   ├── auth.py            # Xác thực người dùng (JWT)
│   └── chat.py            # API chat và dự đoán
├── core/                   # Core modules
│   ├── app.py             # Flask app initialization
│   ├── config.py          # Cấu hình ứng dụng
│   ├── database.py        # Database connection
│   ├── models.py          # SQLAlchemy models
│   ├── security.py        # JWT authentication
│   └── supportfunc.py     # Helper functions (RAG, extract params)
├── services/               # Business logic services
│   ├── llm_service.py     # LLM integration (LM Studio)
│   └── model_service.py   # ML model prediction
├── models/                 # ML model files (.pkl)
│   ├── ceto_stacked.pkl
│   ├── poseidon_best_model-001.pkl
│   └── triton_best_model.pkl
└── main.py                 # Entry point
```

### Frontend (React/TypeScript)

```
frontend/src/
├── components/             # React components
│   ├── ChatBot.tsx        # Component chính của chatbot
│   ├── ChatHistory.tsx    # Lịch sử cuộc trò chuyện
│   ├── ChatInput.tsx      # Input form và textarea
│   ├── FuelConsumptionDashboard.tsx  # Dashboard hiển thị kết quả
│   └── ui/                # UI components (Radix UI)
├── services/api/           # API client services
│   ├── chat.ts           # Chat API client
│   ├── auth.ts            # Auth API client
│   └── client.ts          # Axios client config
├── utils/                  # Utilities
│   ├── mockData.ts        # Mock data types
│   └── translations.ts    # i18n translations
└── App.tsx                 # Root component
```

## 🤖 Cách Hoạt Động của Web Chatbot

### 1. Luồng Tổng Quan

```
User Input → Frontend (ChatBot.tsx) → API Request → Backend (chat.py)
→ Extract Parameters → ML Prediction → LLM Analysis → Response → Frontend Display
```

### 2. Chi Tiết Từng Bước

#### **Bước 1: User Gửi Message (Frontend)**

**File:** `frontend/src/components/ChatBot.tsx`

- User nhập text hoặc điền form 8 features trong `ChatInput.tsx`
- Component `ChatBot` gọi `handleSendMessage()`:
  ```typescript
  const handleSendMessage = async (content: string, formData: any) => {
    // 1. Tạo/tìm conversation
    // 2. Hiển thị optimistic message (user message ngay lập tức)
    // 3. Gọi API chat
    const response = await chatService.chat({
      conversationId: conversationId,
      messages: [...previousMessages, userMessage],
      model: currentModel, // meta-llama-3.1-8b-instruct, gemma-2-9b, qwen2.5-vl-7b
      language: "vi",
      context: formData ? buildContextMessages(formData) : [],
    });
  };
  ```

#### **Bước 2: API Request (Frontend → Backend)**

**File:** `frontend/src/services/api/chat.ts`

- Service `chatService.chat()` gửi POST request đến `/chat/chat`:
  ```typescript
  async chat(request: ChatCompletionRequest): Promise<ChatCompletionResponse> {
    const response = await apiClient.post('/chat/chat', {
      model: request.model,
      conversation_id: request.conversationId,
      messages: request.messages,
      language: request.language,
      context: request.context
    });
    return response.data;
  }
  ```

#### **Bước 3: Backend Xử Lý (Backend)**

**File:** `api/chat.py` - Route `/chat/chat`

**3.1. Extract Parameters từ User Message:**

```python
# Sử dụng regex patterns để tìm các tham số trong text
extracted = extract_params(user_message)
# Trả về dict: {
#   "Ship_SpeedOverGround": 10,
#   "Weather_WindSpeed10M": 30,
#   ...
# }
```

**3.2. Nếu có đủ 8 features → Dự đoán ML:**

```python
if extracted and has_all_features(extracted):
    # Gọi ML model dựa trên ship_type
    prediction = model_service.predict(extracted)
    # prediction = 1.28 (kg/s)

    # Gọi LLM để giải thích kết quả
    llm_response = call_llm(prediction, extracted)
```

**3.3. Nếu không đủ features → RAG (Retrieval-Augmented Generation):**

```python
# Tìm kiếm trong database các document chunks tương tự
similar_chunks = search_embedding(user_message)
# Tạo context từ các chunks
context = build_context_from_chunks(similar_chunks)

# Gọi LLM với context
llm_response = llm_service.chat(messages + context, "vi", model_name)
```

#### **Bước 4: ML Model Prediction**

**File:** `services/model_service.py`

```python
def predict(self, data: Dict[str, Any]) -> float:
    ship_type = data.get("ship_type", "").upper()

    # Chọn model dựa trên loại tàu
    model_path = SHIP_MODEL_MAP.get(ship_type)
    # CETO → ceto_stacked.pkl
    # POSEIDON → poseidon_best_model-001.pkl
    # TRITON → triton_best_model.pkl

    model = joblib.load(model_path)
    features = prepare_features(data)
    prediction = model.predict([features])[0]

    return prediction  # kg/s
```

#### **Bước 5: LLM Analysis**

**File:** `services/llm_service.py`

```python
async def chat(self, messages: List[Dict], language: str, model_name: str) -> str:
    # Gửi request đến LM Studio
    response = httpx.post(
        "http://localhost:1234/v1/chat/completions",
        json={
            "model": model_name,
            "messages": messages,
            "temperature": 0.6,
            "max_tokens": 1024
        },
        timeout=120.0
    )

    raw_content = response.json()["choices"][0]["message"]["content"]

    # Chuẩn hóa markdown (loại bỏ *, **, #)
    normalized = self._normalize_markdown(raw_content)

    return normalized
```

**File:** `core/supportfunc.py` - `call_llm()`

Khi có prediction, LLM được gọi với prompt đặc biệt:

```python
def call_llm(prediction_value: float, params: Dict[str, Any]) -> str:
    # Prompt giải thích kết quả dự đoán
    assistant_message = f"Dựa trên các tham số {params}, mức tiêu thụ nhiên liệu là {prediction_value:.2f}..."

    # Gọi LLM để giải thích chi tiết
    elaboration = llm_service.chat([...], "vi")

    return elaboration
```

#### **Bước 6: Response về Frontend**

**Backend trả về:**

```json
{
  "response": "Dựa trên các tham số... mức tiêu thụ nhiên liệu là 1.28 kg/s...",
  "prediction_made": true,
  "prediction_result": {
    "fuel_consumption": 1.28,
    "parameters": {
      "Ship_SpeedOverGround": 10,
      ...
    }
  },
  "message": {
    "id": 123,
    "role": "assistant",
    "content": "...",
    "metadata": {...}
  }
}
```

#### **Bước 7: Frontend Hiển Thị**

**File:** `frontend/src/components/ChatBot.tsx`

```typescript
// Cập nhật conversation với assistant message
setConversations((prev) => {
  const updated = prev.map((conv) => {
    if (conv.id === conversationId) {
      return {
        ...conv,
        messages: [...conv.messages, assistantMessage],
      };
    }
    return conv;
  });
  return updated;
});

// Nếu có prediction_result → Hiển thị Dashboard
if (response.prediction_result) {
  setFuelPredictionData(response.prediction_result);
  setShowDashboard(true);
}
```

### 3. Các Tính Năng Chính

#### **3.1. Auto Parameter Extraction**

- Sử dụng regex patterns để tự động trích xuất 8 features từ text
- Hỗ trợ cả tiếng Việt và tiếng Anh
- Ví dụ: "tốc độ tàu: 10 m/s" → `Ship_SpeedOverGround: 10`

#### **3.2. RAG (Retrieval-Augmented Generation)**

- Khi không có đủ features, hệ thống tìm kiếm trong database
- Sử dụng cosine similarity với embeddings
- Cung cấp context cho LLM để trả lời chính xác hơn

#### **3.3. Multi-Model Support**

- Hỗ trợ 3 LLM models:
  - `meta-llama-3.1-8b-instruct`
  - `google/gemma-2-9b`
  - `qwen/qwen2.5-vl-7b`
- User có thể chọn model từ dropdown

#### **3.4. Dashboard Visualization**

- Tự động hiển thị dashboard khi có prediction
- Hiển thị biểu đồ, thống kê, và thông tin chi tiết
- Hỗ trợ so sánh nhiều predictions

### 4. Database Schema

**Models (SQLAlchemy):**

- `User`: Thông tin người dùng
- `Conversation`: Cuộc trò chuyện
- `Message`: Tin nhắn (user/assistant)
- `DocumentChunk`: Chunks cho RAG
- `LLMRoleExample`: Ví dụ câu hỏi/trả lời
- `State`: State management

### 5. Environment Variables

**Backend (.env):**

```
SUPABASE_DB_URL=postgresql://...
SECRET_KEY=your-secret-key
LLM_API_URL=http://localhost:1234/v1/chat/completions
LLM_MODEL_NAME=meta-llama-3.1-8b-instruct
LLM_TEMPERATURE=0.6
LLM_MAX_TOKENS=1024
```

**Frontend (.env):**

```
VITE_API_BASE_URL=http://localhost:5000
VITE_API_TIMEOUT=180000
```

## 🚀 Cách Chạy

Xem chi tiết trong `SETUP_GUIDE.md`

1. **Backend:**

   ```bash
   pip install -r requirements.txt
   python main.py
   ```

2. **Frontend:**

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **LM Studio:**
   - Mở LM Studio
   - Load model (meta-llama-3.1-8b-instruct, gemma-2-9b, hoặc qwen2.5-vl-7b)
   - Start local server (port 1234)

## 📝 Lưu Ý

- ML models (.pkl) phải được đặt trong thư mục `models/`
- LM Studio phải chạy trước khi sử dụng chatbot
- Database (PostgreSQL/Supabase) phải được cấu hình đúng
