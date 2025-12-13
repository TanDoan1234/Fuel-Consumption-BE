# Hướng Dẫn Cài Đặt và Chạy Dự Án

## 📋 Yêu Cầu Hệ Thống

### Backend:

- Python 3.8+
- PostgreSQL database (hoặc Supabase)
- LM Studio (cho LLM service) - tùy chọn nhưng khuyến nghị

### Frontend:

- Node.js 18+ và npm/yarn
- Modern web browser

---

## 🔧 Cài Đặt Backend (Python/Flask)

### Bước 1: Tạo Virtual Environment (Khuyến nghị)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Bước 2: Cài Đặt Dependencies

```bash
pip install -r requirements.txt
```

**Lưu ý:** Nếu gặp lỗi khi cài đặt các package ML (xgboost, catboost, lightgbm), bạn có thể cần:

- Windows: Cài Visual Studio Build Tools
- Linux: `sudo apt-get install build-essential`
- Mac: `xcode-select --install`

### Bước 3: Cấu Hình Environment Variables

Tạo file `.env` trong thư mục gốc của project:

```env
# Database URL (Supabase hoặc PostgreSQL)
SUPABASE_DB_URL=postgresql://user:password@host:port/database

# Secret key cho JWT tokens (tạo một chuỗi ngẫu nhiên)
SECRET_KEY=your-secret-key-here-change-in-production

# LLM Service (tùy chọn - mặc định localhost:1234)
LLM_API_URL=http://localhost:1234/v1/chat/completions
LLM_MODEL_NAME=llama3-8b-instruct
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1024
```

**Ví dụ với Supabase:**

```env
SUPABASE_DB_URL=postgresql://postgres.xxxxx:password@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
SECRET_KEY=my-super-secret-key-12345
```

### Bước 4: Chuẩn Bị ML Models

Đảm bảo các file model `.pkl` có trong thư mục `models/`:

- `models/ceto_best_ml_model.pkl`
- `models/poseidon_best_ml_model.pkl`
- `models/triton_best_ml_model.pkl`

Nếu chưa có, bạn cần train models hoặc lấy từ nguồn khác.

### Bước 5: Chạy Backend Server

```bash
python main.py
```

Server sẽ chạy tại: `http://localhost:5000` (hoặc port được set trong biến môi trường `PORT`)

**Kiểm tra:** Mở trình duyệt và truy cập `http://localhost:5000` để xem API đã chạy chưa.

---

## 🎨 Cài Đặt Frontend (React/TypeScript)

### Bước 1: Di Chuyển Vào Thư Mục Frontend

```bash
cd frontend
```

### Bước 2: Cài Đặt Dependencies

```bash
npm install
```

hoặc nếu dùng yarn:

```bash
yarn install
```

### Bước 3: Cấu Hình API Endpoint (Nếu cần)

Kiểm tra file `frontend/src/services/api/client.ts` để đảm bảo API base URL đúng:

```typescript
// Mặc định sẽ là http://localhost:5000
baseURL: "http://localhost:5000";
```

### Bước 4: Chạy Development Server

```bash
npm run dev
```

hoặc

```bash
yarn dev
```

Frontend sẽ chạy tại: `http://localhost:3000` (tự động mở trình duyệt)

---

## 🚀 Chạy Toàn Bộ Hệ Thống

### Terminal 1 - Backend:

```bash
# Kích hoạt virtual environment (nếu chưa)
venv\Scripts\activate  # Windows
# hoặc
source venv/bin/activate  # Linux/Mac

# Chạy backend
python main.py
```

### Terminal 2 - Frontend:

```bash
cd frontend
npm run dev
```

### Terminal 3 - LM Studio (Tùy chọn, cho LLM):

```bash
# Tải và chạy LM Studio từ https://lmstudio.ai/
# Hoặc chạy local LLM server khác tại port 1234
```

---

## 🔍 Kiểm Tra Cài Đặt

### 1. Kiểm Tra Backend:

- Mở `http://localhost:5000` - sẽ thấy trang test hoặc API response
- Kiểm tra database connection trong console logs

### 2. Kiểm Tra Frontend:

- Mở `http://localhost:3000` - sẽ thấy giao diện login
- Thử đăng ký tài khoản mới

### 3. Kiểm Tra Database:

- Đảm bảo các tables được tạo tự động khi chạy lần đầu
- Kiểm tra trong Supabase dashboard hoặc PostgreSQL client

---

## 🐛 Xử Lý Lỗi Thường Gặp

### Lỗi Database Connection:

```
RuntimeError: SUPABASE_DB_URL environment variable is required
```

**Giải pháp:** Tạo file `.env` với `SUPABASE_DB_URL` hợp lệ

### Lỗi Import ML Models:

```
FileNotFoundError: models/ceto_best_ml_model.pkl not found
```

**Giải pháp:** Đảm bảo các file model `.pkl` có trong thư mục `models/`

### Lỗi Port Đã Được Sử Dụng:

```
OSError: [Errno 48] Address already in use
```

**Giải pháp:**

- Thay đổi port trong `.env`: `PORT=5001`
- Hoặc kill process đang dùng port đó

### Lỗi CORS:

**Giải pháp:** Backend đã cấu hình CORS cho tất cả origins, nếu vẫn lỗi kiểm tra lại `core/app.py`

### Lỗi LLM Connection:

```
httpx.HTTPError: Connection refused
```

**Giải pháp:**

- Đảm bảo LM Studio đang chạy tại `http://localhost:1234`
- Hoặc cập nhật `LLM_API_URL` trong `.env`

---

## 📝 Ghi Chú Quan Trọng

1. **Database:** Hệ thống sử dụng PostgreSQL qua Supabase. Đảm bảo database URL đúng format.

2. **ML Models:** Các model cần được train trước và lưu dưới dạng `.pkl` file.

3. **LM Studio:** Tùy chọn nhưng khuyến nghị để có trải nghiệm chatbot tốt nhất. Nếu không có, một số tính năng LLM sẽ không hoạt động.

4. **Admin Account:**

   - Email: `fluxmare_admin@gmail.com`
   - Password: `19062004`
   - (Được hardcode trong `frontend/src/App.tsx`)

5. **Environment Variables:** Không commit file `.env` lên git. Tạo `.env.example` nếu cần.

---

## 🎯 Quick Start (Tóm Tắt)

```bash
# Backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# Tạo file .env với SUPABASE_DB_URL và SECRET_KEY
python main.py

# Frontend (terminal khác)
cd frontend
npm install
npm run dev
```

---

## 📚 Tài Liệu Tham Khảo

- Flask Documentation: https://flask.palletsprojects.com/
- React Documentation: https://react.dev/
- Supabase Documentation: https://supabase.com/docs
- LM Studio: https://lmstudio.ai/
