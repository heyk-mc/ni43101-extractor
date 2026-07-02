# 贡献指南

感谢你对 NI 43-101 资源量提取系统感兴趣！本文档提供贡献指南。

## 开发环境设置

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/ni43101-extractor.git
cd ni43101-extractor
```

### 2. 创建虚拟环境

```bash
# Python 3.10+
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

### 3. 安装开发依赖

```bash
pip install -e ".[dev]"

# 或使用 requirements.txt
pip install -r requirements.txt
```

### 4. 安装 pre-commit hooks

```bash
pre-commit install
```

## 代码规范

### 代码风格

- 遵循 [PEP 8](https://pep8.org/) 规范
- 使用 [Black](https://black.readthedocs.io/) 格式化代码
- 使用 [Ruff](https://docs.astral.sh/ruff/) 进行 lint 检查
- 使用类型注解（Type Hints）

### 运行代码检查

```bash
# Ruff 检查
ruff check .

# Black 格式化
black .

# Mypy 类型检查
mypy agents/ core/ eval/
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_pdf_parser.py -v

# 运行测试并生成覆盖率报告
pytest tests/ -v --cov=agents --cov=core --cov-report=html
```

## 提交指南

### Git 提交信息规范

```
feat: 添加新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式调整
refactor: 代码重构
test: 测试相关
chore: 构建/工具配置
```

### 提交流程

```bash
# 1. 创建功能分支
git checkout -b feature/your-feature

# 2. 开发并提交
git add .
git commit -m "feat: 添加新功能"

# 3. 推送并创建 PR
git push origin feature/your-feature
```

## Pull Request 指南

### PR 标题规范

```
feat: 添加 XX 功能
fix: 修复 XX bug
docs: 更新 XX 文档
```

### PR 描述模板

```markdown
## 变更说明
- 添加了 XX 功能
- 修复了 XX bug

## 测试计划
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试通过

## 相关 Issue
Fixes #123
```

## 发布流程

### 版本号规范

遵循 [Semantic Versioning](https://semver.org/)：

- `MAJOR.MINOR.PATCH`
- MAJOR: 不兼容的变更
- MINOR: 向后兼容的功能
- PATCH: 向后兼容的 bug 修复

### 发布步骤

1. 更新版本号（`pyproject.toml` 和 `__init__.py`）
2. 更新 CHANGELOG.md
3. 创建 Git tag
4. 发布 GitHub Release

## 问题反馈

遇到问题请提交 [Issue](https://github.com/your-username/ni43101-extractor/issues)。

### Issue 模板

```markdown
## 问题描述
简要描述遇到的问题

## 复现步骤
1. 第一步
2. 第二步
3. ...

## 预期行为
应该发生什么

## 实际行为
实际发生了什么

## 环境信息
- Python 版本：3.10
- 操作系统：Windows/Mac/Linux
- 相关日志：（如有）
```

## 许可证

本项目采用 MIT 许可证。提交代码即表示你同意将代码以 MIT 许可证发布。
