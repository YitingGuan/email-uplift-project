-- Descriptive slice; do not condition revenue comparison on post-treatment visit.
SELECT segment, newbie, channel, COUNT(*) AS n,
       AVG(visit) AS visit_rate, AVG(conversion) AS conversion_rate,
       AVG(spend) AS revenue_per_assigned_customer
FROM customers
GROUP BY segment, newbie, channel
ORDER BY newbie, channel, segment;
