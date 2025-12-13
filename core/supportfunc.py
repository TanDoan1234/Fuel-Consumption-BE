import asyncio
import random
import re
from typing import Any, Dict, Optional

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.models import DocumentChunk, LLMRoleExample, State
from services.llm_service import llm_service
from services.model_service import model_service
from core.database import db
STRUCTURED_FIELD_MAP = {
    "speedOverGround": "Ship_SpeedOverGround",
    "windSpeed10M": "Weather_WindSpeed10M",
    "waveHeight": "Weather_WaveHeight",
    "wavePeriod": "Weather_WavePeriod",
    "seaFloorDepth": "Environment_SeaFloorDepth",
    "temperature2M": "Weather_Temperature2M",
    "oceanCurrentVelocity": "Weather_OceanCurrentVelocity",
    "shipType": "ship_type",
}

PATTERNS = {
    "Ship_SpeedOverGround": r"(?:tốc\s*độ|toc\s*do|ship[_\s-]*speed(?:[_\s-]*over)?[_\s-]*ground)\s*[:\-]?\s*(\d+(?:\.\d+)?)",
    "Environment_SeaFloorDepth": r"(?:độ\s*sâu(?:\s*đáy\s*biển)?|do\s*sau(?:\s*day\s*bien)?|sea[_\s-]*floor[_\s-]*depth)\s*[:\-]?\s*(\d+(?:\.\d+)?)",
    "Weather_Temperature2M": r"(?:nhiệt\s*độ|nhiet\s*do|temperature(?:[_\s-]*2m)?)\s*[:\-]?\s*(-?\d+(?:\.\d+)?)",
    "Weather_OceanCurrentVelocity": r"(?:dòng\s*chảy(?:\s*dải\s*đại\s*duong)?|dong\s*chay(?:\s*dai\s*dương)?|ocean[_\s-]*current[_\s-]*velocity)\s*[:\-]?\s*(\d+(?:\.\d+)?)",
    "Weather_WindSpeed10M": r"(?:tốc\s*độ\s*gió|toc\s*do\s*gio|wind[_\s-]*speed(?:[_\s-]*10m)?)\s*[:\-]?\s*(\d+(?:\.\d+)?)",
    "Weather_WaveHeight": r"(?:độ\s*cao\s*sóng|do\s*cao\s*song|wave[_\s-]*height)\s*[:\-]?\s*(\d+(?:\.\d+)?)",
    "Weather_WavePeriod": r"(?:chu\s*kỳ\s*sóng|chu\s*ky\s*song|wave[_\s-]*period)\s*[:\-]?\s*(\d+(?:\.\d+)?)",
    "ship_type": r"(?:ship[_\s-]*type\s*[:\-]?\s*)?(ceto|poseidon|triton)",
}

LABELS = {
    "Ship_SpeedOverGround": "tốc độ tàu",
    "Environment_SeaFloorDepth": "Độ sâu đáy biển",
    "Weather_Temperature2M": "Nhiệt độ",
    "Weather_OceanCurrentVelocity": "Tốc độ dòng chảy",
    "Weather_WindSpeed10M": "Tốc độ gió",
    "Weather_WaveHeight": "Độ cao sóng",
    "Weather_WavePeriod": "Chu kỳ sóng",
    "ship_type": "Loại tàu",
}


def get_example_response(db: Session, user_message: str):
    # Tìm câu gần giống (LIKE)
    example = (
        db.query(LLMRoleExample)
        .filter(func.lower(LLMRoleExample.user_prompt).like(f"%{user_message.lower()}%"))
        .first()
    )
    if example:
        return example.assistant_response
    return None


def _normalize_markdown(text: str) -> str:
    """
    Chuẩn hóa markdown: loại bỏ các ký tự * và ** nhưng giữ lại format
    """
    if not text:
        return text
    
    import re
    
    # Loại bỏ ** (bold markdown) - giữ lại text bên trong
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    
    # Loại bỏ * (italic markdown) - giữ lại text bên trong
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    
    # Loại bỏ các ký tự * còn sót lại (không có cặp)
    text = re.sub(r'\*+', '', text)
    
    # Loại bỏ các dấu # (heading markdown) ở đầu dòng
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    
    # Loại bỏ các dấu - hoặc * ở đầu dòng (list markdown)
    text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
    
    # Loại bỏ các dấu ` (code markdown)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Loại bỏ các dấu _ (underline/italic markdown)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    
    # Loại bỏ khoảng trắng thừa
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    
    return text.strip()


def call_llm(prediction_value: float, params: Dict[str, Any]) -> str:
    assistant_message = (
    f"Bạn PHẢI trả lời HOÀN TOÀN bằng tiếng Việt, "
    f"ngay cả khi các tham số hoặc dữ liệu đầu vào có chứa tiếng Anh (dịch các dữ liệu đầu vào sang tiếng Việt).\n\n"
    f"Dựa trên các thông số chuyến đi {params}"
    f"mức tiêu thụ nhiên liệu là {prediction_value:.2f} đơn vị.\n\n"
    f"Bây giờ để tôi giải thích ý nghĩa của kết quả này và những yếu tố nào đã ảnh hưởng đến dự đoán..."
    )
    elaboration_prompt = "Vui lòng giải thích chi tiết về dự đoán này với những thông tin hữu ích. KHÔNG sử dụng các ký tự markdown như *, **, #, -, ` trong câu trả lời."
    result_messages = [{"role": "assistant", "content": assistant_message}]
    elaboration_messages = result_messages + [{"role": "user", "content": elaboration_prompt}]
    final_response = asyncio.run(llm_service.chat(elaboration_messages, "vi"))
    # Chuẩn hóa markdown sau khi nhận response
    final_response = _normalize_markdown(final_response)
    return final_response


def _normalize_ship_type(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.capitalize()


def _normalize_numeric(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_from_structured(structured_params: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for source_key, target_key in STRUCTURED_FIELD_MAP.items():
        if source_key not in structured_params:
            continue
        value = structured_params[source_key]
        if target_key == "ship_type":
            ship_type = _normalize_ship_type(value)
            if ship_type:
                normalized[target_key] = ship_type
        else:
            numeric = _normalize_numeric(value)
            if numeric is not None:
                normalized[target_key] = numeric
    return normalized


def extract_params(
    message: str,
    conversation_id: int,
    db: Session,
    structured_params: Optional[Dict[str, Any]] = None,
):
    extracted: Dict[str, Any] = {}

    if structured_params:
        extracted.update(_extract_from_structured(structured_params))

    for key, pattern in PATTERNS.items():
        if extracted.get(key) is not None:
            continue
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            extracted[key] = match.group(1)

    if not extracted:
        return False

    state = db.query(State).filter_by(conversation_id=conversation_id).first()
    if not state:
        state = State(conversation_id=conversation_id)
        db.add(state)

    all_fields = list(PATTERNS.keys())
    previously_full = all(getattr(state, field) is not None for field in all_fields)

    for key, value in extracted.items():
        if key == "ship_type":
            setattr(state, key, _normalize_ship_type(value))
        else:
            numeric = _normalize_numeric(value)
            setattr(state, key, numeric)

    db.commit()

    missing = [field for field in all_fields if getattr(state, field) is None]
    provided = [key for key in extracted.keys()]
    params = {field: getattr(state, field) for field in all_fields}

    if previously_full:
        prediction = model_service.predict(params)
        answer = call_llm(prediction, params)
        response = (
            f"Cảm ơn bạn đã cập nhật thông tin về {', '.join(LABELS[p] for p in provided)}. "
            f"Tôi sẽ tính toán lại dự đoán dựa trên dữ liệu mới."
        )
        return {
            "done": True,
            "message": response,
            "updated": True,
            "prediction": prediction,
            "llm_response": answer,
            "params": params,
        }

    if missing:
        intro = random.choice(["Tuyệt vời!", "Rất tốt!", "Cảm ơn bạn!", "Tốt lắm!"])
        transition = random.choice([
            "Để có kết quả chính xác nhất,",
            "Để tôi dự đoán tốt hơn,",
            "Cần thêm một chút dữ liệu,"
        ])
        ask = random.choice([
            "bạn vui lòng cung cấp thêm về",
            "bạn có thể nói rõ hơn về",
            "bạn giúp tôi bổ sung thông tin về"
        ])

        response = (
            f"{intro} Tôi đã ghi nhận {', '.join(LABELS[p] for p in provided)}. "
            f"{transition} {ask} {', '.join(LABELS[m] for m in missing)} không?"
        )

        return {"done": False, "message": response, "updated": False, "params": params}

    result = model_service.predict(params)
    llm_answer = call_llm(result, params)

    return {
        "done": True,
        "message": "Tôi đã có đủ thông tin, đang tính toán mức tiêu thụ nhiên liệu...",
        "updated": False,
        "result": result,
        "llm_response": llm_answer,
        "params": params,
    }
def store_document_chunk(content: str, metadata: dict):
    """
    Tạo embedding, sau đó lưu vào bảng fluxmare_chunks.
    """
    try:
        # 1. Tạo embedding từ nội dung
        embedding_vector = model_service.get_embedding(content)

        # 2. Tạo row mới
        chunk = DocumentChunk(
            content=content,
            embedding=embedding_vector,
            metadata=metadata,
        )

        # 3. Lưu DB
        db.session.add(chunk)
        db.session.commit()

        print(f"[✓] Saved chunk id={chunk.id}, dim={len(embedding_vector)}")
        return chunk

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Failed to store chunk: {str(e)}")
        raise

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)

    if a is None or b is None:
        return 0.0

    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0

    return float(np.dot(a, b) / denom)
def search_embedding(message: str):
    # 1. Lấy embedding của message nhập vào
    query_vec = model_service.get_embedding(message)

    # 2. Lấy toàn bộ chunk từ DB
    chunks = DocumentChunk.query.all()

    results = []
    for chunk in chunks:
        if chunk.embedding is None:
            continue

        sim = cosine_similarity(query_vec, chunk.embedding)

        # Chỉ lấy chunk có similarity >= 0.7
        if sim >= 0.7:
            results.append({
                "id": chunk.id,
                "content": chunk.content,
                "similarity": round(sim, 4)
            })

    # Nếu không có chunk nào ≥ 0.7 → trả về message gốc, không context
    if not results:
        return [
            {"role": "system", "content": "Không tìm thấy thông tin liên quan (similarity < 0.7)."},
            {"role": "user", "content": message}
        ]

    # Sort giảm dần similarity và lấy top 3
    top_results = sorted(results, key=lambda x: x["similarity"], reverse=True)[:3]

    context_text = (
        "Dưới đây là các thông tin tham khảo để giúp bạn trả lời câu hỏi, "
        "không phải lịch sử trò chuyện:\n"
    )
    
    for idx, r in enumerate(top_results, 1):
        context_text += f"{idx}. {r['content']} (sim={r['similarity']})\n"

    messages = [
        {"role": "system", "content": context_text},
        {"role": "user", "content": message}
    ]

    return messages
