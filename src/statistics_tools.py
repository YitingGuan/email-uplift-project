"""Transparent estimators used in the report. Effects are in original outcome units."""
import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests
import statsmodels.api as sm

def mean_difference(y1,y0):
    y1=np.asarray(y1,float);y0=np.asarray(y0,float)
    v1=y1.var(ddof=1)/len(y1);v0=y0.var(ddof=1)/len(y0)
    se=np.sqrt(v1+v0);df=(v1+v0)**2/(v1*v1/(len(y1)-1)+v0*v0/(len(y0)-1))
    effect=y1.mean()-y0.mean();critical=stats.t.ppf(.975,df)
    p=2*stats.t.sf(abs(effect/se),df) if se>0 else float(effect==0)
    return dict(effect=float(effect),se=float(se),ci_low=float(effect-critical*se),ci_high=float(effect+critical*se),p_value=float(p))

def cuped_ancova(df,outcome):
    """CUPED-style single pre-treatment covariate adjustment, HC2 robust SE.

    OLS jointly estimates T and the coefficient of centered log1p(history).
    It is ANCOVA, not an unsupported claim of a preperiod same-metric CUPED.
    """
    x=np.log1p(df.history.to_numpy());x=x-x.mean()
    design=np.column_stack([np.ones(len(df)),df.treatment.to_numpy(),x])
    fit=sm.OLS(df[outcome].to_numpy(),design).fit(cov_type='HC2')
    low,high=fit.conf_int()[1]
    return dict(effect=float(fit.params[1]),se=float(fit.bse[1]),ci_low=float(low),ci_high=float(high),p_value=float(fit.pvalues[1]),covariate_beta=float(fit.params[2]))

def ipw_score(y,t,e=.5):
    """Horvitz-Thompson incremental pseudo-outcome for known randomized assignment."""
    y=np.asarray(y,float);t=np.asarray(t,int)
    if not 0<e<1:raise ValueError('Assignment propensity must be between 0 and 1')
    return t*y/e-(1-t)*y/(1-e)

def normal_mean_ci(values):
    a=np.asarray(values,float);se=a.std(ddof=1)/np.sqrt(len(a));m=a.mean()
    return dict(estimate=float(m),ci_low=float(m-1.96*se),ci_high=float(m+1.96*se),se=float(se))

def policy_mask(scores,fraction):
    """Fixed fraction capacity policy. Stable tie-breaking by current row order."""
    scores=np.asarray(scores);n=len(scores)
    if not 0<=fraction<=1:raise ValueError('fraction outside [0,1]')
    k=int(np.floor(n*fraction));mask=np.zeros(n,dtype=float)
    mask[np.argsort(-scores,kind='stable')[:k]]=1
    return mask

def bootstrap_means(matrix,replicates=1500,seed=42):
    """Paired record bootstrap; fitted scores and selected policy are held fixed.

    Policies are NOT retrained or re-ranked inside bootstrap. Conditional
    uncertainty only; model-training and cohort-threshold uncertainty excluded.
    """
    a=np.asarray(matrix,float)
    if a.ndim==1:a=a[:,None]
    rng=np.random.default_rng(seed);est=np.empty((replicates,a.shape[1]))
    for b in range(replicates):est[b]=a[rng.integers(0,len(a),len(a))].mean(axis=0)
    return np.quantile(est,[.025,.975],axis=0)

def holm(p):return multipletests(p,method='holm')[1]
