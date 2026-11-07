-- One row is one randomized record. No fabricated event or order tables.
SELECT segment, COUNT(*) AS n,
       SUM(visit) AS visitors, AVG(visit) AS visit_rate,
       SUM(conversion) AS converters, AVG(conversion) AS conversion_rate,
       SUM(spend) AS total_spend, AVG(spend) AS revenue_per_assigned_customer,
       AVG(history) AS historical_spend_mean
FROM customers
GROUP BY segment ORDER BY segment;
