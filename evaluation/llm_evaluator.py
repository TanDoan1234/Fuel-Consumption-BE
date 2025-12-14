"""
LLM Evaluation Script for Research Paper
Đánh giá 3 LLMs (Gemma 2 9B, Qwen 2.5 7B, Llama 3 8B) trên 50 test cases với RAG system.
"""

import json
import logging
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Thêm thư mục gốc vào sys.path để import được core module
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import httpx
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from scipy import stats

# Import Flask app context để sử dụng database
from core import create_app
from core.database import db
from core.supportfunc import search_embedding

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('llm_evaluation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Config:
    """Chứa constants và configuration"""
    
    # LM Studio endpoint
    LLM_API_URL = "http://localhost:1234/v1/chat/completions"
    
    # Model names (theo format LM Studio)
    # Lưu ý: Tên model phải khớp CHÍNH XÁC với tên model đã load trong LM Studio
    # Script sẽ tự động discover và map models nếu tên không khớp
    # Từ log: Available models: ['qwen/qwen2.5-vl-7b', 'google/gemma-2-9b', 'meta-llama-3.1-8b-instruct']
    MODELS = {
        # "gemma": {
        #     "name": "google/gemma-2-9b",  # Đã bỏ Gemma
        #     "display": "Gemma 2 9B"
        # },
        "qwen": {
            "name": "qwen/qwen2.5-vl-7b",  # Đã sửa theo discovered models
            "display": "Qwen 2.5 VL 7B"
        },
        "llama": {
            "name": "meta-llama-3.1-8b-instruct",  # Đúng rồi
            "display": "Llama 3.1 8B"
        }
    }
    
    # API settings
    TIMEOUT = 120.0  # Tăng timeout lên 120s vì models chạy chậm trên GPU
    MAX_RETRIES = 3
    TEMPERATURE = 0.1
    MAX_TOKENS = 500
    
    # Performance settings để giảm nóng máy
    RUN_SEQUENTIAL = True  # Chạy tuần tự thay vì song song (giảm tải GPU)
    DELAY_BETWEEN_REQUESTS = 2.0  # Delay giây giữa các requests (để GPU nghỉ)
    DELAY_BETWEEN_TEST_CASES = 5.0  # Delay giây giữa các test cases
    
    # Scoring weights
    WEIGHTS = {
        "time": 0.15,
        "vietnamese": 0.20,
        "keyword": 0.20,
        "no_hallucination": 0.25,
        "length": 0.10,
        "manual": 0.10
    }
    
    # Hallucination patterns
    HALLUCINATION_PATTERNS = {
        "fake_citations": re.compile(
            r"(?:theo|theo lời|theo ý kiến|theo nghiên cứu của|theo giáo sư|theo tiến sĩ|theo chuyên gia)\s+[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ][a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ\s]+",
            re.IGNORECASE
        ),
        "future_dates": re.compile(r"(?:năm|year)\s*(?:20)?(2[5-9]|[3-9]\d{2})"),
        "fake_ships": re.compile(r"tàu\s+([A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]{2,})"),
        "unattributed_numbers": re.compile(r"(\d+(?:\.\d+)?%)(?!\s*(?:theo|nguồn|IMO|IEA|EEDI|nghiên cứu|research|study))", re.IGNORECASE)
    }
    
    # Valid entities
    VALID_SHIPS = {"CETO", "POSEIDON", "TRITON"}
    COMMON_ENGLISH_WORDS = {"the", "is", "are", "was", "were", "have", "has", "according", "based", "research", "study"}
    TECHNICAL_TERMS = {"CETO", "POSEIDON", "TRITON", "EEDI", "EEOI", "IMO", "m/s", "kg", "km", "h", "s"}
    
    # Length scoring curve
    LENGTH_SCORE_CURVE = {
        "optimal": (50, 150, 100.0),
        "good_min": (30, 49, 70.0),
        "good_max": (151, 200, 50.0),
        "poor": (0, 29, 50.0),
        "too_long": (201, 10000, 50.0)
    }
    
    # Vietnamese character pattern
    VIETNAMESE_CHARS = re.compile(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]')


class RAGManager:
    """Quản lý RAG context retrieval"""
    
    def __init__(self, app_context):
        """
        Args:
            app_context: Flask application context
        """
        self.app_context = app_context
    
    def get_context(self, question: str) -> List[Dict[str, str]]:
        """
        Gọi search_embedding để lấy RAG context
        
        Args:
            question: Câu hỏi từ user
            
        Returns:
            List of messages với format [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        try:
            with self.app_context:
                messages = search_embedding(question)
                return messages
        except Exception as e:
            logger.error(f"RAG error for question '{question[:50]}...': {str(e)}")
            # Fallback: trả về message không có context
            return [
                {"role": "system", "content": "Không thể lấy RAG context."},
                {"role": "user", "content": question}
            ]


class LLMCaller:
    """Gọi LLM API với retry logic"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = httpx.Client(timeout=config.TIMEOUT)
    
    def discover_models(self) -> List[str]:
        """
        Discover available models từ LM Studio
        
        Returns:
            List of available model names
        """
        try:
            # LM Studio có endpoint /v1/models để list models
            models_url = self.config.LLM_API_URL.replace("/chat/completions", "/models")
            response = self.client.get(models_url, timeout=10.0)
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
                logger.info(f"Discovered {len(models)} models: {models}")
                return models
        except Exception as e:
            logger.warning(f"Could not discover models: {str(e)}")
        return []
    
    def call_lm_studio(
        self, 
        model_name: str, 
        messages: List[Dict[str, str]]
    ) -> Tuple[str, float]:
        """
        Gọi LM Studio API với retry logic
        
        Args:
            model_name: Tên model (vd: "google/gemma-2-9b-it")
            messages: List of messages
            
        Returns:
            Tuple (response_text, elapsed_time_seconds)
        """
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": self.config.TEMPERATURE,
            "max_tokens": self.config.MAX_TOKENS,
            "stream": False
        }
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                start_time = time.time()
                response = self.client.post(
                    self.config.LLM_API_URL,
                    json=payload,
                    timeout=self.config.TIMEOUT
                )
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if content:
                        return content.strip(), round(elapsed, 2)
                    else:
                        logger.warning(f"Empty response from {model_name}, attempt {attempt + 1}")
                else:
                    # Log response body để debug
                    try:
                        error_body = response.json()
                        logger.warning(
                            f"HTTP {response.status_code} from {model_name}, attempt {attempt + 1}. "
                            f"Error: {error_body}"
                        )
                    except:
                        error_body = response.text[:500]  # Limit length
                        logger.warning(
                            f"HTTP {response.status_code} from {model_name}, attempt {attempt + 1}. "
                            f"Response: {error_body}"
                        )
                    
                    # Nếu là lỗi 400 và attempt đầu tiên, thử discover models
                    if response.status_code == 400 and attempt == 0:
                        available_models = self.discover_models()
                        if available_models:
                            logger.info(f"Available models in LM Studio: {available_models}")
                            logger.info(f"Trying to use model: {model_name}")
                            logger.info("HINT: Kiểm tra tên model trong Config.MODELS có khớp với LM Studio không")
                    
            except httpx.TimeoutException:
                logger.warning(f"Timeout for {model_name}, attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Error calling {model_name}, attempt {attempt + 1}: {str(e)}")
            
            # Exponential backoff
            if attempt < self.config.MAX_RETRIES - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
        
        # Nếu tất cả retries đều fail
        logger.error(f"All retries failed for {model_name}")
        return "", self.config.TIMEOUT
    
    def __del__(self):
        if hasattr(self, 'client'):
            self.client.close()


class MetricsCalculator:
    """Tính toán các metrics tự động"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def is_vietnamese_acceptable(self, text: str) -> bool:
        """
        Kiểm tra response có phải tiếng Việt không
        
        Tiêu chí:
        - Trên 15% ký tự là chữ tiếng Việt có dấu
        - Dưới 5 từ tiếng Anh phổ biến (trừ technical terms)
        """
        if not text:
            return False
        
        # Đếm ký tự tiếng Việt
        vietnamese_chars = len(self.config.VIETNAMESE_CHARS.findall(text))
        total_chars = len(text.replace(" ", ""))
        
        if total_chars == 0:
            return False
        
        vietnamese_ratio = vietnamese_chars / total_chars if total_chars > 0 else 0
        
        # Đếm từ tiếng Anh phổ biến (case-insensitive, whole word)
        words = re.findall(r'\b\w+\b', text.lower())
        english_count = sum(1 for word in words if word in self.config.COMMON_ENGLISH_WORDS)
        
        # Cho phép technical terms
        technical_count = sum(1 for word in words if word.upper() in self.config.TECHNICAL_TERMS)
        english_count = max(0, english_count - technical_count)
        
        return vietnamese_ratio > 0.15 and english_count < 5
    
    def extract_keywords(self, response: str, expected_keywords: str) -> Tuple[int, int, str]:
        """
        Đếm keywords xuất hiện trong response
        
        Args:
            response: LLM response text
            expected_keywords: Comma-separated keywords
            
        Returns:
            Tuple (found_count, total_count, "X/Y" format)
        """
        if not expected_keywords or not response:
            return 0, 0, "0/0"
        
        keywords = [k.strip().lower() for k in expected_keywords.split(",") if k.strip()]
        total = len(keywords)
        
        if total == 0:
            return 0, 0, "0/0"
        
        response_lower = response.lower()
        found = sum(1 for keyword in keywords if keyword in response_lower)
        
        return found, total, f"{found}/{total}"
    
    def detect_hallucination(self, response: str) -> bool:
        """
        Phát hiện hallucination dựa trên 4 patterns
        
        Returns:
            True nếu phát hiện hallucination
        """
        if not response:
            return False
        
        # Pattern 1: Fake citations
        if self.config.HALLUCINATION_PATTERNS["fake_citations"].search(response):
            logger.debug("Hallucination detected: fake citations")
            return True
        
        # Pattern 2: Future dates
        if self.config.HALLUCINATION_PATTERNS["future_dates"].search(response):
            logger.debug("Hallucination detected: future dates")
            return True
        
        # Pattern 3: Fake ships
        ship_matches = self.config.HALLUCINATION_PATTERNS["fake_ships"].findall(response)
        for ship in ship_matches:
            if ship.upper() not in self.config.VALID_SHIPS:
                logger.debug(f"Hallucination detected: fake ship '{ship}'")
                return True
        
        # Pattern 4: Unattributed numbers with %
        if self.config.HALLUCINATION_PATTERNS["unattributed_numbers"].search(response):
            logger.debug("Hallucination detected: unattributed numbers")
            return True
        
        return False
    
    def calculate_length_score(self, word_count: int) -> float:
        """
        Tính điểm dựa trên số từ (scoring curve)
        
        Args:
            word_count: Số từ trong response
            
        Returns:
            Score từ 0-100
        """
        curve = self.config.LENGTH_SCORE_CURVE
        
        # Optimal range: 50-150 từ → 100 điểm
        if curve["optimal"][0] <= word_count <= curve["optimal"][1]:
            return 100.0
        
        # Good min: 30-49 từ → tăng dần từ 70 đến 98.5
        if curve["good_min"][0] <= word_count < curve["optimal"][0]:
            # Linear interpolation: 30→70, 49→98.5
            ratio = (word_count - curve["good_min"][0]) / (curve["optimal"][0] - curve["good_min"][0])
            return 70.0 + ratio * (98.5 - 70.0)
        
        # Good max: 151-200 từ → giảm dần từ 100 đến 50
        if curve["optimal"][1] < word_count <= curve["good_max"][1]:
            # Linear interpolation: 151→100, 200→50
            ratio = (word_count - curve["optimal"][1]) / (curve["good_max"][1] - curve["optimal"][1])
            return 100.0 - ratio * (100.0 - 50.0)
        
        # Poor: < 30 từ hoặc > 200 từ → 50 điểm
        return 50.0
    
    def calculate_total_score(
        self,
        response_time: float,
        is_vietnamese: bool,
        keyword_coverage: float,
        has_hallucination: bool,
        length_score: float,
        manual_score: float = 0.0
    ) -> float:
        """
        Tính tổng điểm weighted
        
        Args:
            response_time: Thời gian response (giây)
            is_vietnamese: Có phải tiếng Việt không
            keyword_coverage: Tỷ lệ keywords tìm được (0-100)
            has_hallucination: Có hallucination không
            length_score: Điểm độ dài (0-100)
            manual_score: Điểm đánh giá thủ công (0-5)
            
        Returns:
            Tổng điểm (0-100)
        """
        weights = self.config.WEIGHTS
        
        # Time score: max(0, 100 - response_time × 10)
        time_score = max(0.0, 100.0 - response_time * 10.0)
        
        # Vietnamese score: 100 nếu YES, 0 nếu NO
        vietnamese_score = 100.0 if is_vietnamese else 0.0
        
        # Keyword score: keyword_coverage
        keyword_score = keyword_coverage
        
        # No hallucination score: 100 nếu NO, 0 nếu YES
        no_hallucination_score = 100.0 if not has_hallucination else 0.0
        
        # Length score: từ curve
        length_score_val = length_score
        
        # Manual score: manual_score × 20
        manual_score_val = manual_score * 20.0
        
        # Weighted sum
        total = (
            time_score * weights["time"] +
            vietnamese_score * weights["vietnamese"] +
            keyword_score * weights["keyword"] +
            no_hallucination_score * weights["no_hallucination"] +
            length_score_val * weights["length"] +
            manual_score_val * weights["manual"]
        )
        
        return round(total, 2)


class ExcelReader:
    """Đọc test cases từ Excel file"""
    
    def read_test_cases(self, file_path: str) -> List[Dict]:
        """
        Đọc 50 test cases từ sheet "TEST_CASES"
        
        Args:
            file_path: Đường dẫn đến file eval_llms.xlsx
            
        Returns:
            List of dicts với keys: ID, Category, Question, Expected_Keywords, Expected_Behavior, Source
        """
        try:
            df = pd.read_excel(file_path, sheet_name="TEST_CASES")
            
            # Validate
            if len(df) < 50:
                logger.warning(f"Chỉ có {len(df)} test cases, yêu cầu 50")
            
            # Convert to list of dicts
            test_cases = []
            for _, row in df.iterrows():
                test_case = {
                    "ID": int(row.get("ID", 0)),
                    "Category": str(row.get("Category", "")),
                    "Question": str(row.get("Question", "")),
                    "Expected_Keywords": str(row.get("Expected_Keywords", "")),
                    "Expected_Behavior": str(row.get("Expected_Behavior", "")),
                    "Source": str(row.get("Source", ""))
                }
                test_cases.append(test_case)
            
            logger.info(f"Đọc được {len(test_cases)} test cases từ {file_path}")
            return test_cases
            
        except Exception as e:
            logger.error(f"Lỗi đọc Excel file: {str(e)}")
            raise


class ResultsWriter:
    """Ghi kết quả ra CSV, Excel và text report"""
    
    def __init__(self, config: Config, metrics_calc: MetricsCalculator):
        self.config = config
        self.metrics_calc = metrics_calc
    
    def write_csv_results(
        self, 
        results: Dict[str, List[Dict]], 
        output_dir: Path
    ):
        """
        Ghi 3 CSV files (1 file/model)
        
        Args:
            results: Dict với keys là model keys ("gemma", "qwen", "llama")
            output_dir: Thư mục output
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for model_key, model_results in results.items():
            model_display = self.config.MODELS[model_key]["display"]
            filename = f"results_{model_key}.csv"
            filepath = output_dir / filename
            
            df = pd.DataFrame(model_results)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            logger.info(f"Đã ghi {len(model_results)} kết quả vào {filepath}")
    
    def write_comparison_excel(
        self,
        results: Dict[str, List[Dict]],
        output_dir: Path
    ):
        """
        Ghi Excel file với 5 sheets
        
        Args:
            results: Dict với keys là model keys
            output_dir: Thư mục output
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / "comparison_summary.xlsx"
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Sheets 1-3: Raw results
            for model_key, model_results in results.items():
                model_display = self.config.MODELS[model_key]["display"]
                df = pd.DataFrame(model_results)
                sheet_name = f"{model_display}_Results"
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Sheet 4: Aggregate Metrics
            agg_data = self._calculate_aggregate_metrics(results)
            agg_df = pd.DataFrame(agg_data)
            agg_df.to_excel(writer, sheet_name="Aggregate_Metrics", index=False)
            
            # Sheet 5: Category Breakdown
            category_data = self._calculate_category_breakdown(results)
            category_df = pd.DataFrame(category_data)
            category_df.to_excel(writer, sheet_name="Category_Breakdown", index=False)
        
        logger.info(f"Đã ghi Excel file: {filepath}")
    
    def _calculate_aggregate_metrics(
        self, 
        results: Dict[str, List[Dict]]
    ) -> List[Dict]:
        """Tính aggregate metrics và statistical tests"""
        agg_data = []
        
        # Tính metrics cho từng model
        model_metrics = {}
        for model_key, model_results in results.items():
            model_display = self.config.MODELS[model_key]["display"]
            
            df = pd.DataFrame(model_results)
            
            # Convert columns
            df['Response_Time_Seconds'] = pd.to_numeric(df['Response_Time_Seconds'], errors='coerce')
            df['Keyword_Coverage_Percent'] = pd.to_numeric(df['Keyword_Coverage_Percent'], errors='coerce')
            df['Response_Length_Words'] = pd.to_numeric(df['Response_Length_Words'], errors='coerce')
            df['Total_Score'] = pd.to_numeric(df['Total_Score'], errors='coerce')
            
            # Vietnamese compliance
            vietnamese_count = (df['Is_Vietnamese'] == 'YES').sum()
            vietnamese_pct = (vietnamese_count / len(df)) * 100
            
            # No hallucination rate
            no_hallucination_count = (df['Has_Hallucination'] == 'NO').sum()
            no_hallucination_rate = (no_hallucination_count / len(df)) * 100
            
            model_metrics[model_key] = {
                "avg_response_time": df['Response_Time_Seconds'].mean(),
                "std_response_time": df['Response_Time_Seconds'].std(),
                "vietnamese_compliance": vietnamese_pct,
                "avg_keyword_coverage": df['Keyword_Coverage_Percent'].mean(),
                "std_keyword_coverage": df['Keyword_Coverage_Percent'].std(),
                "no_hallucination_rate": no_hallucination_rate,
                "avg_response_length": df['Response_Length_Words'].mean(),
                "std_response_length": df['Response_Length_Words'].std(),
                "avg_total_score": df['Total_Score'].mean(),
                "std_total_score": df['Total_Score'].std()
            }
            
            # Add row
            agg_data.append({
                "Metric": model_display,
                "Avg_Response_Time": f"{model_metrics[model_key]['avg_response_time']:.2f} ± {model_metrics[model_key]['std_response_time']:.2f}",
                "Vietnamese_Compliance_Percent": f"{vietnamese_pct:.1f}%",
                "Avg_Keyword_Coverage": f"{model_metrics[model_key]['avg_keyword_coverage']:.1f} ± {model_metrics[model_key]['std_keyword_coverage']:.1f}",
                "No_Hallucination_Rate": f"{no_hallucination_rate:.1f}%",
                "Avg_Response_Length": f"{model_metrics[model_key]['avg_response_length']:.0f} ± {model_metrics[model_key]['std_response_length']:.0f}",
                "Avg_Total_Score": f"{model_metrics[model_key]['avg_total_score']:.2f} ± {model_metrics[model_key]['std_total_score']:.2f}"
            })
        
        # Statistical tests
        model_keys = list(results.keys())
        if len(model_keys) >= 2:
            # T-test và Cohen's d cho Total_Score
            for i in range(len(model_keys)):
                for j in range(i + 1, len(model_keys)):
                    key1, key2 = model_keys[i], model_keys[j]
                    name1 = self.config.MODELS[key1]["display"]
                    name2 = self.config.MODELS[key2]["display"]
                    
                    df1 = pd.DataFrame(results[key1])
                    df2 = pd.DataFrame(results[key2])
                    
                    scores1 = pd.to_numeric(df1['Total_Score'], errors='coerce').dropna()
                    scores2 = pd.to_numeric(df2['Total_Score'], errors='coerce').dropna()
                    
                    if len(scores1) > 0 and len(scores2) > 0:
                        t_stat, p_value = stats.ttest_ind(scores1, scores2)
                        
                        # Cohen's d
                        pooled_std = np.sqrt((scores1.std()**2 + scores2.std()**2) / 2)
                        cohens_d = (scores1.mean() - scores2.mean()) / pooled_std if pooled_std > 0 else 0
                        
                        agg_data.append({
                            "Metric": f"T-test {name1} vs {name2}",
                            "Avg_Response_Time": f"p-value: {p_value:.4f}",
                            "Vietnamese_Compliance_Percent": f"Cohen's d: {cohens_d:.3f}",
                            "Avg_Keyword_Coverage": "",
                            "No_Hallucination_Rate": "",
                            "Avg_Response_Length": "",
                            "Avg_Total_Score": ""
                        })
        
        return agg_data
    
    def _calculate_category_breakdown(
        self, 
        results: Dict[str, List[Dict]]
    ) -> List[Dict]:
        """Tính performance theo categories"""
        category_data = []
        
        # Lấy tất cả categories
        all_categories = set()
        for model_results in results.values():
            for result in model_results:
                all_categories.add(result.get("Category", ""))
        
        # Tính avg score cho mỗi category và model
        for category in sorted(all_categories):
            row = {"Category": category}
            
            for model_key, model_results in results.items():
                model_display = self.config.MODELS[model_key]["display"]
                category_results = [r for r in model_results if r.get("Category") == category]
                
                if category_results:
                    scores = [float(r.get("Total_Score", 0)) for r in category_results]
                    avg_score = np.mean(scores) if scores else 0.0
                    row[model_display] = f"{avg_score:.2f}"
                else:
                    row[model_display] = "N/A"
            
            category_data.append(row)
        
        return category_data
    
    def write_summary_report(
        self,
        results: Dict[str, List[Dict]],
        output_dir: Path
    ):
        """
        Ghi text report
        
        Args:
            results: Dict với keys là model keys
            output_dir: Thư mục output
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / "summary_report.txt"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("LLM EVALUATION REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Executive Summary
            f.write("EXECUTIVE SUMMARY\n")
            f.write("-" * 80 + "\n")
            
            # Tính winner
            model_scores = {}
            for model_key, model_results in results.items():
                model_display = self.config.MODELS[model_key]["display"]
                df = pd.DataFrame(model_results)
                scores = pd.to_numeric(df['Total_Score'], errors='coerce').dropna()
                avg_score = scores.mean() if len(scores) > 0 else 0.0
                model_scores[model_display] = avg_score
            
            winner = max(model_scores.items(), key=lambda x: x[1])
            f.write(f"Winner: {winner[0]} với điểm trung bình {winner[1]:.2f}/100\n\n")
            
            # Detailed metrics
            f.write("DETAILED METRICS\n")
            f.write("-" * 80 + "\n")
            
            for model_key, model_results in results.items():
                model_display = self.config.MODELS[model_key]["display"]
                df = pd.DataFrame(model_results)
                
                df['Response_Time_Seconds'] = pd.to_numeric(df['Response_Time_Seconds'], errors='coerce')
                df['Keyword_Coverage_Percent'] = pd.to_numeric(df['Keyword_Coverage_Percent'], errors='coerce')
                df['Total_Score'] = pd.to_numeric(df['Total_Score'], errors='coerce')
                
                vietnamese_count = (df['Is_Vietnamese'] == 'YES').sum()
                no_hallucination_count = (df['Has_Hallucination'] == 'NO').sum()
                
                f.write(f"\n{model_display}:\n")
                f.write(f"  - Avg Response Time: {df['Response_Time_Seconds'].mean():.2f}s\n")
                f.write(f"  - Vietnamese Compliance: {vietnamese_count}/{len(df)} ({vietnamese_count/len(df)*100:.1f}%)\n")
                f.write(f"  - Avg Keyword Coverage: {df['Keyword_Coverage_Percent'].mean():.1f}%\n")
                f.write(f"  - No Hallucination Rate: {no_hallucination_count}/{len(df)} ({no_hallucination_count/len(df)*100:.1f}%)\n")
                f.write(f"  - Avg Total Score: {df['Total_Score'].mean():.2f}/100\n")
            
            f.write("\n" + "=" * 80 + "\n")
        
        logger.info(f"Đã ghi text report: {filepath}")


class LLMEvaluator:
    """Main orchestrator cho evaluation pipeline"""
    
    def __init__(self, excel_file: str, output_dir: str = "evaluation_results", max_test_cases: Optional[int] = None):
        self.config = Config()
        self.excel_file = excel_file
        self.output_dir = Path(output_dir)
        self.max_test_cases = max_test_cases  # Giới hạn số test cases để test nhanh
        
        # Initialize components
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        self.rag_manager = RAGManager(self.app_context)
        self.llm_caller = LLMCaller(self.config)
        self.metrics_calc = MetricsCalculator(self.config)
        self.excel_reader = ExcelReader()
        self.results_writer = ResultsWriter(self.config, self.metrics_calc)
        
        logger.info("LLMEvaluator initialized")
    
    def run(self):
        """Main pipeline"""
        try:
            # 1. Đọc test cases
            logger.info("Bước 1: Đọc test cases từ Excel...")
            test_cases = self.excel_reader.read_test_cases(self.excel_file)
            
            if len(test_cases) == 0:
                logger.error("Không có test cases nào!")
                return
            
            # Giới hạn số test cases nếu có max_test_cases
            if self.max_test_cases and self.max_test_cases > 0:
                test_cases = test_cases[:self.max_test_cases]
                logger.info(f"Giới hạn chỉ chạy {len(test_cases)} test cases đầu tiên")
            
            # 2. Xử lý từng test case
            logger.info(f"Bước 2: Xử lý {len(test_cases)} test cases...")
            results = self._process_test_cases(test_cases)
            
            # 3. Ghi kết quả
            logger.info("Bước 3: Ghi kết quả...")
            self.results_writer.write_csv_results(results, self.output_dir)
            self.results_writer.write_comparison_excel(results, self.output_dir)
            self.results_writer.write_summary_report(results, self.output_dir)
            
            logger.info("Hoàn thành evaluation!")
            
        except Exception as e:
            logger.error(f"Lỗi trong pipeline: {str(e)}", exc_info=True)
            raise
        finally:
            self.app_context.pop()
    
    def _process_test_cases(self, test_cases: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Xử lý tất cả test cases
        
        Returns:
            Dict với keys là model keys, values là list of results
        """
        results = {model_key: [] for model_key in self.config.MODELS.keys()}
        
        total = len(test_cases)
        for idx, test_case in enumerate(test_cases, 1):
            logger.info(f"Processing test case {idx}/{total}: ID={test_case['ID']}, Category={test_case['Category']}")
            
            # Skip nếu question rỗng
            if not test_case.get("Question", "").strip():
                logger.warning(f"Test case {test_case['ID']} có question rỗng, bỏ qua")
                continue
            
            # Lấy RAG context
            try:
                messages = self.rag_manager.get_context(test_case["Question"])
            except Exception as e:
                logger.error(f"Lỗi RAG cho test case {test_case['ID']}: {str(e)}")
                messages = [
                    {"role": "system", "content": "Không thể lấy RAG context."},
                    {"role": "user", "content": test_case["Question"]}
                ]
            
            # Gọi models (tuần tự hoặc song song tùy config)
            model_results = self._call_models(messages, test_case)
            
            # Lưu kết quả
            for model_key, result in model_results.items():
                results[model_key].append(result)
            
            # Delay giữa các test cases để GPU nghỉ
            if idx < len(test_cases) and self.config.DELAY_BETWEEN_TEST_CASES > 0:
                logger.info(f"Đợi {self.config.DELAY_BETWEEN_TEST_CASES}s trước test case tiếp theo...")
                time.sleep(self.config.DELAY_BETWEEN_TEST_CASES)
        
        return results
    
    def _call_models(
        self, 
        messages: List[Dict[str, str]], 
        test_case: Dict
    ) -> Dict[str, Dict]:
        """
        Gọi models (tuần tự hoặc song song tùy config)
        
        Returns:
            Dict với keys là model keys, values là result dict
        """
        results = {}
        
        def call_model(model_key: str) -> Tuple[str, Dict]:
            model_name = self.config.MODELS[model_key]["name"]
            response, elapsed = self.llm_caller.call_lm_studio(model_name, messages)
            
            # Tính metrics
            is_vietnamese = self.metrics_calc.is_vietnamese_acceptable(response)
            found, total, keywords_found = self.metrics_calc.extract_keywords(
                response, test_case.get("Expected_Keywords", "")
            )
            keyword_coverage = (found / total * 100) if total > 0 else 0.0
            has_hallucination = self.metrics_calc.detect_hallucination(response)
            
            # Đếm từ
            words = re.findall(r'\b\w+\b', response)
            word_count = len(words)
            length_score = self.metrics_calc.calculate_length_score(word_count)
            
            # Total score (manual_score = 0 ban đầu)
            total_score = self.metrics_calc.calculate_total_score(
                elapsed, is_vietnamese, keyword_coverage, 
                has_hallucination, length_score, 0.0
            )
            
            result = {
                "Test_ID": test_case["ID"],
                "Category": test_case["Category"],
                "Question": test_case["Question"],
                "Response": response,
                "Response_Time_Seconds": elapsed,
                "Is_Vietnamese": "YES" if is_vietnamese else "NO",
                "Keywords_Found": keywords_found,
                "Keyword_Coverage_Percent": round(keyword_coverage, 1),
                "Has_Hallucination": "YES" if has_hallucination else "NO",
                "Response_Length_Words": word_count,
                "Length_Score": round(length_score, 2),
                "Manual_Quality_Score": 0.0,  # User điền sau
                "Total_Score": total_score,
                "Notes": ""
            }
            
            return model_key, result
        
        # Parallel execution
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(call_model, model_key): model_key 
                for model_key in self.config.MODELS.keys()
            }
            
            for future in as_completed(futures):
                try:
                    model_key, result = future.result()
                    results[model_key] = result
                except Exception as e:
                    model_key = futures[future]
                    logger.error(f"Lỗi khi gọi model {model_key}: {str(e)}")
                    # Default result nếu fail
                    results[model_key] = {
                        "Test_ID": test_case["ID"],
                        "Category": test_case["Category"],
                        "Question": test_case["Question"],
                        "Response": "",
                        "Response_Time_Seconds": self.config.TIMEOUT,
                        "Is_Vietnamese": "NO",
                        "Keywords_Found": "0/0",
                        "Keyword_Coverage_Percent": 0.0,
                        "Has_Hallucination": "NO",
                        "Response_Length_Words": 0,
                        "Length_Score": 0.0,
                        "Manual_Quality_Score": 0.0,
                        "Total_Score": 0.0,
                        "Notes": f"Error: {str(e)}"
                    }
        
        return results


def main():
    """Main entry point"""
    import sys
    
    # Kiểm tra arguments
    excel_file = sys.argv[1] if len(sys.argv) > 1 else "eval_llms.xlsx"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "evaluation_results"
    max_test_cases = None
    
    # Kiểm tra có parameter max_test_cases không
    if len(sys.argv) > 3:
        try:
            max_test_cases = int(sys.argv[3])
        except ValueError:
            logger.warning(f"Parameter thứ 3 không phải số, bỏ qua: {sys.argv[3]}")
    
    if not Path(excel_file).exists():
        logger.error(f"File không tồn tại: {excel_file}")
        logger.info("Usage: python llm_evaluator.py <excel_file> [output_dir] [max_test_cases]")
        logger.info("Example: python llm_evaluator.py eval_llms.xlsx evaluation_results 2")
        sys.exit(1)
    
    # Chạy evaluation
    evaluator = LLMEvaluator(excel_file, output_dir, max_test_cases=max_test_cases)
    evaluator.run()


if __name__ == "__main__":
    main()

