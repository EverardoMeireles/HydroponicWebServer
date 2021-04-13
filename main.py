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


@api.route('/all', methods=['GET'])
# get all sensor information
def get_all():
    print(frames_result)
    return json.dumps(frames_result)


def execute_query(query):
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    connection = sqlite3.connect("C:\sqlite3\hydroponicDatabase.db")
    connection.row_factory = dict_factory
    cursor = connection.cursor()
    query_result = cursor.execute(query)
    list_of_results = query_result.fetchall()
    if not list_of_results:
        connection.commit()
    else:
        return list_of_results

    # connection.close()


def frame_breakdown(frame):
    all_frames = frame.split("&")
    for current_frame in all_frames:
        dictionary_item = current_frame.split("@")
        frame_dictionary = {
            'device': dictionary_item[0],
            'serialnumber': int(dictionary_item[1]),
            'value': dictionary_item[2],
            'frametype': dictionary_item[3]
        }
        frames_result.append(frame_dictionary)
    return frames_result


# process temperature and humidity frames
def process_frames(result):
    for frame in result:
        if frame['frametype'] == "temperature" or frame['frametype'] == "humidity":
            execute_query("INSERT INTO " + frame['frametype'] + " (serial_number, value, timestamp) VALUES(" + str(frame['serialnumber'])
                          + ", " + str(int(frame['value'])) + ", "
                          + str(int(datetime.datetime.now(pytz.timezone('Europe/Berlin')).timestamp())) + ");")

        # if frame['frametype'] == "crawlerstart":
        #     path = pathfinding({"y": 8, "x": 1}, {"y": 1, "x": 1})
        #     path.a_star_start()


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
            counter = counter + 1
        schedules_counter = 0
        for schedule in schedule_list:
            if schedule is not None and schedule.serial_number == serial_number:
                schedules_counter = schedules_counter + 1
        if schedules_counter == 0:
            device_has_pending_instructions[device_has_pending_instructions.index(serial_number)] = None

    # if the instruction is about starting the crawler, change the contents of the instruction to the directions
    # it should be moving
    for instruction in instruction_to_send:
        if "GOTO" in instruction:
            # get first available crawler's data
            crawler_serial_number = execute_query("SELECT serialnumber FROM crawlers WHERE status = 'available'")[0]
            starting_position_x = execute_query("SELECT restingpositionx FROM crawlers WHERE status = 'available'")[0]
            starting_position_y = execute_query("SELECT restingpositiony FROM crawlers WHERE status = 'available'")[0]
            destination_x = instruction[5]
            destination_y = instruction[7]

            path = PathFinding({"y": starting_position_y, "x": starting_position_x},
                               {"y": destination_y, "x": destination_x},
                               schedule.timestamp)
            path.a_star_start()
            crawler_directions = path.final_directions
            execute_query("UPDATE crawlers SET status = moving, directions = " + crawler_directions + ", timestamp =" +
                          path.time_started_moving + " ... WHERE serialnumber = " + crawler_serial_number + ";")

            instruction_to_send = "PATH:" + path.final_directions
            print(instruction)

    return instruction_to_send


# Socket Server
async def receiver(websocket, path):
    frames_receive = (await websocket.recv())
    global frames_result
    frames_result = frame_breakdown(frames_receive)
    process_frames(frames_result)
    instruction_to_send = prepare_to_send_instructions(frames_result[0]['serialnumber'])
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

        print(execute_query("SELECT MIN(scheduleTimestamp) FROM schedule"))
        print(ts)
        if execute_query("SELECT MIN(scheduleTimestamp) FROM schedule")[0]['MIN(scheduleTimestamp)'] == int(ts):
            results = execute_query("SELECT serialnumber, instruction, to_delete, type, scheduleid FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + ";")

            # optimizable?
            if len(results) > 1:
                for result in results:
                    if result['serialnumber'] not in device_has_pending_instructions:
                        device_has_pending_instructions.append(result['serialnumber'])
            else:
                if results[0]['serialnumber'] not in device_has_pending_instructions:
                    device_has_pending_instructions.append(results[0]['serialnumber'])

            counter = 0
            while counter < len(results):
                schedule_list.append(Schedule(results[counter]['serialnumber'],
                                              results[counter]['instruction'],
                                              results[counter]['to_delete'],
                                              results[counter]['type'],
                                              int(ts)))
                counter = counter + 1

            for result in results:
                if result['to_delete'] == 'TRUE':
                    execute_query("DELETE FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + " AND scheduleid = " + str(result['scheduleId']) + ";")


thread_server = threading.Thread(target=thread_socket_server, args=())
thread_server.start()

api_server = threading.Thread(target=rest_api_server, args=())
api_server.start()

thread_scheduler = threading.Thread(target=scheduler, args=())
thread_scheduler.start()

# temporary, test purposes
dd = PathFinding({"y": 8, "x": 1}, {"y": 1, "x": 1}, 1617633825)
# dd.a_star_start()