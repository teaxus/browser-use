"""
截图工具
"""
import asyncio
import time
from pathlib import Path
from typing import Optional


async def capture_screenshot(browser_session, output_dir: Path, prefix: str = "screenshot") -> Optional[Path]:
    """
    捕获当前页面截图

    Args:
        browser_session: 浏览器会话
        output_dir: 输出目录
        prefix: 文件名前缀

    Returns:
        截图文件路径，失败返回None
    """
    try:
        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        timestamp = int(time.time())
        filename = f"{prefix}_{timestamp}.png"
        screenshot_path = output_dir / filename

        # 获取当前页面
        if hasattr(browser_session, 'agent_current_page') and browser_session.agent_current_page:
            page = browser_session.agent_current_page

            # 截图
            await page.screenshot(path=str(screenshot_path))
            return screenshot_path
        else:
            return None

    except Exception as e:
        print(f"截图失败: {e}")
        return None
