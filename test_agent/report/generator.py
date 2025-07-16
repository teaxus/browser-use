"""
测试报告生成器
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from ..core.parser import TestCase
from ..core.executor import TestExecutionResult, StepResult


class TestReportGenerator:
    """测试报告生成器"""

    def __init__(
        self,
        save_screenshots: bool = True,
        save_conversation_history: bool = True
    ):
        self.save_screenshots = save_screenshots
        self.save_conversation_history = save_conversation_history

    async def generate_html_report(
        self,
        test_case: TestCase,
        result: TestExecutionResult,
        output_dir: Path
    ) -> Path:
        """生成HTML测试报告"""

        # 首先生成JSON数据
        json_data = await self._generate_report_data(test_case, result)

        # 生成HTML报告
        html_content = self._generate_html_content(json_data)

        # 保存HTML文件
        html_file = output_dir / "test_report.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return html_file

    async def generate_json_report(
        self,
        test_case: TestCase,
        result: TestExecutionResult,
        output_dir: Path
    ) -> Path:
        """生成JSON测试报告数据"""

        # 生成报告数据
        json_data = await self._generate_report_data(test_case, result)

        # 保存JSON文件
        json_file = output_dir / "test_report.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)

        return json_file

    async def _generate_report_data(
        self,
        test_case: TestCase,
        result: TestExecutionResult
    ) -> Dict[str, Any]:
        """生成报告数据"""

        return {
            "report_info": {
                "generated_at": datetime.now().isoformat(),
                "generator_version": "1.0.0"
            },
            "test_case": {
                "name": test_case.metadata.test_name,
                "environment": test_case.metadata.environment,
                "timeout": test_case.metadata.timeout,
                "retry_count": test_case.metadata.retry_count,
                "objective": test_case.objective,
                "expected_results": test_case.expected_results,
                "total_steps": len(test_case.steps),
                "original_content": test_case.original_content,
                "processed_content": test_case.processed_content
            },
            "execution_result": {
                "success": result.success,
                "total_time": result.total_time,
                "final_message": result.final_message,
                "step_results": self._format_step_results(result.step_results),
                "summary": self._generate_execution_summary(result)
            },
            "conversation_history": result.conversation_history if self.save_conversation_history else None,
            "screenshots": self._collect_screenshot_info(result) if self.save_screenshots else None
        }

    def _format_step_results(self, step_results: list[StepResult]) -> list[Dict[str, Any]]:
        """格式化步骤结果"""
        formatted_results = []

        for step_result in step_results:
            formatted_result = {
                "step_number": step_result.step_number,
                "success": step_result.success,
                "execution_time": step_result.execution_time,
                "error_message": step_result.error_message,
                "screenshot_path": step_result.screenshot_path,
                "intervention_used": step_result.intervention_used,
                "intervention_details": step_result.intervention_details,
                "agent_output": step_result.agent_output
            }
            formatted_results.append(formatted_result)

        return formatted_results

    def _generate_execution_summary(self, result: TestExecutionResult) -> Dict[str, Any]:
        """生成执行摘要"""
        total_steps = len(result.step_results)
        successful_steps = sum(1 for step in result.step_results if step.success)
        failed_steps = total_steps - successful_steps

        intervention_count = sum(1 for step in result.step_results if step.intervention_used)

        return {
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "success_rate": f"{(successful_steps / total_steps * 100):.1f}%" if total_steps > 0 else "0%",
            "intervention_count": intervention_count,
            "average_step_time": sum(step.execution_time for step in result.step_results) / total_steps if total_steps > 0 else 0
        }

    def _collect_screenshot_info(self, result: TestExecutionResult) -> Optional[Dict[str, Any]]:
        """收集截图信息"""
        if not result.screenshots_dir or not result.screenshots_dir.exists():
            return None

        screenshots = []
        for step_result in result.step_results:
            if step_result.screenshot_path and Path(step_result.screenshot_path).exists():
                screenshots.append({
                    "step_number": step_result.step_number,
                    "path": step_result.screenshot_path,
                    "type": "error" if not step_result.success else "success"
                })

        return {
            "directory": str(result.screenshots_dir),
            "count": len(screenshots),
            "screenshots": screenshots
        }

    def _generate_html_content(self, data: Dict[str, Any]) -> str:
        """生成HTML报告内容"""

        # 基础HTML模板
        html_template = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Agent 测试报告 - {test_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header .subtitle {{
            opacity: 0.9;
            margin-top: 10px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 15px;
        }}
        .status-success {{
            background-color: #4CAF50;
            color: white;
        }}
        .status-failure {{
            background-color: #f44336;
            color: white;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #667eea;
            font-size: 1.1em;
        }}
        .summary-card .value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #333;
        }}
        .steps-container {{
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }}
        .step {{
            border-bottom: 1px solid #eee;
            transition: background-color 0.2s;
        }}
        .step:last-child {{
            border-bottom: none;
        }}
        .step-header {{
            padding: 15px 20px;
            background-color: #f8f9fa;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .step-header:hover {{
            background-color: #e9ecef;
        }}
        .step-title {{
            font-weight: bold;
            color: #333;
        }}
        .step-status {{
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .step-success {{
            background-color: #d4edda;
            color: #155724;
        }}
        .step-failure {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .step-details {{
            padding: 20px;
            background-color: white;
            display: none;
        }}
        .step-details.active {{
            display: block;
        }}
        .detail-item {{
            margin-bottom: 15px;
        }}
        .detail-label {{
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        .detail-value {{
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            border-left: 3px solid #667eea;
        }}
        .screenshot {{
            max-width: 100%;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .json-data {{
            background-color: #2d3748;
            color: #e2e8f0;
            padding: 20px;
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
            overflow-x: auto;
            max-height: 500px;
            overflow-y: auto;
        }}
        .expandable {{
            cursor: pointer;
            user-select: none;
        }}
        .expandable:hover {{
            background-color: #e9ecef;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            background-color: #f8f9fa;
            color: #666;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Test Agent 测试报告</h1>
            <div class="subtitle">{test_name}</div>
            <div class="status-badge status-{status_class}">{status_text}</div>
            <div style="margin-top: 15px; opacity: 0.8;">
                <div>总耗时: {total_time:.2f}秒</div>
                <div>生成时间: {generated_at}</div>
            </div>
        </div>
        
        <div class="content">
            <!-- 执行摘要 -->
            <div class="section">
                <h2>📊 执行摘要</h2>
                <div class="summary-grid">
                    <div class="summary-card">
                        <h3>总步骤数</h3>
                        <div class="value">{total_steps}</div>
                    </div>
                    <div class="summary-card">
                        <h3>成功步骤</h3>
                        <div class="value" style="color: #4CAF50;">{successful_steps}</div>
                    </div>
                    <div class="summary-card">
                        <h3>失败步骤</h3>
                        <div class="value" style="color: #f44336;">{failed_steps}</div>
                    </div>
                    <div class="summary-card">
                        <h3>成功率</h3>
                        <div class="value">{success_rate}</div>
                    </div>
                    <div class="summary-card">
                        <h3>人工干预次数</h3>
                        <div class="value">{intervention_count}</div>
                    </div>
                    <div class="summary-card">
                        <h3>平均步骤时间</h3>
                        <div class="value">{avg_step_time:.1f}s</div>
                    </div>
                </div>
            </div>
            
            <!-- 测试目标 -->
            <div class="section">
                <h2>🎯 测试目标</h2>
                <div class="detail-value">{objective}</div>
            </div>
            
            <!-- 步骤详情 -->
            <div class="section">
                <h2>📋 步骤执行详情</h2>
                <div class="steps-container">
                    {steps_html}
                </div>
            </div>
            
            <!-- 原始数据 -->
            <div class="section">
                <h2 class="expandable" onclick="toggleSection('json-section')">📄 原始数据 (点击展开)</h2>
                <div id="json-section" style="display: none;">
                    <div class="json-data">
                        <pre id="json-content"></pre>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            Generated by Test Agent v1.0.0 | Browser Use Framework
        </div>
    </div>
    
    <script>
        // 存储报告数据
        const reportData = {json_data};
        
        // 显示JSON数据
        document.getElementById('json-content').textContent = JSON.stringify(reportData, null, 2);
        
        // 切换步骤详情显示
        function toggleStep(stepNumber) {{
            const details = document.getElementById('step-details-' + stepNumber);
            if (details.classList.contains('active')) {{
                details.classList.remove('active');
            }} else {{
                details.classList.add('active');
            }}
        }}
        
        // 切换区域显示
        function toggleSection(sectionId) {{
            const section = document.getElementById(sectionId);
            if (section.style.display === 'none') {{
                section.style.display = 'block';
            }} else {{
                section.style.display = 'none';
            }}
        }}
    </script>
</body>
</html>
        '''

        # 格式化数据
        test_case_data = data['test_case']
        execution_data = data['execution_result']
        summary_data = execution_data['summary']

        # 生成步骤HTML
        steps_html = self._generate_steps_html(execution_data['step_results'])

        # 替换模板变量
        return html_template.format(
            test_name=test_case_data['name'],
            status_class='success' if execution_data['success'] else 'failure',
            status_text='✅ 测试通过' if execution_data['success'] else '❌ 测试失败',
            total_time=execution_data['total_time'],
            generated_at=data['report_info']['generated_at'],
            total_steps=summary_data['total_steps'],
            successful_steps=summary_data['successful_steps'],
            failed_steps=summary_data['failed_steps'],
            success_rate=summary_data['success_rate'],
            intervention_count=summary_data['intervention_count'],
            avg_step_time=summary_data['average_step_time'],
            objective=test_case_data['objective'],
            steps_html=steps_html,
            json_data=json.dumps(data, ensure_ascii=False, default=str)
        )

    def _generate_steps_html(self, step_results: list[Dict[str, Any]]) -> str:
        """生成步骤HTML"""
        steps_html = []

        for step in step_results:
            step_number = step['step_number']
            success = step['success']
            status_class = 'step-success' if success else 'step-failure'
            status_text = '✅ 成功' if success else '❌ 失败'

            # 构建详情内容
            details_items = []

            if step['execution_time']:
                details_items.append(f'''
                    <div class="detail-item">
                        <div class="detail-label">执行时间</div>
                        <div class="detail-value">{step['execution_time']:.2f}秒</div>
                    </div>
                ''')

            if step['error_message']:
                details_items.append(f'''
                    <div class="detail-item">
                        <div class="detail-label">错误信息</div>
                        <div class="detail-value" style="border-left-color: #f44336;">{step['error_message']}</div>
                    </div>
                ''')

            if step['intervention_used']:
                details_items.append(f'''
                    <div class="detail-item">
                        <div class="detail-label">人工干预</div>
                        <div class="detail-value" style="border-left-color: #ff9800;">
                            已使用人工干预<br>
                            详情: {step.get('intervention_details', '无详情')}
                        </div>
                    </div>
                ''')

            if step['screenshot_path']:
                details_items.append(f'''
                    <div class="detail-item">
                        <div class="detail-label">截图</div>
                        <div class="detail-value">
                            <img src="{step['screenshot_path']}" alt="步骤截图" class="screenshot" loading="lazy">
                        </div>
                    </div>
                ''')

            if step['agent_output']:
                details_items.append(f'''
                    <div class="detail-item">
                        <div class="detail-label">Agent输出</div>
                        <div class="detail-value">{step['agent_output']}</div>
                    </div>
                ''')

            step_html = f'''
                <div class="step">
                    <div class="step-header" onclick="toggleStep({step_number})">
                        <div class="step-title">步骤 {step_number}</div>
                        <div class="step-status {status_class}">{status_text}</div>
                    </div>
                    <div id="step-details-{step_number}" class="step-details">
                        {''.join(details_items)}
                    </div>
                </div>
            '''

            steps_html.append(step_html)

        return ''.join(steps_html)
