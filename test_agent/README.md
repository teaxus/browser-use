# Test Agent

一个基于 browser-use 的自动化测试智能体框架

## 项目简介

Test Agent 是一个完整的前端自动化测试解决方案，基于 browser-use 库构建。它支持通过 Markdown 格式编写测试用例，提供智能的错误处理和人工干预机制，并生成详细的测试报告。

## 主要特性

- ✅ **Markdown 格式测试用例** - 使用简单直观的格式定义测试步骤
- ✅ **环境变量模板替换** - 轻松配置不同环境的测试参数
- ✅ **人工干预机制** - 在关键步骤允许人工介入和调整
- ✅ **智能错误重试** - 自动处理临时性错误
- ✅ **详细测试报告** - 完整记录测试过程和结果
- ✅ **WebSocket 接口支持** - 实时监控测试执行状态
- ✅ **灵活的超时控制** - 支持长时间运行的测试步骤（最长 600 秒）

## 安装

确保已安装 browser-use 库：

```bash
pip install browser-use
```

然后克隆本仓库：

```bash
git clone https://github.com/yourusername/test_agent.git
cd test_agent
```

## 快速开始

### 基本用法

1. 创建 Markdown 测试用例文件：

```markdown
# 登录测试

## 测试步骤

1. 打开浏览器访问 {{base_url}}
2. 点击登录按钮
3. 在手机号输入框中输入 {{credentials.phone}}
4. 在验证码输入框中输入 {{credentials.code}}
5. 点击登录按钮
6. 验证是否成功登录到主页
```

2. 创建配置文件 `test_agent_config.yaml`：

```yaml
environments:
  test:
    base_url: "https://test.example.com"
    credentials:
      phone: "18600000000"
      code: "123456"
    custom_vars:
      debug_mode: true
      timeout: 60000
      step_timeout: 600 # 10分钟，合理的步骤超时时间

  prod:
    base_url: "https://prod.example.com"
    credentials:
      phone: "prod_phone"
      code: "prod_code"
    custom_vars:
      debug_mode: false
      timeout: 60000

default_environment: "test"

# LLM 配置
llm_config:
  provider: "openai"
  model: "gpt-4"
  api_key: "${OPENAI_API_KEY}"
  temperature: 0.1
```

3. 运行测试：

```bash
python -m test_agent.cli.interface run your_test_case.md --config test_agent_config.yaml
```

## CLI 命令参考

Test Agent 提供了多种命令行选项，以下是常用命令：

### 运行测试用例

```bash
# 基本用法
python -m test_agent.cli.interface run test_chat.md --config test_agent_config.yaml

# 指定环境
python -m test_agent.cli.interface run test_chat.md --config test_agent_config.yaml --env prod

# 启用调试模式
python -m test_agent.cli.interface run test_chat.md --config test_agent_config.yaml --debug
```

### 创建配置文件

```bash
# 生成默认配置模板
python -m test_agent.cli.interface init-config

# 指定配置文件路径
python -m test_agent.cli.interface init-config --output my_config.yaml
```

### 查看帮助信息

```bash
# 显示所有可用命令
python -m test_agent.cli.interface --help

# 显示特定命令的帮助
python -m test_agent.cli.interface run --help
```

### 高级配置

Test Agent 支持多种高级配置选项，包括：

- 错误重试策略
- 截图和视频记录
- 自定义 WebDriver 选项
- 自定义 LLM 提供商
- 测试报告格式

详细配置请参考 `docs` 目录中的文档。

## 项目结构

```
test_agent/
├── __init__.py         # 包定义和导出
├── __main__.py         # 入口点
├── cli/                # 命令行接口
├── config/             # 配置管理
├── core/               # 核心功能
│   ├── agent.py        # 测试代理主类
│   ├── executor.py     # 测试执行器
│   ├── parser.py       # Markdown 解析器
│   └── intervention.py # 人工干预处理
├── report/             # 测试报告生成
└── utils/              # 工具函数
```

## 开发指南

### 开发环境设置

1. 创建虚拟环境：

```bash
python -m venv venv
source venv/bin/activate  # Windows 使用 venv\Scripts\activate
```

2. 安装开发依赖：

```bash
pip install -e ".[dev]"
```

### 核心开发原则

1. **模块化设计** - 每个功能独立封装
2. **异步优先** - 所有 I/O 操作使用 async/await
3. **错误处理** - 完善的异常捕获和恢复
4. **可观测性** - 详细的日志和遥测
5. **可扩展性** - 支持插件和自定义动作

## 已知问题与解决方案

### 1. 超时问题 ✅ 已解决

- **问题**: 30 秒超时导致代理中断
- **解决**: 增加到 600 秒，支持复杂操作

### 2. 浏览器会话管理 ✅ 已解决

- **问题**: 人工干预后浏览器退出
- **解决**: 优化会话生命周期管理

### 3. 页面识别 🔧 持续优化

- **问题**: 页面跳转后识别为空白
- **解决**: 增强 DOM 解析和状态检测

## 贡献指南

欢迎提交 Pull Request 和 Issue 来帮助改进项目。在提交代码前，请确保：

1. 添加适当的测试用例
2. 遵循项目的代码风格
3. 更新相关文档

## 许可证

本项目使用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件
