#!/usr/bin/env python

import asyncio
import websockets
import threading
import time
from flask import Flask
import datetime
import pytz
from schedule import Schedule
import pathfinding
import builtins
import os
import cProfile
import re
import ujson
from database import execute_query
from utils import config

# frames_receive = []
api = Flask(__name__)

frames_result = []
schedule_list = []

# builtins.room_map = [["Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z"],
#                      ["Z", "G", "Z", "Z", "G", "Z", "Z", "Z", "G", "Z"],
#                      ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
#                      ["Z", "Z", "G", "G", "G", "Z", "Z", "G", "G", "Z"],
#                      ["Z", "Z", "Z", "G", "Z", "Z", "G", "Z", "Z", "Z"],
#                      ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
#                      ["Z", "Z", "Z", "G", "G", "Z", "G", "Z", "G", "Z"],
#                      ["Z", "Z", "Z", "G", "Z", "Z", "G", "Z", "Z", "Z"],
#                      ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
#                      ["Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "G", "Z"]]

device_has_pending_instructions = []

if config.getboolean("Main", "start_with_profiler"):
    pid = os.getpid()
    os.system("profiler.bat " + str(pid))


@api.route('/all', methods=['GET'])
# get all sensor information
def get_all():
    print(frames_result)
    return ujson.dumps(frames_result)


# send instruction message to device that sent server a message
def prepare_to_send_instructions(serial_number):
    global device_has_pending_instructions
    global schedule_list

    # if the instruction is about starting the crawler, change the contents of the instruction to the directions
    # it should be moving
    def instruction_pre_processing(instruction):
        processed_instruction = instruction
        passed = True
        # what to do to the schedule in case of pre-processing failure: none, postpone, delete
        failure_measure_to_take = "none"
        # if the instruction is to move the crawler to a position
        if "move_crawler_to" in processed_instruction:
            processed_instruction = calculate_crawler_path(processed_instruction)
            if processed_instruction == "crawler unavailable":
                passed = False
                failure_measure_to_take = "postpone"
        # elif

        return processed_instruction, passed, failure_measure_to_take

    # if there are no instructions for this device "" will be sent
    instruction_to_send = ""
    for schedule in schedule_list:
        instruction_to_send, processing_passed, measure = instruction_pre_processing(schedule.instruction)
        if schedule.serial_number == serial_number:
            if processing_passed is True or measure == "delete":
                schedule_list.pop(schedule_list.index(schedule))

            break

    schedules_counter = 0
    for schedule in schedule_list:
        if schedule is not None and schedule.serial_number == serial_number:
            schedules_counter += 1

    if schedules_counter == 0:
        device_has_pending_instructions.pop(device_has_pending_instructions.index(serial_number))

    return instruction_to_send


# get instruction message from the scheduler and calculate the crawler's path
def calculate_crawler_path(instruction):
    destination_y = int(instruction[16])
    destination_x = int(instruction[18])
    path = pathfinding.PathFinding({"y": destination_y, "x": destination_x})
    if path.current_crawler != "crawler unavailable":
        path.a_star_start()
        instruction_to_send = "PATH: " + " ".join(path.final_directions)
    else:
        instruction_to_send = path.current_crawler
    print(instruction_to_send)
    return instruction_to_send


# apply processing type based on the type of frame
def apply_frame_processing_type(result):
    for frame in result:
        # log into database(sensor data)
        if frame['frame_type'] in ["temperature", "humidity"]:
            log_into_database(frame)

        # elif frame['frame_type'] == "placeholder":


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
    frames_result = ujson.loads(frames_receive)
    # if there's only one message, create a list with one element
    if not isinstance(frames_result, list):
        temp_list = [frames_result]
        frames_result = temp_list

    if frames_result not in ["", None]:
        apply_frame_processing_type(frames_result)

    instruction_to_send = ""
    if int(frames_result[0]['serial_number']) in device_has_pending_instructions:
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


# if scheduler_optimization is True on config.ini, makes code execution faster but makes
# modifying database on the fly impossible, difficult to debug.
if config.getboolean("Main", "scheduler_optimization"):
    minimum_schedule_timestamp = execute_query("SELECT MIN(schedule_timestamp) "
                                               "FROM schedule")[0]['MIN(schedule_timestamp)']


def scheduler():
    global schedule_list
    global minimum_schedule_timestamp
    while True:
        ct = datetime.datetime.now(pytz.timezone('Europe/Berlin'))
        ts = ct.timestamp()
        # prevents timestamp from skipping a second due cpu delay
        if (ts % 1) < 0.97:
            time.sleep(1)
        else:
            time.sleep(1 - (ts % 1))

        print(ts)
        if config.getboolean("Main", "scheduler_optimization") is not True:
            minimum_schedule_timestamp = execute_query("SELECT MIN(schedule_timestamp) "
                                                       "FROM schedule")[0]['MIN(schedule_timestamp)']

        if minimum_schedule_timestamp == int(ts):
            results = execute_query("SELECT serial_number, instruction, to_delete, type, schedule_id "
                                    "FROM schedule WHERE schedule_timestamp = " + str(int(ts)) + ";")

            if len(results) > 1:
                for result in results:
                    if result['serial_number'] not in device_has_pending_instructions:
                        device_has_pending_instructions.append(result['serial_number'])
            else:
                if results[0]['serial_number'] not in device_has_pending_instructions:
                    device_has_pending_instructions.append(results[0]['serial_number'])

            for result in results:
                schedule_list.append(Schedule(result['serial_number'],
                                              result['instruction'],
                                              result['to_delete'],
                                              result['type'],
                                              int(ts)))

            for result in results:
                if result['to_delete'] == 'TRUE':
                    execute_query("DELETE FROM schedule WHERE schedule_timestamp = " + str(int(ts)) +
                                  " AND schedule_id = " + str(result['scheduleId']) + ";")

            minimum_schedule_timestamp = execute_query("SELECT MIN(schedule_timestamp) FROM schedule")[0][
                'MIN(schedule_timestamp)']


thread_server = threading.Thread(target=thread_socket_server, args=())
thread_server.start()

api_server = threading.Thread(target=rest_api_server, args=())
api_server.start()

thread_scheduler = threading.Thread(target=scheduler, args=())
thread_scheduler.start()

# temporary, test purposes
# dd = pathfinding.PathFinding({"y": 8, "x": 1}, {"y": 1, "x": 1})
# dd = pathfinding.PathFinding({"y": 1, "x": 1})
# dd.a_star_start()
