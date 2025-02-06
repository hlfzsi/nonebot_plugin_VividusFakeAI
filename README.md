<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/A-kirami/nonebot-plugin-VividusFakeAI/blob/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://github.com/A-kirami/nonebot-plugin-VividusFakeAI/blob/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# nonebot-plugin-VividusFakeAI

_✨ 模仿你的群友！ ✨_

<a href="./LICENSE">
    <img src="https://img.shields.io/pypi/l/nonebot-plugin-VividusFakeAI" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-VividusFakeAI">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-VividusFakeAI.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="python">

</details>

## 📖 介绍

`nonebot_plugin_VividusFakeAI`在本质上是一个词库插件。我们尝试过训练AI模型的方案，但无论是何种方案，都无法在低性能机器（双核+2GB）和小规模数据集（单个群聊的聊天数据）表现出一定的效果。受`ChatLearning`项目启发，制作`nonebot_plugin_VividusFakeAI`。

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

nb plugin install nonebot-plugin-VividusFakeAI

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

pip install nonebot-plugin-VividusFakeAI

</details>
<details>
<summary>pdm</summary>

pdm add nonebot-plugin-VividusFakeAI

</details>
<details>
<summary>poetry</summary>

poetry add nonebot-plugin-VividusFakeAI

</details>
<details>
<summary>conda</summary>

conda install nonebot-plugin-VividusFakeAI

</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

plugins = ["nonebot_plugin_VividusFakeAI"]

</details>

## ⚙️ 配置

暂无配置项


| 配置项 | 必填 | 默认值 |   说明   |
| :-----: | :--: | :----: | :------: |
| 配置项1 |  是  |   无   | 配置说明 |
| 配置项2 |  否  |   无   | 配置说明 |

## 🎉 使用

### 指令表

暂无指令


| 指令 | 权限 | 需要@ | 范围 |   说明   |
| :---: | :--: | :---: | :--: | :------: |
| 指令1 | 主人 |  否  | 私聊 | 指令说明 |
| 指令2 | 群员 |  是  | 群聊 | 指令说明 |

### 效果

正常聊天即可。机器人在群内时间越久，发送消息越有意思。支持发送表情。
