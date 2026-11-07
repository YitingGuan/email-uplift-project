"""Execute audited SQL, A/B inference and held-out uplift evaluation."""
from pathlib import Path
import json,hashlib,sys,platform
import numpy as np
import pandas as pd
import duckdb
from scipy import stats
from sklearn.model_selection import train_test_split
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize
from download_data import download
from statistics_tools import mean_difference,cuped_ancova,holm,ipw_score,policy_mask,bootstrap_means,normal_mean_ci
from uplift_models import MetaLearner,FEATURES

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports';OUT.mkdir(exist_ok=True)
CONFIG=json.loads((ROOT/'config.json').read_text());SEED=CONFIG['seed']
CONTROL=CONFIG['control'];TREATMENT=CONFIG['model_treatment']

def load_data():
    path=download();df=pd.read_csv(path)
    expected={'recency','history_segment','history','mens','womens','zip_code','newbie','channel','segment','visit','conversion','spend'}
    if set(df.columns)!=expected:raise ValueError('Schema changed')
    if df.isna().any().any():raise ValueError('Missing source values require review')
    for col in ['mens','womens','newbie','visit','conversion']:
        if not set(df[col].unique())<={0,1}:raise ValueError(f'Invalid binary {col}')
    if not set(df.segment)=={'Mens E-Mail','Womens E-Mail','No E-Mail'}:raise ValueError('Invalid experiment arms')
    if not ((df.spend>=0)&(df.history>=0)&df.recency.between(1,12)).all():raise ValueError('Invalid ranges')
    df.insert(0,'record_id',np.arange(len(df))) # Source row key, NOT a customer identifier.
    return df

def make_splits(pair):
    train,rest=train_test_split(pair,test_size=.4,random_state=SEED,stratify=pair.treatment)
    validation,test=train_test_split(rest,test_size=.5,random_state=SEED+1,stratify=rest.treatment)
    return train.copy(),validation.copy(),test.copy()

def quality_and_sql(df):
    conn=duckdb.connect();conn.register('customers',df)
    for file in sorted((ROOT/'sql').glob('0[123]_*.sql')):
        conn.execute(file.read_text()).df().to_csv(OUT/(file.stem+'.csv'),index=False)
    counts=df.segment.value_counts().sort_index()
    chi,p=stats.chisquare(counts.to_numpy(),f_exp=np.ones(3)*len(df)/3)
    quality={'n_records':len(df),'n_columns_source':12,'missing_cells':int(df.isna().sum().sum()),'identical_source_rows':int(df.drop(columns='record_id').duplicated().sum()),'identity_note':'No customer ID supplied; identical feature/outcome rows retained. record_id is source row position, not verified unique customer ID.','arm_counts':counts.to_dict(),'srm_expected_ratio':[1,1,1],'srm_chi2':float(chi),'srm_p_value':float(p),'source_sha256':hashlib.sha256((ROOT/'data/raw/hillstrom.csv.gz').read_bytes()).hexdigest()}
    (OUT/'quality.json').write_text(json.dumps(quality,indent=2))
    # Balance is a diagnostic, not a proof that randomization succeeded.
    encoded=pd.get_dummies(df[['recency','history','mens','womens','newbie','zip_code','channel']],dtype=float)
    rows=[]
    for arm in ['Mens E-Mail','Womens E-Mail']:
        a=encoded[df.segment==arm];b=encoded[df.segment==CONTROL]
        for col in encoded:
            denom=np.sqrt((a[col].var(ddof=1)+b[col].var(ddof=1))/2)
            rows.append(dict(treatment=arm,feature=col,smd=(a[col].mean()-b[col].mean())/denom if denom else 0))
    pd.DataFrame(rows).to_csv(OUT/'balance_smd.csv',index=False)
    return quality

def ab_analysis(df):
    rows=[];adj=[];boot=[]
    for arm in ['Mens E-Mail','Womens E-Mail']:
        pair=df[df.segment.isin([arm,CONTROL])].copy();pair['treatment']=(pair.segment==arm).astype(int)
        for outcome in ['visit','conversion','spend']:
            a=pair.loc[pair.treatment==1,outcome].to_numpy();b=pair.loc[pair.treatment==0,outcome].to_numpy()
            result=mean_difference(a,b)
            rows.append(dict(treatment=arm,outcome=outcome,n_treatment=len(a),n_control=len(b),mean_treatment=a.mean(),mean_control=b.mean(),relative_lift=(a.mean()-b.mean())/b.mean(),**result))
            adjusted=cuped_ancova(pair,outcome)
            adj.append(dict(treatment=arm,outcome=outcome,unadjusted_effect=result['effect'],unadjusted_se=result['se'],estimated_variance_reduction=1-(adjusted['se']/result['se'])**2,**adjusted))
            if outcome=='spend':
                rng=np.random.default_rng(SEED);est=[]
                for _ in range(CONFIG['bootstrap_replicates']):est.append(a[rng.integers(0,len(a),len(a))].mean()-b[rng.integers(0,len(b),len(b))].mean())
                low,high=np.quantile(est,[.025,.975]);boot.append(dict(treatment=arm,outcome=outcome,bootstrap_ci_low=low,bootstrap_ci_high=high,replicates=CONFIG['bootstrap_replicates']))
    ab=pd.DataFrame(rows);ab['p_holm_six']=holm(ab.p_value);ab.to_csv(OUT/'ab_effects.csv',index=False)
    adjusted=pd.DataFrame(adj);adjusted['p_holm_six']=holm(adjusted.p_value);adjusted.to_csv(OUT/'covariate_adjustment.csv',index=False)
    pd.DataFrame(boot).to_csv(OUT/'revenue_bootstrap.csv',index=False)
    # Planning scenarios for a NEW experiment, not observed/post-hoc power.
    p0=float(df.loc[df.segment==CONTROL,'visit'].mean());planning=[]
    for delta in [.005,.01,.02]:
        effect=abs(proportion_effectsize(p0+delta,p0));n=NormalIndPower().solve_power(effect_size=effect,alpha=.025,power=.8,ratio=1,alternative='two-sided')
        planning.append(dict(baseline_visit_rate=p0,absolute_mde=delta,alpha_per_comparison=.025,power=.8,n_per_arm=int(np.ceil(n))))
    pd.DataFrame(planning).to_csv(OUT/'sample_size_planning.csv',index=False)
    return ab,adjusted

def subgroup_analysis(pair):
    import statsmodels.api as sm
    rows=[]
    for feature in ['newbie','mens','womens']:
        t=pair.treatment.to_numpy();x=pair[feature].to_numpy()
        design=np.column_stack([np.ones(len(pair)),t,x,t*x]);fit=sm.OLS(pair.visit,design).fit(cov_type='HC2')
        ci=fit.conf_int().iloc[3].to_numpy() if hasattr(fit.conf_int(),'iloc') else fit.conf_int()[3]
        rows.append(dict(feature=feature,interaction_effect=float(fit.params.iloc[3]),ci_low=ci[0],ci_high=ci[1],p_value=float(fit.pvalues.iloc[3])))
    res=pd.DataFrame(rows);res['p_holm_three']=holm(res.p_value);res.to_csv(OUT/'subgroup_interactions.csv',index=False)

def uplift_analysis(pair):
    train,val,test=make_splits(pair)
    split_rows=[]
    for name,part in [('train',train),('validation',val),('test',test)]:
        split_rows.extend(dict(record_id=int(i),split=name,treatment=int(t)) for i,t in zip(part.record_id,part.treatment))
    # This file is private local output; excluded from distributed project package.
    (ROOT/'data/processed').mkdir(exist_ok=True)
    pd.DataFrame(split_rows).to_csv(ROOT/'data/processed/split_membership.csv',index=False)
    val_z=ipw_score(val.visit,val.treatment);test_z=ipw_score(test.visit,test.treatment)
    candidates=[]
    for name in CONFIG['model_candidates']:
        model=MetaLearner(name,SEED).fit(train,train.visit);scores=model.predict(val)
        mask=policy_mask(scores,CONFIG['target_fraction']);gain=np.mean(mask*val_z)
        candidates.append(dict(model=name,validation_gain_per_1000=1000*gain,validation_capacity=float(mask.mean())))
    candidate_table=pd.DataFrame(candidates);candidate_table.to_csv(OUT/'model_selection.csv',index=False)
    chosen=candidate_table.sort_values('validation_gain_per_1000',ascending=False,kind='stable').iloc[0].model
    print('Selected on validation:',chosen,flush=True)
    dev=pd.concat([train,val]);test_rows=[];test_scores={};fitted={}
    for name in CONFIG['model_candidates']:
        m=MetaLearner(name,SEED).fit(dev,dev.visit);scores=m.predict(test);test_scores[name]=scores;fitted[name]=m
        mask=policy_mask(scores,.3);test_rows.append(dict(model=name,test_gain_per_1000=1000*np.mean(mask*test_z),selected_on_validation=bool(name==chosen)))
    pd.DataFrame(test_rows).to_csv(OUT/'model_test_comparison.csv',index=False)
    score=test_scores[chosen];mask=policy_mask(score,.3);fraction=mask.mean()
    response_model=MetaLearner('t_hgb',SEED).fit(dev,dev.visit)
    response_mask=policy_mask(response_model.response_score(test),.3)
    contributions={'uplift_top30':mask*test_z,'random30_expected':fraction*test_z,'response_top30':response_mask*test_z,'send_all':test_z,'send_none':np.zeros(len(test))}
    matrix=np.column_stack(list(contributions.values()));ci=bootstrap_means(matrix,CONFIG['bootstrap_replicates'],SEED)
    policies=[]
    for i,(name,a) in enumerate(contributions.items()):
        cap={'uplift_top30':fraction,'random30_expected':fraction,'response_top30':response_mask.mean(),'send_all':1,'send_none':0}[name]
        policies.append(dict(policy=name,fraction_contacted=float(cap),incremental_visits_per_1000=float(1000*a.mean()),ci_low=float(1000*ci[0,i]),ci_high=float(1000*ci[1,i])))
    policies=pd.DataFrame(policies);policies.to_csv(OUT/'policy_evaluation.csv',index=False)
    differences=np.column_stack([contributions['uplift_top30']-contributions['random30_expected'],contributions['uplift_top30']-contributions['response_top30']])
    dci=bootstrap_means(differences,CONFIG['bootstrap_replicates'],SEED+2)
    comparisons=[]
    for i,name in enumerate(['random30_expected','response_top30']):
        comparisons.append(dict(comparator=name,difference_per_1000=1000*differences[:,i].mean(),ci_low=1000*dci[0,i],ci_high=1000*dci[1,i]))
    pd.DataFrame(comparisons).to_csv(OUT/'policy_differences.csv',index=False)
    # Definition fixed explicitly: normalized cumulative HT gain, not library-specific Qini.
    curves=[];auc=[]
    for name,scores in test_scores.items():
        order=np.argsort(-scores,kind='stable');gain=np.r_[0,np.cumsum(test_z[order])/len(test)];q=np.arange(len(test)+1)/len(test)
        area=float(np.trapezoid(gain,q));random_area=float(.5*test_z.mean())
        auc.append(dict(model=name,auuc_ht=area,qini_area_ht=area-random_area))
        for k in np.linspace(0,len(test),101).astype(int):curves.append(dict(model=name,fraction=q[k],gain_per_1000=1000*gain[k]))
    pd.DataFrame(curves).to_csv(OUT/'uplift_curves.csv',index=False);pd.DataFrame(auc).to_csv(OUT/'ranking_metrics.csv',index=False)
    # Descriptive decile calibration; intervals are marginal, not simultaneous CATE intervals.
    order=np.argsort(-score,kind='stable');deciles=[]
    for j,indices in enumerate(np.array_split(order,10),1):
        sub=test.iloc[indices];a=sub.loc[sub.treatment==1,'visit'];b=sub.loc[sub.treatment==0,'visit'];r=mean_difference(a,b)
        deciles.append(dict(decile=j,n=len(indices),mean_predicted_effect=float(score[indices].mean()),observed_difference=r['effect'],ci_low=r['ci_low'],ci_high=r['ci_high']))
    pd.DataFrame(deciles).to_csv(OUT/'decile_calibration.csv',index=False)
    # Actual costs absent. Lambda is assumed email cost / value of one incremental visit.
    costs=[]
    for lam in [0,.01,.03,.05,.08,.1]:
        for row in policies.to_dict('records'):
            costs.append(dict(policy=row['policy'],assumed_cost_in_visit_value_units=lam,net_visit_equivalents_per_1000=row['incremental_visits_per_1000']-1000*lam*row['fraction_contacted']))
    pd.DataFrame(costs).to_csv(OUT/'cost_sensitivity.csv',index=False)
    # Only aggregate score outputs are distributed; row data stays local.
    private=test[['record_id','treatment','visit']].copy();private['uplift_score']=score;private['selected']=mask
    private.to_csv(ROOT/'data/processed/test_scores.csv',index=False)
    connection=duckdb.connect();connection.register('scored_customers',private)
    connection.execute((ROOT/'sql/04_policy_deciles.sql').read_text()).df().to_csv(OUT/'04_policy_deciles.csv',index=False)
    summary={'selected_model':chosen,'n_pair':len(pair),'splits':{'train':len(train),'validation':len(val),'test':len(test)},'n_test_treatment':int(test.treatment.sum()),'n_test_control':int((1-test.treatment).sum()),'capacity_fraction':float(fraction),'seed':SEED,'selection_metric':CONFIG['selection_metric'],'bootstrap_note':'Paired record bootstrap holding fitted scores and policy selection fixed; excludes training and cohort cutoff uncertainty','propensity':.5,'test_ate_ipw':normal_mean_ci(test_z)}
    return summary

def main():
    df=load_data();quality=quality_and_sql(df);ab,adjusted=ab_analysis(df)
    pair=df[df.segment.isin([CONTROL,TREATMENT])].copy();pair['treatment']=(pair.segment==TREATMENT).astype(int)
    subgroup_analysis(pair);summary=uplift_analysis(pair)
    summary['quality']=quality;summary['versions']={'python':platform.python_version()}
    import sklearn,scipy,statsmodels
    for package in [np,pd,sklearn,scipy,duckdb,statsmodels]:summary['versions'][package.__name__]=package.__version__
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(ab[['treatment','outcome','effect','ci_low','ci_high','p_holm_six']].to_string(index=False))
    print(pd.read_csv(OUT/'policy_evaluation.csv').to_string(index=False));print(pd.read_csv(OUT/'policy_differences.csv').to_string(index=False))
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
