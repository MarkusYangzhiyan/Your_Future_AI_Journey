import time
import struct
import hmac
import hashlib
import base64
import random
from io import BytesIO

VERSION = "001"

PRIVILEGES = {
    "PrivPublishStream": 0,                 # 发布流的总入口
    "privPublishAudioStream": 1,            # 发送音频
    "privPublishVideoStream": 2,            # 发送视频
    "privPublishDataStream": 3,             # 发送数据流
    "PrivSubscribeStream": 4,               # 接收其他参与者的流
}

class ByteBuf:
    # 创建一个存放字节的内存容器；传入 data 时，用这些字节初始化容器
    def __init__(self, data=None):
        self.buffer = BytesIO(data) if data else BytesIO()

    # 取出容器里的全部字节
    def pack(self):
        return self.buffer.getvalue()

    # 把数字转换成无符号16位整数，写入2字节
    def put_uint16(self, v):
        self.buffer.write(struct.pack("<H", v))
        return self

    # 把数字转换成无符号32位整数，写入4字节
    def put_uint32(self, v):
        self.buffer.write(struct.pack("<I", v))
        return self

    # 先写入长度，再写入字节内容
    def put_bytes(self, b):
        self.put_uint16(len(b))
        self.buffer.write(b)
        return self

    # 把字符串转成 UTF-8 字节，然后调用 put_bytes()，先写入长度，再写入字节内容
    def put_string(self, s):
        return self.put_bytes(s.encode("utf-8"))

    # 写入字典条目数量，然后依次写入每个键和值
    def put_tree_map_uint32(self, m):
        if not m:
            self.put_uint16(0)
            return self

        self.put_uint16(len(m))

        for k, v in m.items():
            self.put_uint16(int(k))
            self.put_uint32(int(v))

        return self


class AccessToken:
    def __init__(self, app_id, app_key, room_id, user_id):
        self.app_id = app_id
        self.app_key = app_key
        self.room_id = room_id
        self.user_id = user_id
        self.issued_at = int(time.time())               # 创建时间
        self.nonce = random.randint(0, 0xFFFFFFFF)      # 随机数，让多次生成的凭证可以不同
        self.expire_at = 0                              # 权限到期时间  
        self.privileges = {}                            # 权限

    # 添加权限
    def add_privilege(self, privilege, expire_timestamp):
        self.privileges[privilege] = expire_timestamp
        if privilege == PRIVILEGES["PrivPublishStream"]:
            self.privileges[PRIVILEGES["privPublishVideoStream"]] = expire_timestamp
            self.privileges[PRIVILEGES["privPublishAudioStream"]] = expire_timestamp
            self.privileges[PRIVILEGES["privPublishDataStream"]] = expire_timestamp

    # 设置整个 Token 的到期时间
    def expire_time(self, expire_timestamp):
        self.expire_at = expire_timestamp

    # 把凭证信息按顺序打包
    # 初始化创建存放字节的容器，依次写入：随机数、创建时间、到期时间、房间ID、用户ID、权限表
    def pack_msg(self):
        buf = ByteBuf()
        buf.put_uint32(self.nonce); buf.put_uint32(self.issued_at); buf.put_uint32(self.expire_at)
        buf.put_string(self.room_id); buf.put_string(self.user_id); buf.put_tree_map_uint32(self.privileges)
        return buf.pack()

    # 生成最终凭证
    def serialize(self):
        msg = self.pack_msg()
        signature = hmac.new(self.app_key.encode('utf-8'), msg, hashlib.sha256).digest()
        content = ByteBuf().put_bytes(msg).put_bytes(signature).pack()
        return VERSION + self.app_id + base64.b64encode(content).decode('utf-8')