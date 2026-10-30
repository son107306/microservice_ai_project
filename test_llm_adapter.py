
from llm_adapter import MultiLLMAdapter

adapter = MultiLLMAdapter(
    provider="mock"
)

quiz, model, latency = adapter.generate(
    text="Đây là tài liệu dùng để kiểm thử bộ sinh câu hỏi.",
    num_questions=3
)

print("Model:", model)
print("Thời gian xử lý:", latency, "ms")
print("Tóm tắt:", quiz.topic_summary)
print("Số câu hỏi:", len(quiz.questions))

for question in quiz.questions:
    print("\nCâu", question.id, ":", question.question)
    print("Các lựa chọn:", question.options)
    print("Đáp án:", question.correct_answer)
    print("Giải thích:", question.explanation)
