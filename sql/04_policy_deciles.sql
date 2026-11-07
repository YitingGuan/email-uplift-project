-- Runs only AFTER scoring the held-out test set. No outcomes in ranking.
WITH ranked AS (
 SELECT *, NTILE(10) OVER (ORDER BY uplift_score DESC, record_id) AS decile
 FROM scored_customers
)
SELECT decile, COUNT(*) AS n,
       COUNT(*) FILTER (WHERE treatment=1) AS n_treated,
       COUNT(*) FILTER (WHERE treatment=0) AS n_control,
       AVG(uplift_score) AS mean_predicted_effect,
       AVG(visit) FILTER (WHERE treatment=1) AS treated_visit_rate,
       AVG(visit) FILTER (WHERE treatment=0) AS control_visit_rate,
       AVG(CASE WHEN treatment=1 THEN 2.0*visit ELSE -2.0*visit END) AS mean_ipw_effect
FROM ranked
GROUP BY decile ORDER BY decile;
