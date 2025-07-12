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
llm_base = ChatOpenRouter(
    # model='gpt-4.1',
    model="deepseek-r1",  # 模型名称可以是任意值 deepseek-v3-0324 qwq-32b  qwen2.5-coder-32b-instruct qwen3-32b-mlx deepseek-v3-0324
    base_url="https://yunwu.ai/v1",  # LM Studio 默认端口 http://localhost:1234/v1  https://yunwu.ai/v1
    api_key='sk-MhBwOiyBUVlWbxOqgbUAwwiQG6T3qRP8Kk24BABcGErlyvmK',
    # openai_api_key="lm-studio", # 可以是任意值
    # temperature=0.0,
)

task = 'Find the founders of browser-use'
agent = Agent(task=task, llm=llm_base)


async def main():
    await agent.run()


if __name__ == '__main__':
    asyncio.run(main())
