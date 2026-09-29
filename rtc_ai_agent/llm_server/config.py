import os

from dotenv import load_dotenv


load_dotenv()

class Config:
    ARK_API_KEY = os.getenv("ARK_API_KEY")
    ARK_ENDPOINT_ID = os.getenv("ARK_ENDPOINT_ID")
    BASE_URL = os.getenv("BASE_URL","https://ark.cn-beijing.volces.com/api/v3")

    # RTC
    RTC_APP_ID = os.getenv("RTC_APP_ID")
    RTC_APP_KEY = os.getenv("RTC_APP_KEY")

settings = Config()
