-- unused
SELECT co.name,COUNT(v.visitor_id)
FROM country as co, city as ci, visitor as v, ip_range as i
WHERE co.country_id = ci.country_id
    AND ci.city_id = i.city_id
    AND i.ip_range_id = v.ip_range_id
GROUP BY co.name
ORDER BY COUNT(v.visitor_id)
