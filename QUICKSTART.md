# Quick Start — Mirror · 镜身

## 1. 启动本地服务器

在 `Mirror-Lean` 仓库根目录运行：

```bash
python -m http.server 8081
```

> 如果 `8081` 被占用，可换 `8082`、`8083` 等任意空闲端口。

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
