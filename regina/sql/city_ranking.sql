-- unused
SELECT ci.name,COUNT(v.visitor_id)
FROM city as ci, visitor as v, ip_range as i
WHERE ci.city_id = i.city_id
AND i.ip_range_id = v.ip_range_id
AND EXISTS(
    SELECT 1
    FROM request AS r
    WHERE r.visitor_id = v.visitor_id
    AND r.time BETWEEN {timestamps[0]} AND {timestamps[1]}
)
GROUP BY ci.name
ORDER BY COUNT(v.visitor_id)
