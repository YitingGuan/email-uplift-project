"""S/T/X meta-learners built with scikit-learn; no copied library implementation.

Method references: Künzel et al. (2019); EconML meta-learner documentation.
Known assignment propensity is 0.5 in the selected pair of randomized arms.
"""
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder,StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier,HistGradientBoostingRegressor
from sklearn.pipeline import make_pipeline

CATEGORICAL=['zip_code','channel']
NUMERIC=['recency','log_history','mens','womens','newbie']
FEATURES=CATEGORICAL+NUMERIC

def features(df):
    result=df[CATEGORICAL+['recency','history','mens','womens','newbie']].copy()
    result['log_history']=np.log1p(result.pop('history'))
    return result[FEATURES]

def preprocessor():return ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore',sparse_output=False),CATEGORICAL),('num',StandardScaler(),NUMERIC)])

def classifier(kind,seed):
    if kind=='logistic':return LogisticRegression(C=1,max_iter=1000,random_state=seed)
    return HistGradientBoostingClassifier(max_iter=100,max_leaf_nodes=7,min_samples_leaf=150,learning_rate=.06,l2_regularization=10,early_stopping=False,random_state=seed)

def regressor(seed):return HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=7,min_samples_leaf=150,learning_rate=.06,l2_regularization=10,early_stopping=False,random_state=seed)

class MetaLearner:
    def __init__(self,name,seed=42):self.name=name;self.seed=seed
    def fit(self,df,y):
        self.prep=preprocessor();x=self.prep.fit_transform(features(df));t=df.treatment.to_numpy();y=np.asarray(y)
        if self.name=='s_hgb':
            self.single=classifier('hgb',self.seed).fit(np.column_stack([x,t]),y)
        else:
            kind='logistic' if self.name=='t_logistic' else 'hgb'
            self.control=classifier(kind,self.seed).fit(x[t==0],y[t==0])
            self.treated=classifier(kind,self.seed).fit(x[t==1],y[t==1])
            if self.name=='x_hgb':
                # Pseudo-effects for each arm use the opposite arm outcome model.
                d0=self.treated.predict_proba(x[t==0])[:,1]-y[t==0]
                d1=y[t==1]-self.control.predict_proba(x[t==1])[:,1]
                self.tau0=regressor(self.seed).fit(x[t==0],d0)
                self.tau1=regressor(self.seed).fit(x[t==1],d1)
        return self
    def predict(self,df):
        x=self.prep.transform(features(df))
        if self.name=='s_hgb':
            return self.single.predict_proba(np.column_stack([x,np.ones(len(x))]))[:,1]-self.single.predict_proba(np.column_stack([x,np.zeros(len(x))]))[:,1]
        if self.name=='x_hgb':return .5*self.tau0.predict(x)+.5*self.tau1.predict(x)
        return self.treated.predict_proba(x)[:,1]-self.control.predict_proba(x)[:,1]
    def response_score(self,df):
        x=self.prep.transform(features(df))
        if self.name=='s_hgb':return self.single.predict_proba(np.column_stack([x,np.ones(len(x))]))[:,1]
        return self.treated.predict_proba(x)[:,1]
