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

# frames_receive = []
api = Flask(__name__)

DATABASE = 'C:\sqlite3\hydroponicDatabase.db'

frames_result = []
schedule_list = []

builtins.room_map = [["Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z"],
                     ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
                     ["Z", "Z", "Z", "G", "Z", "Z", "G", "Z", "Z", "Z"],
                     ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
                     ["Z", "Z", "Z", "G", "Z", "Z", "G", "Z", "Z", "Z"],
                     ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
                     ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
                     ["Z", "Z", "Z", "G", "Z", "Z", "G", "Z", "Z", "Z"],
                     ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
                     ["Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z"]]

device_has_pending_instructions = []


@api.route('/all', methods=['GET'])
# get all sensor information
def get_all():
    # all = [{"temperature": 1, "name": "Company One"}, {"id": 2, "name": "Company Two"}]
    # connection = sqlite3.connect("C:\sqlite3\hydroponicDatabase.db")
    # cursor = connection.cursor()
    # cursor.execute("INSERT INTO esp3 values(85);")
    # connection.commit()
    # connection.close()
    print(frames_result)
    return json.dumps(frames_result)


def execute_query(query):
    connection = sqlite3.connect("C:\sqlite3\hydroponicDatabase.db")
    connection.row_factory = lambda cursor, row: row[0]
    cursor = connection.cursor()
    query_result = cursor.execute(query)
    connection.commit()
    return query_result.fetchall()
    # connection.close()


def frame_breakdown(frame):
    all_frames = frame.split("&")
    for current_frame in all_frames:
        dictionary_item = current_frame.split("@")
        frame_dictionary = {
            'device': dictionary_item[0],
            'id': int(dictionary_item[1]),
            'value': dictionary_item[2],
            'frametype': dictionary_item[3]
        }
        frames_result.append(frame_dictionary)
    return frames_result


# process temperature and humidity frames
def process_frames(result):
    for frame in result:
        if frame['frametype'] == "temperature" or frame['frametype'] == "humidity":
            execute_query("INSERT INTO " + frame['frametype'] + " (id, value, timestamp) VALUES(" + str(frame['id'])
                          + ", " + str(int(frame['value'])) + ", "
                          + str(int(datetime.datetime.now(pytz.timezone('Europe/Berlin')).timestamp())) + ");")

        # if frame['frametype'] == "crawlerstart":
        #     path = pathfinding({"y": 8, "x": 1}, {"y": 1, "x": 1})
        #     path.a_star_start()


def prepare_to_send_instructions(id):
    global device_has_pending_instructions
    global schedule_list
    # if there are no instructions for this esp "" will be sent
    instruction_to_send = ""

    if int(id) in device_has_pending_instructions:
        i = 0
        for schedule in schedule_list:
            print(schedule)
            if schedule.id == id:
                instruction_to_send = schedule.instruction
                schedule_list[i] = None
                break
            i = i + 1
        e = 0
        for schedule in schedule_list:
            if schedule is not None and schedule.id == id:
                e = e + 1
        if e == 0:
            device_has_pending_instructions[device_has_pending_instructions.index(id)] = None
    # if the instruction is about starting the crawler, change the contents of the instruction to the directions
    # it should be moving
    for instruction in instruction_to_send:
        if "GOTO" in instruction:
            # get next available crawler's data
            crawlers_directions = execute_query("SELECT directions FROM crawlers WHERE status = 'available'")[0]
            starting_position_x = execute_query("SELECT restingpositionx FROM crawlers WHERE status = 'available'")[0]
            starting_position_y = execute_query("SELECT restingpositiony FROM crawlers WHERE status = 'available'")[0]
            destination_x = instruction[5]
            destination_y = instruction[7]

            path = PathFinding({"y": starting_position_y, "x": starting_position_x},
                               {"y": destination_y, "x": destination_x},
                               schedule.timestamp)
            path.a_star_start()

    return instruction_to_send


# Socket Server
async def receiver(websocket, path):
    frames_receive = (await websocket.recv())
    global frames_result
    frames_result = frame_breakdown(frames_receive)
    process_frames(frames_result)
    instruction_to_send = prepare_to_send_instructions(frames_result[0]['id'])
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
    cycle_counter = 0
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
        if execute_query("SELECT MIN(scheduleTimestamp) FROM schedule")[0] == int(ts):
            id_query = "SELECT id FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + ";"
            instruction_query = "SELECT instruction FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + ";"
            to_delete_query = "SELECT to_delete FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + ";"
            type_query = "SELECT type FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + ";"
            ids_for_timestamp = execute_query(id_query)
            instructions_for_timestamp = execute_query(instruction_query)
            to_delete_for_timestamp = execute_query(to_delete_query)
            type_for_timestamp = execute_query(type_query)
            if len(ids_for_timestamp) > 1:
                for id in ids_for_timestamp:
                    if id not in device_has_pending_instructions:
                        device_has_pending_instructions.append(id)
            else:
                print(execute_query(id_query))
                if execute_query(id_query)[0] not in device_has_pending_instructions:
                    device_has_pending_instructions.append(execute_query(id_query)[0])

            if execute_query(to_delete_query)[0] == "TRUE":
                execute_query("DELETE FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + ";")

            i = 0
            while i < len(ids_for_timestamp):
                print(ids_for_timestamp)
                schedule_list.append(Schedule(ids_for_timestamp[i],
                                              instructions_for_timestamp[i],
                                              to_delete_for_timestamp[i],
                                              type_for_timestamp[i],
                                              int(ts)))
                i = i + 1

        # cut 'none' elements after 10 cycles
        if cycle_counter == 20:
            schedule_list = cut_none_elements(schedule_list)
            cycle_counter = 0

        cycle_counter = cycle_counter + 1


def cut_none_elements(original_list):
    temp_list = []
    for element in original_list:
        if element is not None:
            temp_list.append(element)

    return temp_list


thread_server = threading.Thread(target=thread_socket_server, args=())
thread_server.start()

api_server = threading.Thread(target=rest_api_server, args=())
api_server.start()

thread_scheduler = threading.Thread(target=scheduler, args=())
thread_scheduler.start()

# temporary, test purposes
dd = PathFinding({"y": 8, "x": 1}, {"y": 1, "x": 1}, 1617633825)
dd.a_star_start()
