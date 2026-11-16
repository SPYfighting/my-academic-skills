# My Academic Skills

适用于 Claude Code、Codex 和 OpenCode 的科研技能集合，涵盖论文与证据规划、蛋白设计和可编辑科研绘图。每个一级技能目录独立维护，具体流程、依赖和验证范围见各自的 `SKILL.md`。

[English](README.en.md) · [安装](#安装) · [维护约定](AGENTS.md)

## 技能

| Skill | 用途 |
|---|---|
| [binder-design-campaign](binder-design-campaign/SKILL.md) | 先明确靶点与实验目标、形成分阶段计划，再按用户授权的阶段执行蛋白结合子设计、结构预测或蛋白工程 |
| [paper-anchor](paper-anchor/SKILL.md) | 用 Markdown 将论文主张连到证据、可复核产出和下一步。项目规则采用后自动使用 |
| [scientific-illustrator-local](scientific-illustrator-local/SKILL.md) | 将科研示意图重建为可编辑矢量图，保留真实文字，并在本地 Illustrator 中绘制 |
| [scientific-ppt-drawing](scientific-ppt-drawing/SKILL.md) | 在 PowerPoint 中用原生图形和文字绘制可编辑的科研示意图 |

## 安装

```bash
git clone https://github.com/SPYfighting/my-academic-skills.git
cd my-academic-skills
```

将需要的 Skill 完整目录复制到下表的位置，也可以给 Agent 提供 `SKILL.md` 的路径，并让它访问同目录的配套文件。例如，使用 Codex 时，将 `paper-anchor/` 复制到目标项目的 `.agents/skills/paper-anchor/`。

| Agent | 项目内技能目录 |
|---|---|
| [Codex](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills) | `.agents/skills/<skill-name>/` |
| [Claude Code](https://code.claude.com/docs/en/skills#choose-where-skills-load) | `.claude/skills/<skill-name>/` |
| [OpenCode](https://opencode.ai/docs/skills/#discovery) | `.opencode/skills/<skill-name>/` |

OpenCode 也会发现项目内的 `.agents/skills/` 和 `.claude/skills/`。同一个 Skill 复制到其中一个位置即可。

### 各 Skill 的依赖

- **binder-design-campaign**：运行自检前，在本仓库根目录执行 `python -m pip install -r binder-design-campaign/requirements.txt`。计算依赖按 [技能说明](binder-design-campaign/SKILL.md) 单独准备。
- **paper-anchor**：日常只用 Markdown，维护者自检使用 Python 标准库。见 [使用说明](paper-anchor/README.md)。
- **scientific-illustrator-local**：按 [环境与兼容性说明](scientific-illustrator-local/references/installation-and-compatibility.md) 准备 CPython 3.11–3.13 和声明的依赖。原生绘图使用 Illustrator，VTracer 可选。
- **scientific-ppt-drawing**：按 [环境与应用控制说明](scientific-ppt-drawing/references/setup-and-app-control.md) 准备 CPython 3.11–3.13 和固定版本依赖。原生渲染和编辑的验收需要 PowerPoint。

## 自检与维护

```bash
python check.py
python check.py paper-anchor
```

在本仓库根目录运行。第一条检查全部技能，第二条演示如何检查单个技能。自检调用各自的 `scripts/selfcheck.py`。Illustrator 自检可用技能目录内的 `.venv` 或 `SCIENTIFIC_ILLUSTRATOR_PYTHON` 指定解释器，PowerPoint 自检使用运行 `check.py` 的解释器。科研结论和原生应用的表现需另行验证。添加技能遵循 [AGENTS.md](AGENTS.md)。

## 许可

仓库采用 [MIT](LICENSE)。各 Skill 的来源、第三方内容与适用许可见 [NOTICE.md](NOTICE.md)。
