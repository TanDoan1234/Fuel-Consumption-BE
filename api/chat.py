from __future__ import annotations

import asyncio
from datetime import datetime
import json
from typing import Any, Dict, List, Optional
import re

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload
from werkzeug.exceptions import InternalServerError

from core.database import db
from core.models import Conversation, DocumentChunk, Message, User
from core.security import token_required
from models.request import ChatRequest, ChatWithPredictionRequest, PredictionRequest
from models.response import ChatWithPredictionResponse, PredictionResponse, ChatResponse
from services import model_service
from services.llm_service import llm_service
from services.model_service import model_service
from core.supportfunc import cosine_similarity, extract_params, get_example_response, search_embedding, store_document_chunk


chat_bp = Blueprint("chat", __name__)

DEFAULT_BOT_REPLY = "Hien tai chua ket noi LM Studio"


def _extract_structured_inputs(context_messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for ctx in context_messages:
        content = ctx.get("content")
        if not isinstance(content, str):
            continue
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            continue
        json_payload = content[start : end + 1]
        try:
            return json.loads(json_payload)
        except json.JSONDecodeError:
            continue
    return None


def _params_to_form_data(params: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not params:
        return None

    return {
        "speedOverGround": params.get("Ship_SpeedOverGround"),
        "windSpeed10M": params.get("Weather_WindSpeed10M"),
        "waveHeight": params.get("Weather_WaveHeight"),
        "wavePeriod": params.get("Weather_WavePeriod"),
        "seaFloorDepth": params.get("Environment_SeaFloorDepth"),
        "temperature2M": params.get("Weather_Temperature2M"),
        "oceanCurrentVelocity": params.get("Weather_OceanCurrentVelocity"),
        "shipType": params.get("ship_type"),
    }


def _message_to_dict(message: Message) -> Dict[str, Any]:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "content": message.content,
        "metadata": message.metadata_json,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def _conversation_to_dict(
    conversation: Conversation, include_messages: bool = False
) -> Dict[str, Any]:
    message_objects = list(conversation.messages or [])
    messages: List[Dict[str, Any]] = []
    last_message: Optional[Dict[str, Any]] = None

    if include_messages:
        messages = [_message_to_dict(msg) for msg in message_objects]
    elif message_objects:
        last_message = _message_to_dict(message_objects[-1])

    first_user_message = next(
        (msg for msg in message_objects if msg.role == "user"), None
    )

    return {
        "id": conversation.id,
        "title": conversation.title,
        "user_id": conversation.user_id,
        "created_at": conversation.created_at.isoformat()
        if conversation.created_at
        else None,
        "updated_at": conversation.updated_at.isoformat()
        if conversation.updated_at
        else None,
        "last_message": last_message,
        "messages": messages if include_messages else None,
        "message_count": len(message_objects),
        "first_user_message": _message_to_dict(first_user_message)
        if first_user_message
        else None,
    }


@chat_bp.route("/conversations", methods=["POST"])
@token_required
def create_conversation(current_user: User):
    payload = request.get_json(silent=True) or {}

    user_id = payload.get("user_id")
    title = (payload.get("title") or "Cuoc tro chuyen moi").strip()

    if user_id and user_id != current_user.id:
        return jsonify({"error": "Khong duoc gan cuoc tro chuyen cho nguoi dung khac"}), 403

    conversation = Conversation(title=title, user_id=user_id or current_user.id)
    db.session.add(conversation)
    db.session.commit()

    return jsonify(_conversation_to_dict(conversation, include_messages=True)), 201


@chat_bp.route("/conversations", methods=["GET"])
@token_required
def list_conversations(current_user: User):
    conversations = (
        Conversation.query.options(joinedload(Conversation.messages))
        .filter(Conversation.user_id == current_user.id)
        .all() 
    )
    data = [_conversation_to_dict(conv, include_messages=False) for conv in conversations]
    return jsonify({"items": data, "total": len(data)})


@chat_bp.route("/conversations/<int:conversation_id>", methods=["GET"])
def get_conversation(conversation_id: int):
    conversation = (
        Conversation.query.options(joinedload(Conversation.messages))
        .filter_by(id=conversation_id)
        .first()
    )
    if not conversation:
        return jsonify({"error": "Conversation khong ton tai"}), 404

  

    return jsonify(_conversation_to_dict(conversation, include_messages=True))


@chat_bp.route("/conversations/<int:conversation_id>/messages", methods=["GET"])
@token_required
def list_messages(conversation_id: int, current_user: User):
    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation khong ton tai"}), 404

    if conversation.user_id != current_user.id:
        return jsonify({"error": "Khong the truy cap cuoc tro chuyen nay"}), 403

    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(
        Message.created_at.asc(), Message.id.asc()
    )
    return jsonify({"items": [_message_to_dict(msg) for msg in messages]})


@chat_bp.route("/conversations/<int:conversation_id>/messages", methods=["POST"])
@token_required
def create_message(conversation_id: int, current_user: User):
    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation khong ton tai"}), 404

    if conversation.user_id != current_user.id:
        return jsonify({"error": "Khong the truy cap cuoc tro chuyen nay"}), 403

    payload = request.get_json(silent=True) or {}
    role = (payload.get("role") or "").strip().lower()
    content = (payload.get("content") or "").strip()
    metadata = payload.get("metadata")

    if role not in {"user", "assistant"}:
        return jsonify({"error": "Role khong hop le"}), 400

    if not content:
        return jsonify({"error": "Noi dung khong duoc de trong"}), 400

    message = Message(
        conversation_id=conversation.id,
        role=role,
        content=content,
        metadata_json=metadata,
    )
    db.session.add(message)
    conversation.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify(_message_to_dict(message)), 201


@chat_bp.route("/conversations/<int:conversation_id>", methods=["DELETE"])
@token_required
def delete_conversation(conversation_id: int, current_user: User):
    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation khong ton tai"}), 404

    if conversation.user_id != current_user.id:
        return jsonify({"error": "Khong the truy cap cuoc tro chuyen nay"}), 403

    db.session.delete(conversation)
    db.session.commit()

    return jsonify({"deleted": True})


@chat_bp.route("/conversations", methods=["DELETE"])
@token_required
def delete_all_conversations(current_user: User):
    conversations = Conversation.query.filter(Conversation.user_id == current_user.id).all()
    deleted = len(conversations)

    if deleted == 0:
        return jsonify({"deleted": 0})

    for conversation in conversations:
        db.session.delete(conversation)

    db.session.commit()
    return jsonify({"deleted": deleted})


@chat_bp.route("/predict", methods=["POST"])
def predict_endpoint():
    try:
        # Get JSON body from the request
        data = request.get_json()

        # Predict using your model service
        prediction = model_service.predict(data)

        # Build response JSON
        response = {
            "fuel_consumption": prediction,
            "parameters": data
        }

        return jsonify(response), 200

    except Exception as e:
        raise InternalServerError(description=f"Prediction error: {str(e)}")
    
@chat_bp.route("/chat", methods=["POST"])
def chat_with_auto_prediction():
    try:
        data = request.get_json()
        model = data.get("model")
        print(f"Model selected: {model}")
        messages = data.get("messages", [])
        language = data.get("language", "en")
        context = data.get("context", [])
        conversation_id = data.get("conversation_id")
        conversation_id = int(conversation_id)
        structured_params = None
        user_message_content = messages[-1].get("content", "")
        print("User message content:")
        print(user_message_content)
        extracted = extract_params(user_message_content, conversation_id, db.session, structured_params)
        # store new message of user to DB
        user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=user_message_content
        )
        db.session.add(user_msg)
        db.session.commit()
        
        response_payload: Dict[str, Any]
        metadata_payload: Optional[Dict[str, Any]] = None
        if extracted is False:
            user_message = user_message_content.lower()
            response = get_example_response(db.session, user_message)
            if response is not None:
                assistant_reply = response
                response_payload = {"response": response}
            else:
                embedding_result  = search_embedding(user_message)
                print("Embedding search result:")
                print(embedding_result)
                print("Calling LLM for chat...")
                llm_response = asyncio.run(llm_service.chat(embedding_result, "vi", model_name=model))
                # LLM service đã tự động chuẩn hóa markdown
                assistant_reply = llm_response
                response_payload = {"response": llm_response}
        else:
            print("Extracted parameters:")
            print(extracted)
            assistant_reply = extracted.get("llm_response") or extracted.get("message", "")
            prediction_value = extracted.get("prediction") or extracted.get("result")
            params = extracted.get("params")
            params = params if isinstance(params, dict) else {}
            form_data = structured_params or _params_to_form_data(params)
            prediction_result = None
            if prediction_value is not None:
                prediction_result = {
                    "fuel_consumption": prediction_value,
                    "parameters": form_data or params,
                }
            response_payload = {
                "response": assistant_reply,
                "prediction_made": prediction_result is not None,
                "prediction_result": prediction_result,
            }
            if prediction_result:
                metadata_payload = {
                    "prediction_made": True,
                    "prediction_result": prediction_result,
                    "form_data": form_data or params,
                }
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=str(assistant_reply),
            metadata_json=metadata_payload,
        )
        db.session.add(assistant_msg)
        db.session.commit()
        return jsonify(response_payload)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise InternalServerError(description=f"Prediction error: {str(e)}")


@chat_bp.route("/llm-analysis", methods=["POST"])
def llm_analysis():
    """
    Nhận danh sách các phương án đã chọn (features + fuel_consumption)
    và gọi LLM để sinh phân tích cho frontend.
    Trả về JSON có cấu trúc; nếu không parse được thì trả raw_text.
    """
    try:
        payload = request.get_json(silent=True) or {}
        items = payload.get("items") or []
        language = payload.get("language", "vi")

        if not items:
            return jsonify({"error": "items_required"}), 400

        # Chuẩn hóa dữ liệu gửi LLM, giữ tiếng Việt gốc (ensure_ascii=False)
        items_json = json.dumps(items, ensure_ascii=False, indent=2)
        prompt = (
            "Bạn là chuyên gia phân tích tiêu thụ nhiên liệu tàu thủy. "
            "Mỗi mục có 7 thông số + ship_type. Đơn vị: "
            "Ship_SpeedOverGround (m/s), Weather_WindSpeed10M (m/s), Weather_WaveHeight (m), "
            "Weather_WavePeriod (s), Environment_SeaFloorDepth (m), Weather_Temperature2M (°C), "
            "Weather_OceanCurrentVelocity (m/s). "
            "Hãy trả về JSON với schema:\n"
            "{\n"
            '  "overview": "tóm tắt 1-2 câu",\n'
            '  "optimal": { "name": "#1", "fuel": 0.064, "reason": "vì sao tối ưu" },\n'
            '  "factors": ["gió thấp", "sóng nhỏ"],\n'
            '  "actions": ["hành động 1", "hành động 2"],\n'
            '  "notes": ["ghi chú thêm"],\n'
            '  "raw_text": "nếu cần thêm diễn giải"\n'
            "}\n"
            "Chỉ trả JSON hợp lệ, không thêm giải thích ngoài JSON.\n\n"
            f"Dữ liệu:\n{items_json}"
        )

        llm_messages = [{"role": "user", "content": prompt}]
        llm_response = asyncio.run(llm_service.chat(llm_messages, language))

        def _clean_and_parse(text: str):
            # Loại bỏ ```json ... ``` hoặc ``` ...
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.lstrip("`")
                # cắt phần nhãn (json)
                if "\n" in cleaned:
                    cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.strip().rstrip("`").strip()
            # Tìm khối JSON đầu tiên
            json_match = None
            try:
                json_match = next(iter(re.finditer(r"\{[\s\S]*\}", cleaned)))
            except StopIteration:
                json_match = None
            target = cleaned
            if json_match:
                target = json_match.group(0)
            try:
                return json.loads(target)
            except Exception:
                return None

        parsed = _clean_and_parse(llm_response)

        return jsonify({"analysis": parsed, "raw_text": llm_response}), 200
    except Exception as e:
        # Trả lỗi an toàn để frontend fallback local analysis
        return jsonify({"analysis": None, "raw_text": "", "error": str(e)}), 500

@chat_bp.route("/chunk", methods=["POST"])
def chunk():
    try:
        data = request.get_json()

        content = data.get("content")
        metadata = data.get("metadata", {})

        if not content:
            return jsonify({"error": "content is required"}), 400

        # Gọi lại hàm lưu chunk
        new_chunk = store_document_chunk(
            content=content,
            metadata=metadata
        )

        return jsonify({
            "message": "Chunk stored successfully",
            "chunk_id": new_chunk.id
        }), 200

    except Exception as e:
        print("Error storing chunk:", e)
        return jsonify({"error": str(e)}), 500



