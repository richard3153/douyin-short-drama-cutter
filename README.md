# 短剧解说自动剪辑工具

> 纯本地运行 · 抖音短剧推广合规 · 批量处理 · 可视化 Web 界面

一套把整部短剧（多集/多视频）自动剪成符合抖音投放规范的短视频的本地流水线。
从字幕识别 → AI 解说生成 → 片段智能选取 → 本地 TTS 配音 → 调色/混音 →
合规预检，全程不依赖云端付费 API（ASR/TTS 均本地推理）。

---

## 功能特性

- **全自动流水线**：丢入原始短剧视频，自动产出成片，支持批量多部剧。
- **本地 ASR**：优先使用 `whisper.cpp`（Metal GPU 加速），回退 `faster-whisper`。
- **本地 TTS 解说**：优先 `ChatTTS`（每部剧确定性音色），回退 `edge-tts` / `gTTS`。
- **智能叙事编排**：基于字幕与（可选）视觉语义匹配选取高光片段，解说与画面对齐。
- **合规预检**：`compliance_checker.py` 6 维检测（AI 标识 / 内容安全 / 音频 / 文本 / 画质 / 元数据），不合规视频标记而非静默删除。
- **AI 内容声明**：片尾强制叠加「AI生成内容 / 本视频由AI辅助创作，仅供娱乐」免责卡，话题标签注入 `#AI生成#仅供娱乐`。
- **可视化界面**：标准库 `http.server` 提供 Web 工作站（端口 `8765`），自动打开浏览器。
- **画幅自适应**：自动检测原片比例，默认输出 9:16 竖屏，可强制 16:9 / 4:3 / 1:1。

---

## 系统架构

```
原始视频 (raw_videos/)
   │
   ├─[1] Whisper 字幕识别        → asr_whisper_cpp_wrapper.py
   ├─[2] LLM 解说脚本生成        → ai_short_video_cutter_pro.py（三层 Agent）
   ├─[3] 时间锚点选片段           → 字幕/视觉语义匹配
   ├─[4] ChatTTS 解说配音         → tts_chattts_wrapper.py
   ├─[5] 片段提取 + 调色          → ai_short_video_cutter_pro.py
   ├─[6] 拼接 + 混音（原声/解说/BGM）
   ├─[7] 片尾 AI 声明 + 话题标签
   └─[8] 合规预检 + 质量审计       → compliance_checker.py
                                    ↓
成品 (output_videos/*.mp4)
```

### 核心源码

| 文件 | 说明 |
|------|------|
| `ai_short_video_cutter_pro.py` | 主流程：识别→解说→选片→混音→合规的全链路编排 |
| `server.py` | 标准库 `http.server` Web 工作站（端口 8765），服务 `index.html` / `app.js` / `main.js` |
| `compliance_checker.py` | 6 维合规预检，输出每部剧合规报告 JSON |
| `tts_chattts_wrapper.py` | ChatTTS 封装（确定性种子音色 + edge-tts 兜底） |
| `asr_whisper_cpp_wrapper.py` | whisper.cpp 封装（Metal GPU，GGML 模型）+ faster-whisper 兜底 |
| `config_merger.py` | 三层配置优先级合并（默认 / `config.json` / `user_config.json`） |
| `jellyfish_studio.py` | 资产管理器（角色/场景/道具 + 多集连续性追踪） |
| `_lowbiz_detector.py` | 解说低俗/低质内容检测 |
| `index.html` / `app.js` / `main.js` | Web 可视化前端 |
| `config.json` / `user_config.json` | 运行配置（默认 / 用户覆盖） |
| `run.sh` / `run_gui.sh` | 命令行 / Web 界面启动脚本 |

> `assets/`、`bgm/`、`models/`、`music.db`、`.venv/` 等重资源与运行时目录不入库（见 `.gitignore`），需本地自备。

---

## 目录结构

```
.
├── ai_short_video_cutter_pro.py   # 主流程（识别→解说→选片→混音→合规）
├── server.py                      # Web 工作站（端口 8765）
├── compliance_checker.py          # 6 维合规预检
├── tts_chattts_wrapper.py         # ChatTTS 封装
├── asr_whisper_cpp_wrapper.py     # whisper.cpp 封装
├── config_merger.py               # 三层配置合并
├── jellyfish_studio.py            # 资产管理器
├── _lowbiz_detector.py            # 低俗内容检测
├── index.html / app.js / main.js  # Web 前端
├── config.json / user_config.json # 运行配置
├── run.sh / run_gui.sh            # 启动脚本
├── raw_videos/                    # 原始素材（占位，需自备）
├── bgm/                           # 背景音乐（占位，需自备）
├── output_videos/                 # 成品输出（占位）
├── narration/                     # 解说音频（占位）
├── subtitles/                     # 字幕（占位）
├── assets/                        # 运行时生成的资产元数据（占位）
├── fonts/                         # 字体（占位）
├── logs/                          # 运行日志（占位）
├── drama_memory/                  # 多集记忆（占位）
└── tmp_frames/                    # 临时帧（占位）
```

带「占位」的目录仅保留结构（内含 `.gitkeep`），**目录内实际文件不入库**，运行时由本地生成或需自备。
重资源 `.venv/`、`models/`、`whisper.cpp/`（本地大模型）不入库，请本地准备。

## 环境依赖

- **Python** 3.11+（推荐用 `uv` 管理虚拟环境）
- **FFmpeg**（需 `ffmpeg` / `ffprobe` 在 `PATH` 中）
- **本地大模型**（体积大，不入库，需自行下载到 `models/`）：
  - `ChatTTS` 模型（约 1.2 GB）
  - `whisper.cpp` 编译产物 + GGML `medium` 模型（约 1.4 GB，Metal GPU 加速）
  - `faster-whisper` 的 `small` / `medium` 模型（作为回退）
- **Python 第三方包**：`Pillow`、`pydub`、`moviepy`、`numpy`、`opencv-python`、`edge-tts`、`gTTS`（可选）、`torch`（ChatTTS / faster-whisper 需要）、`whisper.cpp` 相关依赖。

> 实际可用模块由代码运行时探测：`ChatTTS` 不可用则回退 `edge-tts`；`whisper.cpp` 不可用则回退 `faster-whisper`。

---

## 安装

```bash
# 1. 准备虚拟环境（以 uv 为例）
uv venv .venv
uv pip install pillow pydub moviepy numpy opencv-python edge-tts torch

# 2. 下载本地模型到 models/
#    ChatTTS  → models/ChatTTS/
#    whisper.cpp → 编译后产物；GGML medium 模型放到 models/
#    faster-whisper → 首次运行自动下载 small/medium

# 3. 准备素材目录
mkdir -p raw_videos bgm output_videos narration subtitles
```

---

## 使用方法

### 方式一：可视化界面（推荐）

```bash
bash run_gui.sh
```

浏览器自动打开 **http://localhost:8765**，在界面点击「开始剪辑」。

### 方式二：命令行

```bash
bash run.sh                      # 处理 raw_videos/ 下全部短剧
# 或指定单部剧
.venv/bin/python ai_short_video_cutter_pro.py
```

---

## 准备素材

```
raw_videos/    ← 放入原始短剧视频（MP4 / MOV）
bgm/           ← 无版权 BGM（MP3 / WAV）
output_videos/ ← 成品自动输出到这里
narration/     ← 自动生成的解说音频
subtitles/     ← 自动生成的字幕文件
```

---

## 输出规格（默认）

| 参数 | 值 |
|------|------|
| 画幅 | 9:16（竖屏，自动检测原片比例） |
| 时长 | 60 ~ 180 秒（可在 `CONFIG` 调整） |
| 帧率 | 30 fps |
| 音频 | AAC，解说音量 2.50 / BGM 0.15 |
| 字幕 | 白字黑边，底部居中 |
| AI 标识 | 片尾「AI生成内容 / 本视频由AI辅助创作，仅供娱乐」+ 话题标签 `#AI生成#仅供娱乐` |

---

## 可调参数

编辑 `ai_short_video_cutter_pro.py` 中的 `CONFIG` 字典：

```python
CONFIG = {
    "aspect_ratio": "auto",   # auto / 9:16 / 16:9 / 4:3 / 1:1
    "min_duration": 60,       # 成片最短时长(秒)
    "max_duration": 180,      # 成片最长时长(秒)
    "bgm_volume": 0.15,       # BGM 音量
    "narration_volume": 2.50, # 解说音量（ChatTTS 输出较轻需放大）
    "asr_model": "medium",    # whisper 识别精度
}
```

用户级覆盖写在 `user_config.json`（如 `{"selected_dramas": ["《剧名》"]}`），优先级高于 `config.json`。

---

## 合规说明

- **AI 内容标识**：片尾强制叠加 AI 生成声明卡，话题标签注入 `#AI生成#仅供娱乐`，满足平台 AI 内容标注要求。
- **不合规处理**：`compliance_checker.py` 检测到高风险内容时**标记文件名**（加「不合规」前缀）而非直接删除，便于人工复核。
- **敏感词**：内置敏感词/警告词库，生成解说时自动替换高危词。
- **免责声明**：成片底部含「本视频由AI辅助创作，仅供娱乐」。

---

## Ollama 本地大模型集成

解说脚本由本地部署的 **Ollama** 负责生成（不调用任何云端付费 LLM API）。

### 安装与启动

```bash
# 1. 安装 Ollama（https://ollama.com），确保本地服务已启动（默认监听 11434）
ollama serve          # 若未随系统自启

# 2. 拉取解说所用模型（当前默认 qwen3.5:4b）
ollama pull qwen3.5:4b
```

### 集成方式（代码层面）

- 统一调用函数 `_call_ollama_retry(prompt, agent_name, timeout=90, retries=2)`，向
  `http://localhost:11434/api/generate` 发送 POST 请求，请求体示例：

  ```json
  {
    "model": "qwen3.5:4b",
    "prompt": "<清洗后的提示词>",
    "stream": false,
    "think": false,
    "options": { "temperature": 0.5, "num_predict": 2000 }
  }
  ```

- **多 Agent 分工**：通过 `agent_name` 区分任务，例如 `narration_viral`（爆款解说生成）、
  `highlight_detection`（高光片段检测）、`bgm_selection`（BGM 匹配）、`narration_filler`（结尾填充语）等。
- **结构化输出**：需要 JSON 的场景（如高光检测、反同质化）使用 `"format": "json"` 引导生成。
- **重试与退避**：调用失败按指数退避重试（等待 3s / 6s），全部失败后返回 `None` 走兜底逻辑。
- **冷启动预热**：`server.py` 启动时调用 `warmup_ollama()`，先发一个极小请求把模型加载进显存，
  消除首次调用的冷启动延迟。

### 切换模型 / 调参

- 切换模型：修改 `_call_ollama_retry` 与 `warmup_ollama` 中的 `"model"` 字段
  （如 `qwen3.5:4b` → 其他已 `ollama pull` 的模型）。
- 调参：各 Agent 的 `temperature` / `num_predict` 由 `_get_llm_params(agent_name)` 控制，
  可按任务在源码中调整。

### 常见问题

- Ollama 未启动或 `11434` 不可达 → 解说生成失败，流水线会停止并提示，请先 `ollama serve`。
- 首次调用慢属正常（模型加载），服务启动后的预热可显著缓解。

## 技术栈

- 语言：**Python 3.11**
- Web：标准库 `http.server` + 原生 JS 前端（无框架依赖）
- 视频：`moviepy` + `opencv-python` + `FFmpeg`
- ASR：`whisper.cpp`（Metal GPU）/ `faster-whisper`
- TTS：`ChatTTS` / `edge-tts` / `gTTS`
- 解说脚本：本地 LLM（如 Ollama `qwen3.5`）

---

## 许可证

本项目仅供学习与个人创作使用。短视频素材、BGM、字体等请确保拥有相应授权；
生成内容须遵守各平台社区规范与 AI 内容标识相关规定。
