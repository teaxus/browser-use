"""
干预处理器模块 - 处理测试过程中的人工干预，提供与人类操作者的交互接口
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

# 导入测试相关类型
from browser_use.test_agent.parser.types import TestCase, TestStep
from browser_use.test_agent.core.types import StepResult, InterventionType, InterventionResponse, InterventionContext
from browser_use.test_agent.core.browser_manager import BrowserManager


class EnhancedInterventionHandler:
    """增强的人工干预处理器，处理测试执行过程中的干预请求"""

    def __init__(self, base_handler=None):
        """
        初始化干预处理器

        Args:
            base_handler: 基础干预处理器，用于实际的交互
        """
        self.logger = logging.getLogger(__name__)
        self._is_intervention_in_progress = False
        self.base_handler = base_handler  # 基础干预处理器

    def set_base_handler(self, handler):
        """
        设置基础干预处理器

        Args:
            handler: 处理干预请求的基础处理器
        """
        self.base_handler = handler
        self.logger.debug("已设置基础干预处理器")

    async def handle_step_failure(
        self,
        step: TestStep,
        step_result: StepResult,
        test_case: TestCase,
        browser_manager: BrowserManager,
        max_retries: int
    ) -> str:
        """
        处理步骤失败，决定后续操作

        Args:
            step: 失败的步骤
            step_result: 步骤执行结果
            test_case: 测试用例
            browser_manager: 浏览器管理器
            max_retries: 最大重试次数

        Returns:
            决策动作: retry, skip, continue, goto:X
        """
        # 检查是否已达到最大重试次数
        retry_count = getattr(step, '_retry_count', 0)

        if retry_count < max_retries:
            # 尝试重试
            step._retry_count = retry_count + 1  # type: ignore
            self.logger.info(f"🔄 步骤 {step.step_number} 重试第 {retry_count + 1}/{max_retries} 次")
            self.logger.info(f"   ❌ 失败原因: {step_result.error_message}")
            return "retry"

        # 达到最大重试次数，请求人工干预
        current_url = await browser_manager.get_current_url()

        context = await self.prepare_intervention_context(
            step=step,
            error_message=step_result.error_message or "未知错误",
            screenshot_path=step_result.screenshot_path,
            browser_manager=browser_manager,
            retry_count=retry_count
        )

        # 标记人工干预开始，通知浏览器管理器启用保护
        self._is_intervention_in_progress = True
        browser_manager.set_protection(True)
        self.logger.info("⚠️ === 人工干预开始，浏览器保护模式启动 ===")
        self.logger.info(f"📋 步骤 {step.step_number}: {step.title}")
        self.logger.info(f"🌐 当前URL: {current_url}")
        self.logger.info(f"❌ 错误信息: {step_result.error_message}")
        self.logger.info(f"🔢 重试次数: {retry_count}/{max_retries}")

        try:
            # 请求人工干预
            if self.base_handler:
                response = await self.base_handler.request_intervention(
                    context,
                    InterventionType.ERROR_RETRY
                )
            else:
                # 如果没有基础处理器，创建默认响应
                self.logger.warning("未设置基础干预处理器，使用默认响应")
                response = InterventionResponse(
                    action="retry",
                    message="默认响应: 重试",
                    additional_instructions="系统自动决定重试"
                )
        finally:
            # 标记人工干预结束，关闭浏览器保护
            self.logger.info("✅ === 人工干预结束，浏览器保护模式关闭 ===")
            self._is_intervention_in_progress = False
            browser_manager.set_protection(False)

        # 记录干预信息
        step_result.intervention_used = True
        step_result.intervention_details = {
            "action": response.action,
            "message": response.message,
            "additional_instructions": response.additional_instructions
        }

        self.logger.info(f"👤 干预结果: {response.action}")
        if response.message:
            self.logger.info(f"📝 干预消息: {response.message}")
        if response.additional_instructions:
            self.logger.info(f"📋 额外指示: {response.additional_instructions}")

        # 人工干预后验证浏览器状态
        try:
            page_ok, page_status = await browser_manager.verify_page_state()
            self.logger.info(f"人工干预后页面状态: {page_status}")
        except Exception as e:
            self.logger.warning(f"人工干预后页面状态检查失败: {e}")

        # 根据响应决定下一步动作
        return self.process_intervention_response(response, step, step_result)

    async def prepare_intervention_context(
        self,
        step: TestStep,
        error_message: str,
        screenshot_path: Optional[str],
        browser_manager: BrowserManager,
        retry_count: int
    ) -> InterventionContext:
        """
        准备干预上下文信息

        Args:
            step: 当前步骤
            error_message: 错误信息
            screenshot_path: 截图路径
            browser_manager: 浏览器管理器
            retry_count: 重试次数

        Returns:
            干预上下文
        """
        # 获取当前页面URL
        current_url = await browser_manager.get_current_url()

        # 构建干预上下文
        context = InterventionContext(
            step_number=step.step_number,
            step_title=step.title,
            error_message=error_message,
            screenshot_path=screenshot_path,
            page_url=current_url,
            retry_count=retry_count
        )

        return context

    def process_intervention_response(
        self,
        response: InterventionResponse,
        step: TestStep,
        step_result: StepResult
    ) -> str:
        """
        处理干预响应，返回后续动作

        Args:
            response: 干预响应
            step: 当前步骤
            step_result: 步骤结果

        Returns:
            决策动作: retry, skip, continue, goto:X
        """
        if response.action == "continue":
            if response.additional_instructions:
                # 更新步骤说明
                step.description += f"\n\n### 人工指导:\n{response.additional_instructions}"
                self.logger.info(f"已添加人工指导: {response.additional_instructions}")
            return "retry"

        elif response.action == "skip":
            self.logger.info("用户选择跳过当前步骤")
            return "skip"

        elif response.action == "modify":
            if response.message:
                # 修改步骤操作
                old_actions = step.actions.copy()
                step.actions = [response.message]
                self.logger.info(f"步骤操作已修改: {old_actions} -> {step.actions}")
            return "retry"

        elif response.action == "goto" and response.skip_to_step:
            return f"goto:{response.skip_to_step}"

        else:
            return "continue"

    def is_intervention_in_progress(self) -> bool:
        """
        检查人工干预是否进行中

        Returns:
            是否进行中
        """
        return self._is_intervention_in_progress
