from fastapi import FastAPI
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
    return StreamingResponse(
        chat_stream(request.query),
        media_type = "text/plain"
    )