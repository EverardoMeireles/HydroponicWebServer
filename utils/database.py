import ujson
import sqlite3
from utils.config import config

# database path
DATABASE = config.get("Database", "db_path")

if config.getboolean("Database", "db_optimization") is not True:
    connection = sqlite3.connect(DATABASE, check_same_thread=False)

db_uncommitted_count = 0
# only commit after 100 uncommitted changes

with open('crawler/crawlers.json', 'r') as json_file:
    list_of_crawlers = ujson.load(json_file)


def execute_query(query):
    global db_uncommitted_count

    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    if config.getboolean("Database", "db_optimization") is not True:
        connection = sqlite3.connect(DATABASE, check_same_thread=False)

    connection.row_factory = dict_factory
    cursor = connection.cursor()
    query_result = cursor.execute(query)
    list_of_results = query_result.fetchall()
    if not list_of_results:
        db_uncommitted_count += 1
    else:
        return list_of_results

    if db_uncommitted_count == config.getint("Database", "db_uncommitted_limit")\
            and config.getboolean("Database", "db_optimization"):
        db_uncommitted_count = 0
        connection.commit()
    else:
        connection.commit()


# takes dictionary
def select_crawler(condition):
    crawlers_to_return = []
    for crawler in list_of_crawlers:
        for value in sorted(condition):
            if crawler[value] == condition[value]:
                crawlers_to_return.append(crawler)
    return crawlers_to_return


def update_crawler(serial_number, updated_values):
    for crawler in list_of_crawlers:
        if crawler['serial_number'] == serial_number:
            for value in sorted(updated_values):
                crawler[value] = updated_values[value]
            break


def save_crawler():
    with open('crawler/crawlers.json', 'w') as json_file:
        ujson.dump(list_of_crawlers, json_file)