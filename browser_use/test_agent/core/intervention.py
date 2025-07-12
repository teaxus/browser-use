"""
人工干预处理器
"""
import asyncio
import json
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import logging


class InterventionType(Enum):
    """干预类型"""
    ERROR_RETRY = "error_retry"  # 错误重试
    STEP_GUIDANCE = "step_guidance"  # 步骤指导
    CONTEXT_UPDATE = "context_update"  # 上下文更新
    MANUAL_OPERATION = "manual_operation"  # 手动操作


@dataclass
class InterventionContext:
    """干预上下文"""
    step_number: int
    step_title: str
    error_message: str
    screenshot_path: Optional[str] = None
    page_url: Optional[str] = None
    retry_count: int = 0
    previous_attempts: List[str] = None

    def __post_init__(self):
        if self.previous_attempts is None:
            self.previous_attempts = []


@dataclass
class InterventionResponse:
    """干预响应"""
    action: str  # continue, skip, retry, modify, status
    message: Optional[str] = None
    additional_instructions: Optional[str] = None
    skip_to_step: Optional[int] = None


class HumanInterventionHandler:
    """人工干预处理器"""

    def __init__(self, timeout: int = 600):
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.intervention_history: List[Dict[str, Any]] = []
        self.websocket_callback: Optional[Callable] = None

    def set_websocket_callback(self, callback: Callable):
        """设置WebSocket回调函数（预留接口）"""
        self.websocket_callback = callback

    async def request_intervention(
        self,
        context: InterventionContext,
        intervention_type: InterventionType = InterventionType.ERROR_RETRY
    ) -> InterventionResponse:
        """请求人工干预"""

        self.logger.info(f"请求人工干预 - 步骤 {context.step_number}: {context.step_title}")

        # 记录干预历史
        intervention_record = {
            "timestamp": asyncio.get_event_loop().time(),
            "step_number": context.step_number,
            "step_title": context.step_title,
            "error_message": context.error_message,
            "intervention_type": intervention_type.value,
            "retry_count": context.retry_count
        }

        try:
            # 如果启用了WebSocket，优先使用WebSocket接口
            if self.websocket_callback:
                response = await self._handle_websocket_intervention(context, intervention_type)
            else:
                # 使用命令行接口
                response = await self._handle_cli_intervention(context, intervention_type)

            # 记录响应
            intervention_record["response"] = {
                "action": response.action,
                "message": response.message,
                "additional_instructions": response.additional_instructions
            }

            self.intervention_history.append(intervention_record)
            return response

        except asyncio.TimeoutError:
            self.logger.warning(f"人工干预超时 ({self.timeout}秒)")
            intervention_record["response"] = {"action": "timeout", "message": "人工干预超时"}
            self.intervention_history.append(intervention_record)
            return InterventionResponse(action="continue", message="超时，继续执行")

    async def _handle_cli_intervention(
        self,
        context: InterventionContext,
        intervention_type: InterventionType
    ) -> InterventionResponse:
        """处理命令行干预"""

        # 显示错误信息和上下文
        print("\n" + "="*60)
        print("🚨 需要人工干预")
        print("="*60)
        print(f"步骤: {context.step_number} - {context.step_title}")
        print(f"错误: {context.error_message}")
        print(f"重试次数: {context.retry_count}")

        if context.page_url:
            print(f"当前页面: {context.page_url}")

        if context.previous_attempts:
            print(f"之前的尝试:")
            for i, attempt in enumerate(context.previous_attempts, 1):
                print(f"  {i}. {attempt}")

        print("\n可用命令:")
        print("  continue              - 继续执行当前步骤")
        print("  skip                  - 跳过当前步骤")
        print("  retry                 - 重试当前步骤")
        print("  hint \"<说明>\"         - 提供额外指导说明")
        print("  modify \"<新指令>\"      - 修改当前步骤的操作")
        print("  status                - 查看当前页面状态")
        print("  goto <步骤号>          - 跳转到指定步骤")
        print("  help                  - 显示帮助信息")
        print("-"*60)

        # 等待用户输入
        while True:
            try:
                user_input = await asyncio.wait_for(
                    asyncio.to_thread(input, "请输入命令 > "),
                    timeout=self.timeout
                )

                response = self._parse_cli_command(user_input.strip())
                if response:
                    return response
                else:
                    print("无效命令，请重新输入（输入 help 查看帮助）")

            except asyncio.TimeoutError:
                raise
            except Exception as e:
                print(f"输入错误: {e}")

    def _parse_cli_command(self, command: str) -> Optional[InterventionResponse]:
        """解析命令行命令"""
        if not command:
            return None

        parts = command.split(' ', 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else None

        if cmd == "continue":
            return InterventionResponse(action="continue")

        elif cmd == "skip":
            return InterventionResponse(action="skip")

        elif cmd == "retry":
            return InterventionResponse(action="retry")

        elif cmd == "hint":
            if not arg:
                print("请提供指导说明，例如: hint \"请点击页面右上角的设置按钮\"")
                return None
            return InterventionResponse(
                action="continue",
                additional_instructions=arg.strip('"\'')
            )

        elif cmd == "modify":
            if not arg:
                print("请提供新的操作指令，例如: modify \"改为点击左侧菜单栏\"")
                return None
            return InterventionResponse(
                action="modify",
                message=arg.strip('"\'')
            )

        elif cmd == "status":
            return InterventionResponse(action="status")

        elif cmd == "goto":
            if not arg or not arg.isdigit():
                print("请提供有效的步骤号，例如: goto 3")
                return None
            return InterventionResponse(
                action="goto",
                skip_to_step=int(arg)
            )

        elif cmd == "help":
            print("\n命令说明:")
            print("  continue              - 继续执行当前步骤")
            print("  skip                  - 跳过当前步骤，继续下一步")
            print("  retry                 - 重新尝试当前步骤")
            print("  hint \"<说明>\"         - 为当前步骤提供额外的执行指导")
            print("  modify \"<新指令>\"      - 修改当前步骤的具体操作")
            print("  status                - 查看当前浏览器页面状态")
            print("  goto <步骤号>          - 跳转到指定的步骤号")
            print("  help                  - 显示此帮助信息")
            return None

        else:
            return None

    async def _handle_websocket_intervention(
        self,
        context: InterventionContext,
        intervention_type: InterventionType
    ) -> InterventionResponse:
        """处理WebSocket干预（预留）"""
        if not self.websocket_callback:
            raise ValueError("WebSocket回调未设置")

        # 发送干预请求到WebSocket客户端
        request_data = {
            "type": "intervention_required",
            "context": {
                "step_number": context.step_number,
                "step_title": context.step_title,
                "error_message": context.error_message,
                "screenshot_path": context.screenshot_path,
                "page_url": context.page_url,
                "retry_count": context.retry_count,
                "previous_attempts": context.previous_attempts
            },
            "intervention_type": intervention_type.value
        }

        # 等待WebSocket响应
        response_data = await self.websocket_callback(request_data)

        return InterventionResponse(
            action=response_data.get("action", "continue"),
            message=response_data.get("message"),
            additional_instructions=response_data.get("additional_instructions"),
            skip_to_step=response_data.get("skip_to_step")
        )

    def get_intervention_history(self) -> List[Dict[str, Any]]:
        """获取干预历史"""
        return self.intervention_history

    def clear_history(self):
        """清空干预历史"""
        self.intervention_history.clear()

    def save_history_to_file(self, file_path: str):
        """保存干预历史到文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.intervention_history, f, ensure_ascii=False, indent=2)
