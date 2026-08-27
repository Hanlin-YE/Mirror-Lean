# Mirror · 镜身 — G1 Sim 训练数据集选型调研

**需求**（源自 PRD）：可仿真训练的成型动作数据集，直接供 Unitree G1 训练（标准动作库 B + 策略训练语料）。
**调研日期**：2026-08-27（全部经线上核实）

---

## 1. 首选方案：BONES-SEED（G1 原生，无需重定向）

**BONES-SEED**（Bones Studio × NVIDIA，HuggingFace: `bones-studio/seed`）

| 项 | 数据 |
| --- | --- |
| 规模 | **142,220 条动作**（71,132 原始 + 71,088 镜像），约 288 小时 @120fps |
| 表演者 | 522 人（253F/269M，17–71 岁，145–199cm，38–145kg）——体型多样性好 |
| 输出格式 | SOMA Uniform BVH · SOMA Proportional BVH · **Unitree G1 CSV（MuJoCo 兼容，直接可训）** |
| 标注 | 每条最多 6 条自然语言描述 + 时间分段标签 + 骨骼元数据（支持语言条件策略与动作检索） |
| 动作类别 | 运动/步态 74k、沟通手势 21k、交互 14k、**舞蹈 11k**、游戏 8.7k、日常 5.8k、**体育 4k、Other 2k（含武术/特技）** |
| 获取 | `huggingface-cli download bones-studio/seed --repo-type dataset`；在线浏览 seed-viewer.bones.studio |

**关键事实**：其中的 G1 轨迹就是用 NVIDIA soma-retargeter 批量生成的——与我们 TDD 的重定向选型同源，坐标系和关节语义天然一致。

## 2. 配套训练框架：ProtoMotions（SEED → G1 真机 zero-shot）

**NVlabs/ProtoMotions**（Apache-2.0，2026-08 仍活跃更新）

- 在 **BONES-SEED 全量（~142K）**上训练单一 General Tracking Policy，**zero-shot 部署到真机 Unitree G1**；
- 部署管线导出**单个 ONNX 模型**（观测计算内嵌），部署侧只需喂原始传感器信号——实测通过 RoboJuDo 框架在 G1 上落地（只加一个 policy 文件）；
- 多仿真后端：NVIDIA Newton / IsaacGym / IsaacLab / Genesis / MuJoCo，一键 sim2sim 验证（--simulator=newton → mujoco）；
- 算法内置：GPC/PEFT、MaskedMimic、AMP、ASE、PPO；支持 G1 / H1 / SMPL / 自定义机型；
- 性能量级：AMASS 全量（40+ 小时）4×A100 12 小时训完；曾用 24×A100 训 13K motions/GPU；
- 附带能力：**AMASS 一键重定向到任意机器人**（PyRoki 优化器，一条命令）；
- 姊妹仓库 **MimicKit**：轻量动作模仿学习框架。

## 3. 备选与补充数据源

| 方案 | 定位 | 说明 |
| --- | --- | --- |
| **GEAR SONIC / GR00T-WholeBodyControl**（NVlabs） | 人形行为基础模型 | 以 BONES-SEED 为主训练数据（G1 关节轨迹直接可用）；开源状态标注 "coming soon"，进度需跟踪 |
| **AMASS**（amass.is.tue.mpg.de） | 上游人体动作大库 | 40+ 小时 / 11k+ 动作 / SMPL 参数；⚠️ 学术 License（注册下载，商用受限），商用前需替换或谈授权；武术相关看 ACCAD 与 Eyes_Japan 子集（含表演类动作，太极素材需在下载页确认） |
| **Kimodo**（nv-tlabs） | 文本生成动作 | 自然语言 → SOMA 动作 → retarget → 训练；可按「太极口令」定制生成，ProtoMotions 官方支持 Kimodo 数据准备流程 |
| **GEM-X**（NVlabs，已在 TDD 选型） | 视频 → 动作 | 教练示范视频 → SOMA → G1 CSV，冷启动标准动作库的主通道 |
| **soma-retargeter**（NVIDIA） | 重定向工具 | 自有动捕/教练数据 → G1 CSV 的批量转换（batch 模式） |

## 4. 推荐落地组合（对齐 PRD 路线图）

```
数据冷启动（T-3 周即可开始）：
  BONES-SEED 下载 → 检索 Sport/Other/舞蹈类 → 筛选可原地演示动作
       ↓ 作为「标准轨迹 B」与策略训练语料
训练管线：
  ProtoMotions（MuJoCo/Newton 后端）+ BONES-SEED subset
       → 训 tracking policy（先小规模：1×A100 + 单类别子集）
       → ONNX 导出 → 仿真回放验证 → 真机 G1
差异化数据（太极/武术）：
  路线 A：AMASS ACCAD/Eyes_Japan 子集（学术期可用，商用需授权）
  路线 B：GEM-X 处理教练视频 / soma-retargeter 批量转换自采动捕
  路线 C：Kimodo 文本生成补充长尾动作
```

## 5. 风险与注意

| 项 | 说明 |
| --- | --- |
| BONES-SEED License | 数据集 LICENSE.md 需在商用前确认条款（当前标注为 open dataset，但条款以仓库为准） |
| AMASS | 学术 License，商用受限——Demo/Pilot 期可用，规模化前替换为自采 + SEED |
| GEAR SONIC | 开源进度未定，仅作跟踪项，不进 Demo 依赖 |
| 算力 | ProtoMotions 需 NVIDIA GPU；Demo 阶段建议只训小子集或不训（直接用 SEED 轨迹回放），训练属于 Demo 后演进项 |
| 与 TDD 的关系 | v1 Demo 不做策略训练（轨迹回放即可）；本调研主要服务 MVP/Pilot 阶段的「标准库 B 扩充 + RL 策略」路线（TDD 第 10 节演进方向的数据底座） |
