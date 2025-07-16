# 测试执行器使用指南

本文档提供了关于如何使用重构后的测试执行器组件的指南。

## 快速开始

以下是使用重构后测试执行器的基本示例：

```python
import asyncio
from pathlib import Path
from browser_use.llm import create_llm
from browser_use.test_agent.parser import TestCaseParser
from browser_use.test_agent.core import TestExecutor
from browser_use.test_agent.intervention import HumanInterventionHandler

async def run_test(test_file_path: str):
    # 创建LLM
    llm = create_llm("anthropic")

    # 创建干预处理器
    intervention_handler = HumanInterventionHandler()

    # 创建测试执行器
    executor = TestExecutor(
        llm=llm,
        intervention_handler=intervention_handler,
        max_retries=3,
        step_timeout=60000,  # 60秒
        use_vision=True,
        headless=False,
        screenshots_dir=Path("./test_screenshots")
    )

    # 解析测试用例
    parser = TestCaseParser()
    test_case = parser.parse_file(test_file_path)

    # 执行测试并获取结果
    result = await executor.execute_test_case(
        test_case=test_case,
        test_file_name=Path(test_file_path).name
    )

    # 输出测试结果
    print(f"Test: {result.test_name}")
    print(f"Success: {result.success}")
    print(f"Time: {result.total_time:.2f}s")
    print(f"Steps: {len(result.step_results)}")

    return result

if __name__ == "__main__":
    asyncio.run(run_test("path/to/test_file.md"))
```

## 组件说明

重构后的测试执行器由以下主要组件组成：

### 1. 核心执行器 (TestExecutor)

整个测试执行的协调者，负责管理测试用例的执行流程。

```python
executor = TestExecutor(
    llm=llm,
    intervention_handler=intervention_handler,
    max_retries=3,
    step_timeout=60000,
    use_vision=True,
    headless=False,
    screenshots_dir=Path("./test_screenshots")
)

result = await executor.execute_test_case(test_case, test_file_name)
```

### 2. 浏览器管理器 (BrowserManager)

管理浏览器会话的创建、标签页切换和浏览器状态。

```python
browser_manager = BrowserManager(headless=False)
await browser_manager.create_and_start_session()
await browser_manager.check_and_switch_to_new_tab()
await browser_manager.close_session()
```

### 3. 上下文构建器 (TestContextBuilder)

构建测试步骤的上下文和任务描述。

```python
context_builder = TestContextBuilder()
task_description = context_builder.build_step_task(step, test_case)
test_context = context_builder.extract_test_case_context(test_case)
```

### 4. 日志管理器 (TestLogger)

管理测试过程中的日志记录和截图。

```python
logger = TestLogger(screenshots_dir=Path("./test_screenshots"))
logger.setup_file_logger("test_file.md")
logger.log_test_start(test_case)
logger.log_step_start(step)
screenshot_path = await logger.take_screenshot(browser_session, step_number)
```

### 5. 干预处理器 (EnhancedInterventionHandler)

处理测试过程中的人工干预。

```python
intervention_handler = EnhancedInterventionHandler(base_handler)
action = await intervention_handler.handle_step_failure(step, step_result, test_case, browser_manager, max_retries)
```

## 高级用法

### 自定义干预处理

可以通过继承 `EnhancedInterventionHandler` 实现自定义干预处理逻辑：

```python
class MyInterventionHandler(EnhancedInterventionHandler):
    async def handle_step_failure(self, step, step_result, test_case, browser_manager, max_retries):
        # 自定义处理逻辑
        return "retry"
```

### 监控浏览器会话

在测试执行过程中监控浏览器会话状态：

```python
async def monitor_browser(browser_manager, interval=5):
    while True:
        await asyncio.sleep(interval)
        page_ok, status = await browser_manager.verify_page_state()
        if not page_ok:
            print(f"页面状态异常: {status}")
```

## 故障排除

### 浏览器崩溃

如果测试执行过程中浏览器崩溃，核心执行器会尝试重新创建浏览器会话并继续测试。如果仍然失败，可以检查以下问题：

1. 检查浏览器依赖是否正确安装
2. 增加内存限制或使用无头模式
3. 检查是否有复杂的网页导致浏览器崩溃

### 测试超时

如果测试步骤执行超时，可以考虑以下解决方案：

1. 增加 `step_timeout` 参数值
2. 简化测试步骤，将复杂步骤拆分为多个简单步骤
3. 检查网页是否有长时间加载的资源
