# Mirror · 镜身 (Embodied Motion Coach)

> The robot doesn't move for you — it teaches your body.
> 机器人不是替你运动，而是教会你的身体。

**Mirror · 镜身** 将人形机器人（Unitree G1）从「代替人类干活」（Robot Task Loop）转向「教会人类身体」（**Human Capability Loop**）：机器人实时复刻用户动作（Mistake Mirroring）、高亮差异、渐变演示修正姿态（Motion Morphing），最终让**用户**获得身体技能。

- 背景：VentureD Hackathon 2026 · 杭州 · Track 02 Physical AI（Unitree G1）

## Human Capability Loop

```
人不会 → Robot observes → Robot understands → Robot demonstrates → Human learns → 人会了
```

## 仓库内容

| 文件 | 说明 |
| --- | --- |
| [docs/PRD.md](docs/PRD.md) | 产品文档：问题/洞察/UVP/用户与场景/功能 P0-P2/指标/商业模式/护城河/风险/路线图 |
| [docs/TDD.md](docs/TDD.md) | 技术实现文档 v1.1：架构分层/选型（组件已全部核实）/模块设计/unitree_sdk2 集成/延迟预算/安全设计/60 秒 Demo 分镜/人力排期 |
| [docs/dataset-survey.md](docs/dataset-survey.md) | G1 训练数据集选型调研（2026-08-27 全部线上核实） |
| [lean-canvas/index.html](lean-canvas/index.html) | Lean Canvas（浏览器打开即可预览） |

## 可行数据集与组件清单（全部已核实，2026-08-27）

### 训练数据集

| 数据集 | 规模 | G1 支持 | License | 用途 |
| --- | --- | --- | --- | --- |
| [BONES-SEED](https://huggingface.co/datasets/bones-studio/seed) | 142,220 条动作 / ~288h / 522 人 | ✅ Unitree G1 CSV（MuJoCo 兼容），G1 轨迹由 soma-retargeter 生成 | 以仓库 LICENSE.md 为准（商用前确认） | **首选**：标准动作库 B 冷启动 + 策略训练语料；含舞蹈 11k / 体育 4k / 武术特技 2k 类别 |
| [AMASS](https://amass.is.tue.mpg.de/) | 40+ 小时 / 11k+ 动作（SMPL） | 需重定向（ProtoMotions 一键） | ⚠️ 学术 License，商用受限 | 补充语料；武术类看 ACCAD / Eyes_Japan 子集 |
| [Kimodo](https://github.com/nv-tlabs/kimodo) | 文本 → 动作生成 | SOMA 输出 → retarget | NVIDIA 模型条款 | 按口令定制生成长尾动作 |

### 训练框架与工具链

| 组件 | 功能 | License | 在 Mirror 中的角色 |
| --- | --- | --- | --- |
| [NVlabs/ProtoMotions](https://github.com/NVLabs/ProtoMotions) | GPU 仿真 + RL 训练框架；在 BONES-SEED 全量上训 General Tracking Policy，**zero-shot 部署真机 G1**（单 ONNX 导出，RoboJuDo 实测）；多后端 Newton/IsaacGym/IsaacLab/Genesis/MuJoCo | Apache-2.0 | MVP/Pilot 期策略训练主框架 |
| [NVlabs/GEM-X](https://github.com/NVlabs/GEM-X) | 单目视频 → SOMA 77 关节姿态 → 直接 retarget G1（`demo_soma.py --retarget --robot unitree_g1`） | Apache-2.0 | **Demo 首选**：捕获 + 重定向一站式 |
| [NVIDIA/soma-retargeter](https://github.com/NVIDIA/soma-retargeter) | SOMA BVH → G1 29 DoF CSV（Newton/Warp GPU IK） | Apache-2.0 | GEM-X 底层重定向器；自有动捕批量转换 |
| [DataVisards/PoseForge](https://github.com/DataVisards/PoseForge) | 单目视频 → 3D 骨骼 → 生物力学指标（feet gap / elbow angle）+ AI 教练反馈 | 开源 | Diff Engine 参考实现（前后端可 fork） |
| [unitree_sdk2](https://github.com/unitreerobotics/unitree_sdk2) | Unitree 官方 C++ SDK（CycloneDDS） | Unitree 官方 | 低层接口关节级下发、loco_client、Mimic 动作库 |
| [GEAR SONIC](https://nvlabs.github.io/GEAR-SONIC/) | 人形行为基础模型（BONES-SEED 训练） | 开源进度 coming soon | 跟踪项，不进 Demo 依赖 |

### 学术储备（论文级，未开源或代码待确认）

| 工作 | 论文 | 价值 |
| --- | --- | --- |
| CoachMe | [arXiv 2509.11698](https://arxiv.org/abs/2509.11698)（项目页 [motionxperts.github.io](https://motionxperts.github.io/)） | 参考式教练指令生成（差值 → 自然语言反馈），滑冰/拳击上超 GPT-4o 31.6%/58.3% |
| NMR | [arXiv 2603.22201](https://arxiv.org/abs/2603.22201) | 神经动作重定向（CEPR + CNN-Transformer），G1 武术/舞蹈验证 |
| IKMR | [arXiv 2509.15443](https://arxiv.org/abs/2509.15443) | 隐式运动动力学重定向，5000 FPS，G1 真机部署 |
| H2O | Human-to-Humanoid（He et al.） | RL 全身控制遥操作，演进方向参考 |

## 技术管道

```
[单目相机捕获用户动作 A]
   ↓
[3D 骨骼提取 (GEM-X / SOMA)] ── 记录轨迹 A
   ↓
[Retargeting → G1 关节角] ── 四道安全校验（限位/自碰撞/稳定/速度）
   ↓
[Diff Engine：A vs 标准轨迹 B] ── 差异高亮 + 量化分
   ↓
阶段1：G1 复刻动作 A（用户第三人称回看自己的错误）
阶段2：G1 从 A 渐变插值至修正姿态 B（Motion Morphing）
阶段3：用户二次尝试 → 重合度上升曲线（闭环完成）
```

## License

本仓库文档与代码（如有）默认保留所有权利；引用的第三方数据集与组件遵循各自 License。
