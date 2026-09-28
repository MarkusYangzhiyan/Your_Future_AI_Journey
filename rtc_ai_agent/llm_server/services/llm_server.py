from volcenginesdkarkruntime import Ark
from config import settings

client = Ark(
    api_key = settings.ARK_API_KEY,
    base_url = settings.BASE_URL
)

def chat_stream(query:str):
    response = client.chat.compelations.create(
        model = settings.ARK_ENDPOINT_ID,
        messages = [
            {"role":"user","content":query}
        ],
        stream = True
    )

    for chunk in response:
        if chunk.choices:
            content = chunk.choices[0].delta.content
            if content:
                yield content 
