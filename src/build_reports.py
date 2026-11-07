"""Produce figures, Markdown findings and a portable HTML dashboard."""
from pathlib import Path
import json,base64,html
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports';FIG=OUT/'figures';FIG.mkdir(exist_ok=True)
plt.rcParams.update({'figure.dpi':150,'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'})

def load(name):return pd.read_csv(OUT/(name+'.csv'))
def save(fig,name):fig.tight_layout();fig.savefig(FIG/(name+'.png'));plt.close(fig)

def main():
    arms=load('01_arm_metrics');ab=load('ab_effects');cov=load('covariate_adjustment');policy=load('policy_evaluation');diff=load('policy_differences');selection=load('model_selection');s=json.loads((OUT/'summary.json').read_text());chosen=s['selected_model']
    labels={'Mens E-Mail':'Mens email','No E-Mail':'No email','Womens E-Mail':'Womens email'}
    fig,axes=plt.subplots(1,2,figsize=(10,3.8))
    for ax,col,title in zip(axes,['visit_rate','conversion_rate'],['Website visits','Purchases']):
        vals=100*arms[col];ax.bar([labels[x] for x in arms.segment],vals,color=['#2878A8','#9CAAB5','#52A7A2']);ax.set(ylabel='Percent of assigned customers',title=title)
        for i,v in enumerate(vals):ax.text(i,v+.03,f'{v:.2f}%',ha='center',va='bottom')
        ax.set_ylim(0,vals.max()*1.2)
    save(fig,'01_arm_rates')
    fig,ax=plt.subplots(figsize=(8,3.7));sub=ab[ab.outcome=='visit'].reset_index(drop=True)
    for i,row in sub.iterrows():ax.errorbar(100*row.effect,i,xerr=[[100*(row.effect-row.ci_low)],[100*(row.ci_high-row.effect)]],fmt='o',capsize=4,color='#2878A8')
    ax.set(yticks=range(len(sub)),yticklabels=[labels[x] for x in sub.treatment],xlabel='Absolute visit lift (percentage points)',title='Full-sample visit effects | marginal 95% confidence intervals');ax.axvline(0,color='gray',linestyle='--');save(fig,'02_visit_effects')
    fig,ax=plt.subplots(figsize=(8,3.7));bal=load('balance_smd')
    for arm,d in bal.groupby('treatment'):ax.scatter(d.smd,d.feature,label=labels[arm],s=25,alpha=.8)
    ax.axvline(0,color='gray');ax.set(xlabel='Standardized mean difference',title='Pre-treatment balance | no proof of randomization');ax.legend(fontsize=8);ax.tick_params(axis='y',labelsize=8);save(fig,'03_balance')
    fig,ax=plt.subplots(figsize=(8,4));curves=load('uplift_curves')
    for name,d in curves.groupby('model'):ax.plot(d.fraction,d.gain_per_1000,label=name+(' (selected)' if name==chosen else ''),linewidth=2 if name==chosen else 1,alpha=1 if name==chosen else .6)
    ate=s['test_ate_ipw']['estimate']*1000;ax.plot([0,1],[0,ate],'k--',label='Random expected')
    ax.set(xlabel='Fraction contacted',ylabel='Estimated incremental visitors / 1,000 eligible',title='Held-out test gain curves | HT definition');ax.legend(fontsize=8);save(fig,'04_uplift_curves')
    fig,ax=plt.subplots(figsize=(9,4));p=policy[policy.policy!='send_none'].reset_index(drop=True)
    names={'uplift_top30':'Uplift top 30%','random30_expected':'Random 30% expected','response_top30':'Response top 30%','send_all':'Send all (100%)'}
    for i,r in p.iterrows():ax.errorbar(r.incremental_visits_per_1000,i,xerr=[[r.incremental_visits_per_1000-r.ci_low],[r.ci_high-r.incremental_visits_per_1000]],fmt='o',capsize=4,color='#2878A8')
    ax.set(yticks=range(len(p)),yticklabels=[names[x] for x in p.policy],xlabel='Incremental visitors / 1,000 eligible customers',title='Test policy estimates | conditional bootstrap 95% intervals');ax.axvline(0,color='gray');save(fig,'05_policy_values')
    fig,ax=plt.subplots(figsize=(8,4));cal=load('decile_calibration');ax.errorbar(cal.decile,100*cal.observed_difference,yerr=[100*(cal.observed_difference-cal.ci_low),100*(cal.ci_high-cal.observed_difference)],fmt='o',capsize=3,label='Observed group difference');ax.plot(cal.decile,100*cal.mean_predicted_effect,label='Mean predicted effect');ax.set(xlabel='Score decile (1 = highest)',ylabel='Visit effect (percentage points)',title='Exploratory decile calibration | marginal intervals');ax.legend(fontsize=8);save(fig,'06_deciles')
    fig,ax=plt.subplots(figsize=(8,4));cost=load('cost_sensitivity')
    for name,d in cost.groupby('policy'):ax.plot(d.assumed_cost_in_visit_value_units,d.net_visit_equivalents_per_1000,label=names.get(name,name))
    ax.set(xlabel='Assumed email cost / value of one incremental visitor',ylabel='Net visit equivalents / 1,000 eligible',title='Scenario analysis | costs and visit value are NOT observed');ax.legend(fontsize=8);save(fig,'07_cost_sensitivity')
    (OUT/'results.md').write_text(make_report(arms,ab,cov,policy,diff,selection,s),encoding='utf-8')
    sections=[('整体实验效果','所有比例均以原分配客户为分母，单位是百分比。','01_arm_rates'),('绝对提升与不确定性','这是百分点提升，不是相对百分比。区间为边际95%，p值另做Holm六重校正。','02_visit_effects'),('实验前特征平衡','组间差异很小，但无法代替对原始随机化系统的审计。','03_balance'),('模型排序能力','选择依据为验证集30%容量增量；测试曲线只报告，不反向选模型。','04_uplift_curves'),('投放策略评估','每千名合格客户的增量访问，非每千名已触达客户。全量发送与30%策略成本不同。','05_policy_values'),('分位效果检查','分位区间不是个体CATE置信区间，也未同时校正。','06_deciles'),('成本假设','场景成本不是真实业务ROI；未观测真实投递费、毛利或访问价值。','07_cost_sensitivity')]
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>邮件营销实验分析</title><style>body{font:16px/1.75 system-ui,sans-serif;color:#19364c;background:#f2f5f8;max-width:1100px;margin:30px auto;padding:0 20px}h1{font-size:32px}h2{font-size:23px}section{padding:26px;background:white;border-radius:12px;margin:20px 0}img{max-width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}.scroll{overflow-x:auto}a{color:#226d9c}</style><h1>邮件营销效果与增量投放分析</h1><p>Hillstrom 64,000条随机分组记录 · DuckDB SQL · Python统计推断 · S T X Learner</p><section><h2>核心结论</h2><p>男装邮件访问率提升7.66个百分点，女装邮件提升4.52个百分点。验证集选择T-Learner逻辑回归；测试集30%触达策略估计每千名合格客户增加36.61名访问客户，随机同容量为27.16名访问客户，普通响应模型为38.25名访问客户。</p><p>增量模型相对普通响应模型的差值区间跨零，不能声称明确胜出。协变量调整方差缩减不足1%，不夸大收益。</p></section>'''
    for title,text,filename in sections:
        b=base64.b64encode((FIG/(filename+'.png')).read_bytes()).decode();page+=f'<section><h2>{title}</h2><p>{text}</p><img alt="{title}" src="data:image/png;base64,{b}"></section>'
    page+='<section><h2>可核对的完整指标</h2><div class="scroll">'+ab.round(6).to_html(index=False,border=0)+'</div></section><section><h2>项目边界</h2><p>公开数据离线回顾性分析，未实施新的线上实验。不存在已验证的真实成本节约或商业落地。随机分组依据公开数据描述，缺少客户ID、分流日志与逐日事件，不能分析邮件打开、留存或重复触达。</p><p>来源与方法见项目docs/sources.md；数据提供者Kevin Hillstrom，原始挑战2008年。</p></section></html>'
    (OUT/'dashboard.html').write_text(page,encoding='utf-8')
    print('Generated reports and 7 figures.')

def mdtable(d):
    headers=list(d.columns);rows=['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']
    rows += ['| '+' | '.join(str(x) for x in row)+' |' for row in d.to_numpy()]
    return '\n'.join(rows)

def make_report(arms,ab,cov,policy,diff,selection,s):
    return f'''# 邮件营销实验分析结果\n\n生成日期 2026年11月7日。公开数据回顾性分析，非新开展的线上实验。\n\n## 结论\n\n两类邮件均提高访问、购买转化和人均消费；六项对照比较经Holm校正后p值均小于0.05。男装邮件访问率比对照高7.659个百分点，女装高4.523个百分点。不能由这两项分别对照的检验直接替代男装与女装的直接比较。\n\n## 原始组指标\n\n{mdtable(arms.round(6))}\n\n## 六项效果检验\n\n{mdtable(ab[['treatment','outcome','effect','ci_low','ci_high','p_holm_six']].round(8))}\n\nvisit和conversion差值为概率单位，乘100才是百分点；spend差值为每分配客户的两周消费金额。区间是边际95%区间，不是Holm同时区间。\n\n## 数据质量\n\n64,000条，12个原始字段，无缺失单元格。6,562行内容完全重复，因没有客户ID，保留所有记录，不能认定为重复客户。三组SRM检验p={s['quality']['srm_p_value']:.4f}。实验前特征最大绝对SMD约0.0137，未见明显失衡，但不能证明分流系统无误。\n\n## 协变量调整\n\n使用实验前log(1+history)作ANCOVA调整，HC2稳健标准误；是CUPED思想的具体实现，不是假称存在实验前相同两周指标。\n\n{mdtable(cov[['treatment','outcome','estimated_variance_reduction']].round(6))}\n\n方差缩减很小，最大约0.52%，不能写成显著提高实验效率。\n\n## 增量模型与独立测试\n\n仅建模男装邮件与不发邮件两组，共{s['n_pair']}条。训练/验证/测试为{s['splits']['train']}/{s['splits']['validation']}/{s['splits']['test']}。按实验分组分层随机划分，未按结果分层，固定种子{s['seed']}。没有日期字段，不能虚构时间切分。\n\n{mdtable(selection.round(4))}\n\n按验证集30%触达容量的HT增量选择{s['selected_model']}；验证值并列时按配置顺序确定。开发集重训后只报告一次测试结果。四候选为S-HGB、T-Logistic、T-HGB、X-HGB，未使用EconML或CausalML运行库；参考其公开方法，用scikit-learn独立实现。\n\n{mdtable(policy.round(4))}\n\n这里所有增量均相对于不发邮件，分母为1000名合格客户。随机30%是同容量随机策略的期望，不是挑选一次有利随机抽样。\n\n{mdtable(diff.round(4))}\n\n增量策略相对随机同容量点估计更高；与响应模型差异区间跨零，不能说增量模型明确胜出。Bootstrap为1500次成对记录重采样，固定训练好的模型和已选人群，只反映条件评估不确定性；不涵盖训练与阈值不确定性，也未做多重策略区间校正。\n\n## 样本量与异质性\n\n新实验规划：基线访问率10.62%、双侧单比较alpha=0.025、功效80%，检测1个百分点提升约需每组18,775人。这是未来规划场景，不是事后功效。三项探索性交互在Holm校正后均未达到0.05，不能据此宣布明确的人群差异。\n\n## 实施建议\n\n公开实验支持继续验证邮件营销效果；若受30%容量限制，保留增量排序与响应排序两种候选，在线随机比较。成本敏感性只是情景推演，不能报告真实ROI或已实现成本节约。\n\n## 附件\n\n统计细节见docs/methodology.md，SQL见sql目录，所有CSV与图表见reports目录。\n'''

if __name__=='__main__':main()
