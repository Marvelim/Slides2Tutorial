# Slides2Tutorial

Slides2Tutorial 是一个把 PDF 课件逐页转换为中文复习讲义的命令行工具。它会将每一页 PDF 渲染成截图，调用 OpenAI-compatible 的 Gemini 接口生成 Markdown + LaTeX 笔记，并保存可恢复的处理状态，适合把课程 slides 批量整理成复习资料。

## 功能特性

- 逐页读取 PDF，并把页面截图发送给视觉语言模型。
- 输出中文 Markdown 讲义，支持行内公式 `$...$` 和块级公式 `$$...$$`。
- 维护滚动上下文摘要，让长课件的前后概念保持连续。
- 生成 `state.jsonl`，中断后可继续处理已完成页面。
- 对上游拥塞、限流等临时错误自动等待并重试。
- 支持命令行参数、`.env` 文件和环境变量配置。

## 项目结构

```text
.
├── src/slides2tutorial/    # 核心 Python 包
├── tests/                  # 单元测试
├── run.sh                  # 一键创建本地环境并运行
├── environment.yml         # Conda 环境定义
├── pyproject.toml          # Python 包配置
├── .env.example            # 环境变量示例
├── slides/                 # 本地课件目录，默认不提交
└── output/                 # 生成结果目录，默认不提交
```

## 环境要求

- Python 3.10+
- Conda，或任意可安装 Python 包的虚拟环境
- 一个兼容 OpenAI Chat Completions API 的 Gemini 网关

## 安装

使用 Conda 创建项目本地环境：

```bash
conda env create -p ./.conda -f environment.yml
conda activate ./.conda
```

也可以安装到已有 Python 环境：

```bash
pip install -e ".[dev]"
```

## 配置

复制环境变量模板：

```bash
cp .env.example .env
```

然后填写本地 `.env`：

```bash
GEMINI_BASE_URL="https://your-openai-compatible-endpoint/v1"
GEMINI_API_KEY="your_api_key_here"
GEMINI_MODEL="gemini-3.1-pro"
```

`.env` 会被 Git 忽略；请只提交 `.env.example`，不要提交真实 API Key。

## 使用方法

最简单的运行方式：

```bash
./run.sh slides/input.pdf
```

`run.sh` 会优先使用项目里的 `./.conda` 环境；如果还没有安装，会自动根据 `environment.yml` 创建或补装依赖。

常用参数：

```bash
./run.sh slides/input.pdf --limit-pages 5
./run.sh slides/input.pdf --out output/cn-notes.md --dpi 220 --force
```

也可以直接使用 CLI：

```bash
slides2tutorial slides/input.pdf \
  --base-url "$GEMINI_BASE_URL" \
  --api-key "$GEMINI_API_KEY" \
  --model gemini-3.1-pro \
  --out output/tutorial.md
```

默认输出：

- `output/tutorial.md`：生成的中文讲义。
- `output/state.jsonl`：逐页处理状态，用于断点续跑。

如果想重新生成所有页面：

```bash
slides2tutorial slides/input.pdf --force
```

如果只想测试前几页：

```bash
slides2tutorial slides/input.pdf --limit-pages 3
```

## 开发

运行测试：

```bash
pytest
```

本项目的命令行入口定义在 `pyproject.toml`：

```toml
[project.scripts]
slides2tutorial = "slides2tutorial.cli:main"
```

主要模块：

- `src/slides2tutorial/cli.py`：命令行参数解析和配置读取。
- `src/slides2tutorial/generator.py`：PDF 逐页处理主流程。
- `src/slides2tutorial/client.py`：OpenAI-compatible 接口封装和重试逻辑。
- `src/slides2tutorial/prompts.py`：页面讲解和滚动摘要提示词。
- `src/slides2tutorial/state.py`：JSONL 状态和 Markdown 输出。
