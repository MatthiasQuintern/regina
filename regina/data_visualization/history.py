from regina.database import Database

def get_visitor_count_between(db: Database, timestamps: tuple[int, int], only_human=False):
    return db(f"""SELECT COUNT(visitor_id)
    FROM visitor AS v
    WHERE EXISTS (
        SELECT 1
        FROM request as r
        WHERE r.visitor_id = v.visitor_id
        AND r.time BETWEEN {timestamps[0]} AND {timestamps[1]}
    )
    {'AND v.is_human = 1' if only_human else ''}""")[0][0]

def get_request_count_between(db: Database, timestamps: tuple[int, int], only_human=False):
    return db(f"""SELECT COUNT(r.request_id)
    FROM request AS r, visitor AS v
    WHERE r.time BETWEEN {timestamps[0]} AND {timestamps[1]}
    {'AND v.is_human = 1' if only_human else ''}""")[0][0]


def get_new_visitor_count_between(db: Database, timestamps: tuple[int, int]):
    return db(f"""SELECT COUNT(*)
    FROM visitor AS v
    JOIN (
        SELECT visitor_id, MIN(time) AS first_request_time
        FROM request
        GROUP BY visitor_id
    ) AS r ON v.visitor_id = r.visitor_id
    WHERE r.first_request_time BETWEEN {timestamps[0]} AND {timestamps[1]}""")[0][0]

def get_request_from_new_visitor_count_between(db: Database, timestamps: tuple[int, int]):
    return db(f"""SELECT COUNT(*)
    FROM request AS r
    JOIN (
        SELECT visitor_id, MIN(time) AS first_request_time
        FROM request
        GROUP BY visitor_id
    ) AS v ON r.visitor_id = v.visitor_id
    WHERE v.first_request_time BETWEEN {timestamps[0]} AND {timestamps[1]}""")[0][0]


def get_mobile_visitor_count_between(db: Database, timestamps: tuple[int, int], only_human=True) -> float:
    return db(f"""SELECT COUNT(*)
    FROM visitor AS v
    WHERE EXISTS (
        SELECT 1
        FROM request as r
        WHERE r.visitor_id = v.visitor_id
        AND r.time BETWEEN {timestamps[0]} AND {timestamps[1]}
    )
    {'AND v.is_human = 1' if only_human else ''}
    AND v.is_mobile = 1""")[0][0]

