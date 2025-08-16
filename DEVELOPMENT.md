# Yomitoku Client 开发文档

## 项目简介

Yomitoku Client 是一个Python客户端库，用于与Yomitoku API进行交互，实现文档解析、结果可视化和格式转换功能。

## 环境设置

### 系统要求
- Python 3.8+
- pip 或 conda
- Git

### 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd yomitoku-client
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

## 项目结构

```
yomitoku-client/
├── src/                    # 源代码目录
│   ├── __init__.py
│   ├── client.py          # 主客户端类
│   ├── api/               # API相关模块
│   ├── utils/             # 工具函数
│   └── exceptions.py      # 自定义异常
├── tests/                 # 测试代码
├── notebooks/             # Jupyter笔记本示例
├── docs/                  # 文档
├── requirements.txt       # Python依赖
├── setup.py              # 安装配置
├── README.md             # 项目说明
├── DEVELOPMENT.md        # 开发文档
└── .cursorrules          # Cursor AI配置
```

## 开发流程

### 1. 功能开发

1. 创建功能分支
```bash
git checkout -b feature/新功能名称
```

2. 实现功能代码
3. 编写测试
4. 更新文档
5. 提交代码
```bash
git add .
git commit -m "feat: 添加新功能描述"
```

### 2. 代码审查

- 所有代码必须通过代码审查
- 确保测试覆盖率达标
- 检查代码风格和文档完整性

### 3. 合并到主分支

```bash
git checkout main
git merge feature/新功能名称
```

## API开发指南

### 客户端类设计

```python
class YomitokuClient:
    """Yomitoku API客户端"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.yomitoku.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = aiohttp.ClientSession()
    
    async def analyze_document(self, file_path: str, options: dict = None) -> dict:
        """分析文档"""
        pass
    
    async def get_analysis_result(self, task_id: str) -> dict:
        """获取分析结果"""
        pass
    
    async def export_result(self, task_id: str, format: str) -> bytes:
        """导出结果"""
        pass
```

### 错误处理

```python
class YomitokuError(Exception):
    """Yomitoku API基础异常"""
    pass

class DocumentAnalysisError(YomitokuError):
    """文档分析错误"""
    pass

class APIError(YomitokuError):
    """API调用错误"""
    pass
```

## 测试指南

### 单元测试

```python
import pytest
from src.client import YomitokuClient

class TestYomitokuClient:
    def test_client_initialization(self):
        client = YomitokuClient("test_key")
        assert client.api_key == "test_key"
    
    @pytest.mark.asyncio
    async def test_analyze_document(self):
        # 测试文档分析功能
        pass
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_client.py

# 生成覆盖率报告
pytest --cov=src tests/
```

## 文档规范

### 代码文档

- 所有公共API必须有详细的文档字符串
- 使用Google风格的文档字符串格式
- 包含参数类型、返回值类型和异常说明

### 用户文档

- 提供完整的使用示例
- 包含常见问题解答
- 支持中文和日文

## 发布流程

### 版本管理

使用语义化版本控制：
- MAJOR.MINOR.PATCH
- 例如：1.0.0, 1.1.0, 1.1.1

### 发布步骤

1. 更新版本号
2. 更新CHANGELOG.md
3. 创建发布标签
4. 构建分发包
5. 上传到PyPI

## 贡献指南

### 提交规范

使用约定式提交：
- `feat:` 新功能
- `fix:` 修复bug
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建过程或辅助工具的变动

### 代码审查清单

- [ ] 代码符合项目规范
- [ ] 测试通过且覆盖率达标
- [ ] 文档已更新
- [ ] 没有引入新的依赖
- [ ] 错误处理完善

## 联系方式

- 问题反馈：GitHub Issues
- 技术支持：support-aws-marketplace@mlism.com
- 项目维护：项目维护者

## 许可证

本项目采用MIT许可证，详见LICENSE文件。
