"""
类型定义模块 - 为测试执行器定义共享类型
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path


class InterventionType(Enum):
    """人工干预类型"""
    ERROR_RETRY = "error_retry"  # 执行错误后重试
    EXECUTION_PAUSE = "execution_pause"  # 暂停执行
    MANUAL_VALIDATION = "manual_validation"  # 人工验证
    EMERGENCY_STOP = "emergency_stop"  # 紧急停止


@dataclass
class InterventionContext:
    """人工干预上下文"""
    step_number: int  # 步骤编号
    step_title: str  # 步骤标题
    error_message: str  # 错误信息
    screenshot_path: Optional[str] = None  # 截图路径
    page_url: Optional[str] = None  # 当前页面URL
    retry_count: int = 0  # 重试次数


@dataclass
class InterventionResponse:
    """人工干预响应"""
    action: str  # 动作：continue, retry, skip, goto, modify
    message: Optional[str] = None  # 消息
    additional_instructions: Optional[str] = None  # 额外指示
    skip_to_step: Optional[int] = None  # 跳转到的步骤编号


@dataclass
class StepResult:
    """步骤执行结果"""
    step_number: int  # 步骤编号
    success: bool  # 是否成功
    execution_time: float  # 执行时间
    error_message: Optional[str] = None  # 错误信息
    screenshot_path: Optional[str] = None  # 截图路径
    intervention_used: bool = False  # 是否使用了人工干预
    intervention_details: Optional[Dict[str, Any]] = None  # 人工干预详情
    agent_output: Optional[str] = None  # Agent输出结果


@dataclass
class TestExecutionResult:
    """测试执行结果"""
    test_name: str  # 测试名称
    success: bool  # 是否成功
    total_time: float  # 总执行时间
    step_results: List[StepResult]  # 步骤结果
    final_message: str  # 最终消息
    screenshots_dir: Optional[Path] = None  # 截图目录
    conversation_history: Optional[List[Dict[str, Any]]] = None  # 对话历史
