SELECT COUNT(*) AS n,
       SUM(CASE WHEN conversion > visit THEN 1 ELSE 0 END) AS purchase_without_visit,
       SUM(CASE WHEN spend < 0 THEN 1 ELSE 0 END) AS negative_spend,
       SUM(CASE WHEN spend > 0 AND conversion = 0 THEN 1 ELSE 0 END) AS positive_spend_without_conversion,
       SUM(CASE WHEN history < 0 OR recency < 1 OR recency > 12 THEN 1 ELSE 0 END) AS invalid_history
FROM customers;
