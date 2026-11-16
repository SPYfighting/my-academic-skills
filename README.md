# My Academic Skills

适用于 Claude Code、Codex 和 OpenCode 的科研技能集合，涵盖论文与证据规划、蛋白设计和可编辑科研绘图。每个一级技能目录独立维护，具体流程、依赖和验证范围见各自的 `SKILL.md`。

[English](README.en.md) · [安装](docs/installation.md) · [维护约定](AGENTS.md)

## 技能

| Skill | 用途 |
|---|---|
| [binder-design-campaign](binder-design-campaign/SKILL.md) | 先明确靶点与实验目标、形成分阶段计划，再按用户授权的阶段执行蛋白结合子设计、结构预测或蛋白工程 |
| [paper-anchor](paper-anchor/SKILL.md) | 用 `PAPER.md` 将论文主张连到证据、可复核产出和科研交接，分别记录分析进度和证据判读 |
| [scientific-illustrator-local](scientific-illustrator-local/SKILL.md) | 将科研示意图重建为可编辑矢量图，保留真实文字，并在本地 Illustrator 中绘制 |
| [scientific-ppt-drawing](scientific-ppt-drawing/SKILL.md) | 在 PowerPoint 中用原生图形和文字绘制可编辑的科研示意图 |

## 使用

```bash
git clone https://github.com/SPYfighting/my-academic-skills.git
```

选择需要的 Skill，将完整目录复制到项目内的技能目录，或让 Agent 直接读取它的 `SKILL.md`。

| Agent | 项目内技能目录 |
|---|---|
| Codex | `.agents/skills/` |
| Claude Code | `.claude/skills/` |
| OpenCode | `.opencode/skills/` |

依赖按 Skill 单独准备；安装步骤见 [安装说明](docs/installation.md)。

## 自检与维护

```bash
python check.py
```

自检按目录发现技能，检查入口并调用各自的 `scripts/selfcheck.py`。运行前准备相应依赖；自动检查不代表科研结果或所有应用版本已通过实测。添加技能遵循 [AGENTS.md](AGENTS.md)，无需在首页展开其完整工作流。

## 许可

仓库采用 [MIT](LICENSE)。各 Skill 的来源、第三方内容与适用许可见 [NOTICE.md](NOTICE.md)。
