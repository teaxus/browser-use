from browser_use import Agent
from dotenv import load_dotenv
import asyncio
import os
import sys

# from browser_use.llm.openai.chat import ChatOpenAI
# from browser_use.llm.openai.chat import ChatOpenRouter
from browser_use.llm import ChatAnthropic, ChatGoogle, ChatGroq, ChatOpenAI, ChatOpenRouter

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


load_dotenv()


# Initialize the model
# llm = ChatOpenAI(
#     model='gpt-4.1-mini',
# )
llm_base = ChatOpenAI(
    # model='gpt-4.1',
    model="qwen-vl-max",  # 模型名称可以是任意值 qwq-plus qwen-max deepseek-v3-0324 qwq-32b  qwen2.5-coder-32b-instruct qwen3-32b-mlx deepseek-v3-0324
    base_url="https://yunwu.zeabur.app/v1",  # LM Studio 默认端口 http://localhost:1234/v1  https://yunwu.ai/v1  https://yunwu.zeabur.app/v1
    api_key='sk-MhBwOiyBUVlWbxOqgbUAwwiQG6T3qRP8Kk24BABcGErlyvmK',
    # openai_api_key="lm-studio", # 可以是任意值
    # temperature=0.0,
)

task = '''
## 发送聊天信息

** 目标：**
打开https://devcloud.kanghehealth.com/#/login，在咨询互动里的主管在管，点击第一条会话，发送“hello world”，等待其他信息，尝试和其他聊天人愉快聊天，直到最后一条信息是exit内容为止（注意要看的是最后一条信息！！！！！！！）
- 聊天页面的聊天框是一个class="editor text-put"的div，请尝试点击后输入内容，或者直接从里面插入要发送的内容
---
* *重要:* *
- 登陆进网页主页后先在筛选输入框输入“咨询互动”，浏览器会在一个新tab交互
- 
---

### 步骤 1: 登陆网页
- 访问 [https://devcloud.kanghehealth.com/#/login](https://devcloud.kanghehealth.com/#/login)，先不要输入帐号密码！，先点击【手机登陆】。

### 步骤 2: 开始登陆
- 点击手机号输入框输入18682025716
- 点击验证码输入框输入250410
- 点击登陆按钮

### 步骤 3: 找到咨询互动，打开一个新的浏览器tab
- 登陆后先在placeholder='请输入内容'筛选输入框输入“咨询互动”内容，然后在菜单栏找到【咨询互动】

### 步骤 4: 选择第一个会话
- 步骤3打开的新页面，找到咨询互动，主管在管里的第一个会话并点击

### 步骤 5: 发送消息
- 点击输入框，输入“hello world”，我建议输入后检查一下输入框内容是否正确，我很担心你识别错误
- 点击发送按钮

### 步骤 6: 等待其他信息
- 等待其他人发送消息(每2分钟浏览一次消息是否更新)，然后尝试和其他聊天人愉快聊天，最后一条信息是exit内容为止（注意要看的是最后一条信息！！！！！！！）
'''
agent = Agent(task=task, llm=llm_base, use_vision=True)


async def main():
    history = await agent.run()
    print("Conversation History:")
    result = history.final_result()
    print(result)


if __name__ == '__main__':
    asyncio.run(main())
