"""
日志管理器模块 - 负责测试过程中的日志记录、格式化和截图功能
"""

import logging
import sys
import os
import time
from pathlib import Path
from datetime import datetime
import traceback
from typing import Optional, List, Dict, Any, Tuple

# 导入测试相关类型
from browser_use.test_agent.parser.types import TestCase, TestStep
from browser_use.test_agent.core.types import StepResult


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器，使日志更易读"""

    # 各种日志级别的颜色
    COLORS = {
        'DEBUG': '\033[94m',      # 蓝色
        'INFO': '\033[92m',       # 绿色
        'WARNING': '\033[93m',    # 黄色
        'ERROR': '\033[91m',      # 红色
        'CRITICAL': '\033[91m\033[1m',  # 红色加粗
    }
    RESET = '\033[0m'  # 重置颜色

    def format(self, record):
        """格式化日志记录"""
        log_message = super().format(record)
        level_name = record.levelname
        if level_name in self.COLORS and sys.stdout.isatty():
            # 只在终端中添加颜色
            log_message = f"{self.COLORS[level_name]}{log_message}{self.RESET}"
        return log_message


class TestLogger:
    """测试日志管理器，负责所有测试日志的记录和格式化"""

    def __init__(self, screenshots_dir: Optional[Path] = None):
        """
        初始化日志管理器

        Args:
            screenshots_dir: 截图保存目录
        """
        self.logger = logging.getLogger("test_agent")
        self.screenshots_dir = screenshots_dir or Path("./test_screenshots")
        self._file_logger_initialized = False
        self.test_file_name = None

        # 确保目录存在
        self._ensure_directories()

        # 配置控制台日志
        self._setup_console_logger()

    def _ensure_directories(self):
        """确保日志和截图目录存在"""
        try:
            # 创建日志目录
            logs_dir = Path("./logs")
            logs_dir.mkdir(parents=True, exist_ok=True)

            # 创建截图目录
            if self.screenshots_dir:
                self.screenshots_dir.mkdir(parents=True, exist_ok=True)

            self.logger.debug(f"日志目录: {logs_dir.absolute()}")
            self.logger.debug(f"截图目录: {self.screenshots_dir.absolute() if self.screenshots_dir else '未设置'}")
        except Exception as e:
            self.logger.error(f"创建日志目录失败: {e}")

    def _setup_console_logger(self):
        """配置控制台日志处理器"""
        # 检查是否已经有处理器，避免重复添加
        if self.logger.handlers:
            self.logger.debug("日志处理器已存在，跳过配置")
            return

        try:
            # 设置日志级别
            self.logger.setLevel(logging.DEBUG)

            # 创建控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # 创建格式化器
            formatter = ColoredFormatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                                         datefmt='%Y-%m-%d %H:%M:%S')
            console_handler.setFormatter(formatter)

            # 添加处理器到日志记录器
            self.logger.addHandler(console_handler)
            self.logger.debug("控制台日志处理器配置完成")
        except Exception as e:
            # 使用内置的print，因为日志系统可能还未配置成功
            print(f"配置控制台日志失败: {e}")
            traceback.print_exc()

    def setup_file_logger(self, test_file_name: str) -> None:
        """
        为特定测试配置文件日志

        Args:
            test_file_name: 测试文件名，用于生成日志文件
        """
        # 如果已经初始化且文件相同，则跳过
        if self._file_logger_initialized and self.test_file_name == test_file_name:
            self.logger.debug(f"文件日志已配置为 {test_file_name}，跳过重复配置")
            return

        try:
            # 保存测试文件名
            self.test_file_name = test_file_name

            # 从文件名中提取测试名称（去掉扩展名）
            test_name = Path(test_file_name).stem

            # 创建日志文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = Path(f"./logs/{test_name}_{timestamp}.log")

            # 检查是否已经有文件处理器，有则移除
            for handler in self.logger.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    self.logger.removeHandler(handler)

            # 创建文件处理器
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)

            # 创建格式化器（文件中不使用彩色）
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                                          datefmt='%Y-%m-%d %H:%M:%S')
            file_handler.setFormatter(formatter)

            # 添加处理器到日志记录器
            self.logger.addHandler(file_handler)

            self._file_logger_initialized = True
            self.logger.info(f"文件日志已配置，保存到: {log_file}")
        except Exception as e:
            self.logger.error(f"配置文件日志失败: {e}")
            self.logger.debug(traceback.format_exc())

    def log_test_start(self, test_case: TestCase) -> None:
        """
        记录测试开始信息

        Args:
            test_case: 测试用例
        """
        self.logger.info(f"====================================================")
        self.logger.info(f"🚀 开始执行测试用例: {test_case.metadata.test_name}")
        self.logger.info(f"📋 测试目标: {test_case.objective}")
        self.logger.info(f"🔢 共 {len(test_case.steps)} 个步骤")
        self.logger.info(f"====================================================")

    def log_test_end(self, test_case: TestCase, success: bool, total_time: float,
                     step_results: List[StepResult]) -> None:
        """
        记录测试结束信息

        Args:
            test_case: 测试用例
            success: 是否成功
            total_time: 总执行时间
            step_results: 步骤结果列表
        """
        status = "✅ 成功" if success else "❌ 失败"
        self.logger.info(f"====================================================")
        self.logger.info(f"🏁 测试用例 {test_case.metadata.test_name} 执行{status}")
        self.logger.info(f"⏱️ 总执行时间: {total_time:.2f}秒")
        self.logger.info(f"📊 步骤执行结果: 成功 {sum(1 for r in step_results if r.success)}/{len(step_results)}")
        self.logger.info(f"====================================================")

    def log_step_start(self, step: TestStep) -> None:
        """
        记录步骤开始信息

        Args:
            step: 测试步骤
        """
        self.logger.info(f"▶️ 开始执行步骤 {step.step_number}: {step.title}")
        self.logger.info(f"📋 步骤说明: {step.description}")
        self.logger.info(f"🔍 具体操作:")
        for i, action in enumerate(step.actions):
            self.logger.info(f"  {i+1}. {action}")

    def log_step_end(self, step: TestStep, success: bool, execution_time: float,
                     error_message: Optional[str] = None) -> None:
        """
        记录步骤结束信息

        Args:
            step: 测试步骤
            success: 是否成功
            execution_time: 执行时间
            error_message: 错误信息
        """
        if success:
            self.logger.info(f"✅ 步骤 {step.step_number} 执行成功")
        else:
            self.logger.error(f"❌ 步骤 {step.step_number} 执行失败: {error_message}")

        self.logger.info(f"⏱️ 步骤 {step.step_number} 执行耗时: {execution_time:.2f}秒")

    def log_intervention_start(self, step_number: int, step_title: str, error_message: str,
                               current_url: Optional[str] = None, retry_count: int = 0) -> None:
        """
        记录人工干预开始

        Args:
            step_number: 步骤编号
            step_title: 步骤标题
            error_message: 错误信息
            current_url: 当前URL
            retry_count: 重试次数
        """
        self.logger.info("⚠️ === 人工干预开始，浏览器保护模式启动 ===")
        self.logger.info(f"📋 步骤 {step_number}: {step_title}")
        self.logger.info(f"🌐 当前URL: {current_url}")
        self.logger.info(f"❌ 错误信息: {error_message}")
        self.logger.info(f"🔢 重试次数: {retry_count}")

    def log_intervention_end(self, action: str, message: Optional[str] = None,
                             instructions: Optional[str] = None) -> None:
        """
        记录人工干预结束

        Args:
            action: 干预动作
            message: 干预消息
            instructions: 额外指示
        """
        self.logger.info("✅ === 人工干预结束，浏览器保护模式关闭 ===")
        self.logger.info(f"👤 干预结果: {action}")
        if message:
            self.logger.info(f"📝 干预消息: {message}")
        if instructions:
            self.logger.info(f"📋 额外指示: {instructions}")

    async def take_screenshot(self, browser_session, step_number: int, suffix: str = "") -> Optional[Path]:
        """
        截图并保存

        Args:
            browser_session: 浏览器会话
            step_number: 步骤编号
            suffix: 文件名后缀

        Returns:
            截图保存路径
        """
        if not browser_session:
            self.logger.warning("❌ 无法截图：浏览器会话不存在")
            return None

        try:
            # 确保截图目录存在
            if self.screenshots_dir:
                self.screenshots_dir.mkdir(parents=True, exist_ok=True)

            timestamp = int(time.time())
            filename = f"step_{step_number:02d}_{timestamp}"

            if suffix:
                filename += f"_{suffix}"

            filename += ".png"
            screenshot_path = self.screenshots_dir / filename

            # 截图
            try:
                if hasattr(browser_session, 'agent_current_page'):
                    page = browser_session.agent_current_page
                    if page and not page.is_closed():
                        await page.screenshot(path=str(screenshot_path))
                        self.logger.info(f"📸 截图已保存: {screenshot_path}")
                        return screenshot_path
            except Exception as e:
                self.logger.warning(f"截图操作失败: {e}")

            # 尝试使用浏览器会话的截图方法
            try:
                if hasattr(browser_session, 'screenshot'):
                    await browser_session.screenshot(str(screenshot_path))
                    self.logger.info(f"📸 使用备用方法截图已保存: {screenshot_path}")
                    return screenshot_path
            except Exception as e:
                self.logger.warning(f"备用截图方法失败: {e}")

            self.logger.warning("无法使用任何方法截图")
            return screenshot_path  # 返回路径但可能未创建成功

        except Exception as e:
            self.logger.warning(f"截图失败: {e}")
            self.logger.debug(traceback.format_exc())
            return None
