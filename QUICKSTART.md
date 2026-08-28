# Quick Start — Mirror · 镜身

## 1. 启动本地服务器

在 `Mirror-Lean` 仓库根目录运行：

```bash
python serve.py
```

> 如果 `8081` 被占用，可设置环境变量 `PORT=8082` 或在 `.env` 里指定 `PORT`。

### 配置语音 API key（可选）

`g1_23dof_coach.html` 左侧语音教练支持三种模式：

1. **浏览器语音**（默认，免费，使用系统语音）
2. **OpenAI TTS**（推荐，更像真人教练，需要 OpenAI key）
3. **most.ai TTS**（需要 most.ai key 且账户有余额）

把 key 写入仓库根目录的 `.env` 文件：

```bash
MOSTAI_API_KEY=your-mostai-key
OPENAI_API_KEY=your-openai-key
```

`.env` 已被加入 `.gitignore`，不会提交到 Git。

## 2. 打开前端页面

- **主入口 / PRD Hub：** `http://localhost:8081/frontend/index.html`
- **实时对标教练：** `http://localhost:8081/demos/g1_23dof_coach.html`
- **误差可视化报告：** `http://localhost:8081/error_detection/frontend/index.html`
- **算法说明：** `http://localhost:8081/error_detection/frontend/how-it-works.html`

## 3. 实时对标使用步骤

1. 打开 `demos/g1_23dof_coach.html`。
2. 在左侧列表选择一段 G1 参考视频（来自 `videos/`）。
3. 点击 **打开彩色摄像头**。
4. 等待 MediaPipe 模型加载完成。
5. 点击 **开始对标**。
6. 跟随 G1 视频做动作，右侧会实时显示：
   - 误差提示语音 / 文字
   - 12 点对齐骨架
   - 实时误差柱状图

## 4. 项目结构速览

```
Mirror-Lean/
├── frontend/index.html              # 主入口 / PRD Hub
├── demos/g1_23dof_coach.html        # 实时对标教练
├── error_detection/                 # 误差检测
│   ├── frontend/index.html          # 可视化报告
│   ├── frontend/how-it-works.html   # 算法说明
│   └── ...
├── videos/                          # 示例参考视频
├── docs/                            # PRD / TDD / 数据集调研
├── unitree-docs/                    # Unitree / VentureD 资料
└── lean-canvas/                     # Lean Canvas
```

## 5. 后端脚本（离线误差检测）

```bash
python -m error_detection.demo_scenarios
```

结果会输出到 `error_detection_output/demos/`。
