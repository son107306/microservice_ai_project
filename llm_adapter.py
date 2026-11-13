
import os
import json
import time
import hashlib
from enum import Enum
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ConfigDict

load_dotenv()


# ============================================================
# 1. PROVIDER CONFIGURATION
# ============================================================

class ProviderType(str, Enum):
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    MOCK = "mock"


# ============================================================
# 2. DATA MODELS
# ============================================================

class QuizQuestion(BaseModel):
    """Cấu trúc dữ liệu của một câu hỏi trắc nghiệm."""

    model_config = ConfigDict(extra="ignore")

    id: int = Field(ge=1)
    question: str = Field(min_length=1)
    options: list[str] = Field(min_length=4, max_length=4)
    correct_answer: Literal["A", "B", "C", "D"]
    explanation: str = Field(min_length=1)


class QuizPayload(BaseModel):
    """Kết quả dữ liệu của bộ câu hỏi."""

    model_config = ConfigDict(extra="ignore")

    topic_summary: str = ""
    questions: list[QuizQuestion] = Field(default_factory=list)


# ============================================================
# 3. LLM ADAPTER
# ============================================================

class MultiLLMAdapter:
    """
    Adapter thống nhất giao tiếp với nhiều LLM provider.

    Các provider:
    - Gemini
    - DeepSeek
    - OpenAI
    - Mock
    """

    def __init__(
        self,
        provider: str = "mock",
        model_name: Optional[str] = None
    ):
        self.provider = provider.lower().strip()

        if self.provider not in [p.value for p in ProviderType]:
            raise ValueError(
                f"Provider không được hỗ trợ: {provider}"
            )

        self.model_name = model_name
        self.client = None

        if self.provider == ProviderType.GEMINI.value:
            self._init_gemini()

        elif self.provider in [
            ProviderType.DEEPSEEK.value,
            ProviderType.OPENAI.value
        ]:
            self._init_openai_compatible()

    # ========================================================
    # 4. INITIALIZE PROVIDERS
    # ========================================================

    def _init_gemini(self):
        """Khởi tạo Gemini client với retry có giới hạn."""

        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "Chưa cấu hình GEMINI_API_KEY trong file .env"
            )

        retry_options = types.HttpRetryOptions(
            attempts=2,
            initial_delay=1.0,
            max_delay=4.0,
            exp_base=2.0,
            jitter=1.0,
            http_status_codes=[
                408,
                429,
                500,
                502,
                503,
                504
            ]
        )

        http_options = types.HttpOptions(
            timeout=60000,
            retry_options=retry_options
        )

        self.client = genai.Client(
            api_key=api_key,
            http_options=http_options
        )

        self.model_name = (
            self.model_name
            or os.getenv("GEMINI_MODEL")
            or "gemini-3.8-flash"
        )

    def _init_openai_compatible(self):
        """Khởi tạo OpenAI hoặc DeepSeek client."""

        from openai import OpenAI

        if self.provider == ProviderType.DEEPSEEK.value:
            api_key = os.getenv("DEEPSEEK_API_KEY")

            if not api_key:
                raise ValueError(
                    "Chưa cấu hình DEEPSEEK_API_KEY trong file .env"
                )

            base_url = os.getenv(
                "DEEPSEEK_BASE_URL",
                "https://api.deepseek.com"
            )

            self.model_name = (
                self.model_name
                or os.getenv("DEEPSEEK_MODEL")
                or "deepseek-chat"
            )

        else:
            api_key = os.getenv("OPENAI_API_KEY")

            if not api_key:
                raise ValueError(
                    "Chưa cấu hình OPENAI_API_KEY trong file .env"
                )

            base_url = os.getenv("OPENAI_BASE_URL") or None

            self.model_name = (
                self.model_name
                or os.getenv("OPENAI_MODEL")
                or "gpt-4o-mini"
            )

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    # ========================================================
    # 5. PROMPT
    # ========================================================

    def _build_prompt(
        self,
        text: str,
        num_questions: int
    ) -> str:
        """Tạo prompt sinh câu hỏi trắc nghiệm."""

        return f"""
Bạn là một trợ lý AI chuyên tạo câu hỏi trắc nghiệm
từ tài liệu học tập.

NHIỆM VỤ:
Đọc nội dung tài liệu được cung cấp và tạo chính xác
{num_questions} câu hỏi trắc nghiệm.

YÊU CẦU:
1. Câu hỏi phải dựa trên nội dung tài liệu.
2. Không tạo câu hỏi trùng lặp.
3. Mỗi câu hỏi có chính xác 4 lựa chọn.
4. Các lựa chọn được đánh dấu A, B, C, D.
5. Chỉ có một đáp án đúng.
6. correct_answer chỉ được nhận một trong các giá trị:
   A, B, C, D.
7. Giải thích rõ ràng vì sao đáp án đó đúng.
8. Không tự ý bổ sung kiến thức không có trong tài liệu.
9. Trả về đúng định dạng JSON.

CẤU TRÚC JSON:

{{
    "topic_summary": "Tóm tắt nội dung tài liệu",
    "questions": [
        {{
            "id": 1,
            "question": "Nội dung câu hỏi?",
            "options": [
                "A. Lựa chọn thứ nhất",
                "B. Lựa chọn thứ hai",
                "C. Lựa chọn thứ ba",
                "D. Lựa chọn thứ tư"
            ],
            "correct_answer": "A",
            "explanation": "Giải thích đáp án"
        }}
    ]
}}

SỐ LƯỢNG CÂU HỎI: {num_questions}

NỘI DUNG TÀI LIỆU:
{text[:50000]}
"""

    # ========================================================
    # 6. MOCK PROVIDER
    # ========================================================

    def _generate_mock(
        self,
        text: str,
        num_questions: int
    ) -> QuizPayload:
        """Tạo dữ liệu giả lập để kiểm thử pipeline."""

        time.sleep(0.5)

        normalized_text = " ".join(text.split())

        if not normalized_text:
            raise ValueError(
                "Không thể tạo câu hỏi Mock từ văn bản rỗng."
            )

        fingerprint = hashlib.sha256(
            normalized_text.encode("utf-8")
        ).hexdigest()[:12]

        words = normalized_text.split()
        mock_questions = []

        for i in range(num_questions):
            start = (i * 25) % max(1, len(words))

            excerpt = " ".join(
                words[start:start + 25]
            )

            if not excerpt:
                excerpt = normalized_text[:180]

            mock_questions.append({
                "id": i + 1,
                "question": (
                    f"[MOCK:{fingerprint}:{i + 1}] "
                    f"Đoạn tài liệu kiểm thử đề cập nội dung nào: "
                    f"“{excerpt}”?"
                ),
                "options": [
                    "A. Nội dung được trích từ đoạn tài liệu kiểm thử",
                    "B. Một nội dung không xuất hiện trong đoạn tài liệu",
                    "C. Một nội dung giả định không liên quan",
                    "D. Không có thông tin nào được cung cấp"
                ],
                "correct_answer": "A",
                "explanation": (
                    "Đây là câu hỏi giả lập được tạo bởi Mock "
                    "để kiểm thử luồng xử lý của hệ thống."
                )
            })

        mock_data = {
            "topic_summary": (
                "Tóm tắt nội dung được tạo bởi Mock Provider."
            ),
            "questions": mock_questions
        }

        return QuizPayload.model_validate(mock_data)

    # ========================================================
    # 7. GEMINI PROVIDER
    # ========================================================

    def _generate_gemini(
        self,
        prompt: str
    ) -> QuizPayload:
        """Gọi Gemini với đầu ra có cấu trúc."""

        from google.genai import types

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QuizPayload
            )
        )

        if not response.text:
            raise ValueError(
                "Gemini không trả về nội dung."
            )

        return QuizPayload.model_validate_json(
            response.text
        )

    # ========================================================
    # 8. OPENAI / DEEPSEEK PROVIDER
    # ========================================================

    def _generate_openai_compatible(
        self,
        prompt: str
    ) -> QuizPayload:
        """Gọi OpenAI hoặc DeepSeek thông qua OpenAI SDK."""

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Bạn là trợ lý AI chuyên tạo câu hỏi "
                        "trắc nghiệm từ tài liệu. "
                        "Chỉ trả về JSON hợp lệ."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={
                "type": "json_object"
            },
            temperature=0.3
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError(
                f"{self.provider} không trả về nội dung."
            )

        data = json.loads(content)

        return QuizPayload.model_validate(data)

    # ========================================================
    # 9. PUBLIC GENERATE METHOD
    # ========================================================

    def generate(
        self,
        text: str,
        num_questions: int = 5
    ) -> dict:
        """
        Sinh câu hỏi từ một đoạn văn bản.

        Returns:
            {
                "payload": QuizPayload,
                "model": str,
                "latency_ms": int
            }
        """

        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                "Nội dung đầu vào không được để trống."
            )

        if not isinstance(num_questions, int):
            raise TypeError(
                "num_questions phải là số nguyên."
            )

        if num_questions < 1 or num_questions > 50:
            raise ValueError(
                "num_questions phải nằm trong khoảng 1 đến 50."
            )

        start_time = time.perf_counter()

        if self.provider == ProviderType.MOCK.value:
            payload = self._generate_mock(
                text=text,
                num_questions=num_questions
            )
            used_model = "mock-llm-v2"

        elif self.provider == ProviderType.GEMINI.value:
            prompt = self._build_prompt(
                text=text,
                num_questions=num_questions
            )
            payload = self._generate_gemini(prompt)
            used_model = self.model_name

        else:
            prompt = self._build_prompt(
                text=text,
                num_questions=num_questions
            )
            payload = self._generate_openai_compatible(prompt)
            used_model = self.model_name

        # ----------------------------------------------------
        # VALIDATE RESULT
        # ----------------------------------------------------

        if len(payload.questions) != num_questions:
            raise ValueError(
                f"LLM trả về {len(payload.questions)} câu hỏi, "
                f"nhưng yêu cầu {num_questions} câu."
            )

        for index, question in enumerate(
            payload.questions,
            start=1
        ):
            question.id = index

            if len(question.options) != 4:
                raise ValueError(
                    f"Câu hỏi {index} không có đúng 4 lựa chọn."
                )

            if not question.question.strip():
                raise ValueError(
                    f"Câu hỏi {index} có nội dung rỗng."
                )

            if not question.explanation.strip():
                raise ValueError(
                    f"Câu hỏi {index} thiếu phần giải thích."
                )

        latency_ms = int(
            (time.perf_counter() - start_time) * 1000
        )

        return {
            "payload": payload,
            "model": used_model,
            "latency_ms": latency_ms
        }
