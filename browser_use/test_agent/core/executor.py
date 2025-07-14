"""
测试执行器
"""
import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from browser_use import Agent, BrowserSession, BrowserProfile
from browser_use.agent.views import AgentHistoryList

from .parser import TestCase, TestStep
from .intervention import HumanInterventionHandler, InterventionContext, InterventionType, InterventionResponse
from ..utils.screenshot import capture_screenshot


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
        llm,
        intervention_handler: HumanInterventionHandler,
        max_retries: int = 3,
        step_timeout: int = 600,  # 默认10分钟
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
        self._is_intervention_in_progress = False  # 跟踪人工干预状态
        self._execution_id = str(uuid.uuid4())

        # 系统资源监控 (禁用 - macOS内存管理机制不同)
        self._memory_threshold = 85.0  # 内存使用阈值(%)
        self._check_resources = False  # 禁用内存检查

        # 确保截图目录存在
        if hasattr(self, 'screenshots_dir'):
            self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def _check_system_resources(self):
        """检查系统资源状况（已禁用 - macOS内存管理不同）"""
        return  # 跳过所有内存检查

    async def execute_test_case(self, test_case: TestCase) -> TestExecutionResult:
        """执行完整的测试用例"""
        start_time = time.time()
        step_results: List[StepResult] = []

        self.logger.info(f"开始执行测试用例: {test_case.metadata.test_name}")

        try:
            # 初始化浏览器会话 - 使用正确的创建方法
            self.browser_session = self._create_browser_session()
            # browser-use会自动启动，不需要手动调用start()
            self.logger.info(f"浏览器会话已创建，headless模式: {self.headless}")

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
                screenshots_dir=getattr(self, 'screenshots_dir', None),
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
                screenshots_dir=getattr(self, 'screenshots_dir', None)
            )

        finally:
            # 只在测试完全结束时关闭浏览器，不在每个步骤后关闭
            if self.browser_session:
                try:
                    await self.browser_session.close()
                    self.browser_session = None
                    self.current_agent = None
                    self.logger.info("测试完成，浏览器会话已关闭")
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
            # 🔧 关键修复1: 确保浏览器会话是活跃的
            if not self.browser_session:
                self.logger.warning("浏览器会话不存在，重新创建")
                self.browser_session = self._create_browser_session()

            # 🔧 关键修复2: 检查浏览器会话状态（但不重新创建）
            try:
                if hasattr(self.browser_session, 'agent_current_page'):
                    current_page = self.browser_session.agent_current_page
                    if current_page and current_page.is_closed():
                        self.logger.warning("浏览器页面已关闭，但保持会话")
                        # 不重新创建会话，让Agent处理页面导航
            except Exception as e:
                self.logger.warning(f"浏览器状态检查失败: {e}")

            # 🔧 关键修复3: 获取页面状态信息
            current_url = await self._get_current_url_safe()
            page_title = await self._get_page_title_safe()
            self.logger.info(f"执行前状态 - URL: {current_url}, 标题: {page_title}")

            # 构建步骤任务描述
            step_task = self._build_step_task(step, test_case)
            self.logger.info(f"任务描述: {step_task[:200]}...")

            # 🔧 关键修复4: 创建Agent时重用browser_session
            if not self.current_agent:
                self.current_agent = Agent(
                    task=step_task,
                    llm=self.llm,
                    browser_session=self.browser_session,
                    use_vision=self.use_vision
                )
            else:
                # 更新现有Agent的任务，避免重新创建
                self.current_agent.task = step_task

            # 🔧 关键修复5: 使用更宽松的超时和步骤限制执行Agent
            result = None
            try:
                # 设置干预标志，防止在执行期间关闭浏览器
                self._is_intervention_in_progress = True

                # 给Agent足够的时间和步骤数执行
                result = await asyncio.wait_for(
                    self.current_agent.run(max_steps=20),  # 增加最大步骤数
                    timeout=self.step_timeout
                )

                self.logger.info("步骤执行成功")

            except Exception as agent_error:
                import traceback
                error_details = {
                    'type': type(agent_error).__name__,
                    'message': str(agent_error),
                    'traceback': traceback.format_exc()
                }

                self.logger.error(f"Agent执行出错: {error_details['type']}: {error_details['message']}")
                self.logger.debug(f"完整错误堆栈:\n{error_details['traceback']}")

                # 只在特定的致命浏览器错误时重新创建会话
                if any(
                        keyword in str(agent_error).lower()
                        for keyword in ['browser crashed', 'connection refused', 'target closed']):
                    self.logger.warning("检测到致命浏览器错误，尝试重新创建浏览器会话")
                    try:
                        if self.browser_session:
                            await self.browser_session.close()
                        await asyncio.sleep(2)  # 等待浏览器完全关闭
                        self.browser_session = self._create_browser_session()
                        self.current_agent = None  # 重置Agent，下次使用时会重新创建
                    except Exception as reset_error:
                        self.logger.error(f"重新创建浏览器会话失败: {reset_error}")

                # 不要重新抛出异常，而是返回失败结果让干预机制处理
                raise agent_error
            finally:
                self._is_intervention_in_progress = False

            # 验证执行结果
            final_url = await self._get_current_url_safe()
            final_title = await self._get_page_title_safe()
            self.logger.info(f"执行后状态 - URL: {final_url}, 标题: {final_title}")

            # 保存成功截图
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

        # 标记人工干预开始
        self._is_intervention_in_progress = True

        try:
            response = await self.intervention_handler.request_intervention(
                context,
                InterventionType.ERROR_RETRY
            )
        finally:
            # 标记人工干预结束
            self._is_intervention_in_progress = False

        # 记录干预信息
        step_result.intervention_used = True
        step_result.intervention_details = {
            "action": response.action,
            "message": response.message,
            "additional_instructions": response.additional_instructions
        }

        # 人工干预后验证浏览器状态
        if self.browser_session:
            try:
                page_ok, page_status = await self._verify_page_state(step)
                self.logger.info(f"人工干预后页面状态: {page_status}")
                if not page_ok:
                    self.logger.warning(f"人工干预后页面状态异常: {page_status}")
            except Exception as e:
                self.logger.warning(f"人工干预后页面状态检查失败: {e}")

        # 根据响应决定下一步动作
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

    async def _verify_page_state(self, step: TestStep) -> Tuple[bool, str]:
        """验证页面状态，避免空白页面误判"""
        if not self.browser_session:
            return False, "浏览器会话不存在"

        try:
            # 获取当前页面
            current_page = getattr(self.browser_session, 'current_page', None)
            if not current_page:
                return False, "无法获取当前页面"

            # 检查页面URL
            current_url = current_page.url if hasattr(current_page, 'url') else "unknown"
            self.logger.info(f"当前页面URL: {current_url}")

            # 等待页面加载完成
            try:
                await current_page.wait_for_load_state('networkidle', timeout=5000)
            except Exception as e:
                self.logger.warning(f"等待页面网络空闲超时: {e}")

            # 检查页面内容
            try:
                # 获取页面标题
                title = await current_page.title()
                self.logger.info(f"页面标题: {title}")

                # 检查body元素是否存在且有内容
                body_content = await current_page.evaluate("document.body ? document.body.innerText.trim().length : 0")
                self.logger.info(f"页面内容长度: {body_content}")

                # 判断页面是否有效加载
                if body_content > 50:  # 至少50个字符表示有实际内容
                    return True, f"页面正常加载 - 标题: {title}, 内容长度: {body_content}"
                elif title and title.strip():
                    return True, f"页面可能正在加载 - 标题: {title}"
                else:
                    return False, f"页面可能为空白 - URL: {current_url}, 内容长度: {body_content}"

            except Exception as e:
                self.logger.warning(f"页面内容检查失败: {e}")
                return False, f"页面状态检查失败: {str(e)}"

        except Exception as e:
            self.logger.error(f"页面状态验证失败: {e}")
            return False, f"页面状态验证异常: {str(e)}"

    async def _get_current_url_safe(self) -> str:
        """安全获取当前页面URL"""
        try:
            if self.browser_session and hasattr(self.browser_session, 'agent_current_page'):
                page = self.browser_session.agent_current_page
                if page and not page.is_closed():
                    return page.url
            return "未知页面"
        except Exception as e:
            self.logger.warning(f"获取页面URL失败: {e}")
            return "获取失败"

    async def _get_page_title_safe(self) -> str:
        """安全获取当前页面标题"""
        try:
            if self.browser_session and hasattr(self.browser_session, 'agent_current_page'):
                page = self.browser_session.agent_current_page
                if page and not page.is_closed():
                    title = await page.title()
                    return title or "无标题"
            return "未知标题"
        except Exception as e:
            self.logger.warning(f"获取页面标题失败: {e}")
            return "获取失败"

    def _create_browser_session(self) -> 'BrowserSession':
        """创建浏览器会话"""
        # 创建浏览器配置
        profile = BrowserProfile(
            headless=self.headless
        )

        # 使用正确的BrowserSession创建方式
        return BrowserSession(browser_profile=profile)

    async def _safe_browser_close(self):
        """安全关闭浏览器，在干预期间不关闭"""
        if not getattr(self, '_is_intervention_in_progress', False):
            if self.browser_session:
                try:
                    await self.browser_session.close()
                    self.browser_session = None
                    self.current_agent = None
                    self.logger.info("浏览器会话已关闭")
                except Exception as e:
                    self.logger.warning(f"关闭浏览器会话失败: {e}")
        else:
            self.logger.info("干预进行中，保持浏览器会话打开")

    async def close_browser_safely(self):
        """安全关闭浏览器，只在没有人工干预时关闭"""
        if self.browser_session and not self._is_intervention_in_progress:
            try:
                self.logger.info("安全关闭浏览器会话")
                await self.browser_session.close()
                self.browser_session = None
            except Exception as e:
                self.logger.warning(f"关闭浏览器会话失败: {e}")
        elif self._is_intervention_in_progress:
            self.logger.info("人工干预进行中，保持浏览器开启")
        else:
            self.logger.info("浏览器会话已关闭或不存在")
