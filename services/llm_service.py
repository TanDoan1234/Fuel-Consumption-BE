import json
import os
import re
from typing import List, Dict, Any, Optional, Tuple

import httpx
from httpx import URL

# System Prompts
SYSTEM_PROMPT_EN = """You are a helpful maritime fuel consumption assistant powered by AI.

**LANGUAGE REQUIREMENT:**
- You MUST answer 100% in Vietnamese. Even if the prompt or parameters are in English, always reply in Vietnamese only.

**YOUR ROLE:**
You do not calculate fuel consumption yourself.
Your job is to collect all necessary parameters from the user and then CALL the prediction model.

**IMPORTANT RULES:**
- NEVER estimate or calculate fuel consumption by yourself.
- ONLY call the function `predict_fuel_consumption` once you have all required parameters.
- Respond politely and in Vietnamese natural language, but do not perform any math.
- If parameters are missing, ask for them (in Vietnamese).

**REQUIRED PARAMETERS:**
- distance (km)
- engine_efficiency (0-1)
- ship_type: Oil Service Boat, Surfer Boat, or Tanker Ship
- route_id: Lagos-Apapa, Port Harcourt-Lagos, or Warri-Bonny
- month (1-12)
- fuel_type: HFO or Other
- weather_conditions: Clear, Moderate, or Stormy

**FUNCTION CALL FORMAT:**
When all parameters are provided, respond ONLY with:

CALL_FUNCTION: predict_fuel_consumption
{
  "distance": <value>,
  "engine_efficiency": <value>,
  "ship_type": "<type>",
  "route_id": "<route>",
  "month": <value>,
  "fuel_type": "<type>",
  "weather_conditions": "<condition>"
}

Do not include any explanations, notes, or calculations before or after this call."""


SYSTEM_PROMPT_VI = """Bạn là trợ lý AI hỗ trợ dự đoán tiêu thụ nhiên liệu hàng hải. Bạn PHẢI trả lời HOÀN TOÀN bằng tiếng Việt, kể cả khi câu hỏi hay dữ liệu đầu vào là tiếng Anh."""

def _get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class LLMService:
    def __init__(
        self, 
        api_url: str = "http://localhost:1234/v1/chat/completions",
        # Default khớp với model đã tải trong LM Studio (ví dụ meta-llama-3.1-8b-instruct)
        model_name: str = "meta-llama-3.1-8b-instruct",
        temperature: float = 0.6,
        max_tokens: int = 1024
    ):
        self.api_url = api_url or os.getenv("LLM_API_URL", "http://localhost:1234/v1/chat/completions")
        self.model_name = model_name or os.getenv("LLM_MODEL_NAME", "llama3-8b-instruct")
        self.temperature = temperature if temperature is not None else _get_env_float("LLM_TEMPERATURE", 0.7)
        self.max_tokens = max_tokens if max_tokens is not None else _get_env_int("LLM_MAX_TOKENS", 1024)
        api_url_object = URL(self.api_url)
        self.models_url = str(api_url_object.copy_with(path="/v1/models", query=None))

    async def _discover_model(self, client: httpx.AsyncClient) -> Optional[str]:
        try:
            response = await client.get(self.models_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            print(f" Unable to fetch models list from {self.models_url}: {exc}")
            return None

        try:
            payload = response.json()
        except ValueError:
            return None

        data = payload.get("data") or payload.get("models")
        if not isinstance(data, list) or not data:
            return None

        first = data[0]
        if isinstance(first, dict):
            return first.get("id") or first.get("name")
        if isinstance(first, str):
            return first
        return None
    
    def get_system_prompt(self, language: str = "en") -> str:
        """Get system prompt for specified language"""
        return SYSTEM_PROMPT_VI if language == "vi" else SYSTEM_PROMPT_EN
    
    def _normalize_markdown(self, text: str) -> str:
        """
        Chuẩn hóa markdown: loại bỏ các ký tự * và ** nhưng giữ lại format in đậm
        Chuyển **text** thành text (in đậm) và *text* thành text (in nghiêng)
        """
        if not text:
            return text
        
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
    
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        language: str = "en",
        model_name: Optional[str] = None
    ) -> str:
        """
        Send chat request to LLM
        
        Args:
            messages: List of {'role': 'user/assistant', 'content': '...'}
            language: 'en' or 'vi'
        
        Returns:
            LLM response text
        """
        # Prepend system prompt
        system_prompt = self.get_system_prompt(language)
        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages
        ]
        print("Full messages sent to LLM:")
        print(full_messages)

        # Chuẩn hóa tên model (frontend có thể gửi alias cũ)
        model_to_use = model_name or self.model_name
        
        # Mapping model names từ frontend sang LM Studio identifiers
        model_mapping = {
            "meta-llama-3-8b-instruct": "meta-llama-3.1-8b-instruct",
            "meta-llama-3.1-8b-instruct": "meta-llama-3.1-8b-instruct",  # Giữ nguyên nếu đúng
            "google/gemma-2-9b": "google/gemma-2-9b",
            "qwen/qwen2.5-vl-7b": "qwen/qwen2.5-vl-7b",
        }
        
        # Áp dụng mapping nếu có
        if model_to_use in model_mapping:
            model_to_use = model_mapping[model_to_use]

        payload = {
            "model": model_to_use,
            "messages": full_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
                response = await client.post(self.api_url, json=payload)
                if response.status_code == 404:
                    fallback_model = await self._discover_model(client)
                    if fallback_model and fallback_model != self.model_name:
                        print(
                            f" LLM model '{self.model_name}' not available; retrying with '{fallback_model}'"
                        )
                        self.model_name = fallback_model
                        payload["model"] = fallback_model
                        response = await client.post(self.api_url, json=payload)
                response.raise_for_status()
                data = response.json()
                raw_content = data["choices"][0]["message"]["content"]
                # Chuẩn hóa markdown: loại bỏ các ký tự * và ** nhưng giữ lại format
                normalized_content = self._normalize_markdown(raw_content)
                return normalized_content
        except httpx.HTTPStatusError as e:
            body = None
            if e.response is not None:
                try:
                    body = e.response.json()
                except ValueError:
                    body = e.response.text
            print(f" LLM HTTP error: {e} | response={body}")
            raise
        except httpx.RequestError as e:
            # Request-level errors (timeout, connection) may not have response
            print(f" LLM request error: {e}")
            raise
        except Exception as e:
            print(f" LLM error: {e}")
            raise
    
    def parse_function_call(self, response: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if LLM response contains a function call
        
        Returns:
            (is_function_call, parameters_dict)
        """
        if re.search(r"CALL_?\s*FUNCTION\s*:\s*predict_fuel_consumption", response, re.IGNORECASE):
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    params = json.loads(json_match.group())
                    return True, params
                except json.JSONDecodeError:
                    return False, None
        return False, None

# Singleton instance
llm_service = LLMService()
