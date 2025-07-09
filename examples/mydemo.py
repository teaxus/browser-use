from pynput.keyboard import Key, Controller
import time
from browser_use.agent.views import ActionResult
import browser_use
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use import Agent, Browser, BrowserConfig
from browser_use.llm import ChatOpenAI
from dotenv import load_dotenv
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


load_dotenv()

# Initialize the model
# llm = ChatOpenAI(
# 	model='gpt-4o',
# 	temperature=0.0,
# )
controller = browser_use.Controller()
keyboard = Controller()
llm_my = ChatOpenAI(
    model="deepseek-v3-0324",  # 模型名称可以是任意值 deepseek-v3-0324 qwq-32b  qwen2.5-coder-32b-instruct qwen3-32b-mlx deepseek-v3-0324
    base_url="https://yunwu.ai/v1",  # LM Studio 默认端口 http://localhost:1234/v1  https://yunwu.ai/v1
    # openai_api_key="lm-studio", # 可以是任意值
    temperature=0.0,
)


# @controller.registry.action('input_text')
# def input_text(text: str):
# 	keyboard.type(text)
# 	keyboard.press(Key.enter)
# 	keyboard.release(Key.enter)
# 	return ActionResult(extracted_content="input is ok")


# @controller.registry.action('run_javascript')
# async def run_javascript(text: str):
# 	await context.execute_javascript(text)
# 	return ActionResult(extracted_content="run javascipt script ok")


# llm=ChatOllama(
# 			model='qwen2.5-coder:32b',
# 			num_ctx=32000,
# 		)

# task = 'Go to kayak.com and find the cheapest flight from Zurich to San Francisco on 2025-05-01'
# task = '请打开https:/bilibili.com 搜索博主"程序员哈利"，来到程序员哈利的主页，并且打开第一个视频进行播放'


task = '''
## 网页信息收集

** 目标：**
打开https://devcloud.kanghehealth.com/#/login，收集【自定义模版】列表所有信息

---
* *重要:* *
- 登陆进网页主页后先在筛选输入框输入“短信”内容，然后在菜单栏找到模版管理打开找到短信模版后，先不要收集信息，记得点击【自定义模版】的Tab
- 收集完毕后，务必以JSON格式输出（!!!除了JSON不能包含其他字符!!!），包含序号、业务场景名称、服务商、模版名称、模版内容
---

### 步骤 1: 登陆网页
- 访问 [https://devcloud.kanghehealth.com/#/login](https://devcloud.kanghehealth.com/#/login)，先不要输入帐号密码！，先点击右上角的【管理员登陆】。

### 步骤 3: 开始登陆
- 点击手机号输入框输入18927582828
- 点击密码输入框输入Kh123456
- 点击验证码输入框输入250410
- 点击登陆按钮

### 步骤 2: 找到短信模版菜单
- 登陆进网页主页后先在筛选输入框输入“短信”内容，然后在菜单栏找到【短信模版】，然后点击（如果找不到短信模版重复一次搜索）

### 步骤 3: 点击【自定义模版】
- 在短信模版页面，点击【自定义模版】的Tab

### 步骤 4: 开始收集数据
- 在列表收集数据，内容包含序号、业务场景名称、服务商、模版名称

### 步骤 5: 翻页
- 将列表拉到最底有个分页器，1/2/3/4...后面有个【下一页】按钮，可以点击到下一页
- 有数据继续收集，将收集的数据拼接在同一个JSON，直到页面无法再下滑和最后一页为止

'''


# 启动这个记得现在终端执行命令：
#  /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome  --remote-debugging-port=9222 --remote-allow-hosts=0.0.0.0


# 配置本地 Chrome 浏览器
# browser = Browser(
#     config=BrowserConfig(
#         # NOTE: you need to close your chrome browser - so that this can open your browser in debug mode
#         cdp_url='http://192.168.0.115:9222'
#         # cdp_url='http://localhost:9222'
#         # browser_binary_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
#     )
# )
# context = BrowserContext(browser=browser)


agent = Agent(task=task,
              llm=llm_my,
              #   browser_context=context,
              controller=controller, use_vision=False)


async def main():
    history = await agent.run(max_steps=500)
    # history.save_to_file('./tmp/history_simple.json')
    # await browser.close()  # Close the browser when done

    print("原始结果:")
    # # history.action_results()[-2].extracted_content
    result = history.final_result()
    print(result)
    # import json
    # # print("JSON格式:------------------------- Begin")
    # parsed_data = json.loads(result)
    # print(parsed_data)
    # # print("JSON格式:------------------------- End")


if __name__ == '__main__':
    asyncio.run(main())
