# my-academic-skills

科研工作用的 agent skill 集合，遵循同一条原则：**凡是领域专家想过目的判断，都做成人工签字的关卡；凡是能机械核验的规则，都写成脚本而不是段落。**

可用于 Claude Code、Codex、opencode 以及任何读取 `SKILL.md` 或 `AGENTS.md` 的 agent。无运行时依赖；检查脚本需要 Python 3.8 以上。

[English](README.md) · [安装说明](docs/installation.md) · [负责任使用](RESPONSIBLE_USE.md)

## 已有 skill

| Skill | 用途 | 文档 |
|---|---|---|
| [`binder-design-campaign`](skills/binder-design-campaign/) | 带关卡的蛋白计算 campaign：de novo 小蛋白 binder 设计、结构与复合物预测、蛋白工程改造 | [设计理由](docs/binder-design-campaign/design-rationale.md) · [来源对照](docs/binder-design-campaign/source-mapping.md) |

---

## binder-design-campaign

改编自 Anthropic 公开发布的[协议 prompt][prompt]，及其[自主 binder 设计工作][blog]与[技术报告][report]，只做了一处刻意的反转。原 prompt 是为完全自主的 48 小时运行而写的，明确禁止向操作者提问。本 skill 保留其科学内容，反转这一条：**凡是领域专家想过目的决定都做成关卡，campaign 在关卡处停下，等人签字。**

[prompt]: https://huggingface.co/datasets/Anthropic/claude-protein-binder-design
[blog]: https://www.anthropic.com/research/Claude-accelerates-protein-design
[report]: https://www-cdn.anthropic.com/30bf50e22a01388bb29bf077ee3f244531594b7a.pdf

### 为什么需要它

原 prompt 是 16,000 词、无任何标题的连续散文，其中约三分之一是绑定单一公司内部技术栈的基础设施——云计费治理器、Slack 线程契约、Drive 上传协调器。没人会为了设计一个 binder 每次都把它粘进终端，而且其中大部分离开原环境根本跑不起来。

| 原材料 | 本仓库的处理 |
|---|---|
| 内部编排（约占三分之一） | 换成四个动词的计算后端契约，Slurm 为一等适配器 |
| 科学方法 | 保留，重组进按需加载的 `references/` |
| 用散文陈述的机械不变量 | 改写为 `scripts/` 中可运行的检查 |
| "不许向操作者提任何问题" | 反转为七个带审核清单的关卡 |
| 一次 48 小时云端 campaign | 三档规模预设，从几个 GPU 小时到原始规模 |

结果是一份 159 行的 `SKILL.md`，其余内容由它指向。此外还吸收了原 prompt 缺少的内容——绝对阈值、campaign 规模测算、通过率诊断和各方法单条设计成本——来自 Adaptyv Bio 与 Claude Science 的公开 skill 集合，出处见 [NOTICE.md](NOTICE.md)。

### 七个关卡

```
G0 范围  ->  环境搭建 + 工具验收  ->  G1 靶点档案  ->  G2 表位选择
   ->  G3 打分仪器验证  ->  G4 规模  ->  生成与初筛
   ->  in silico 优化  ->  终轮打分  ->  G5 最终选择  ->  G6 交付
```

| 关卡 | 由人决定什么 |
|---|---|
| G0 | 靶点、计算后端、规模、许可证regime、交付物 |
| G1 | assay 构建体、参考结构、辅因子清单 |
| G2 | 表位与热点残基 |
| G3 | 打分仪器**在这个靶点上**是否真能把结合物与噪声分开 |
| G4 | 各靶点的算力分配 |
| G5 | 最终要下单的排序集合 |
| G6 | 验收，逐项从产物核对 |

G3 最重要也最容易被跳过，所以它是机械的：`state/gates/<target>.json` 不写 `PASS`，提交闸门就拒绝每一个生产打分作业。

### 整个设计围绕的那条校准事实

已发表的 campaign 中，15 个靶点共合成 1,320 条设计，354 条结合——命中率 27%，各靶点排名第一的设计命中率 49%。三个靶点几乎颗粒无收：麦芽糖结合蛋白 0/90，de novo β-桶 BBF-14 3/90，15-PGDH 1 条。

**co-folding 分数事先毫无预警。** 失败靶点上的设计，分数与那些产出大量结合物的靶点上的设计几乎一样高。在单个靶点内部，该集成在 13 个可评估靶点中的 12 个上能把结合物排在非结合物之前（平均精度均值 0.52，随机期望 0.31）；但跨靶点它无法提前标出失败，且在结合物内部与亲和力只有弱相关。

因此本 skill 把 in silico 置信度当作**筛子，而非神谕**（a filter, never an oracle），并要求这一判断出现在它产出的每一份报告里。

## 安装

```bash
git clone https://github.com/SPYfighting/my-academic-skills.git
```

**Claude Code / opencode** —— 软链你要用的 skill：

```bash
ln -s "$PWD/my-academic-skills/skills/binder-design-campaign" \
      ~/.claude/skills/binder-design-campaign
```

**Codex 及其他读取 AGENTS.md 的 agent** —— 把 [`AGENTS.md`](AGENTS.md) 复制到项目根目录，或把其内容追加到已有文件。

Windows 安装、项目级安装与验证步骤见 [docs/installation.md](docs/installation.md)。

## 使用

用自己的话提出需求即可：

> 帮我针对 PD-L1 设计小蛋白 binder。我在 Slurm 集群上有 4 张 A100，大约一周时间。

skill 会从 G0 接管，问清它需要的信息，并在每个关卡停下。

## 目录结构

```
skills/binder-design-campaign/
  SKILL.md                  协议主体，159 行
  workflows/                binder 设计 · 结构预测 · 蛋白工程
  references/               打分仪器 · 阈值 · 验证关卡
                            工具目录 · 靶点档案 · 失败模式
                            交付物规范 · 计算后端
  checklists/               每个关卡该呈现什么
  templates/                档案 · 配置 · 表格 schema · 打分策略
                            报告提纲
  scripts/                  可运行检查，纯标准库
examples/binder-design-campaign/minimal/   脚本运行用的样例数据
docs/                       安装说明、各 skill 的设计理由与来源对照
check.py                    仓库自检
```

## 自检

```bash
python check.py
```

先用样例数据跑一遍全部脚本，再用故意损坏的副本跑一遍，并断言校验脚本确实拒绝了损坏数据并说明了原因。

## 适用范围与局限

- 这些 skill 做的是 **in silico** 工作。结合与否由你或 CRO 通过实验确定，这里没有任何东西能预测它。
- 工具名称、参数和许可证信息只在其标注日期上正确，使用前须回上游核实。本仓库与上游 README 冲突时，以 README 为准。
- 双重用途问题见 [RESPONSIBLE_USE.md](RESPONSIBLE_USE.md)。
- 尚未在真实 campaign 上端到端跑通。已验证的是：检查脚本确实能抓到它声称要抓的东西。

## 署名与许可

仓库代码与文字：MIT（[LICENSE](LICENSE)）。改编自 Anthropic 的 CC-BY-4.0 发布内容与若干 MIT 许可的公开 skill 集合，详见 [NOTICE.md](NOTICE.md)。与上述任何一方均无隶属关系，也未获其背书。

参与贡献：[CONTRIBUTING.md](CONTRIBUTING.md)。
