# 运行与代码阅读指南

## 直接查看

先打开reports/dashboard.html，它内嵌图表，不依赖服务器和外部图片。随后阅读reports/results.md和docs/methodology.md。所有数值表位于reports；项目只分发聚合结果，不附带原始数据。

## 环境与复现

推荐Python 3.12，先解压项目并进入项目根目录。路径尽量不带特殊字符。

```bash
python -m venv .venv
```

macOS/Linux执行`source .venv/bin/activate`；Windows PowerShell执行`.venv\Scripts\Activate.ps1`。

```bash
python -m pip install -r requirements.txt
python run_all.py
python -m unittest discover -s tests -v
```

首次运行需要网络下载约几百KB的压缩数据，并校验SHA256。完整运行包括1500次评估Bootstrap、金额Bootstrap、4种模型的开发/验证/测试，耗时依机器与线程而变。项目目录写权限必须可用。若数据镜像失效或校验变化，程序停止，不会静默换数据。可从来源核对后将同一压缩文件放到data/raw/hillstrom.csv.gz。

机器学习小样本任务若受过多线程影响，可在Linux/macOS运行`OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 python run_all.py`。Windows可在PowerShell中设置对应环境变量后运行。无需GPU、数据库账号或外部API key。

## 推荐阅读顺序

1. config.json：分析对象、随机种子、固定容量与候选模型。
2. docs/data_dictionary.md：确认哪些变量发生在处理前。
3. sql/01_arm_metrics.sql：理解每个分子分母。
4. src/statistics_tools.py：均值差、协变量调整、HT和Bootstrap。
5. src/uplift_models.py：S、T、X的区别与实际超参数。
6. src/run_analysis.py：数据、实验统计、模型选择与策略评估。
7. sql/04_policy_deciles.sql：测试评分后的窗口函数汇总。
8. src/build_reports.py：图表和报告。
9. tests/test_analysis.py：统计公式交叉核验、泄露检查与数据完整性。

## 产物与版本

requirements.txt记录这次实际运行的直接依赖版本，requirements-lock.txt记录完整环境解析后的依赖快照。报告summary.json记录Python与核心包版本。不同底层数值库可能带来微小浮点差异，不能把最后一位小数视为方法差异。

data/processed含本地重建的划分与逐行测试分数，未纳入分发包或GitHub提交。报告中的CSV可以独立核对。没有模型序列化文件，避免版本差异与隐藏训练状态；运行脚本重新拟合。

## Notebook

notebooks/walkthrough.ipynb包含数据读取、SQL、实验结果和模型步骤。已附带6个代码单元的实际执行输出，可以在Jupyter中逐段重跑。核心一键脚本不依赖Jupyter。

## 扩展分析

可以在重新定义验证流程后研究20%或40%触达容量，增加响应预测基线，或对女装邮件单独建模。扩展时保留原始实验配置与结果，不根据测试集反复选择最优容量。
