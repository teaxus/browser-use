"""
Test Agent - 基于browser-use的自动化测试智能体

这个模块提供了一个完整的前端自动化测试解决方案，具有以下特性：
- 支持Markdown格式的测试用例
- 环境变量模板替换
- 人工干预机制
- 智能错误重试
- 详细的测试报告
- WebSocket接口支持

Author: GitHub Copilot
Version: 1.0.0
"""

from .core.agent import TestAgent
from .core.parser import MarkdownTestCaseParser
from .core.executor import TestExecutor
from .core.intervention import HumanInterventionHandler
from .config.environment import EnvironmentConfig
from .config.settings import TestAgentSettings

__all__ = [
    'TestAgent',
    'MarkdownTestCaseParser',
    'TestExecutor',
    'HumanInterventionHandler',
    'EnvironmentConfig',
    'TestAgentSettings'
]

__version__ = '1.0.0'
