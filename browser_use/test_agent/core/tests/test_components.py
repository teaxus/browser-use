"""
测试脚本 - 验证重构后的测试执行器是否正常工作
"""

import asyncio
import logging
import sys
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 尝试导入重构后的组件
try:
    from browser_use.test_agent.core import (
        TestExecutor,
        BrowserManager,
        TestContextBuilder,
        TestLogger,
        EnhancedInterventionHandler
    )
    from browser_use.test_agent.parser import TestCaseParser
    from browser_use.test_agent.intervention import HumanInterventionHandler
    from browser_use.llm import create_llm
except ImportError as e:
    logger.error(f"导入失败: {e}")
    sys.exit(1)


async def run_test():
    """运行测试用例"""
    logger.info("开始测试重构后的测试执行器")

    try:
        # 创建LLM
        logger.info("创建LLM...")
        llm = create_llm("anthropic")

        # 创建干预处理器
        logger.info("创建干预处理器...")
        intervention_handler = HumanInterventionHandler()

        # 创建测试执行器
        logger.info("创建测试执行器...")
        executor = TestExecutor(
            llm=llm,
            intervention_handler=intervention_handler,
            max_retries=3,
            step_timeout=60000,  # 60秒
            use_vision=True,
            headless=False,
            screenshots_dir=Path("./test_screenshots")
        )

        # 确认组件创建正常
        logger.info("验证组件:")
        logger.info(f"- BrowserManager: {executor.browser_manager.__class__.__name__}")
        logger.info(f"- TestLogger: {executor.logger_manager.__class__.__name__}")
        logger.info(f"- TestContextBuilder: {executor.context_builder.__class__.__name__}")
        logger.info(f"- EnhancedInterventionHandler: {executor.enhanced_intervention_handler.__class__.__name__}")

        # 测试组件方法
        logger.info("测试浏览器管理器...")
        browser_session = await executor.browser_manager.create_and_start_session()
        logger.info(f"浏览器会话创建成功: {browser_session is not None}")

        logger.info("测试日志管理器...")
        executor.logger_manager.setup_file_logger("test_validation.md")

        logger.info("测试结束，关闭浏览器...")
        await executor.browser_manager.close_session()

        logger.info("✅ 所有组件验证通过")
        return True

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(run_test())
    sys.exit(0 if success else 1)
