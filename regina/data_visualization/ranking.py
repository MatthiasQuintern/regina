from re import fullmatch

from regina.database import Database
from regina.utility.globals import settings
from regina.utility.utility import pdebug, warning, is_blacklisted, is_whitelisted
from regina.utility.sql_util import sanitize
from regina.data_visualization.utility import is_valid_status, cleanup_referer


def get_route_ranking(db: Database, timestamps: tuple[int, int]) -> list[tuple[int, str]]:
    """
    :returns [(request_count, route name)]
    """
    ranking = []
    for (route_id, name) in db(f"SELECT route_id, name FROM route"):
        if     is_blacklisted(name, settings["rankings"]["route_blacklist"]): continue
        if not is_whitelisted(name, settings["rankings"]["route_whitelist"]): continue
        if settings["rankings"]["route_ignore_404"]:  # use only succesful routes
            success = False
            for (status, ) in db(f"SELECT status FROM request WHERE route_id = {route_id}"):
                if is_valid_status(status):
                    pdebug(f"get_route_ranking: success code {status} for route with route_id {route_id} and name {name}", lvl=4)
                    success = True
                    break
            if not success:
                pdebug(f"get_route_ranking: route with route_id {route_id} and name {name} has only requests resulting in error", lvl=3)
                continue
        db.execute(f"SELECT COUNT(*) FROM request WHERE route_id = {route_id} AND time BETWEEN {timestamps[0]} AND {timestamps[1]}")
        ranking.append((db.fetchone()[0], name))
    ranking.sort()
    return ranking

def route_ranking_group_routes(route_ranking: list[tuple[int, str]]):
    """
    group the routes in the route ranking according the groups defined in the config section "route-groups"
    """
    ranking = {}
    for count, route in route_ranking:
        ingroup = False
        for group_name, group_regexp in settings["route-groups"].items():
            if fullmatch(group_regexp, route):
                if group_name in ranking:
                    ranking[group_name] += count
                else:
                    ranking[group_name] = count
                ingroup = True
        if not ingroup:
            ranking[route] = count
    ranking = [ (c, name) for name, c in ranking.items() ]
    ranking.sort()
    return ranking


def get_referer_ranking(db: Database, timestamps: tuple[int, int]) -> list[tuple[int, str]]:
    """
    @returns [(count, referer)]
    """
    ranking = []
    for referer_id, name in db(f"SELECT referer_id, name FROM referer"):
        if     is_blacklisted(name, settings["rankings"]["referer_blacklist"]): continue
        if not is_whitelisted(name, settings["rankings"]["referer_whitelist"]): continue
        db.execute(f"SELECT COUNT(*) FROM request WHERE referer_id = {referer_id} AND time BETWEEN {timestamps[0]} AND {timestamps[1]}")
        ranking.append((db.fetchone()[0], name))
    ranking.sort()
    return ranking

def cleanup_referer_ranking(referer_ranking: list[tuple[int, str]]):
    unique_referers = dict()
    for count, referer in referer_ranking:
        referer = cleanup_referer(referer)
        if referer in unique_referers:
            unique_referers[referer] += count
        else:
            unique_referers[referer] = count
    referer_ranking.clear()
    for referer, count in unique_referers.items():
        referer_ranking.append((count, referer))
    referer_ranking.sort()


def get_city_ranking(db: Database, timestamps: tuple[int, int], add_country_code=True, only_human=True):
    """
    @returns [(count, city (Country Code))]
    """
    ranking = []
    results = db(f"""SELECT co.code, ci.name,COUNT(v.visitor_id)
        FROM country as co, city as ci, visitor as v, ip_range as i
        WHERE ci.city_id = i.city_id
        AND co.country_id = ci.country_id
        AND i.ip_range_id = v.ip_range_id
        AND EXISTS(
            SELECT 1
            FROM request AS r
            WHERE r.visitor_id = v.visitor_id
            AND r.time BETWEEN {timestamps[0]} AND {timestamps[1]}
        )
        {'AND v.is_human = 1' if only_human else ''}
        GROUP BY ci.name
        ORDER BY COUNT(v.visitor_id)
        """)
    for code, name, count in results:
        if     is_blacklisted(name, settings["rankings"]["city_blacklist"]): continue
        if not is_whitelisted(name, settings["rankings"]["city_whitelist"]): continue
        if add_country_code:
            name = f"{name} ({code})"
        ranking.append((count, name))
    # for (city_id, name) in db(f"SELECT city_id, name FROM city"):
    #     if     is_blacklisted(name, settings["rankings"]["city_blacklist"]): continue
    #     if not is_whitelisted(name, settings["rankings"]["city_whitelist"]): continue
    #     db.execute(f"""SELECT COUNT(v.visitor_id)
    #     FROM visitor AS v, ip_range AS i
    #     WHERE i.city_id = {city_id}
    #     AND i.ip_range_id = v.ip_range_id
    #     AND EXISTS(
    #         SELECT 1
    #         FROM request AS r
    #         WHERE r.visitor_id = v.visitor_id
    #         AND r.time BETWEEN {timestamps[0]} AND {timestamps[1]}
    #     )
    #     {'AND v.is_human = 1' if only_human else ''}""")
    #     ranking.append((db.fetchone()[0], name))
    ranking.sort()
    return ranking


def get_country_ranking(db: Database, timestamps: tuple[int, int], only_human=True):
    """
    @returns [(count, country)]
    """
    ranking = []
    # for (country_id, name) in db(f"SELECT country_id, name FROM country"):
    #     if     is_blacklisted(name, settings["rankings"]["country_blacklist"]): continue
    #     if not is_whitelisted(name, settings["rankings"]["country_whitelist"]): continue
    #     db.execute(f"""SELECT COUNT(v.visitor_id)
    #     FROM visitor AS v, ip_range AS i, city AS ci
    #     WHERE ci.country_id = {country_id}
    #     AND ci.city_id = i.city_id
    #     AND i.ip_range_id = v.ip_range_id
    #     AND EXISTS(
    #         SELECT 1
    #         FROM request AS r
    #         WHERE r.visitor_id = v.visitor_id
    #         AND r.time BETWEEN {timestamps[0]} AND {timestamps[1]}
    #     )
    #     {'AND v.is_human = 1' if only_human else ''}""")
    #     ranking.append((db.fetchone()[0], name))
    results = db(f"""SELECT co.name,COUNT(v.visitor_id)
        FROM country as co, city as ci, visitor as v, ip_range as i
        WHERE co.country_id = ci.country_id
        AND ci.city_id = i.city_id
        AND i.ip_range_id = v.ip_range_id
        AND EXISTS(
            SELECT 1
            FROM request AS r
            WHERE r.visitor_id = v.visitor_id
            AND r.time BETWEEN {timestamps[0]} AND {timestamps[1]}
        )
        {'AND v.is_human = 1' if only_human else ''}
        GROUP BY co.name
        ORDER BY COUNT(v.visitor_id)
        """)
    for name, count in results:
        if     is_blacklisted(name, settings["rankings"]["country_blacklist"]): continue
        if not is_whitelisted(name, settings["rankings"]["country_whitelist"]): continue
        ranking.append((count, name))
    ranking.sort()
    return ranking


def _get_platform_or_browser_ranking(db: Database, timestamps: tuple[int, int], table: str, only_human=False):
    ranking = []
    for (table_id, name) in db(f"SELECT {table}_id, name FROM {table}"):
        # if     is_blacklisted(name, settings["rankings"][f"{table}_blacklist"]): continue
        # if not is_whitelisted(name, settings["rankings"][f"{table}_whitelist"]): continue
        if name == "None": continue
        db.execute(f"""SELECT COUNT(v.visitor_id)
        FROM visitor AS v, {table} AS t
        WHERE v.{table}_id = {table_id}
        AND EXISTS(
            SELECT 1
            FROM request AS r
            WHERE r.visitor_id = v.visitor_id
            AND r.time BETWEEN {timestamps[0]} AND {timestamps[1]}
        )
        {'AND v.is_human = 1' if only_human else ''}""")
        count = db.fetchoone()[0]
        if count > 0:
            ranking.append((count, name))
    ranking.sort()
    return ranking

def get_platform_ranking(db: Database, timestamps: tuple[int, int], only_human=False):
    return _get_platform_or_browser_ranking(db, timestamps, "platform", only_human=only_human)

def get_browser_ranking(db: Database, timestamps: tuple[int, int], only_human=False):
    return _get_platform_or_browser_ranking(db, timestamps, "browser", only_human=only_human)


def make_ranking_relative(ranking: list[tuple[int, str]]) -> list[tuple[float, str]]:
    total_count = sum([ c for c, _ in ranking ])
    if total_count == 0:
        warning(f"make_ranking_relative: Can not make ranking relative, total_count is 0")
        return [ (float(c), name) for c, name in ranking ]
    rel_ranking = [ (100.0*c/total_count, name) for c, name in ranking ]
    return rel_ranking



