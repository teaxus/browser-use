"""
Test Agent - 主要的测试智能体类
"""
import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union

from browser_use.llm.base import BaseChatModel

from .parser import MarkdownTestCaseParser, TestCase
from .executor import TestExecutor, TestExecutionResult
from .intervention import HumanInterventionHandler
from ..config.environment import EnvironmentConfig, TemplateEngine
from ..config.settings import TestAgentSettings
from ..report.generator import TestReportGenerator


class TestAgent:
    """
    Test Agent - 基于browser-use的自动化测试智能体

    提供完整的前端自动化测试解决方案，包括：
    - Markdown测试用例解析
    - 环境变量模板替换
    - 人工干预机制
    - 智能错误重试
    - 详细测试报告生成
    """

    def __init__(
        self,
        llm: BaseChatModel,
        config_path: Optional[Union[str, Path]] = None,
        environment: Optional[str] = None,
        settings: Optional[TestAgentSettings] = None
    ):
        """
        初始化Test Agent

        Args:
            llm: 语言模型实例
            config_path: 环境配置文件路径
            environment: 指定使用的环境（如果不指定则使用配置文件中的默认环境）
            settings: 测试设置
        """
        self.llm = llm
        self.settings = settings or TestAgentSettings()
        self.logger = logging.getLogger(__name__)

        # 初始化组件
        self.parser = MarkdownTestCaseParser()
        self.intervention_handler = HumanInterventionHandler(
            timeout=self.settings.intervention_timeout
        )
        self.executor = TestExecutor(
            llm=llm,
            intervention_handler=self.intervention_handler,
            max_retries=self.settings.max_retries,
            step_timeout=self.settings.step_timeout,
            use_vision=self.settings.use_vision,
            headless=self.settings.headless
        )

        # 环境配置
        self.env_config: Optional[EnvironmentConfig] = None
        self.current_environment = environment
        if config_path:
            self.load_environment_config(config_path)

        # 报告生成器
        self.report_generator = TestReportGenerator(
            save_screenshots=self.settings.save_screenshots,
            save_conversation_history=self.settings.save_conversation_history
        )

        self.logger.info(f"Test Agent 初始化完成 - 环境: {self.current_environment}")

    def load_environment_config(self, config_path: Union[str, Path]):
        """加载环境配置"""
        try:
            self.env_config = EnvironmentConfig.from_yaml(config_path)
            if not self.current_environment:
                self.current_environment = self.env_config.default_environment
            self.logger.info(f"环境配置加载成功: {config_path}")
        except Exception as e:
            self.logger.error(f"加载环境配置失败: {e}")
            raise

    async def run_test_case(
        self,
        test_case_content: str,
        environment: Optional[str] = None,
        output_dir: Optional[Path] = None
    ) -> TestExecutionResult:
        """
        执行测试用例（从字符串内容）

        Args:
            test_case_content: 测试用例Markdown内容
            environment: 指定环境（覆盖默认设置）
            output_dir: 输出目录

        Returns:
            测试执行结果
        """
        # 解析测试用例
        test_case = self.parser.parse(test_case_content)

        # 应用环境变量替换
        if self.env_config:
            processed_test_case = self._apply_environment_variables(test_case, environment)
        else:
            processed_test_case = test_case
            self.logger.warning("未加载环境配置，跳过模板变量替换")

        # 执行测试
        return await self._execute_test_case(processed_test_case, output_dir)

    async def run_test_case_from_file(
        self,
        test_case_file: Union[str, Path],
        environment: Optional[str] = None,
        output_dir: Optional[Path] = None
    ) -> TestExecutionResult:
        """
        执行测试用例（从文件）

        Args:
            test_case_file: 测试用例文件路径
            environment: 指定环境（覆盖默认设置）
            output_dir: 输出目录

        Returns:
            测试执行结果
        """
        test_case_file = Path(test_case_file)

        # 解析测试用例
        test_case = self.parser.parse_from_file(test_case_file)

        # 应用环境变量替换
        if self.env_config:
            processed_test_case = self._apply_environment_variables(test_case, environment)
        else:
            processed_test_case = test_case
            self.logger.warning("未加载环境配置，跳过模板变量替换")

        # 执行测试
        return await self._execute_test_case(processed_test_case, output_dir)

    def _apply_environment_variables(
        self,
        test_case: TestCase,
        environment: Optional[str] = None
    ) -> TestCase:
        """应用环境变量模板替换"""
        if not self.env_config:
            return test_case

        # 确定使用的环境
        target_env = environment or test_case.metadata.environment or self.current_environment

        try:
            # 获取环境变量
            env_vars = self.env_config.to_template_vars(target_env)
            template_engine = TemplateEngine(env_vars)

            # 替换测试用例中的变量
            processed_content = template_engine.replace_variables(test_case.processed_content)

            # 重新解析处理后的内容
            processed_test_case = self.parser.parse(processed_content)

            # 保留原始内容用于报告
            processed_test_case.original_content = test_case.original_content

            self.logger.info(f"环境变量替换完成 - 目标环境: {target_env}")
            return processed_test_case

        except Exception as e:
            self.logger.error(f"环境变量替换失败: {e}")
            raise ValueError(f"环境变量替换失败: {e}")

    async def _execute_test_case(
        self,
        test_case: TestCase,
        output_dir: Optional[Path] = None
    ) -> TestExecutionResult:
        """执行测试用例的核心逻辑"""
        start_time = time.time()

        self.logger.info(f"开始执行测试用例: {test_case.metadata.test_name}")

        try:
            # 设置输出目录
            if output_dir is None:
                timestamp = int(time.time())
                output_dir = Path(f"./test_results/{test_case.metadata.test_name}_{timestamp}")

            output_dir.mkdir(parents=True, exist_ok=True)

            # 设置截图目录
            screenshots_dir = output_dir / "screenshots"
            self.executor.screenshots_dir = screenshots_dir

            # 执行测试
            result = await self.executor.execute_test_case(test_case)

            # 生成报告
            await self._generate_test_report(test_case, result, output_dir)

            total_time = time.time() - start_time
            self.logger.info(
                f"测试用例执行完成: {test_case.metadata.test_name} "
                f"- 结果: {'成功' if result.success else '失败'} "
                f"- 耗时: {total_time:.2f}秒"
            )

            return result

        except Exception as e:
            total_time = time.time() - start_time
            self.logger.error(f"测试用例执行异常: {e}")

            # 创建失败结果
            from .executor import TestExecutionResult, StepResult
            return TestExecutionResult(
                test_name=test_case.metadata.test_name,
                success=False,
                total_time=total_time,
                step_results=[],
                final_message=f"测试执行异常: {str(e)}"
            )

    async def _generate_test_report(
        self,
        test_case: TestCase,
        result: TestExecutionResult,
        output_dir: Path
    ):
        """生成测试报告"""
        try:
            # 生成HTML报告
            if self.settings.report_format == "html":
                report_path = await self.report_generator.generate_html_report(
                    test_case, result, output_dir
                )
                self.logger.info(f"HTML报告已生成: {report_path}")

            # 生成JSON数据
            json_path = await self.report_generator.generate_json_report(
                test_case, result, output_dir
            )
            self.logger.info(f"JSON数据已生成: {json_path}")

            # 保存人工干预历史
            if self.intervention_handler.get_intervention_history():
                intervention_path = output_dir / "intervention_history.json"
                self.intervention_handler.save_history_to_file(str(intervention_path))
                self.logger.info(f"人工干预历史已保存: {intervention_path}")

        except Exception as e:
            self.logger.error(f"生成测试报告失败: {e}")

    def get_intervention_history(self) -> list:
        """获取人工干预历史"""
        return self.intervention_handler.get_intervention_history()

    def clear_intervention_history(self):
        """清空人工干预历史"""
        self.intervention_handler.clear_history()

    def set_websocket_callback(self, callback):
        """设置WebSocket回调（预留接口）"""
        self.intervention_handler.set_websocket_callback(callback)


# 便捷函数
async def run_test_from_file(
    test_file: Union[str, Path],
    llm: BaseChatModel,
    config_file: Optional[Union[str, Path]] = None,
    environment: Optional[str] = None,
    output_dir: Optional[Path] = None,
    settings: Optional[TestAgentSettings] = None
) -> TestExecutionResult:
    """
    便捷函数：从文件运行测试用例

    Args:
        test_file: 测试用例文件路径
        llm: 语言模型实例
        config_file: 环境配置文件路径
        environment: 指定环境
        output_dir: 输出目录
        settings: 测试设置

    Returns:
        测试执行结果
    """
    agent = TestAgent(
        llm=llm,
        config_path=config_file,
        environment=environment,
        settings=settings
    )

    return await agent.run_test_case_from_file(
        test_case_file=test_file,
        environment=environment,
        output_dir=output_dir
    )


async def run_test_from_content(
    test_content: str,
    llm: BaseChatModel,
    config_file: Optional[Union[str, Path]] = None,
    environment: Optional[str] = None,
    output_dir: Optional[Path] = None,
    settings: Optional[TestAgentSettings] = None
) -> TestExecutionResult:
    """
    便捷函数：从内容运行测试用例

    Args:
        test_content: 测试用例内容
        llm: 语言模型实例
        config_file: 环境配置文件路径
        environment: 指定环境
        output_dir: 输出目录
        settings: 测试设置

    Returns:
        测试执行结果
    """
    agent = TestAgent(
        llm=llm,
        config_path=config_file,
        environment=environment,
        settings=settings
    )

    return await agent.run_test_case(
        test_case_content=test_content,
        environment=environment,
        output_dir=output_dir
    )
