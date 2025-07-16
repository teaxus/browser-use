# Test Agent 项目概览与开发指南

## 项目简介

Test Agent 是一个基于 Browser-Use 构建的测试自动化框架，专注于提供智能网页测试、交互自动化和前端质量保障。该项目利用 Browser-Use 的浏览器自动化能力和多种 LLM 模型，提供了完整的测试执行、报告生成和人工干预等功能。

## 核心功能模块

### 测试代理框架 (Test Agent) ⭐ 现处于独立项目

- **位置**: `test_agent/`
- **状态**: 🚧 开发中，已解决关键问题
- **核心组件**:
  - `core/executor.py` - 测试执行器
  - `core/intervention.py` - 人工干预处理
  - `cli/interface.py` - 命令行接口
- **功能**:
  - 自动化前端测试
  - 人工干预支持
  - YAML 配置管理
  - 超时控制 (已优化至 600 秒)

## 当前开发进度

### ✅ 已完成功能

1. **测试执行器** - 稳定运行
2. **人工干预机制** - 完整实现
3. **多 LLM 支持** - 广泛兼容
4. **Markdown 解析系统** - 高效准确
5. **报告生成系统** - 支持详细测试记录
6. **环境变量模板** - 灵活配置管理

### 🔧 最近修复的问题

1. **超时问题** - 将步骤超时从 30 秒优化至 600 秒
2. **浏览器会话管理** - 修复退出问题
3. **错误报告** - 增强错误信息详细度
4. **内存监控** - 优化资源使用

### 🚧 正在开发

1. **测试代理稳定性** - 完善错误处理
2. **性能优化** - 减少响应时间
3. **扩展功能** - 新的交互能力

### 📋 待开发功能

1. **批量测试支持**
2. **测试报告生成**
3. **集成测试框架**
4. **可视化测试界面**

### 环境配置

```yaml
# test_agent_config.yaml 示例
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

llm_config:
  provider: "openai"
  model: "qwen-vl-max"
  base_url: "https://yunwu.zeabur.app/v1"
  api_key: "${OPENAI_API_KEY}"

timeout: 600 # 10 分钟超时
max_steps: 20
use_vision: true
```

### CLI 使用

```bash
# 运行测试用例
python -m test_agent.cli.interface run test_chat.md --config test_agent_config.yaml

# 创建示例配置文件
python -m test_agent.cli.interface init-config
```

## 开发指南

### 核心原则

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

### 支持渠道

- GitHub Issues
- 技术文档
- 示例代码
- 社区讨论

## 未来路线图

**注意**: 此文档基于当前开发状态生成，随着项目发展会持续更新。开发者在使用前请确认最新版本的功能和 API。
