from nonebot import get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    checking_rate: float = 0.70    # 相似度高于此阈值才会被发送
    sending_rate: float = 0.30   # 尝试获取回复的可能性


config_ = get_plugin_config(Config)