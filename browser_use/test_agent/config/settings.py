"""
测试智能体配置设置
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from pathlib import Path


class TestAgentSettings(BaseModel):
    """Test Agent全局设置"""

    # 基础设置
    max_retries: int = Field(default=3, description="步骤失败时的最大重试次数")
    timeout: int = Field(default=300, description="测试总超时时间（秒）")
    step_timeout: int = Field(default=30, description="单个步骤超时时间（秒）")

    # 人工干预设置
    intervention_enabled: bool = Field(default=True, description="是否启用人工干预")
    intervention_timeout: int = Field(default=600, description="等待人工干预的超时时间（秒）")

    # 报告设置
    save_screenshots: bool = Field(default=True, description="是否保存截图")
    save_conversation_history: bool = Field(default=True, description="是否保存对话历史")
    report_format: str = Field(default="html", description="报告格式：html, json")

    # 浏览器设置
    use_vision: bool = Field(default=True, description="是否启用视觉识别")
    headless: bool = Field(default=False, description="是否无头模式运行浏览器")

    # WebSocket设置（预留）
    websocket_enabled: bool = Field(default=False, description="是否启用WebSocket接口")
    websocket_port: int = Field(default=8765, description="WebSocket端口")

    # 日志设置
    log_level: str = Field(default="INFO", description="日志级别")
    log_file: Optional[Path] = Field(default=None, description="日志文件路径")

    class Config:
        arbitrary_types_allowed = True
