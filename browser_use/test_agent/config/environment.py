"""
环境配置管理
"""
import re
import yaml
from typing import Dict, Any, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field


class CredentialsConfig(BaseModel):
    """登录凭据配置"""
    phone: Optional[str] = None
    code: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None


class SingleEnvironmentConfig(BaseModel):
    """单个环境配置"""
    base_url: str
    admin_url: Optional[str] = None
    api_url: Optional[str] = None
    credentials: CredentialsConfig = Field(default_factory=CredentialsConfig)
    custom_vars: Dict[str, Any] = Field(default_factory=dict)


class EnvironmentConfig(BaseModel):
    """环境配置管理器"""

    environments: Dict[str, SingleEnvironmentConfig]
    default_environment: str = "test"

    @classmethod
    def from_yaml(cls, config_path: Union[str, Path]) -> 'EnvironmentConfig':
        """从YAML文件加载配置"""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return cls(**data)

    def get_environment(self, env_name: Optional[str] = None) -> SingleEnvironmentConfig:
        """获取指定环境配置"""
        env_name = env_name or self.default_environment
        if env_name not in self.environments:
            raise ValueError(f"环境配置不存在: {env_name}")
        return self.environments[env_name]

    def to_template_vars(self, env_name: Optional[str] = None) -> Dict[str, Any]:
        """转换为模板变量字典"""
        env_config = self.get_environment(env_name)

        # 扁平化配置
        vars_dict: Dict[str, Any] = {
            'base_url': env_config.base_url,
            'environment': env_name or self.default_environment
        }

        # 添加可选URL
        if env_config.admin_url:
            vars_dict['admin_url'] = env_config.admin_url
        if env_config.api_url:
            vars_dict['api_url'] = env_config.api_url

        # 添加凭据（使用嵌套结构）
        vars_dict['credentials'] = env_config.credentials.dict(exclude_none=True)

        # 添加自定义变量
        vars_dict.update(env_config.custom_vars)

        return vars_dict


class TemplateEngine:
    """模板变量替换引擎"""

    def __init__(self, environment_vars: Dict[str, Any]):
        self.env_vars = environment_vars

    def replace_variables(self, content: str) -> str:
        """替换内容中的变量"""
        def replacer(match):
            var_path = match.group(1)
            try:
                return str(self._get_nested_value(self.env_vars, var_path))
            except (KeyError, TypeError) as e:
                raise ValueError(f"模板变量 '${{{var_path}}}' 未找到或无效: {e}")

        # 替换 ${variable} 格式的变量
        return re.sub(r'\$\{([^}]+)\}', replacer, content)

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """获取嵌套路径的值"""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value[key]
            else:
                raise TypeError(f"无法在非字典对象中访问键: {key}")
        return value


# 示例配置文件内容
EXAMPLE_CONFIG = """
environments:
  test:
    base_url: "https://test.kanghehealth.com"
    admin_url: "https://test-admin.kanghehealth.com"
    api_url: "https://test-api.kanghehealth.com"
    credentials:
      phone: "18682025716"
      code: "250410"
    custom_vars:
      debug_mode: true
      timeout: 30
      
  prod:
    base_url: "https://devcloud.kanghehealth.com"
    admin_url: "https://admin.kanghehealth.com"
    api_url: "https://api.kanghehealth.com"
    credentials:
      phone: "prod_phone"
      code: "prod_code"
    custom_vars:
      debug_mode: false
      timeout: 60

default_environment: "test"
"""
