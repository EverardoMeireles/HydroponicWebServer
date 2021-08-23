#!/usr/bin/env python

import asyncio
import websockets
import threading
import time
from flask import Flask
import datetime
import pytz
from utils.schedule import Schedule
from crawler.pathfinding import PathFinding
import os
import cProfile
import re
import ujson
from utils.database import execute_query
from utils.config import config
from utils.database import select_crawler, update_crawler, update_local_list_of_crawlers
import random
import ast


# frames_receive = []
api = Flask(__name__)

frames_result = []
schedule_list = []

device_has_pending_instructions = []

if config.getboolean("Main", "start_with_profiler"):
    pid = os.getpid()
    os.system("profiler.bat " + str(pid))


@api.route('/all', methods=['GET'])
# get all sensor information
def get_all():
    print(frames_result)
    return ujson.dumps(frames_result)


# pre-processing of the instruction to be sent according to its type
def process_instruction_before_sending(instruction):
    instruction_dict = ast.literal_eval(instruction)
    processed_instruction = instruction  # is this necessary????
    # what to do to the schedule in case of pre-processing failure: none, postpone, delete
    postpone = False
    # if the instruction is about starting the crawler, change the contents of the instruction to the directions
    # it should be moving
    if instruction_dict['instruction'] == "move_crawler_to":
        processed_instruction = calculate_crawler_path(processed_instruction)
        if processed_instruction == "no crawler unavailable":
            postpone = True
    # elif

    return processed_instruction, postpone


# prepare to send instruction message to the device that sent the server a message
def prepare_to_send_instructions(serial_number):
    global device_has_pending_instructions
    global schedule_list

    # if there are no instructions for this device "" will be sent
    instruction_to_send = ""

    for schedule in schedule_list:
        instruction_to_send, postpone_sending_instruction = process_instruction_before_sending(schedule.instruction)
        if schedule.serial_number == serial_number:
            if postpone_sending_instruction:
                print("instruction postponed")
                instruction_to_send = ""
                schedule_list[schedule_list.index(schedule)].postponed = True
            else:
                schedule_list.pop(schedule_list.index(schedule))
                break

    schedules_counter = 0
    for schedule in schedule_list:
        if schedule is not None and schedule.serial_number == serial_number:
            schedules_counter += 1

    if schedules_counter == 0:
        device_has_pending_instructions.pop(device_has_pending_instructions.index(serial_number))
    # amanha as 1530
    return instruction_to_send


# randomly selects the crawler to move from available crawlers
def select_crawler_to_move():
    update_local_list_of_crawlers()
    list_of_available_crawlers = select_crawler({"status": "available"})
    print(list_of_available_crawlers)
    try:
        return list_of_available_crawlers[random.randint(0, len(list_of_available_crawlers) - 1)]
    except ValueError:
        # if there are no available crawlers
        return "no crawler unavailable"


# get instruction message from the scheduler and calculate the crawler's path
# used in process_instruction_before_sending(serial_number)
def calculate_crawler_path(instruction):
    current_crawler = select_crawler_to_move()
    if current_crawler == "no crawler unavailable":
        return current_crawler

    instruction_dict = ast.literal_eval(instruction)
    starting_position = {"y": current_crawler["resting_position_y"], "x": current_crawler["resting_position_x"]}
    destination = {"y": instruction_dict['destination_y'], "x": instruction_dict['destination_x']}
    path = PathFinding(starting_position, destination)
    path.a_star_start()
    ct = datetime.datetime.now(pytz.timezone('Europe/Berlin'))
    ts = int(ct.timestamp())
    update_crawler(current_crawler["serial_number"], {"status": "moving",
                                                      "time_started_moving": ts,
                                                      "coordinates": path.direction_coordinates})
    instruction_to_send = str({"path": path.final_directions})

    print(instruction_to_send)
    return instruction_to_send


#  log received data into database(mostly sensor data)
def log_into_database(frame):
    execute_query("INSERT INTO " + frame['frame_type'] + " (serial_number, value, timestamp) "
                                                         "VALUES(" + str(frame['serial_number'])
                  + ", " + str(int(frame['value'])) + ", "
                  + str(int(datetime.datetime.now(pytz.timezone('Europe/Berlin')).timestamp())) + ");")


# apply processing type based on the type of frame when the frame is supposed to trigger an action
def process_received_instructions(result):
    for frame in result:
        # log into database(sensor data)
        if frame['frame_type'] in ["temperature", "humidity"]:
            log_into_database(frame)

        # elif


# Socket Server
# Receives a message and send a response
async def receiver(websocket, path):
    global frames_result
    frames_receive = (await websocket.recv())
    frames_result = ujson.loads(frames_receive)
    instruction_to_send = ""

    # if there's only one message, create a list with one element
    if not isinstance(frames_result, list):
        frames_result = [frames_result]

    # process the instruction to change it or to trigger an action
    if frames_result not in ["", None]:
        process_received_instructions(frames_result)

    # if the device that sent the frame has an instruction waiting to be sent back
    if int(frames_result[0]['serial_number']) in device_has_pending_instructions:
        instruction_to_send = prepare_to_send_instructions(frames_result[0]['serial_number'])
        frames_result = []

    # send back a message to the device, whether it contains a instruction or not
    await websocket.send(instruction_to_send)


# Socket Server thread
def thread_socket_server():
    asyncio.set_event_loop(asyncio.new_event_loop())
    start_server = websockets.serve(receiver, config.get("Thread", "socket_ip"), config.getint("Thread", "socket_port"))
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
    api.run()


def thread_rest_api_server():
    if __name__ == '__main__':
        api.run(host="0.0.0.0", port=5154, debug=False)


# if scheduler_optimization is True on config.ini, makes code execution faster but makes
# modifying database on the fly impossible, difficult to debug.
if config.getboolean("Main", "scheduler_optimization"):
    minimum_schedule_timestamp = execute_query("SELECT MIN(schedule_timestamp) "
                                               "FROM schedule")[0]['MIN(schedule_timestamp)']


def thread_scheduler():
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
                                              False,  # postpone
                                              result['type'],
                                              int(ts)))

                if result['to_delete'] == 'TRUE':
                    print(result)
                    execute_query("DELETE FROM schedule WHERE schedule_timestamp = " + str(int(ts)) +
                                  " AND schedule_Id = " + str(result['schedule_Id']) + ";")

            minimum_schedule_timestamp = execute_query("SELECT MIN(schedule_timestamp) FROM schedule")[0][
                'MIN(schedule_timestamp)']


thread_server = threading.Thread(target=thread_socket_server, args=())
thread_server.start()

api_server = threading.Thread(target=thread_rest_api_server, args=())
api_server.start()

thread_scheduler = threading.Thread(target=thread_scheduler, args=())
thread_scheduler.start()

# temporary, for test purposes
# dd = PathFinding({"y": 8, "x": 1}, {"y": 1, "x": 1})
# dd = PathFinding({"y": 1, "x": 1})
# dd.a_star_start()
