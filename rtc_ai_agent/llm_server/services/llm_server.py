from volcenginesdkarkruntime import Ark
from config import settings

client = Ark(
    api_key = settings.ARK_API_KEY,
    base_url = settings.BASE_URL
)


system_prompt = """
你是一名 Python 学习助手，面向刚开始学习编程的人。

回答要求：
1. 使用中文，先给结论，再解释原因。
2. 用简单的话解释术语，必要时给一个小例子。
3. 结合用户的学习基础和历史对话回答。
4. 每次聚焦当前问题，回答简洁。
""".strip()


def chat_stream(messages:list[dict[str,str]]):
    model_messages = [{"role":"system","content":system_prompt}]
    model_messages.extend(messages)

    response = client.chat.compelations.create(
        model = settings.ARK_ENDPOINT_ID,
        messages = messages,
        stream = True
    )

    for chunk in response:
        yield chunk 
