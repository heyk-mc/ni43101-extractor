# 24 小时完成时间表

## 时间轴概览

| 时间段 | 任务 | 状态 |
|--------|------|------|
| 第 1-2 小时 | 项目初始化 + 工程化配置 | ✅ 完成 |
| 第 3-5 小时 | PDF 解析模块 + 工具类 | ✅ 完成 |
| 第 6-9 小时 | Extractor Agent + CriticMaster Agent | ✅ 完成 |
| 第 10-12 小时 | Revise Loop + Evolution Log | ✅ 完成 |
| 第 13-14 小时 | 评测模块 + Ground Truth | ✅ 完成 |
| 第 15-16 小时 | 主入口 + CLI + 文档 | ✅ 完成 |
| 第 17-18 小时 | 单元测试 + CI/CD 配置 | ✅ 完成 |
| 第 19-20 小时 | 测试运行 + Bug 修复 | ⏳ 待完成 |
| 第 21-22 小时 | PDF 数据准备 + 端到端测试 | ⏳ 待完成 |
| 第 23-24 小时 | 最终检查 + GitHub 提交 | ⏳ 待完成 |

---

## 已完成工作

### 1. 项目结构 ✅

```
ni43101-extractor/
├── agents/              # Agent 实现
│   ├── extractor_agent.py
│   └── critic_master.py
├── core/                # 核心逻辑
│   ├── config.py
│   ├── logging_config.py
│   ├── path_utils.py
│   ├── pdf_parser.py
│   ├── revise_loop.py
│   └── evolution_log.py
├── eval/                # 评测模块
│   ├── metrics.py
│   └── ground_truth.json
├── tests/               # 单元测试
│   ├── test_*.py
│   └── conftest.py
├── .github/workflows/   # CI/CD
│   └── ci.yml
├── data/pdfs/           # PDF 文件目录
├── logs/                # 日志目录
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
├── requirements.txt
├── run.py
├── README.md
├── INSTALL.md
├── CONTRIBUTING.md
└── LICENSE
```

### 2. 工程化规范 ✅

| 规范 | 配置 | 状态 |
|------|------|------|
| 类型注解 | mypy 配置 | ✅ |
| Lint 检查 | ruff 配置 | ✅ |
| 格式化 | black 配置 | ✅ |
| 测试框架 | pytest 配置 | ✅ |
| CI/CD | GitHub Actions | ✅ |
| Pre-commit | hooks 配置 | ✅ |
| 依赖管理 | requirements.txt + pyproject.toml | ✅ |
| 环境变量 | .env.example | ✅ |
| 路径安全 | path_utils.py | ✅ |
| 日志系统 | logging_config.py | ✅ |

### 3. 核心功能 ✅

- [x] PDF 解析模块（pdfplumber + pypdf 兜底）
- [x] Extractor Agent（Claude 调用）
- [x] CriticMaster Agent（Qwen 评分）
- [x] Revise Loop（3 轮修订）
- [x] Evolution Log（自进化机制）
- [x] 评测模块（accuracy@5%）
- [x] CLI 主入口

### 4. 单元测试 ✅

- [x] test_pdf_parser.py
- [x] test_extractor.py
- [x] test_critic.py
- [x] test_revise_loop.py

---

## 待完成工作

### 立即执行（第 19-20 小时）

1. **运行单元测试验证**
   ```bash
   cd D:/ni43101-extractor
   .venv/Scripts/activate
   pip install -r requirements.txt
   pytest tests/ -v
   ```

2. **修复可能的 Bug**
   - 导入路径问题
   - 依赖缺失
   - API 调用问题

### 准备 PDF 数据（第 21-22 小时）

3. **下载真实 NI 43-101 PDF**
   - Newmont: https://www.newmont.com/investors/reports
   - Barrick: https://www.barrick.com/investors/reports/
   - Pilbara Minerals: https://www.pilbaraminerals.com.au/investors/reports/

4. **填写 ground_truth.json**
   - 手动或半自动提取 PDF 中的数据
   - 更新 `eval/ground_truth.json`

### 端到端测试（第 22-23 小时）

5. **运行完整流程**
   ```bash
   # 提取单个 PDF
   python run.py extract data/pdfs/sample.pdf -v -o output/result.json

   # 批量评测
   python run.py evaluate -o eval/report.txt
   ```

6. **检查输出**
   - 查看 logs/ 目录的日志
   - 查看 data/evolution.jsonl
   - 查看 eval/report.txt

### 最终检查（第 23-24 小时）

7. **GitHub 提交**
   ```bash
   git add .
   git commit -m "feat: complete NI 43-101 extraction system"
   git push origin main
   ```

8. **创建 Release**
   - Tag: v0.1.0
   - 说明：24 小时面试作业

---

## 检查清单

### 代码质量
- [ ] `ruff check .` 通过
- [ ] `black --check .` 通过
- [ ] `mypy .` 通过（允许部分忽略）

### 测试
- [ ] 所有单元测试通过
- [ ] 覆盖率报告生成
- [ ] 至少 1 个 PDF 端到端测试通过

### 文档
- [ ] README.md 完整
- [ ] INSTALL.md 清晰
- [ ] .env.example 配置完整

### GitHub
- [ ] 代码已推送
- [ ] Release 已创建
- [ ] 提交信息符合规范

---

## 风险与应对

| 风险 | 应对 |
|------|------|
| API 调用失败 | 使用 mock 测试，确保逻辑正确 |
| PDF 解析失败 | 提供多个 PDF，至少 1 个能解析 |
| 时间不足 | 优先保证核心功能，评测可简化 |
| Ground Truth 难获取 | 手动从 PDF 中提取关键字段 |

---

## 下一步行动

```bash
# 1. 安装依赖
cd D:/ni43101-extractor
.venv/Scripts/activate
pip install -r requirements.txt

# 2. 运行测试
pytest tests/ -v

# 3. 准备 PDF 文件
# 从矿业公司官网下载 NI 43-101 报告

# 4. 运行端到端测试
python run.py extract data/pdfs/sample.pdf -v
```
