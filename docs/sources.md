# 数据与方法来源

1. Kevin Hillstrom，The MineThatData E-Mail Analytics And Data Mining Challenge，2008。
   https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html
2. scikit-uplift Hillstrom说明与加载器。数据描述提供三组各三分之一随机分配及两周结果窗；本项目下载同一数据镜像，未复制其实现。
   https://www.uplift-modeling.com/en/latest/api/datasets/fetch_hillstrom.html
   https://github.com/maks-sh/scikit-uplift/blob/master/sklift/datasets/datasets.py
3. 数据镜像（由上述加载器引用）。
   https://hillstorm1.s3.us-east-2.amazonaws.com/hillstorm_no_indices.csv.gz
4. Künzel, S. R., Sekhon, J. S., Bickel, P. J., Yu, B. (2019). Metalearners for estimating heterogeneous treatment effects using machine learning. PNAS 116(10), 4156–4165. DOI: 10.1073/pnas.1804597116。
   https://pmc.ncbi.nlm.nih.gov/articles/PMC6410831/
5. EconML meta-learner方法说明。参考S/T/X概念与公式；核心实现独立使用scikit-learn，本项目没有安装或调用EconML运行库。
   https://www.pywhy.org/EconML/spec/estimation/metalearners.html
   https://github.com/py-why/EconML
6. Uber CausalML。用作研究方向与开源生态参考，未复制代码、未声称参与Uber项目，也未使用其运行库。
   https://github.com/uber/causalml
7. Deng, A., Xu, Y., Kohavi, R., Walker, T. (2013). Improving the sensitivity of online controlled experiments by utilizing pre-experiment data. WSDM, 123–132. DOI: 10.1145/2433396.2433413。
   https://exp-platform.com/cuped/
8. tea-tasting官方实验统计文档。参考协变量调整、SRM与指标定义的组织方式；主流程使用SciPy和statsmodels独立实现，不把tea-tasting写成已使用的运行依赖。
   https://tea-tasting.e10v.me/user-guide/
   https://github.com/e10v/tea-tasting
