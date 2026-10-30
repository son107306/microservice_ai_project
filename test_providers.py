from llm_adapter import MultiLLMAdapter

TEXT = """
Trí tuệ nhân tạo (AI) là lĩnh vực khoa học máy tính
nghiên cứu việc tạo ra các hệ thống có khả năng thực hiện
những nhiệm vụ thường đòi hỏi trí thông minh của con người.
Machine Learning là một nhánh của AI, cho phép máy tính
học từ dữ liệu.
"""

providers = ["openai", "deepseek"]

for provider in providers:
    print(f"\n{'=' * 40}")
    print("ĐANG KIỂM TRA:", provider.upper())
    print("=" * 40)

    try:
        adapter = MultiLLMAdapter(provider=provider)

        quiz, model, latency = adapter.generate(
            text=TEXT,
            num_questions=3
        )

        print("Model:", model)
        print("Latency:", latency, "ms")
        print("Số câu hỏi:", len(quiz.questions))
        print("Câu hỏi đầu tiên:", quiz.questions[0].question)

    except Exception as e:
        print("LỖI:", str(e))