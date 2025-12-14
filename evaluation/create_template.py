"""
Script tạo template Excel file cho test cases
"""

import pandas as pd
from pathlib import Path

def create_template_excel(output_file: str = "eval_llms.xlsx"):
    """
    Tạo file Excel template với 50 test cases mẫu
    
    Args:
        output_file: Tên file output
    """
    # Tạo 50 test cases mẫu
    test_cases = []
    
    categories = [
        "RAG_Query",
        "Parameter_Extract", 
        "Hallucination",
        "Language_Test",
        "Multi_Turn",
        "Edge_Case"
    ]
    
    # Sample questions cho mỗi category
    sample_questions = {
        "RAG_Query": [
            "CETO là loại tàu gì?",
            "Các yếu tố nào ảnh hưởng đến tiêu thụ nhiên liệu?",
            "Tốc độ gió ảnh hưởng như thế nào đến nhiên liệu?",
            "Độ sâu đáy biển có ảnh hưởng gì không?",
            "Nhiệt độ môi trường ảnh hưởng ra sao?",
            "Chu kỳ sóng là gì?",
            "Tốc độ dòng chảy đại dương là gì?",
            "Loại tàu nào tiêu thụ nhiên liệu ít nhất?",
            "EEDI là gì?",
            "EEOI được tính như thế nào?",
        ],
        "Parameter_Extract": [
            "Tốc độ tàu là 12 m/s, gió 30 km/h, sóng cao 2m",
            "Tàu CETO, tốc độ 15, gió 25, sóng 1.5m, chu kỳ 8s",
            "Tôi có tàu POSEIDON, tốc độ 10 m/s",
            "Nhiệt độ 25 độ C, độ sâu 150m",
            "Tốc độ dòng chảy 1.5 m/s, nhiệt độ 20 độ",
            "Tàu TRITON, tốc độ 18, gió 35, sóng 3m",
            "Gió 20 km/h, sóng 1m, chu kỳ 6 giây",
            "Độ sâu 200m, nhiệt độ 30 độ C",
            "Tốc độ 14 m/s, gió 28, sóng 2.5m, chu kỳ 10s",
            "Tàu CETO, tất cả thông số: tốc độ 12, gió 25, sóng 1.8m, chu kỳ 7s, độ sâu 120m, nhiệt độ 24, dòng chảy 1.2",
        ],
        "Hallucination": [
            "Theo giáo sư Nguyễn Văn A, tàu tiêu thụ 50% nhiên liệu",
            "Năm 2025, IMO sẽ ban hành quy định mới",
            "Tàu NEPTUNE là loại tàu mới nhất",
            "Theo nghiên cứu của tiến sĩ B, hiệu suất tăng 30%",
            "Tàu AQUA là loại tàu tiết kiệm nhất",
            "Năm 2026 sẽ có công nghệ mới",
            "Theo chuyên gia C, tốc độ tối ưu là 20 m/s",
            "Tàu OCEANUS có hiệu suất cao nhất",
            "Theo giáo sư D, nhiệt độ ảnh hưởng 40%",
            "Năm 2027 sẽ có quy định mới về EEDI",
        ],
        "Language_Test": [
            "What is fuel consumption?",
            "How does wind speed affect fuel?",
            "Tell me about CETO ship",
            "What are the parameters?",
            "Explain EEDI",
            "What is wave height?",
            "How to calculate fuel?",
            "What is ship speed?",
            "Tell me about temperature",
            "What is ocean current?",
        ],
        "Multi_Turn": [
            "Tôi muốn biết về tàu CETO",
            "Tốc độ tàu là bao nhiêu?",
            "Còn gió thì sao?",
            "Và sóng?",
            "Nhiệt độ có ảnh hưởng không?",
            "Tôi có tàu POSEIDON",
            "Tốc độ là 12 m/s",
            "Gió 30 km/h",
            "Sóng cao 2m",
            "Chu kỳ sóng là 8 giây",
        ],
        "Edge_Case": [
            "Tốc độ tàu là 0 m/s",
            "Gió 100 km/h",
            "Sóng cao 20m",
            "Nhiệt độ -10 độ C",
            "Độ sâu 10000m",
            "Tất cả thông số đều bằng 0",
            "Tốc độ âm",
            "Gió âm",
            "Sóng âm",
            "Nhiệt độ 200 độ C",
        ]
    }
    
    # Tạo 50 test cases
    test_id = 1
    for category in categories:
        questions = sample_questions.get(category, [])
        for question in questions[:10]:  # Lấy 10 câu mỗi category
            # Tạo expected keywords dựa trên question
            keywords = []
            if "tốc độ" in question.lower() or "speed" in question.lower():
                keywords.append("tốc độ")
            if "gió" in question.lower() or "wind" in question.lower():
                keywords.append("gió")
            if "sóng" in question.lower() or "wave" in question.lower():
                keywords.append("sóng")
            if "nhiệt độ" in question.lower() or "temperature" in question.lower():
                keywords.append("nhiệt độ")
            if "ceto" in question.lower():
                keywords.append("CETO")
            if "poseidon" in question.lower():
                keywords.append("POSEIDON")
            if "triton" in question.lower():
                keywords.append("TRITON")
            if "nhiên liệu" in question.lower() or "fuel" in question.lower():
                keywords.append("nhiên liệu")
            if "eedi" in question.lower():
                keywords.append("EEDI")
            if "eeoi" in question.lower():
                keywords.append("EEOI")
            
            test_cases.append({
                "ID": test_id,
                "Category": category,
                "Question": question,
                "Expected_Keywords": ",".join(keywords) if keywords else "nhiên liệu,tàu",
                "Expected_Behavior": f"Trả lời đúng về {category.lower()}",
                "Source": "Template"
            })
            test_id += 1
    
    # Đảm bảo có đủ 50 test cases
    while len(test_cases) < 50:
        test_cases.append({
            "ID": len(test_cases) + 1,
            "Category": "RAG_Query",
            "Question": f"Câu hỏi mẫu số {len(test_cases) + 1}",
            "Expected_Keywords": "nhiên liệu,tàu",
            "Expected_Behavior": "Trả lời đúng",
            "Source": "Template"
        })
    
    # Tạo DataFrame và ghi Excel
    df = pd.DataFrame(test_cases[:50])  # Chỉ lấy 50 đầu tiên
    df.to_excel(output_file, sheet_name="TEST_CASES", index=False)
    
    print(f"Đã tạo template Excel: {output_file}")
    print(f"Số test cases: {len(df)}")
    print(f"Categories: {df['Category'].value_counts().to_dict()}")


if __name__ == "__main__":
    import sys
    output_file = sys.argv[1] if len(sys.argv) > 1 else "eval_llms.xlsx"
    create_template_excel(output_file)

