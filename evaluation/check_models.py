"""
Script kiểm tra các models có sẵn trong LM Studio
"""

import httpx
import json
import sys
from pathlib import Path

# Thêm thư mục gốc vào sys.path
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def check_lm_studio_models():
    """Kiểm tra models có sẵn trong LM Studio"""
    api_url = "http://localhost:1234/v1/chat/completions"
    models_url = api_url.replace("/chat/completions", "/models")
    
    print("=" * 80)
    print("KIỂM TRA MODELS TRONG LM STUDIO")
    print("=" * 80)
    print()
    
    try:
        with httpx.Client(timeout=10.0) as client:
            # Kiểm tra server có chạy không
            try:
                response = client.get(models_url)
                if response.status_code == 200:
                    data = response.json()
                    models = []
                    
                    if isinstance(data, dict) and "data" in data:
                        for model in data["data"]:
                            if isinstance(model, dict):
                                model_id = model.get("id") or model.get("name")
                                if model_id:
                                    models.append(model_id)
                    elif isinstance(data, list):
                        for model in data:
                            if isinstance(model, dict):
                                model_id = model.get("id") or model.get("name")
                                if model_id:
                                    models.append(model_id)
                            elif isinstance(model, str):
                                models.append(model)
                    
                    if models:
                        print(f"✓ Tìm thấy {len(models)} model(s) trong LM Studio:")
                        print()
                        for i, model in enumerate(models, 1):
                            print(f"  {i}. {model}")
                        print()
                        print("=" * 80)
                        print("CẤU HÌNH TRONG evaluation/llm_evaluator.py:")
                        print("=" * 80)
                        print()
                        
                        # Tìm model phù hợp cho mỗi loại
                        gemma_model = next((m for m in models if "gemma" in m.lower()), models[0] if models else "google/gemma-2-9b")
                        qwen_model = next((m for m in models if "qwen" in m.lower() and "embed" not in m.lower()), models[1] if len(models) > 1 else "qwen/qwen2.5-vl-7b")
                        llama_model = next((m for m in models if "llama" in m.lower()), models[2] if len(models) > 2 else "meta-llama-3.1-8b-instruct")
                        
                        print("MODELS = {")
                        print('    "gemma": {')
                        print(f'        "name": "{gemma_model}",')
                        print('        "display": "Gemma 2 9B"')
                        print('    },')
                        print('    "qwen": {')
                        print(f'        "name": "{qwen_model}",')
                        print('        "display": "Qwen 2.5 VL 7B"')
                        print('    },')
                        print('    "llama": {')
                        print(f'        "name": "{llama_model}",')
                        print('        "display": "Llama 3.1 8B"')
                        print('    }')
                        print("}")
                        print()
                        print("Lưu ý: Copy cấu hình trên vào Config.MODELS trong llm_evaluator.py")
                    else:
                        print("⚠ Không tìm thấy model nào trong LM Studio")
                        print("Hãy đảm bảo:")
                        print("  1. LM Studio đang chạy")
                        print("  2. Đã load ít nhất 1 model")
                        print("  3. Local server đang chạy (port 1234)")
                else:
                    print(f"✗ Lỗi HTTP {response.status_code}")
                    print(f"Response: {response.text[:500]}")
            except httpx.ConnectError:
                print("✗ Không thể kết nối đến LM Studio")
                print()
                print("Hãy đảm bảo:")
                print("  1. LM Studio đang chạy")
                print("  2. Local server đang chạy (port 1234)")
                print("  3. Kiểm tra Settings → Server → Port = 1234")
            except Exception as e:
                print(f"✗ Lỗi: {str(e)}")
                
    except Exception as e:
        print(f"✗ Lỗi kết nối: {str(e)}")
        print()
        print("Hãy đảm bảo LM Studio đang chạy và local server đã được start")


if __name__ == "__main__":
    check_lm_studio_models()

