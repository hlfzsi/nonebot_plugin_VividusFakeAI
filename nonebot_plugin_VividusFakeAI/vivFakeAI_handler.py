import os
from datetime import datetime
from typing import Final

from nonebot import logger, require
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, MessageSegment
from nonebot_plugin_ACMD import BasicHandler
from nonebot_plugin_ACMD.Atypes import UserInput, GroupID, ImageInput, PIN
from nonebot_plugin_VividusCore.perm import VivPermission

from .learn import QAManager

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_data_dir  # noqa

QA: Final[QAManager] = QAManager(
    db_path=os.path.join(str(get_data_dir("nonebot_plugin_VividusFakeAI")), "QA.db3"))
IMAGEDIR: Final[str] = os.path.join(
    str(get_data_dir("nonebot_plugin_VividusFakeAI")), 'Image')
os.makedirs(IMAGEDIR, exist_ok=True)


class VivFakeAI(BasicHandler):
    __slots__ = [slot for slot in BasicHandler.__slots__ if slot !=
                 '__weakref__']+['question']

    def __init__(self, block=True, unique=None, **kwargs):
        super().__init__(block, unique, **kwargs)
        self.question = {}

    async def should_handle(self, msg: UserInput, permission: VivPermission):
        return permission.has_permission(None) and not msg.full.startswith(('/', '-', '*')) and not msg.cmd

    async def handle(self, bot: Bot, event: MessageEvent, msg: UserInput, groupid: GroupID, image: ImageInput, PIN: PIN):
        result = await QA.search(msg.full, groupid.str)

        if result:
            msg_to_send = Message()
            msg_to_send += MessageSegment.text(result[2])
            paths = self.get_image_paths(result[3])
            for path in paths:
                msg_to_send += MessageSegment.image(f"file:///{path}")
            await bot.send(event, msg_to_send)

        target_folder = None
        if image.image_list:
            target_folder = os.path.join(
                IMAGEDIR, f'{int(datetime.now().timestamp()*(10**6))}_{groupid.str}_{PIN.user}')
            await image.download(target_folder=target_folder)

        if not self.question.get(groupid.str,None):
            self.question[groupid.str] = msg.full
            logger.info(f'已记录问题 {msg.full}')
            return

        await QA.db.add_group(groupid.str)

        await QA.add_qa(self.question[groupid.str], msg.full, groupid.str, target_folder)

        self.question[groupid.str] = msg.full

        logger.info(f'已记录在 {groupid.str} 的问答对 {self.question[groupid.str]} -> {msg.full}')

    @staticmethod
    def get_image_paths(directory):
        """
        获取指定目录下的所有文件路径

        :param directory: 要遍历的目录路径
        :return: 包含所有文件路径的列表
        """
        image_paths = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                # 直接添加文件路径，不进行后缀检查
                image_paths.append(os.path.join(root, file))

        return image_paths
