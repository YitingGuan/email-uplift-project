import unittest,sys,json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import ttest_ind
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from statistics_tools import mean_difference,ipw_score,policy_mask,holm,bootstrap_means
from run_analysis import load_data,make_splits
from uplift_models import FEATURES,MetaLearner

class StatisticalTests(unittest.TestCase):
    def test_welch_matches_scipy(self):
        a=np.array([0.,0,1,0,1,4]);b=np.array([0.,0,0,1,0])
        actual=mean_difference(a,b);reference=ttest_ind(a,b,equal_var=False)
        self.assertAlmostEqual(actual['p_value'],reference.pvalue,places=12)
    def test_ht_balanced_identifies_difference(self):
        t=np.array([1,0,1,0,1,0]);y=np.array([1,0,0,0,1,1])
        self.assertAlmostEqual(ipw_score(y,t).mean(),y[t==1].mean()-y[t==0].mean())
    def test_known_ipw_propensity(self):
        # Four equally weighted records, 25% assigned treatment.
        t=np.array([1,0,0,0]);y=np.array([1,0,0,0]);self.assertEqual(ipw_score(y,t,.25).mean(),1.)
    def test_holm_known_example(self):
        np.testing.assert_allclose(holm([.01,.04,.03]),[.03,.06,.06])
    def test_policy_never_uses_outcome(self):
        scores=np.array([.3,-.1,.4,.2,.1]);np.testing.assert_array_equal(policy_mask(scores,.4),[1,0,1,0,0])
    def test_paired_bootstrap_identical_policies(self):
        a=np.arange(100,dtype=float);ci=bootstrap_means(np.column_stack([a-a]),50,1)
        np.testing.assert_array_equal(ci,np.zeros((2,1)))
    def test_invalid_propensity_rejected(self):
        with self.assertRaises(ValueError):ipw_score([1],[1],0)

class ProjectIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.df=load_data()
    def test_duplicate_profiles_retained(self):
        self.assertEqual(len(self.df),64000)
        self.assertGreater(self.df.drop(columns='record_id').duplicated().sum(),0)
        self.assertEqual(self.df.record_id.nunique(),len(self.df))
    def test_feature_leakage_guard(self):
        self.assertFalse(set(FEATURES)&{'visit','conversion','spend','segment','record_id'})
    def test_partition_disjoint_and_complete(self):
        pair=self.df[self.df.segment.isin(['Mens E-Mail','No E-Mail'])].copy();pair['treatment']=(pair.segment=='Mens E-Mail').astype(int)
        parts=make_splits(pair);sets=[set(p.record_id) for p in parts]
        self.assertFalse(sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2])
        self.assertEqual(len(set.union(*sets)),len(pair))
    def test_sql_totals(self):
        report=pd.read_csv(ROOT/'reports/01_arm_metrics.csv');self.assertEqual(int(report.n.sum()),len(self.df))
        self.assertEqual(int(report.visitors.sum()),int(self.df.visit.sum()))
    def test_policy_recomputes_from_private_predictions(self):
        path=ROOT/'data/processed/test_scores.csv'
        if not path.exists():self.skipTest('Run analysis to generate private local test scores')
        d=pd.read_csv(path);v=np.mean(d.selected*ipw_score(d.visit,d.treatment))*1000
        report=pd.read_csv(ROOT/'reports/policy_evaluation.csv')
        self.assertAlmostEqual(v,float(report.loc[report.policy=='uplift_top30','incremental_visits_per_1000'].iloc[0]),places=9)
    def test_selected_model_from_validation(self):
        s=json.loads((ROOT/'reports/summary.json').read_text());v=pd.read_csv(ROOT/'reports/model_selection.csv')
        chosen=v.sort_values('validation_gain_per_1000',ascending=False,kind='stable').iloc[0].model
        self.assertEqual(s['selected_model'],chosen)
    def test_sql_deciles_partition_test(self):
        d=pd.read_csv(ROOT/'reports/04_policy_deciles.csv');s=json.loads((ROOT/'reports/summary.json').read_text())
        self.assertEqual(int(d.n.sum()),s['splits']['test'])
    def test_exported_confidence_order(self):
        for f in ['ab_effects.csv','policy_evaluation.csv','policy_differences.csv']:
            d=pd.read_csv(ROOT/'reports'/f);self.assertTrue((d.ci_low<=d.ci_high).all())
if __name__=='__main__':unittest.main()
