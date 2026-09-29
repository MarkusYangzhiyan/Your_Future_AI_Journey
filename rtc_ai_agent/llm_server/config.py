import os

from dotenv import load_dotenv

_ = load_dotenv()

class Config:
    # 火山引擎
    VOLC_AK = os.getenv("VOLC_ACCESS_KEY")
    VOLC_SK = os.getenv("VOLC_SECRET_ACCESS_KEY")

    # 方舟推理
    ARK_API_KEY = os.getenv("ARK_API_KEY")
    ARK_ENDPOINT_ID = os.getenv("ARK_ENDPOINT_ID")
    BASE_URL = os.getenv("BASE_URL","https://ark.cn-beijing.volces.com/api/v3")

    # RTC 配置
    RTC_APP_ID = os.getenv("RTC_APP_ID")
    RTC_APP_KEY = os.getenv("RTC_APP_KEY")

    # ngrok 
    SERVER_URL = os.getenv("SERVER_URL")

    # ASR TTS
    ASR_APP_ID = os.getenv("ASR_APP_ID")
    ASR_ACCESS_TOKEN = os.getenv("ASR_ACCESS_TOKEN")
    TTS_APP_ID = os.getenv("TTS_APP_ID")
    TTS_ACCESS_TOKEN = os.getenv("TTS_ACCESS_TOKEN")


settings = Config()