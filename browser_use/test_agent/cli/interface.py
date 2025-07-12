"""
Test Agent 命令行界面
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from browser_use.llm import ChatOpenAI

from ..core.agent import TestAgent, run_test_from_file
from ..config.settings import TestAgentSettings
from ..config.environment import EXAMPLE_CONFIG


def setup_logging(level: str = "INFO"):
    """设置日志"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def create_example_config(output_path: Path):
    """创建示例配置文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(EXAMPLE_CONFIG)
    print(f"示例配置文件已创建: {output_path}")


def create_example_test_case(output_path: Path):
    """创建示例测试用例"""
    from ..core.parser import EXAMPLE_TEST_CASE

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(EXAMPLE_TEST_CASE)
    print(f"示例测试用例已创建: {output_path}")


async def run_test_command(args):
    """执行测试命令"""

    # 设置日志
    setup_logging(args.log_level)

    # 检查测试文件
    test_file = Path(args.test_file)
    if not test_file.exists():
        print(f"错误: 测试文件不存在: {test_file}")
        return 1

    # 检查配置文件
    config_file = None
    if args.config:
        config_file = Path(args.config)
        if not config_file.exists():
            print(f"错误: 配置文件不存在: {config_file}")
            return 1

    # 创建LLM实例
    try:
        if args.base_url:
            llm = ChatOpenAI(
                model=args.model,
                base_url=args.base_url,
                api_key=args.api_key,
                temperature=args.temperature
            )
        else:
            llm = ChatOpenAI(
                model=args.model,
                api_key=args.api_key,
                temperature=args.temperature
            )
    except Exception as e:
        print(f"错误: 创建LLM实例失败: {e}")
        return 1

    # 创建设置
    settings = TestAgentSettings(
        max_retries=args.max_retries,
        timeout=args.timeout,
        use_vision=args.use_vision,
        headless=args.headless,
        save_screenshots=args.save_screenshots,
        report_format=args.report_format
    )

    # 设置输出目录
    output_dir = None
    if args.output:
        output_dir = Path(args.output)

    try:
        # 执行测试
        print(f"开始执行测试: {test_file}")
        print(f"使用模型: {args.model}")
        if args.environment:
            print(f"目标环境: {args.environment}")

        result = await run_test_from_file(
            test_file=test_file,
            llm=llm,
            config_file=config_file,
            environment=args.environment,
            output_dir=output_dir,
            settings=settings
        )

        # 输出结果
        print("\n" + "="*60)
        print("测试执行完成")
        print("="*60)
        print(f"测试名称: {result.test_name}")
        print(f"执行结果: {'✅ 成功' if result.success else '❌ 失败'}")
        print(f"总耗时: {result.total_time:.2f}秒")
        print(f"总步骤: {len(result.step_results)}")

        success_count = sum(1 for step in result.step_results if step.success)
        print(f"成功步骤: {success_count}")
        print(f"失败步骤: {len(result.step_results) - success_count}")

        if result.final_message:
            print(f"最终消息: {result.final_message}")

        # 显示报告路径
        if output_dir and output_dir.exists():
            print(f"\n报告输出目录: {output_dir}")

            report_files = []
            if (output_dir / "test_report.html").exists():
                report_files.append("test_report.html")
            if (output_dir / "test_report.json").exists():
                report_files.append("test_report.json")

            if report_files:
                print(f"生成的报告文件: {', '.join(report_files)}")

        return 0 if result.success else 1

    except Exception as e:
        print(f"测试执行失败: {e}")
        return 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Test Agent - 基于browser-use的自动化测试智能体",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 运行测试用例
  python -m browser_use.test_agent.cli run test_case.md --config config.yaml

  # 指定环境运行测试
  python -m browser_use.test_agent.cli run test_case.md --config config.yaml --environment prod

  # 使用自定义模型和设置
  python -m browser_use.test_agent.cli run test_case.md \\
    --model gpt-4o --api-key sk-xxx \\
    --max-retries 5 --timeout 600

  # 生成示例文件
  python -m browser_use.test_agent.cli init
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # run 命令
    run_parser = subparsers.add_parser('run', help='执行测试用例')
    run_parser.add_argument('test_file', help='测试用例文件路径')
    run_parser.add_argument('--config', '-c', help='环境配置文件路径')
    run_parser.add_argument('--environment', '-e', help='指定运行环境')
    run_parser.add_argument('--output', '-o', help='输出目录')

    # LLM 设置
    run_parser.add_argument('--model', default='gpt-4o-mini', help='模型名称 (默认: gpt-4o-mini)')
    run_parser.add_argument('--api-key', help='API密钥')
    run_parser.add_argument('--base-url', help='API基础URL')
    run_parser.add_argument('--temperature', type=float, default=0.1, help='温度参数 (默认: 0.1)')

    # 测试设置
    run_parser.add_argument('--max-retries', type=int, default=3, help='最大重试次数 (默认: 3)')
    run_parser.add_argument('--timeout', type=int, default=300, help='总超时时间秒数 (默认: 300)')
    run_parser.add_argument('--use-vision', action='store_true', default=True, help='启用视觉识别')
    run_parser.add_argument('--no-vision', dest='use_vision', action='store_false', help='禁用视觉识别')
    run_parser.add_argument('--headless', action='store_true', help='无头模式运行')
    run_parser.add_argument('--no-screenshots', dest='save_screenshots',
                            action='store_false', default=True, help='不保存截图')
    run_parser.add_argument('--report-format', choices=['html', 'json'], default='html', help='报告格式 (默认: html)')

    # 日志设置
    run_parser.add_argument(
        '--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO', help='日志级别 (默认: INFO)')

    # init 命令
    init_parser = subparsers.add_parser('init', help='初始化示例文件')
    init_parser.add_argument('--config-file', default='test_agent_config.yaml',
                             help='配置文件名 (默认: test_agent_config.yaml)')
    init_parser.add_argument('--test-file', default='example_test_case.md', help='测试用例文件名 (默认: example_test_case.md)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == 'run':
        return asyncio.run(run_test_command(args))

    elif args.command == 'init':
        print("初始化Test Agent示例文件...")

        # 创建示例配置文件
        config_path = Path(args.config_file)
        if config_path.exists():
            print(f"配置文件已存在: {config_path}")
        else:
            create_example_config(config_path)

        # 创建示例测试用例
        test_path = Path(args.test_file)
        if test_path.exists():
            print(f"测试用例文件已存在: {test_path}")
        else:
            create_example_test_case(test_path)

        print("\n初始化完成！")
        print(f"现在你可以运行: python -m browser_use.test_agent.cli run {args.test_file} --config {args.config_file}")

        return 0


if __name__ == '__main__':
    sys.exit(main())
