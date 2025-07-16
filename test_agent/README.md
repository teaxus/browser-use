# Test Agent

一个基于 browser-use 的自动化测试智能体框架

## 项目简介

Test Agent 是一个完整的前端自动化测试解决方案，基于 browser-use 库构建。它通过 AI 驱动的自动化测试方法，能够智能地理解和执行 Markdown 格式的测试用例，提供错误处理、人工干预和详细报告生成功能。

## 快速链接

- [快速开始](#快速开始)
- [示例测试用例](/examples/simple_login_test.md)
- [高级测试用例](/examples/advanced_test_case.md)
- [详细配置示例](/examples/detailed_config.yaml)
- [CLI 命令参考](#cli-命令参考)
- [测试用例格式详解](#测试用例格式详解)
- [开发指南](#开发指南)

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

## 测试元数据

- 作者: Test Engineer
- 日期: 2025-07-16
- 优先级: 高

## 测试目标

验证用户能够使用手机号和验证码成功登录系统

## 测试步骤

### 步骤 1: 访问登录页面

- 打开浏览器访问 {{base_url}}
- 等待页面完全加载
- 点击导航栏中的"登录"按钮

期望结果: 成功进入登录页面，显示手机号和验证码输入框

### 步骤 2: 输入登录凭据

- 在手机号输入框中输入 {{credentials.phone}}
- 在验证码输入框中输入 {{credentials.code}}
- 点击"登录"按钮

期望结果: 登录成功，重定向到用户主页

### 步骤 3: 验证登录状态

- 检查页面是否显示用户信息
- 验证导航栏是否显示"我的账户"选项

期望结果: 页面顶部显示欢迎信息，导航栏包含用户专属选项
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

## 测试用例格式详解

Markdown 测试用例需要遵循特定格式，以便测试执行器能正确解析和执行。测试用例包含以下几个主要部分：

### 1. 测试标题

使用一级标题 (`#`) 定义测试用例的名称：

```markdown
# 登录功能测试
```

### 2. 测试元数据 (可选)

包含测试的基本信息，如作者、日期、优先级等：

```markdown
## 测试元数据

- 作者: Test Engineer
- 日期: 2025-07-16
- 优先级: 高
```

### 3. 测试目标

明确定义测试的整体目标，使用二级标题：

```markdown
## 测试目标

验证用户能够使用手机号和验证码成功登录系统
```

### 4. 测试步骤

使用三级标题 (`###`) 定义每个测试步骤，包含步骤编号和描述性标题：

```markdown
### 步骤 1: 访问登录页面
```

每个步骤下使用列表项 (`-`) 定义具体操作：

```markdown
- 打开浏览器访问 {{base_url}}
- 点击导航栏中的"登录"按钮
```

每个步骤后应定义期望结果：

```markdown
期望结果: 成功进入登录页面，显示手机号和验证码输入框
```

### 5. 环境变量使用

使用双大括号 `{{变量名}}` 引用配置文件中定义的环境变量：

- `{{base_url}}` - 从配置中获取基础 URL
- `{{credentials.phone}}` - 获取嵌套变量
- `{{custom_vars.timeout}}` - 获取自定义变量

### 完整示例

```markdown
# 新用户注册测试

## 测试元数据

- 作者: Test Team
- 版本: 1.0

## 测试目标

验证新用户可以成功注册并登录系统

## 测试步骤

### 步骤 1: 访问注册页面

- 打开浏览器访问 {{base_url}}/register
- 等待页面完全加载

期望结果: 注册页面成功加载，显示注册表单

### 步骤 2: 填写注册信息

- 在手机号字段输入 {{credentials.new_user.phone}}
- 点击"获取验证码"按钮
- 在验证码字段输入 {{credentials.new_user.code}}
- 勾选"同意服务条款"复选框
- 点击"注册"按钮

期望结果: 注册成功，显示成功提示

### 步骤 3: 验证注册结果

- 点击"立即登录"按钮
- 使用刚注册的手机号登录
- 验证是否进入用户主页

期望结果: 成功登录并显示新用户欢迎信息
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

## 测试执行器工作原理

Test Agent 使用 `TestExecutor` 类来执行测试用例，该类负责：

1. **解析 Markdown 测试用例** - 将 Markdown 文件转换为内部 `TestCase` 对象
2. **浏览器会话管理** - 创建和维护 Browser-Use 的浏览器会话
3. **执行测试步骤** - 按顺序执行每个测试步骤
4. **错误处理与重试** - 在失败时进行智能重试
5. **人工干预** - 在需要时请求人工介入
6. **截图和日志** - 记录测试执行过程

### 关键数据结构

测试用例在内部被解析为以下结构：

```python
class TestCase:
    metadata: TestMetadata  # 测试元数据
    objective: str          # 测试目标
    steps: List[TestStep]   # 测试步骤列表

class TestStep:
    step_number: int        # 步骤编号
    title: str              # 步骤标题
    actions: List[str]      # 动作列表
    expected_result: str    # 期望结果
```

### 示例

查看更复杂的测试用例示例：[高级测试用例示例](/examples/advanced_test_case.md)

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
