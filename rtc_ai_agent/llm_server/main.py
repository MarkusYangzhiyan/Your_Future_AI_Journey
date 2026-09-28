from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from services.llm_server import chat_stream
from pydantic import BaseModel

app = FastAPI()

# 一条历史消息
class ChatMessage(BaseModel):
    role : str
    content : str 

# 一次请求结构
class ChatRequest(BaseModel):
    request : list[ChatMessage]
    query : str

# 调试接口
@app.post("/debug/chat")
def debug_chat(request:ChatRequest):
    messages = [
        message.model_dump()
        for message in request.history
    ]

    messages.append(
        {"role":"user","content":request.query}
    )

    def generate_text():
        for chunk in chat_stream(messages):
            if chunk and chunk.choices:
                content = chunk.choices[0].delat.content 
                if content:
                    yield content 

    
    return StreamingResponse(
        generate_text(),
        media_type = "text/plain"
    )


@app.post("api/chat_callback")
async def chat_callback(request:Request):
    try:
        data = await request.json()
    except Exception:
        return {"text":""}

    messages = data.get("messages",[])

    if not messages or messages[-1].get("role") != "user":
        return {"text":""}


    async def generate_sse():
        for chunk in chat_stream(messages):
            if chunk:
                chunk_json = chunk.model_dump_json()
                yield f"data:{chunk_json}\n\n"

        yield "data:[DONE]\n\n"

    return StreamingResponse(
        generate_sse(),
        media_type = "text/event-stream",
        headers = {
            "Connection":"keep-alive",
            "Access-Control-Allow-Origin":"*",
            "Cache-Control":"no-cache"
        }
    )
