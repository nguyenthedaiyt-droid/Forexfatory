"""
analyzer.py - Tích hợp Google Gemini AI để phân tích tin tức
"""

import google.generativeai as genai
from config import GEMINI_API_KEY
import json

def setup_analyzer():
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)

async def analyze_news_impact(title: str, summary: str) -> dict:
    """
    Sử dụng Gemini để dịch tin tức sang Tiếng Việt và phân tích tác động.
    Trả về Dictionary chứa 'title', 'summary' và 'analysis'.
    """
    if not GEMINI_API_KEY:
        return {}

    prompt = f"""
Hãy đóng vai trò là một biên dịch viên và chuyên gia phân tích tài chính vĩ mô.
Yêu cầu:
1. Dịch Tiêu đề tin tức sang Tiếng Việt.
2. Dịch Tóm tắt tin tức sang Tiếng Việt.
3. Phân tích siêu ngắn gọn bằng Tiếng Việt về tác động dự kiến của bản tin này đối với:
   - Các chỉ số chứng khoán Mỹ (NQ, ES, YM).
   - Nền kinh tế vĩ mô và đồng USD.

Tin tức gốc:
Tiêu đề: {title}
Tóm tắt: {summary}

QUAN TRỌNG: Chỉ trả về ĐÚNG MỘT chuỗi JSON hợp lệ (không kèm theo bất kỳ chữ nào khác, không dùng markdown ```json) với cấu trúc bắt buộc như sau:
{{
  "title": "Tiêu đề tiếng Việt",
  "summary": "Tóm tắt tiếng Việt",
  "analysis": "Nội dung phân tích..."
}}
"""

    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        response = await model.generate_content_async(prompt)
        text = response.text.strip()
        
        # Tiêu diệt markdown lỡ AI có thêm vào
        if text.startswith("```json"): text = text[7:]
        elif text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
        
        return json.loads(text.strip())
    except Exception as e:
        print(f"[ANALYZER] ❌ Lỗi khi phân tích/dịch tự động: {e}")
        return {"analysis": "*(AI Analysis temporarily unavailable)*"}
