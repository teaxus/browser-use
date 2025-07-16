"""
Markdown测试用例解析器
"""
import re
import yaml
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestCaseMetadata:
    """测试用例元数据"""
    test_name: str
    environment: str = "test"
    timeout: int = 300
    retry_count: int = 3
    expected_chat_responses: Optional[List[str]] = None
    custom_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.expected_chat_responses is None:
            self.expected_chat_responses = []
        if self.custom_data is None:
            self.custom_data = {}


@dataclass
class TestStep:
    """单个测试步骤"""
    step_number: int
    title: str
    description: str
    actions: List[str]
    expected_result: Optional[str] = None


@dataclass
class TestCase:
    """完整的测试用例"""
    metadata: TestCaseMetadata
    objective: str
    steps: List[TestStep]
    expected_results: List[str]
    original_content: str
    processed_content: str


class MarkdownTestCaseParser:
    """Markdown测试用例解析器"""

    def __init__(self):
        self.metadata_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL | re.MULTILINE)
        self.step_pattern = re.compile(r'^#{1,3}\s+步骤\s*(\d+)[：:]\s*(.+)$', re.MULTILINE)
        self.objective_pattern = re.compile(r'\*\*\s*目标[：:]\s*\*\*\s*\n(.+?)(?=\n[-*]|\n#{1,3}|\n\*\*|\Z)', re.DOTALL)

    def parse(self, content: str) -> TestCase:
        """解析Markdown测试用例"""
        # 提取元数据
        metadata = self._parse_metadata(content)

        # 移除元数据，获取主要内容
        main_content = self._remove_metadata(content)

        # 提取目标
        objective = self._parse_objective(main_content)

        # 解析步骤
        steps = self._parse_steps(main_content)

        # 提取期待结果
        expected_results = self._parse_expected_results(main_content)

        return TestCase(
            metadata=metadata,
            objective=objective,
            steps=steps,
            expected_results=expected_results,
            original_content=content,
            processed_content=main_content
        )

    def parse_from_file(self, file_path: Path) -> TestCase:
        """从文件解析测试用例"""
        if not file_path.exists():
            raise FileNotFoundError(f"测试用例文件不存在: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return self.parse(content)

    def _parse_metadata(self, content: str) -> TestCaseMetadata:
        """解析YAML元数据"""
        match = self.metadata_pattern.search(content)
        if not match:
            # 如果没有元数据，使用默认值
            return TestCaseMetadata(test_name="未命名测试")

        try:
            yaml_content = match.group(1)
            data = yaml.safe_load(yaml_content)

            return TestCaseMetadata(
                test_name=data.get('test_name', '未命名测试'),
                environment=data.get('environment', 'test'),
                timeout=data.get('timeout', 300),
                retry_count=data.get('retry_count', 3),
                expected_chat_responses=data.get('expected_chat_responses', []),
                custom_data=data.get('custom_data', {})
            )
        except yaml.YAMLError as e:
            raise ValueError(f"YAML元数据解析失败: {e}")

    def _remove_metadata(self, content: str) -> str:
        """移除YAML元数据部分"""
        return self.metadata_pattern.sub('', content).strip()

    def _parse_objective(self, content: str) -> str:
        """提取测试目标"""
        match = self.objective_pattern.search(content)
        if match:
            return match.group(1).strip()
        return "未指定测试目标"

    def _parse_steps(self, content: str) -> List[TestStep]:
        """解析测试步骤"""
        steps = []
        step_matches = list(self.step_pattern.finditer(content))

        for i, match in enumerate(step_matches):
            step_number = int(match.group(1))
            title = match.group(2).strip()

            # 获取步骤内容（从当前匹配到下一个步骤或文件结尾）
            start_pos = match.end()
            if i + 1 < len(step_matches):
                end_pos = step_matches[i + 1].start()
            else:
                end_pos = len(content)

            step_content = content[start_pos:end_pos].strip()

            # 解析步骤中的操作
            actions = self._parse_step_actions(step_content)

            steps.append(TestStep(
                step_number=step_number,
                title=title,
                description=step_content,
                actions=actions
            ))

        return steps

    def _parse_step_actions(self, step_content: str) -> List[str]:
        """解析步骤中的具体操作"""
        lines = step_content.split('\n')
        actions = []

        for line in lines:
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                # 移除列表标记
                action = line[1:].strip()
                if action:
                    actions.append(action)

        return actions

    def _parse_expected_results(self, content: str) -> List[str]:
        """提取期待结果"""
        # 查找"期待结果"、"预期结果"等关键词
        patterns = [
            r'期待结果[：:]\s*\n(.*?)(?=\n#{1,3}|\Z)',
            r'预期结果[：:]\s*\n(.*?)(?=\n#{1,3}|\Z)',
            r'期望结果[：:]\s*\n(.*?)(?=\n#{1,3}|\Z)'
        ]

        results = []
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.DOTALL)
            for match in matches:
                result_text = match.group(1).strip()
                # 按行分割并清理
                for line in result_text.split('\n'):
                    line = line.strip()
                    if line.startswith('-') or line.startswith('*'):
                        result = line[1:].strip()
                        if result:
                            results.append(result)
                    elif line:
                        results.append(line)

        return results


# 创建示例测试用例
EXAMPLE_TEST_CASE = """---
test_name: "聊天功能测试"
environment: "test"
timeout: 300
retry_count: 3
expected_chat_responses: ["你好", "测试消息", "再见"]
---

## 发送聊天信息

** 目标：**
打开${base_url}/#/login，在咨询互动里的主管在管，点击第一条会话，发送"hello world"，等待其他信息，尝试和其他聊天人愉快聊天，直到最后一条信息是exit内容为止

### 步骤 1: 登陆网页
- 访问 ${base_url}/#/login，先不要输入帐号密码！，先点击【手机登陆】

### 步骤 2: 开始登陆
- 点击手机号输入框输入${credentials.phone}
- 点击验证码输入框输入${credentials.code}
- 点击登陆按钮

### 步骤 3: 找到咨询互动
- 登陆后先在placeholder='请输入内容'筛选输入框输入"咨询互动"内容
- 在菜单栏找到【咨询互动】并点击

### 步骤 4: 选择第一个会话
- 找到咨询互动，主管在管里的第一个会话并点击

### 步骤 5: 发送消息
- 点击输入框，输入"hello world"
- 检查输入框内容是否正确
- 点击发送按钮

### 步骤 6: 等待其他信息
- 等待其他人发送消息(每2分钟浏览一次消息是否更新)
- 尝试和其他聊天人愉快聊天
- 直到最后一条信息是exit内容为止

期待结果:
- 能正常回复其他人发过来的聊天信息
- 聊天交互流畅自然
- 正确识别exit退出条件
"""
