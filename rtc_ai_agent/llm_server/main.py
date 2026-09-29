import time

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from services.llm_server import chat_stream
from pydantic import BaseModel
from services.token_builder import AccessToken,PRIVILEGES
from config import settings

app = FastAPI()


# ----2. 前端页面请求后端，获取场景和进房参数 ----
@app.post("/getScenes")
async def get_scenes(request:Request):

    # 1. RTC 房间ID、用户ID
    room_id = "ChatRoom01"
    user_id = "Huoshan01"

    # 2. 创建token构造体
    token_builder = AccessToken(
        app_id = settings.RTC_APP_ID,
        app_key = settings.RTC_APP_KEY,
        room_id=room_id,
        user_id=user_id
    )

    # 3. 添加接收和发布流权限
    token_builder.add_privilege(
        PRIVILEGES["PrivSubscribeStream"],0
    )
    token_builder.add_privilege(
        PRIVILEGES["PrivPublishStream"],0
    )

    # 4. 设置有效期，生成token
    token_builder.expire_time(
        int(time.time()) + 3600 * 24 
    )

    token = token_builder.serialize()

    # 5. 返回场景信息和 RTC 房间参数
    return {
        "ResponseMetadata":{
            "Action":"getScenes"
        },
        "Result":{
            "scenes":[
                {
                    "scene":{
                        # ---- 开发者设置AI身份 ----
                        "id":"Custom",          # 给这个应用场景取一个程序用的编号名
                        "name":"自定义助手",     # 前端显示名称，程序通过 id 判断用户选了哪个助手
                        "botName":"AIAGENT",    # 给AI设置的 RTC 用户 ID
                        # ---- 助手头像的图片地址 ----
                        "icon":"https://lf3-rtc-demo.volccdn.com/obj/rtc-aigc-assets/DoubaoAvatar.png",
                        # ---- 功能相关 ----
                        "isInterruptMode":True,         # 是否支持打断
                        "isVision":False,               # 是否开启视觉（摄像头）
                        "isScreenMode":False,            # 是否开启屏幕共享
                        # ---- 数字人相关（无数字人时设置为None） ----
                        "isAvatarScene":None,           
                        "avatarBgUrl":None,
                    },
                    "rtc":{
                        "AppId":settings.RTC_APP_ID,
                        "RoomId":room_id,
                        "UserId":user_id,
                        "Token":token
                    },
                    "VoiceChat":{}
                }
            ]
        }
    }


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
