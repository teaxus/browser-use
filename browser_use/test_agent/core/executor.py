"""
测试执行器
"""
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from browser_use import Agent
from browser_use.llm.base import BaseChatModel
from browser_use.browser import BrowserSession

from .parser import TestCase, TestStep
from .intervention import HumanInterventionHandler, InterventionContext, InterventionType, InterventionResponse


@dataclass
class StepResult:
    """步骤执行结果"""
    step_number: int
    success: bool
    execution_time: float
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    intervention_used: bool = False
    intervention_details: Optional[Dict[str, Any]] = None
    agent_output: Optional[str] = None


@dataclass
class TestExecutionResult:
    """测试执行结果"""
    test_name: str
    success: bool
    total_time: float
    step_results: List[StepResult]
    final_message: str
    screenshots_dir: Optional[Path] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None


class TestExecutor:
    """测试执行器"""

    def __init__(
        self,
        llm: BaseChatModel,
        intervention_handler: HumanInterventionHandler,
        max_retries: int = 3,
        step_timeout: int = 30,
        use_vision: bool = True,
        headless: bool = False,
        screenshots_dir: Optional[Path] = None
    ):
        self.llm = llm
        self.intervention_handler = intervention_handler
        self.max_retries = max_retries
        self.step_timeout = step_timeout
        self.use_vision = use_vision
        self.headless = headless
        self.screenshots_dir = screenshots_dir or Path("./test_screenshots")

        self.logger = logging.getLogger(__name__)
        self.browser_session: Optional[BrowserSession] = None
        self.current_agent: Optional[Agent] = None

        # 确保截图目录存在
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    async def execute_test_case(self, test_case: TestCase) -> TestExecutionResult:
        """执行完整的测试用例"""
        start_time = time.time()
        step_results: List[StepResult] = []

        self.logger.info(f"开始执行测试用例: {test_case.metadata.test_name}")

        try:
            # 初始化浏览器会话
            self.browser_session = BrowserSession()

            # 执行所有步骤
            current_step = 0
            while current_step < len(test_case.steps):
                step = test_case.steps[current_step]

                step_result = await self._execute_step(step, test_case)
                step_results.append(step_result)

                if step_result.success:
                    current_step += 1
                else:
                    # 步骤失败，需要决定如何处理
                    action = await self._handle_step_failure(step, step_result, test_case)

                    if action == "continue":
                        current_step += 1
                    elif action == "retry":
                        # 重试当前步骤，不增加step_number
                        continue
                    elif action == "skip":
                        current_step += 1
                    elif action.startswith("goto:"):
                        target_step = int(action.split(":")[1])
                        current_step = target_step - 1  # -1 因为下次循环会+1
                    else:
                        # 终止测试
                        break

            # 计算总体结果
            total_time = time.time() - start_time
            success = all(result.success for result in step_results)

            # 获取对话历史
            conversation_history = None
            if self.current_agent:
                try:
                    # Agent.run() 返回 AgentHistoryList
                    agent_history = self.current_agent.state.history
                    # 转换为简单的字典列表格式
                    conversation_history = []
                    if hasattr(agent_history, 'history'):
                        for item in agent_history.history:
                            conversation_history.append({
                                'timestamp': getattr(item, 'timestamp', None),
                                'action_result': str(getattr(item, 'action_result', '')),
                                'model_output': str(getattr(item, 'model_output', ''))
                            })
                except Exception as e:
                    self.logger.warning(f"获取对话历史失败: {e}")

            return TestExecutionResult(
                test_name=test_case.metadata.test_name,
                success=success,
                total_time=total_time,
                step_results=step_results,
                final_message="测试执行完成" if success else "测试执行失败",
                screenshots_dir=self.screenshots_dir,
                conversation_history=conversation_history
            )

        except Exception as e:
            self.logger.error(f"测试执行过程中发生异常: {e}")
            total_time = time.time() - start_time

            return TestExecutionResult(
                test_name=test_case.metadata.test_name,
                success=False,
                total_time=total_time,
                step_results=step_results,
                final_message=f"测试执行异常: {str(e)}",
                screenshots_dir=self.screenshots_dir
            )

        finally:
            # 清理资源
            if self.browser_session:
                try:
                    await self.browser_session.close()
                except Exception as e:
                    self.logger.warning(f"关闭浏览器会话失败: {e}")

    async def _execute_step(self, step: TestStep, test_case: TestCase) -> StepResult:
        """执行单个步骤"""
        start_time = time.time()
        screenshot_path = None
        intervention_used = False
        intervention_details = None

        self.logger.info(f"执行步骤 {step.step_number}: {step.title}")

        try:
            # 构建步骤任务描述
            step_task = self._build_step_task(step, test_case)

            # 创建或更新Agent
            if not self.current_agent:
                self.current_agent = Agent(
                    task=step_task,
                    llm=self.llm,
                    browser_session=self.browser_session,
                    use_vision=self.use_vision
                )
            else:
                # 更新任务
                self.current_agent.task = step_task

            # 执行步骤
            result = await asyncio.wait_for(
                self.current_agent.run(),
                timeout=self.step_timeout
            )

            # 保存截图
            screenshot_path = await self._take_screenshot(step.step_number)

            execution_time = time.time() - start_time

            return StepResult(
                step_number=step.step_number,
                success=True,
                execution_time=execution_time,
                screenshot_path=str(screenshot_path) if screenshot_path else None,
                intervention_used=intervention_used,
                intervention_details=intervention_details,
                agent_output=str(result) if result else None
            )

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            error_msg = f"步骤 {step.step_number} 执行超时 ({self.step_timeout}秒)"

            screenshot_path = await self._take_screenshot(step.step_number, "timeout")

            return StepResult(
                step_number=step.step_number,
                success=False,
                execution_time=execution_time,
                error_message=error_msg,
                screenshot_path=str(screenshot_path) if screenshot_path else None,
                intervention_used=intervention_used
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"步骤 {step.step_number} 执行失败: {str(e)}"

            screenshot_path = await self._take_screenshot(step.step_number, "error")

            return StepResult(
                step_number=step.step_number,
                success=False,
                execution_time=execution_time,
                error_message=error_msg,
                screenshot_path=str(screenshot_path) if screenshot_path else None,
                intervention_used=intervention_used
            )

    def _build_step_task(self, step: TestStep, test_case: TestCase) -> str:
        """构建步骤任务描述"""
        task_parts = [
            f"## 步骤 {step.step_number}: {step.title}",
            "",
            "### 任务目标:",
            test_case.objective,
            "",
            "### 当前步骤要求:",
        ]

        for action in step.actions:
            task_parts.append(f"- {action}")

        if step.expected_result:
            task_parts.extend([
                "",
                "### 期望结果:",
                step.expected_result
            ])

        # 添加特殊提醒
        task_parts.extend([
            "",
            "### 重要提醒:",
            "- 仔细查看页面内容，确保正确识别元素",
            "- 如果遇到加载等待，请耐心等待页面完全加载",
            "- 如果某个操作失败，请尝试不同的方法",
            "- 对于聊天功能，请保持自然的对话风格"
        ])

        return "\n".join(task_parts)

    async def _handle_step_failure(
        self,
        step: TestStep,
        step_result: StepResult,
        test_case: TestCase
    ) -> str:
        """处理步骤失败"""

        # 检查是否已达到最大重试次数
        retry_count = getattr(step, '_retry_count', 0)

        if retry_count < self.max_retries:
            # 尝试重试
            step._retry_count = retry_count + 1  # type: ignore
            self.logger.info(f"步骤 {step.step_number} 重试第 {retry_count + 1} 次")
            return "retry"

        # 达到最大重试次数，请求人工干预
        current_url = None
        if self.browser_session:
            try:
                # 获取当前页面URL
                current_page = getattr(self.browser_session, 'agent_current_page', None)
                if current_page and hasattr(current_page, 'url'):
                    current_url = current_page.url
            except Exception as e:
                self.logger.debug(f"获取当前页面URL失败: {e}")

        context = InterventionContext(
            step_number=step.step_number,
            step_title=step.title,
            error_message=step_result.error_message or "未知错误",
            screenshot_path=step_result.screenshot_path,
            page_url=current_url,
            retry_count=retry_count
        )

        response = await self.intervention_handler.request_intervention(
            context,
            InterventionType.ERROR_RETRY
        )

        # 记录干预信息
        step_result.intervention_used = True
        step_result.intervention_details = {
            "action": response.action,
            "message": response.message,
            "additional_instructions": response.additional_instructions
        }

        # 根据响应决定下一步动作
        if response.action == "continue":
            if response.additional_instructions:
                # 更新步骤说明
                step.description += f"\n\n### 人工指导:\n{response.additional_instructions}"
            return "retry"
        elif response.action == "skip":
            return "skip"
        elif response.action == "modify":
            if response.message:
                # 修改步骤操作
                step.actions = [response.message]
            return "retry"
        elif response.action == "goto" and response.skip_to_step:
            return f"goto:{response.skip_to_step}"
        else:
            return "continue"

    async def _take_screenshot(self, step_number: int, suffix: str = "") -> Optional[Path]:
        """截图"""
        if not self.browser_session:
            return None

        try:
            timestamp = int(time.time())
            filename = f"step_{step_number:02d}_{timestamp}"
            if suffix:
                filename += f"_{suffix}"
            filename += ".png"

            screenshot_path = self.screenshots_dir / filename

            # 这里需要根据browser_use的API进行截图
            # 暂时返回路径，实际实现需要调用browser_use的截图API

            return screenshot_path

        except Exception as e:
            self.logger.warning(f"截图失败: {e}")
            return None
