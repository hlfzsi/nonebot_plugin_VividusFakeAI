from nonebot_plugin_ACMD import ACMD_get_driver,CommandFactory

from .vivFakeAI_handler import VivFakeAI, QA

driver = ACMD_get_driver()


@driver.on_startup
async def hello():
    await QA.initialize()
    
    
CommandFactory.create_command(commands=None,handler_list=VivFakeAI())


@driver.on_shutdown
async def jj():
    await QA.db.pool.close()