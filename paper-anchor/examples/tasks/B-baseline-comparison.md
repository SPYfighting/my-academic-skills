# B · 对比参数高效基线

## 目的

检验 LRA 在 EuroSAT 10-shot 设置下的平均精度是否高于三种参数高效基线。本任务对应[论文总览](../PAPER.example.md)的 `R1.E3`。

## 设计

在相同数据划分和评估口径下，比较 LRA 与 VPT、BitFit、Adapter 的平均分类精度。收齐三种基线后再对 `R1.E3` 给出证据判读。

- [x] 汇总 LRA、VPT 和 BitFit 的已有结果。
- [ ] 跑完 Adapter 并补齐对比表。

**当前状态**：进行中。

[阶段结果](../results/r1e3_baselines.md) · [基线对比表](../fig/R1.E3-baseline-table.md)
