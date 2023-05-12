from re import fullmatch

from regina.database import Database
from regina.utility.globals import settings
from regina.utility.utility import pdebug, warning, missing_arg, is_blacklisted, is_whitelisted
from regina.data_visualization.utility import is_valid_status, cleanup_referer


def get_route_ranking(db: Database, date_condition:str) -> list[tuple[int, str]]:
    """
    :returns [(request_count, route name)]
    """
    ranking = []
    for (route_id, name) in db(f"SELECT route_id, name FROM route"):
        if     is_blacklisted(name, settings["route_ranking_blacklist"]): continue
        if not is_whitelisted(name, settings["route_ranking_whitelist"]): continue
        if settings["route_ranking_ignore_404"]:  # use only succesful routes
            success = False
            for (status) in db(f"SELECT status FROM request WHERE route_id = {route_id}"):
                if is_valid_status(status):
                    pdebug(f"get_route_ranking: success code {status} for route with route_id {route_id} and name {name}")
                    success = True
                    break
            if not success:
                pdebug(f"get_route_ranking: route with route_id {route_id} and name {name} has only requests resulting in error")
                continue
        db.execute(f"SELECT COUNT(*) FROM request WHERE route_id = {route_id} AND {date_condition}")
        ranking.append((db.fetchone()[0], name))
    ranking.sort()
    return ranking


def get_ranking(db: Database, table: str, field_name: str, date_condition:str, whitelist_regex: str|list[str]|None=None, blacklist_regex: str|list[str]|None=None) -> list[tuple[int, str]]:
    """
    1) get all the distinct entries for field_name after min_date_unix_time
    2) call get_name_function with the distinct entry
    3) skip if not fully matching regex whitelist
    4) skip if fully matching regex blacklist
    5) for every entry, get the count in table after min_date_unix_time
    6) sort by count in ascending order
    @returns [(count, name)]
    """
    ranking = []
    for (name) in db(f"SELECT DISTINCT {field_name} FROM {table} WHERE {date_condition}"):
        if     is_blacklisted(name, blacklist_regex): continue
        if not is_whitelisted(name, whitelist_regex): continue
        db.execute(f"SELECT COUNT(*) FROM {table} WHERE {field_name} = '{name}' AND {date_condition}")
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


def get_city_and_country_ranking(db: Database, require_humans=True):
    """
    @returns [(count, "city (CO)")], [(count, country)]
    """
    cities_dict = {}
    country_dict = {}

    sql_cmd = f"SELECT ci.name, co.code, co.name FROM country AS co, city as ci, visitor as v, ip_range as i WHERE v.ip_range_id = i.ip_range_id AND i.city_id = ci.city_id AND ci.country_id = co.country_id"
    if require_humans: sql_cmd += " AND v.is_human = 1"
    result = db(sql_cmd)

    for (city, country_code, country) in result:
        if city in cities_dict:
            cities_dict[city][0] += 1
        else:
            if     is_blacklisted(city, settings["city_ranking_blacklist"]): continue
            if not is_whitelisted(city, settings["city_ranking_whitelist"]): continue
            cities_dict[city] = [1, country_code, country]  # count, country code

        if country in country_dict:
            country_dict[country] += 1
        else:
            if     is_blacklisted(country, settings["country_ranking_blacklist"]): continue
            if not is_whitelisted(country, settings["country_ranking_whitelist"]): continue
            country_dict[country] = 1  # count, country code

    city_ranking = [(v[0], f"{city} ({v[1]})") for city,v in cities_dict.items()]
    city_ranking.sort()
    country_ranking = [(count, country) for country,count in country_dict.items()]
    country_ranking.sort()
    return city_ranking, country_ranking


def get_platform_browser_mobile_rankings(db: Database, visitor_ids: list[int]) -> tuple[list[tuple[int, str]], list[tuple[int, str]], float]:
    """
    returns [(count, operating_system)], [(count, browser)], mobile_visitor_percentage
    """
    platform_ranking = {}
    platform_count = 0.0
    browser_ranking = {}
    browser_count = 0.0
    mobile_ranking = { True: 0.0, False: 0.0 }
    for visitor_id in visitor_ids:
        platform_id, browser_id, is_mobile = db(f"SELECT platform_id, browser_id, is_mobile FROM visitor WHERE visitor_id = {visitor_id}")[0]
        is_mobile = bool(is_mobile)
        if platform_id:
            if platform_id in platform_ranking: platform_ranking[platform_id] += 1
            else: platform_ranking[platform_id] = 1
            platform_count += 1
        if browser_id:
            if browser_id in browser_ranking: browser_ranking[browser_id] += 1
            else: browser_ranking[browser_id] = 1
            browser_count += 1
        if (platform_id or browser_id):
            mobile_ranking[is_mobile] += 1
    try:
        mobile_visitor_percentage = mobile_ranking[True] / (mobile_ranking[True] + mobile_ranking[False])
    except ZeroDivisionError:
        mobile_visitor_percentage = 0.0

    platform_ranking =  [(c * 100/platform_count, db.get_name("platform", p_id)) for p_id, c in platform_ranking.items()]
    platform_ranking.sort()
    browser_ranking = [(c * 100/browser_count, db.get_name("browser", b_id)) for b_id, c in browser_ranking.items()]
    browser_ranking.sort()
    return platform_ranking, browser_ranking, mobile_visitor_percentage*100


# Store ranking in results class and dump with pickle
# class Results:
#     def __init__(self, timespan_name,
#                  r_routes:	    list[tuple[int, str]],
#                  r_referrers:	list[tuple[int, str]],
#                  r_platforms:	list[tuple[int, str]],
#                  r_browsers:	list[tuple[int, str]],
#                  r_cities:	    list[tuple[int, str]],
#                  r_countries:	list[tuple[int, str]],
#                  ):
#         self.r_routes   = r_routes
#         self.r_referrers= r_referrers
#         self.r_platforms= r_platforms
#         self.r_browsers = r_browsers
#         self.r_cities   = r_cities
#         self.r_countries= r_countries


