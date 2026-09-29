import os
import json
import time
import httpx

from servers.llm_server import chat_stream
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from servers.token_build import AccessToken, PRIVILEGES
from config import settings
from servers.utils import Signer


app = FastAPI()

# 前端与后端使用不同端口时，浏览器会把它们视为不同来源。这段配置用于允许前端调用后端。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 一条历史消息的结构
class ChatMessage(BaseModel):
    role:str
    content:str


# 一次请求的结构
class ChatRequest(BaseModel):
    history:list[ChatMessage] = Field(default_factory=list)
    query:str

# ---- 调试接口 ---- 
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
                content = chunk.choices[0].delta.content 
                if content:
                    yield content 

    return StreamingResponse(
        generate_text(),
        media_type = "text/plain"
    )


# ---- 火山RTC请求我们的后端 ----
@app.post("/api/chat_callback")
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

    # 返回流式响应
    # https://docs.volcengine.com/docs/real_time_communication/Accessthird-partylargemodelsoragents?lang=zh
    return StreamingResponse(
        generate_sse(),
        media_type = "text/event-stream",
        headers = {
            "Connection":"keep-alive",
            "Access-Control-Allow-Origin":"*",
            "Cache-Control":"no-cache"
        }
    )

# ---- 前端页面请求我们的后台: 获取场景和进房参数 ----
"""
前端页面
    ↓ POST /getScenes
您的 FastAPI 后端
    ↓ 返回场景配置和进房凭证
前端页面
    ↓ 携带这些参数，通过 RTC SDK 加入房间
火山 RTC
"""
@app.post("/getScenes")
async def get_scenes(request:Request):

    # ---- 1. RTC 房间的ID，用户ID ----
    room_id = "ChatRoom01"
    user_id = "Huoshan01"


    # ---- 2. 创建 token 构造对象 ----
    token_builder = AccessToken(
        app_id = settings.RTC_APP_ID,
        app_key = settings.RTC_APP_KEY,
        room_id = room_id,
        user_id = user_id
    )


    # ---- 3. 添加接收和发送流的权限 ----
    token_builder.add_privilege(
        PRIVILEGES["PrivSubscribeStream"],0
    )
    token_builder.add_privilege(
        PRIVILEGES["PrivPublishStream"],0
    )


    # ---- 4. 设置有效期，并生成token ----
    token_builder.expire_time(
        int(time.time()) + 3600 * 24
    )

    token = token_builder.serialize()


    # ---- 5. 返回场景信息和 RTC 进房参数
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


# ---- 前端启动和停止火山的 RTC 的 AI 语音对话 ----
"""前端 → /proxy → 火山 RTC 的 StartVoiceChat / StopVoiceChat"""
@app.post("/proxy")
async def proxy(request:Request):
    # 1. 读取 URL 中的操作名称和版本
    action = request.query_params.get("Action")
    version = request.query_params.get("Version","2025-06-01")

    # 2. 读取前端发送的JSON
    incoming_body = await request.json()

    # 3. 构造发送给火山的请求正文
    if action == "StartVoiceChat":
        request_body = {
            "AppId":settings.RTC_APP_ID,
            "RoomId":"ChatRoom01",
            "TaskId":"ChatTask01",

            # AI 在房间中的身份，以及和谁对话
            "AgentConfig": {
                "TargetUserId": [
                    "Huoshan01"
                ],
                "UserId": "AIAGENT",
                "WelcomeMessage": "你好主人，有什么吩咐吗？",
                "Burst": {},
                "VoicePrint": {},
                "EnableConversationStateCallback":True
            },

            # 语音识别 → 大模型 → 语音合成
            "Config":{
                "ASRConfig":{
                    "Provider":"volcano",
                    "ProviderParams":{
                        "Mode":"bigmodel",
                        "Credential":{
                            "AppId":settings.ASR_APP_ID,
                            "AccessToken":settings.ASR_ACCESS_TOKEN,
                            "ApiResourceId":"volc.seedasr.sauc.duration"
                        },
                        "StreamMode":2,
                        "VolcanoASRParameters":"{}"
                    },
                    "VADConfig":{},
                    "InterruptConfig":{}
                },

                "LLMConfig":{
                    "Mode":"CustomLLM",
                    "Url":f"{settings.SERVER_URL}/api/chat_callback",
                },

                "TTSConfig":{
                    "Provider":"volcano_bidirection",
                    "ProviderParams":{
                        "Credential":{
                            "AppId":settings.TTS_APP_ID,
                            "Token":settings.TTS_ACCESS_TOKEN,
                            "ResourceId":"seed-tts-2.0"
                        },
                        "VolcanoTTSParameters": json.dumps({
                            "req_params":{
                                "speaker":"zh_female_vv_uranus_bigtts"
                            }
                        })
                    }
                },
            }
        }
    elif action == "StopVoiceChat":
        request_body = {
            "AppId": settings.RTC_APP_ID,
            "RoomId": "ChatRoom01",
            "TaskId": "ChatTask01",
        }

    else:
        request_body = incoming_body

    # 4. 整理需要签名的请求信息
    host = "rtc.volcengineapi.com"

    request_data = {
        "method":"POST",
        "path":"/",
        "params":{
            "Action":action,
            "Version":version,
        },
        "headers":{
            "Host":host,
            "Content-Type":"application/json",
        },
        "body":request_body
    }

    # 5. 使用AK/SK生成签名
    signer = Signer(request_data,"rtc")
    signer.add_authorization(
        {
            "accessKeyId":settings.VOLC_AK,
            "secretKey":settings.VOLC_SK
        }
    )

    # 6. 携带签名向火山发送请求
    url = f"https://{host}?Action={action}&Version={version}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers = request_data["headers"],
            json = request_body,
            timeout = 30.0

        )

    # 7. 把火山返回的结果交给前端
    return response.json()