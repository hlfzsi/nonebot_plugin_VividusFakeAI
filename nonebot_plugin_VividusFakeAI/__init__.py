from nonebot import require
require("nonebot_plugin_ACMD")
from nonebot_plugin_ACMD import ACMD_get_driver, CommandFactory  # noqa
from nonebot.plugin import PluginMetadata  # noqa

from .config import Config  # noqa
from .vivFakeAI_handler import VivFakeAI, QA  # noqa


__plugin_meta__ = PluginMetadata(
    name="nonebot-plugin-VividusFakeAI",
    description="模仿你的群友",
    usage="https://github.com/hlfzsi/nonebot_plugin_VividusFakeAI",

    type="application",

    config=Config,

    homepage="https://github.com/hlfzsi/nonebot_plugin_VividusFakeAI",

    supported_adapters={"~onebot.v11"},
)


driver = ACMD_get_driver()


@driver.on_startup
async def hello():
    await QA.initialize()


CommandFactory.create_command(commands=None, handler_list=VivFakeAI())


@driver.on_shutdown
async def jj():
    await QA.db.pool.close()
