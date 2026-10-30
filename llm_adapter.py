
import json
import os
import time
from enum import Enum
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


# 1. Các nhà cung cấp AI được hỗ trợ
class ProviderType(str, Enum):
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    MOCK = "mock"


# 2. Cấu trúc dữ liệu của một câu hỏi
class QuizQuestion(BaseModel):
    id: int = Field(ge=1)
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_answer: Literal["A", "B", "C", "D"]
    explanation: str


# 3. Cấu trúc dữ liệu kết quả bài quiz
class QuizPayload(BaseModel):
    topic_summary: str
    questions: list[QuizQuestion]


# 4. Bộ chuyển đổi đa nhà cung cấp LLM
class MultiLLMAdapter:

    def __init__(
        self,
        provider: str = "gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.provider = provider.lower()
        self.model_name = model_name
        self.api_key = api_key

        if self.provider not in [p.value for p in ProviderType]:
            raise ValueError(
                f"Provider '{self.provider}' không được hỗ trợ."
            )

    def _get_api_key(self, env_name: str) -> str:
        key = self.api_key or os.getenv(env_name)

        if not key:
            raise ValueError(
                f"Chưa cấu hình API key: {env_name}"
            )

        return key

    def generate(
        self,
        text: str,
        num_questions: int = 5
    ):
        if not text or not text.strip():
            raise ValueError("Nội dung tài liệu đang trống.")

        if not 1 <= num_questions <= 50:
            raise ValueError("Số câu hỏi phải từ 1 đến 50.")

        # Tạo prompt chung cho các provider
        prompt = f"""
Bạn là chuyên gia khảo thí giáo dục.

Hãy đọc tài liệu bên dưới và tạo đúng {num_questions}
câu hỏi trắc nghiệm bằng tiếng Việt.

Yêu cầu:
- Mỗi câu hỏi có đúng 4 lựa chọn.
- Mỗi câu hỏi có đúng 1 đáp án đúng.
- correct_answer chỉ được là A, B, C hoặc D.
- Có giải thích ngắn gọn dựa trên tài liệu.
- Không tự ý thêm kiến thức không có trong tài liệu.

Trả về JSON theo cấu trúc:

{{
    "topic_summary": "Tóm tắt nội dung",
    "questions": [
        {{
            "id": 1,
            "question": "Nội dung câu hỏi",
            "options": [
                "A. Lựa chọn 1",
                "B. Lựa chọn 2",
                "C. Lựa chọn 3",
                "D. Lựa chọn 4"
            ],
            "correct_answer": "A",
            "explanation": "Giải thích đáp án"
        }}
    ]
}}

TÀI LIỆU:
{text[:50000]}
"""

        # Đo thời gian xử lý của LLM
        start_time = time.perf_counter()

        # 5. Google Gemini
        if self.provider == ProviderType.GEMINI.value:
            from google import genai
            from google.genai import types

            model = self.model_name or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
            key = self._get_api_key("GEMINI_API_KEY")

            client = genai.Client(api_key=key)

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=QuizPayload,
                    temperature=0.2,
                ),
            )

            if not response.text:
                raise ValueError("Gemini không trả về nội dung.")

            payload = QuizPayload.model_validate_json(
                response.text
            )

            used_model = f"google/{model}"

        # 6. DeepSeek
        elif self.provider == ProviderType.DEEPSEEK.value:
            from openai import OpenAI

            model = self.model_name or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            key = self._get_api_key("DEEPSEEK_API_KEY")

            client = OpenAI(
                api_key=key,
                base_url="https://api.deepseek.com",
            )

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là trợ lý giáo dục. Chỉ trả về JSON hợp lệ."
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            content = response.choices[0].message.content

            if not content:
                raise ValueError("DeepSeek không trả về nội dung.")

            payload = QuizPayload.model_validate_json(content)
            used_model = f"deepseek/{model}"

        # 7. OpenAI
        elif self.provider == ProviderType.OPENAI.value:
            from openai import OpenAI

            model = self.model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            key = self._get_api_key("OPENAI_API_KEY")

            client = OpenAI(api_key=key)

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an educational assistant. Return valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            content = response.choices[0].message.content

            if not content:
                raise ValueError("OpenAI không trả về nội dung.")

            payload = QuizPayload.model_validate_json(content)
            used_model = f"openai/{model}"

        # 8. Mock: giả lập AI để kiểm thử miễn phí
        else:
            time.sleep(2)

            mock_data = {
                "topic_summary": "Tóm tắt nội dung kiểm thử Mock.",
                "questions": [
                    {
                        "id": i,
                        "question": f"Câu hỏi kiểm thử số {i}?",
                        "options": [
                            "A. Lựa chọn 1",
                            "B. Lựa chọn 2",
                            "C. Lựa chọn 3",
                            "D. Lựa chọn 4",
                        ],
                        "correct_answer": "A",
                        "explanation": "Đây là câu hỏi được tạo bởi Mock."
                    }
                    for i in range(1, num_questions + 1)
                ],
            }

            payload = QuizPayload.model_validate(mock_data)
            used_model = "mock-llm-v1"

        # Tính thời gian xử lý
        llm_latency_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2
        )

        # Kiểm tra số lượng câu hỏi
        if len(payload.questions) != num_questions:
            raise ValueError(
                f"Yêu cầu {num_questions} câu hỏi nhưng AI trả về "
                f"{len(payload.questions)} câu."
            )

        return payload, used_model, llm_latency_ms
