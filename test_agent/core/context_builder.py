"""
上下文构建器模块 - 负责从测试用例中提取上下文信息并构建任务描述
"""

import logging
import re
from typing import Dict, Any, List, Optional

# 导入测试相关类型
from browser_use.test_agent.parser.types import TestCase, TestStep


class TestContextBuilder:
    """测试上下文构建器，从测试用例中提取信息并构建任务描述"""

    def __init__(self):
        """初始化上下文构建器"""
        self.logger = logging.getLogger(__name__)

    def build_step_task(self, step: TestStep, test_case: TestCase) -> str:
        """
        构建步骤任务描述 - 提供详细的任务描述供AI执行

        Args:
            step: 当前要执行的步骤
            test_case: 测试用例

        Returns:
            任务描述文本
        """
        self.logger.info(f"开始构建步骤 {step.step_number} [{step.title}] 的任务描述...")

        # 提取测试用例的上下文信息
        test_context = self.extract_test_case_context(test_case)
        important_values = test_context["important_values"]

        # 日志记录提取的关键信息
        self.logger.info(f"测试上下文信息摘要:")
        if important_values:
            self.logger.info(f"   重要值: {important_values}")
        if test_context['urls']:
            self.logger.info(f"   URLs: {test_context['urls']}")
        if test_context['form_fields']:
            self.logger.info(f"   表单字段: {len(test_context['form_fields'])} 个字段")

        task_parts = [
            f"## 步骤 {step.step_number}: {step.title}",
            "",
            "### 任务目标:",
            test_case.objective,
            "",
            "### 完整测试流程概述:",  # 添加完整流程概述
        ]

        # 添加所有步骤的详细概述，让AI了解整个测试流程
        task_parts.append("以下是完整测试流程，每个步骤包含具体操作细节：")
        task_parts.append("")

        for test_step in test_case.steps:
            step_status = "【当前步骤】" if test_step.step_number == step.step_number else ""
            task_parts.append(f"#### 步骤{test_step.step_number}: {test_step.title} {step_status}")

            # 添加步骤描述
            if test_step.description:
                task_parts.append(f"{test_step.description}")
                task_parts.append("")

            # 添加详细操作步骤
            task_parts.append("具体操作：")
            for action in test_step.actions:
                task_parts.append(f"- {action}")

            # 添加期望结果（如果有）
            if test_step.expected_result:
                task_parts.extend([
                    "",
                    "期望结果：",
                    f"{test_step.expected_result}"
                ])

            task_parts.append("")

        task_parts.append("")

        # 添加测试上下文和相关步骤的详细信息
        task_parts.extend([
            "### 测试上下文和相关信息:",
            "",
        ])

        # 添加关键URL
        if test_context["urls"]:
            task_parts.append("#### 测试中涉及的URL:")
            for url in test_context["urls"]:
                # 处理各种可能的markdown格式，提取纯URL
                url_match = re.search(r'https?://[^\s()<>\[\]]+', url)
                if url_match:
                    clean_url = url_match.group(0)
                    # 去掉URL尾部的标点符号
                    clean_url = re.sub(r'[.,;:?!]+$', '', clean_url)
                    task_parts.append(f"- {clean_url}")
            task_parts.append("")

        # 添加表单字段信息
        if test_context["form_fields"]:
            task_parts.append("#### 测试中涉及的表单字段:")
            for field in test_context["form_fields"]:
                task_parts.append(f"- 步骤{field['step']} - {field['field']}: {field['value']}")
            task_parts.append("")

        # 添加多个验证码的情况
        if len(test_context["verification_codes"]) > 1:
            task_parts.append("#### 注意：测试中包含多个验证码!")
            for step, code in test_context["verification_codes"].items():
                task_parts.append(f"- {step}验证码: {code}")
            task_parts.append("")

        # 添加步骤间的关系
        if test_context["step_relationships"]:
            task_parts.append("#### 步骤间的逻辑关系:")
            for relation, type in test_context["step_relationships"].items():
                task_parts.append(f"- {relation}: {type}")
            task_parts.append("")

        # 添加相关步骤的详细信息
        task_parts.extend([
            "### 相关步骤详细信息:",
            "",
        ])

        # 获取前一个步骤（如果存在）
        prev_step_index = step.step_number - 2  # 索引从0开始，而且要找前一个
        if prev_step_index >= 0 and prev_step_index < len(test_case.steps):
            prev_step = test_case.steps[prev_step_index]
            task_parts.extend([
                f"#### 前一步骤 (步骤{prev_step.step_number}): {prev_step.title}",
                f"{prev_step.description}",
                "",
                "操作:",
            ])
            for action in prev_step.actions:
                task_parts.append(f"- {action}")

            # 添加期望结果（如果存在），但与操作明确分开
            if prev_step.expected_result:
                task_parts.extend([
                    "",
                    "期望结果:",
                    f"{prev_step.expected_result}"
                ])

            task_parts.append("")

        # 获取后一个步骤（如果存在）
        next_step_index = step.step_number  # 索引从0开始，当前是step_number-1，所以下一个是step_number
        if next_step_index < len(test_case.steps):
            next_step = test_case.steps[next_step_index]
            task_parts.extend([
                f"#### 后一步骤 (步骤{next_step.step_number}): {next_step.title}",
                f"{next_step.description}",
                "",
                "操作:",
            ])
            for action in next_step.actions:
                task_parts.append(f"- {action}")

            # 添加期望结果（如果存在），但与操作明确分开
            if next_step.expected_result:
                task_parts.extend([
                    "",
                    "期望结果:",
                    f"{next_step.expected_result}"
                ])

            task_parts.append("")

        task_parts.append("")

        # 使用已提取的上下文信息

        # 如果有重要数值，直接在开头强调
        if important_values:
            task_parts.extend([
                "### 🎯 系统锁定的关键数值 (必须严格使用):",
            ])
            for value_type, value in important_values.items():
                task_parts.append(f"- {value_type}: {value}")
            task_parts.append("")

        task_parts.append("### 当前步骤要求:")

        # 构建更直接的操作指令
        for action in step.actions:
            direct_action = self.make_action_direct(action, important_values)
            task_parts.append(f"- {direct_action}")

        # 添加当前步骤的期望结果
        if step.expected_result:
            task_parts.extend([
                "",
                "### 期望结果:",
                step.expected_result
            ])

        # 如果有重要数值，添加更强的约束
        if important_values:
            task_parts.extend([
                "",
                "### 🚨 系统强制约束 🚨:",
            ])
            for value_type, value in important_values.items():
                task_parts.append(f"- {value_type}只能是 {value}，不得使用其他任何数值")
            task_parts.extend([
                "- 系统已锁定以上数值，请严格执行",
                "- 如检测到使用了错误数值，测试将自动终止",
            ])

        task_parts.extend([
            "",
            "### 其他要求:",
            "- 仔细查看页面内容，确保正确识别元素",
            "- 如果遇到加载等待，请耐心等待页面完全加载",
            "- 如果某个操作失败，请尝试不同的方法",
            "- 对于聊天功能，请保持自然的对话风格"
        ])

        return "\n".join(task_parts)

    def make_action_direct(self, action: str, important_values: Dict[str, str]) -> str:
        """
        将操作指令转换为更直接的形式，避免依赖AI理解

        Args:
            action: 原始操作指令
            important_values: 重要值字典

        Returns:
            更直接的操作指令
        """
        direct_action = action

        # 如果包含手机号，直接指定数值
        if "手机号" in action and "手机号" in important_values:
            phone = important_values["手机号"]
            # 更直接的指令
            direct_action = f"在手机号输入框中精确输入: {phone} (系统指定)"

        # 如果包含验证码，直接指定数值
        elif "验证码" in action and "验证码" in important_values:
            code = important_values["验证码"]
            # 更直接的指令
            direct_action = f"在验证码输入框中精确输入: {code} (系统指定)"

        return direct_action

    def extract_important_values(self, actions: List[str]) -> Dict[str, str]:
        """
        从步骤操作中提取重要数值

        Args:
            actions: 操作列表

        Returns:
            重要值字典
        """
        values = {}

        for action in actions:
            # 提取手机号（中国手机号格式：1开头的11位数字）
            phone_pattern = r'1[3-9]\d{9}'
            phone_match = re.search(phone_pattern, action)
            if phone_match and '手机号' in action:
                values['手机号'] = phone_match.group()

            # 提取验证码（通常是4-6位数字）
            if '验证码' in action or '代码' in action:
                # 多种验证码匹配模式
                code_patterns = [
                    r'输入(\d{4,6})',       # 输入后面的数字
                    r'[（(](\d{4,6})[）)]',  # 括号中的数字
                    r'\b(\d{6})\b',         # 独立的6位数字
                    r'\b(\d{4,5})\b'        # 独立的4-5位数字
                ]

                for pattern in code_patterns:
                    code_match = re.search(pattern, action)
                    if code_match:
                        code_value = code_match.group(1) if code_match.groups() else code_match.group()
                        # 确保不是手机号的一部分
                        if len(code_value) <= 6 and code_value not in values.get('手机号', ''):
                            values['验证码'] = code_value
                            self.logger.info(f"检测到验证码: {code_value} (从操作中提取)")
                            break

        return values

    def extract_important_values_from_test_case(self, test_case: TestCase) -> Dict[str, str]:
        """
        从整个测试用例中提取重要数值

        Args:
            test_case: 测试用例

        Returns:
            重要值字典
        """
        values = {}

        # 从所有步骤中收集动作
        all_actions = []
        for step in test_case.steps:
            all_actions.extend(step.actions)

        for action in all_actions:
            # 提取手机号（中国手机号格式：1开头的11位数字）
            phone_pattern = r'1[3-9]\d{9}'
            phone_match = re.search(phone_pattern, action)
            if phone_match and '手机号' in action:
                values['手机号'] = phone_match.group()
                self.logger.info(f"从测试用例中提取到手机号: {phone_match.group()}")

            # 提取验证码（通常是4-6位数字）
            if '验证码' in action or '代码' in action:
                # 多种验证码匹配模式
                code_patterns = [
                    r'输入:(\d{4,6})',      # 输入:后面的数字
                    r'输入(\d{4,6})',       # 输入后面的数字
                    r'[（(](\d{4,6})[）)]',  # 括号中的数字
                    r'\b(\d{6})\b',         # 独立的6位数字
                    r'\b(\d{4,5})\b'        # 独立的4-5位数字
                ]

                for pattern in code_patterns:
                    code_match = re.search(pattern, action)
                    if code_match:
                        code_value = code_match.group(1) if code_match.groups() else code_match.group()
                        # 确保不是手机号的一部分
                        if len(code_value) <= 6 and code_value not in values.get('手机号', ''):
                            values['验证码'] = code_value
                            self.logger.info(f"从测试用例中提取到验证码: {code_value}")
                            break

        return values

    def extract_test_case_context(self, test_case: TestCase) -> Dict[str, Any]:
        """
        提取测试用例的上下文信息

        Args:
            test_case: 测试用例

        Returns:
            上下文信息字典
        """
        self.logger.info(f"开始从测试用例《{test_case.metadata.test_name}》提取上下文信息...")
        self.logger.info(f"测试用例共有 {len(test_case.steps)} 个步骤")

        context = {
            "important_values": self.extract_important_values_from_test_case(test_case),
            "step_relationships": {},
            "verification_codes": {},
            "credential_info": {},
            "urls": [],
            "form_fields": [],
            "sequences": []
        }

        # 提取URL信息
        self.logger.info(f"搜索测试步骤中的URL...")
        url_pattern = r'https?://[^\s()<>\[\]]+|www\.[^\s()<>\[\]]+'
        for step in test_case.steps:
            for action in step.actions:
                urls = re.findall(url_pattern, action)
                for url in urls:
                    # 清理URL，去掉可能的尾部标点
                    clean_url = re.sub(r'[.,;:?!]+$', '', url)
                    if clean_url not in context["urls"]:
                        context["urls"].append(clean_url)
                        self.logger.info(f"步骤{step.step_number} 发现URL: {clean_url}")

        # 提取表单字段信息
        form_field_pattern = r'(?:输入|填写|在)(.*?)(?:输入框|字段|栏)(?:中|里)(?:输入|填写)(.*?)(?:$|，|。)'
        for step in test_case.steps:
            for action in step.actions:
                matches = re.findall(form_field_pattern, action)
                for match in matches:
                    if len(match) >= 2:
                        field_name = match[0].strip()
                        field_value = match[1].strip()
                        if field_name and field_value and field_name != "验证码" and field_name != "手机号":
                            context["form_fields"].append(
                                {"field": field_name, "value": field_value, "step": step.step_number})
                            self.logger.info(f"步骤{step.step_number} 找到表单字段: {field_name} = {field_value}")

        # 检测多个验证码
        self.logger.info(f"检查是否有多个验证码...")
        code_pattern = r'验证码.*?(\d{4,6})'
        for i, step in enumerate(test_case.steps):
            for action in step.actions:
                matches = re.findall(code_pattern, action)
                for code in matches:
                    context["verification_codes"][f"步骤{step.step_number}"] = code
                    self.logger.info(f"步骤{step.step_number} 发现验证码: {code}")

        # 分析步骤之间的逻辑关系
        self.logger.info(f"分析步骤间的逻辑关系...")
        for i, step in enumerate(test_case.steps):
            # 如果不是最后一步，添加与下一步的关系
            if i < len(test_case.steps) - 1:
                next_step = test_case.steps[i+1]
                relationship = "继续执行"

                # 检查是否有条件跳转
                conditional_words = ["如果", "当", "若", "一旦", "假如"]
                if any(word in step.description or word in next_step.description for word in conditional_words):
                    relationship = "条件跳转"
                    self.logger.info(f"检测到条件跳转关系: 步骤{step.step_number} -> 步骤{next_step.step_number}")

                context["step_relationships"][f"{step.step_number}->{next_step.step_number}"] = relationship

        # 总结日志
        self.logger.info(
            f"上下文提取完成: {len(context['urls'])} 个URL, {len(context['form_fields'])} 个表单字段, {len(context['verification_codes'])} 个验证码")

        return context
