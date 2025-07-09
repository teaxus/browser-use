import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('/Users/teaxus/AILearning/AIAgent')

import asyncio

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from browser_use import Agent, Browser, BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig
import browser_use
from browser_use.agent.views import ActionResult

import time
from pynput.keyboard import Key, Controller
import json
import browser_use

from llm.LLMBuilder import build_api_handler
from roles.BasicRole import BasicRole, RoleConfig
import threading
import subprocess


load_dotenv()

all_data = []  # 用于存储所有收集的数据
controller = browser_use.Controller()
llm = ChatOpenAI(
    model="deepseek-v3-0324", # 模型名称可以是任意值 deepseek-v3-0324 qwq-32b  qwen2.5-coder-32b-instruct qwen3-32b-mlx deepseek-v3-0324
    base_url="https://yunwu.ai/v1", # LM Studio 默认端口 http://localhost:1234/v1  https://yunwu.ai/v1
    # openai_api_key="lm-studio", # 可以是任意值
    temperature=0.0,
)

# Extract the data from the current page of the product list
@controller.registry.action('run javascript to Extract the data')  
async def get_page_info():
    data_collection_py = await context.execute_javascript('''
    (function() {
        function getTableData() {
            const table_data = [];
            var data_collection = document.querySelector("#container > section > section > main > section.micro-apps-content.micro-SBN.micro-base__micro--TejQSwFI > section > div > div > div > div > div > div > div.so-tabs-panel.so-tabs-show > div > main > div > div > div.so-tabs-panel.so-tabs-show > div > div.so-tabs.so-tabs-line.list-box > div.so-tabs-panel.so-tabs-show > div > div > div.so-table.so-table-default.so-table-hover.so-table-bordered.so-table-fixed.so-table-vertical-middle.so-table-sticky > div.so-scroll.so-scroll-show-x.so-table-body.so-table-float-right > div.so-scroll-inner > div > table > tbody").children;
            data_collection = Array.from(data_collection);
            data_collection.forEach((element) => {
                table_data.push({
                    "url": element.children[0].querySelector('img').src,
                    "商品名称": element.children[0].querySelector("div > div > div:nth-child(1)").innerText,
                    "skc": element.children[0].querySelector("div > div > div:nth-child(2) > span").innerText.replace('SKC:',''),
                    "供方货号": element.children[0].querySelector("div > div > div:nth-child(3) > span").innerText.replace('供方货号:',''),
                    "日均销量": element.children[2].innerText,
                    "日均订单数": element.children[3].innerText,
                    "日均访客": element.children[4].innerText,
                    "日均加车访客": element.children[5].innerText
                });
            });
            return JSON.stringify(table_data);
        }
        return getTableData();
    })();
    ''')
    print("data_collection_py:", data_collection_py)
    try:
        all_data.extend(json.loads(data_collection_py))
    finally:
    	return ActionResult(extracted_content=f"run javascript to Extract the data OK", data=data_collection_py, include_in_memory=True)

# task = '''
# ### 网页信息收集

# ** 目标：**
# 打开连接https://sellerhub.shein.com/#/sbn/marketing/activities。 使用javascript收集3页数据

# ---
# * *重要:* *
# - 不要点击！！！[查看趋势]和如何商品图片！！！
# - 严格遵守以下步骤进行操作
# - 必须通过run javascript to Extract the data，来收集数据，不要用其他方法！
# ---

# ### 步骤 1: 打开网站连接
# - 网站连接如下: https://sellerhub.shein.com/#/sbn/marketing/activities
# - 等待3-10秒，确保页面加载完成

# ### 步骤 2: 选择需要收集的列表
# - 直接点击: 商品列表
# - 切换站点，假如原来是shein-all需要切换成shein-mx

# ### 步骤 3: 开始收集数据
# - run javascript to Extract the data（执行失败检查[步骤 2]是否点击"商品列表"）

# ### 步骤 4: 翻页，重复[步骤 3]操作
# - 下拉到最底部
# - 点击下一页(下一页的按钮的XPATH:/html/body/div[1]/section/section/main/section[45]/section/div/div/div/div/div/div/div[2]/div/main/div/div/div[2]/div/div[2]/div[3]/div/div/div[2]/div[2]/div[1]/a[11])
# - 收集超过目标页数后完成任务
# '''

task = '''
### 网页信息收集
Open the connection at https://sellerhub.shein.com/#/sbn/marketing/activities. Collect 3 pages of data using javascript

---
* * Important :* *
Don't click!! [查看趋势] and how to get product pictures!!
Operate strictly in accordance with the following steps
data must be collected by running javascript to Extract the data. Do not use any other methods!
---

Step 1: Open the website link
- the website is as follows: https://sellerhub.shein.com/#/sbn/marketing/activities
- Wait for 3 to 10 seconds to ensure the page loads completely

Step 2: Select the list that needs to be collected
- Click directly: 商品列表
- Switch the 站点. If it was originally shein-all, it needs to be switched to shein-mx

Step 3: Start collecting data
- Wait for 10 to 15 seconds to ensure the page loads completely
- run javascript to Extract the data (Execution failure check [Step 2] whether to click "商品列表")

Step 4: Turn the page and repeat the operation in Step 3
- Pull down to the very bottom
-  Click on the next page (the button on the next page XPATH: / HTML/body/div [1] / section/section/main/section [45] / section/div/div/div/div/div/div/div [2] / div/main/di v/div/div[2]/div/div[2]/div[3]/div/div/div[2]/div[2]/div[1]/a[11])
- Complete the task after collecting more than the target number of pages
'''

# 配置本地 Chrome 浏览器
browser = Browser(
	config=BrowserConfig(
		use_vision=False,
		cdp_url='http://localhost:9222'
		# browser_binary_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
	)
)

context = BrowserContext(browser=browser)


async def main():
	agent = Agent(task=task, llm=llm, 
				controller=controller,
			browser_context=context, use_vision=False)
	history = await agent.run(max_steps=500)
	# history.save_to_file('./tmp/history_simple.json')
	# await context.close()  # Close the browser when done
	await agent.close() 

	# print("JSON格式:------------------------- Begin")
	print("JSON:")
	print(all_data)
	# print("JSON格式:------------------------- End")
	print("\n\n\n\n\nMarkdown Table:\n\n")
	markdown = "| 商品图片 | 商品名称 | SKC | 供方货号 | 日均销量 | 日均订单数 | 日均访客 | 日均加车访客 |\n"
	markdown += "|---------|---------|-----|---------|---------|----------|---------|------------|\n"
    
	for item in all_data:
		image_cell = f"![商品图片]({item['url']})"
		markdown += f"| {image_cell} | {item['商品名称']} | {item['skc']} | {item['供方货号']} | {item['日均销量']} | {item['日均订单数']} | {item['日均访客']} | {item['日均加车访客']} |\n"
	print(markdown)
	return markdown

	# print("原始结果:")
	# # # history.action_results()[-2].extracted_content
	# result = history.final_result()
	# print(result)
	# # print("JSON格式:------------------------- Begin")
	# parsed_data = json.loads(result)
	# print(parsed_data)
	# # print("JSON格式:------------------------- End")


class BSAgent(BasicRole):
    async def rxMsgCallback(self, msg):
        if msg.receiver_id == self.im_client.user_id:
            self.im_client.start_typing()  # 开始输入状态，上锁，防止切他用户发送消息
            rsp = await main()
            self.im_client.send_message(self.config.receiver_id, rsp)


if __name__ == '__main__':
	# asyncio.run(main())
	# Import subprocess for launching Chrome

	session_id = "1"
	op_openAI = {
        "provider": "openai",
        "openaiBaseUrl": "https://yunwu.ai/v1",  # 替换为你的API地址
        "openaiApiKey": "sk-XtFlyYNjSI3kB8yd1OFiUrr16vmV2I1ZgGBkmbd3FfvOEI2S",  # 替换为你的API密钥
        "openaiModelId": "deepseek-v3-0324",  # 替换为你要使用的模型ID
        "openaiModelInfo": {
            "context_length": 131072,
            "pricing": {"prompt": 0.002, "completion": 0.002},
            "temperature": 0.7
        }
    }
	role_config = RoleConfig(
        system_prompt="你是负责使用浏览器收集数据的助手，负责打开网页和收集数据，sam会给你发送指令，你会根据指令打开网页和收集数据",
        sender_id="bsagent",
        session_id=session_id,
        llm_options=op_openAI
    )
	role = BSAgent(role_config)

	thread1 = threading.Thread(target=role.run)
	thread1.start()
	thread1.join()



# 启动这个记得现在终端执行命令：
#  /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome  --remote-debugging-port=9222 --remote-allow-hosts=0.0.0.0
