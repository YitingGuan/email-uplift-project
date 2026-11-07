# 邮件营销实验评估与增量投放分析

基于Hillstrom 64,000条公开随机邮件实验记录，完成SQL质量核验、A/B/n效果评估、历史协变量调整、S/T/X增量建模和独立测试策略评估。

本项目对已有公开随机实验进行离线回顾性分析。数据与方法来源见 `docs/sources.md`。

## 核心发现

| 结果 | 实际数值 |
|---|---:|
| 男装邮件访问率 / 不发邮件访问率 | 18.28% / 10.62% |
| 男装邮件访问率绝对提升 | 7.66个百分点 |
| 女装邮件访问率绝对提升 | 4.52个百分点 |
| 男装邮件人均消费提升 | 0.770金额单位/分配客户/两周 |
| 男装访问效果ANCOVA方差缩减 | 约0.52% |
| 训练 / 验证 / 测试记录 | 25,567 / 8,523 / 8,523 |
| 验证选择模型 | T-Learner Logistic Regression |
| 测试30%增量排序策略 | 36.61名增量访问客户/千名合格客户 |
| 测试同容量随机策略期望 | 27.16名访问客户/千名合格客户 |
| 测试同容量普通响应排序 | 38.25名访问客户/千名合格客户 |

增量排序相对随机策略的差值约9.44，条件Bootstrap95%区间[1.39,17.25]；相对响应排序的差值约-1.64，区间[-12.09,8.21]。这些是离线条件估计，不是线上保证。

![测试策略比较](reports/figures/05_policy_values.png)

## 主要内容

1. `reports/dashboard.html`：浏览器直接打开的自包含展示页。
2. `reports/results.md`：完整实际结果。
3. `docs/methodology.md`：公式、假设、评估定义和局限。
4. `docs/run_guide.md`与`notebooks/walkthrough.ipynb`：运行和逐步理解。

## 复现

```bash
python -m pip install -r requirements.txt
python run_all.py
python -m unittest discover -s tests -v
```
## 使用的方法与工具

- DuckDB SQL：GROUP BY、CASE WHEN、FILTER、CTE、NTILE窗口汇总。
- SciPy / statsmodels：Welch均值差、SRM、Holm、HC2 ANCOVA、功效样本量规划。
- NumPy / pandas：质量核验、IPW、1500次Bootstrap、分位与排名统计。
- scikit-learn：独热编码、标准化、逻辑回归、直方图梯度提升，独立实现S/T/X。
- Matplotlib：7张图；HTML静态展示无需服务器。
