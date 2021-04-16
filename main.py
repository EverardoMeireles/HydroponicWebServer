#!/usr/bin/env python

import asyncio
import websockets
import threading
import time
import sqlite3
from flask import Flask, json
import datetime
import pytz
from schedule import Schedule
from pathfinding import PathFinding
import builtins
import os
import cProfile
import re

# frames_receive = []
api = Flask(__name__)

# database path
DATABASE = r'C:\sqlite3\hydroponicDatabase.db'
# global db connection
# connection = sqlite3.connect(r"C:\sqlite3\hydroponicDatabase.db", check_same_thread=False)
db_uncommitted_count = 0
# only commit after 100 uncommitted changes
db_uncommitted_limit = 100

frames_result = []
schedule_list = []

builtins.room_map = [["Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z"],
                     ["Z", "G", "Z", "Z", "G", "Z", "Z", "Z", "G", "Z"],
                     ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
                     ["Z", "Z", "G", "G", "G", "Z", "Z", "Z", "G", "Z"],
                     ["Z", "Z", "Z", "G", "Z", "Z", "G", "Z", "Z", "Z"],
                     ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
                     ["Z", "Z", "Z", "G", "G", "Z", "Z", "Z", "G", "Z"],
                     ["Z", "Z", "Z", "G", "Z", "Z", "G", "Z", "Z", "Z"],
                     ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
                     ["Z", "Z", "Z", "Z", "G", "Z", "Z", "Z", "G", "Z"]]

device_has_pending_instructions = []

start_with_profiler = True

if start_with_profiler:
    pid = os.getpid()
    os.system("profiler.bat " + str(pid))


@api.route('/all', methods=['GET'])
# get all sensor information
def get_all():
    print(frames_result)
    return json.dumps(frames_result)


def execute_query(query):
    global db_uncommitted_count
    global db_uncommitted_count

    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    connection = sqlite3.connect(r"C:\sqlite3\hydroponicDatabase.db", check_same_thread=False)
    connection.row_factory = dict_factory
    cursor = connection.cursor()
    query_result = cursor.execute(query)
    list_of_results = query_result.fetchall()
    if not list_of_results:
        db_uncommitted_count += 1
    else:
        return list_of_results

    if db_uncommitted_count == db_uncommitted_limit:
        db_uncommitted_count = 0
        connection.commit()


def frame_breakdown(frame):
    all_frames = frame.split("&")
    for current_frame in all_frames:
        dictionary_item = current_frame.split("@")
        frame_dictionary = {
            'device': dictionary_item[0],
            'serial_number': int(dictionary_item[1]),
            'value': dictionary_item[2],
            'frame_type': dictionary_item[3]
        }
        frames_result.append(frame_dictionary)
    return frames_result


def prepare_to_send_instructions(serial_number):
    global device_has_pending_instructions
    global schedule_list
    # if there are no instructions for this esp "" will be sent
    instruction_to_send = ""
    if int(serial_number) in device_has_pending_instructions:
        counter = 0
        for schedule in schedule_list:
            if schedule.serial_number == serial_number:
                instruction_to_send = schedule.instruction
                schedule_list.pop(counter)
                break
            counter += 1
        schedules_counter = 0
        for schedule in schedule_list:
            if schedule is not None and schedule.serial_number == serial_number:
                schedules_counter += 1
        if schedules_counter == 0:
            device_has_pending_instructions[device_has_pending_instructions.index(serial_number)] = None

    # if the instruction is about starting the crawler, change the contents of the instruction to the directions
    # it should be moving
    for instruction in instruction_to_send:
        if "GOTO" in instruction:
            # get first available crawler's data
            crawler_serial_number = execute_query("SELECT serial_number FROM crawlers WHERE status = 'available'")[0]
            starting_position_x = execute_query("SELECT resting_position_x FROM crawlers WHERE status = 'available'")[0]
            starting_position_y = execute_query("SELECT resting_position_y FROM crawlers WHERE status = 'available'")[0]
            destination_x = instruction[5]
            destination_y = instruction[7]

            path = PathFinding({"y": starting_position_y, "x": starting_position_x},
                               {"y": destination_y, "x": destination_x},
                               schedule.timestamp)
            path.a_star_start()
            crawler_directions = path.final_directions
            execute_query("UPDATE crawlers SET status = moving, directions = " + crawler_directions + ", timestamp =" +
                          path.time_started_moving + " ... WHERE serial_number = " + crawler_serial_number + ";")

            instruction_to_send = "PATH:" + path.final_directions
            print(instruction)
    return instruction_to_send


def apply_frame_processing_type(result):
    for frame in result:
        # log into database(sensor data)
        if frame['frame_type'] in ["temperature", "humidity"]:
            log_into_database(frame)

        # elif frame['frame_type'] == "move_crawler":


# process temperature and humidity frames
def log_into_database(frame):
    execute_query("INSERT INTO " + frame['frame_type'] + " (serial_number, value, timestamp) "
                                                         "VALUES(" + str(frame['serial_number'])
                  + ", " + str(int(frame['value'])) + ", "
                  + str(int(datetime.datetime.now(pytz.timezone('Europe/Berlin')).timestamp())) + ");")


# Socket Server
async def receiver(websocket, path):
    frames_receive = (await websocket.recv())
    global frames_result
    frames_result = frame_breakdown(frames_receive)
    apply_frame_processing_type(frames_result)
    instruction_to_send = prepare_to_send_instructions(frames_result[0]['serial_number'])
    frames_result = []
    await websocket.send(instruction_to_send)


# Socket Server thread
def thread_socket_server():
    asyncio.set_event_loop(asyncio.new_event_loop())
    start_server = websockets.serve(receiver, "192.168.1.58", 5153)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
    api.run()


def rest_api_server():
    if __name__ == '__main__':
        api.run(host="0.0.0.0", port=5154, debug=False)


# crawlers = []
# # get list of crawlers from database
# def updateCrawlerList():
#     global crawlers
#     query_result = execute_query("SELECT * FROM crawlers")
#     for column in query_result:
#         crawlers.appe


def scheduler():
    global schedule_list
    while True:
        ct = datetime.datetime.now(pytz.timezone('Europe/Berlin'))
        ts = ct.timestamp()
        # prevents timestamp from skipping a second due cpu delay
        if (ts % 1) < 0.97:
            time.sleep(1)
        else:
            time.sleep(1 - (ts % 1))

        print(ts)
        if execute_query("SELECT MIN(schedule_timestamp) FROM schedule")[0]['MIN(schedule_timestamp)'] == int(ts):
            results = execute_query("SELECT serial_number, instruction, to_delete, type, schedule_id FROM schedule "
                                    "WHERE schedule_timestamp = " + str(int(ts)) + ";")

            if len(results) > 1:
                for result in results:
                    if result['serial_number'] not in device_has_pending_instructions:
                        device_has_pending_instructions.append(result['serial_number'])
            else:
                if results[0]['serial_number'] not in device_has_pending_instructions:
                    device_has_pending_instructions.append(results[0]['serial_number'])

            counter = 0
            while counter < len(results):
                schedule_list.append(Schedule(results[counter]['serial_number'],
                                              results[counter]['instruction'],
                                              results[counter]['to_delete'],
                                              results[counter]['type'],
                                              int(ts)))
                counter += 1

            for result in results:
                if result['to_delete'] == 'TRUE':
                    execute_query("DELETE FROM schedule WHERE schedule_timestamp = " + str(int(ts)) +
                                  " AND schedule_id = " + str(result['scheduleId']) + ";")


thread_server = threading.Thread(target=thread_socket_server, args=())
thread_server.start()

api_server = threading.Thread(target=rest_api_server, args=())
api_server.start()

thread_scheduler = threading.Thread(target=scheduler, args=())
thread_scheduler.start()

# temporary, test purposes
dd = PathFinding({"y": 8, "x": 1}, {"y": 1, "x": 1}, 1617633825)
# cProfile.run('dd.a_star_start()')
dd.a_star_start()

