#!/usr/bin/env python

import asyncio
import websockets
import threading
import time
from flask import Flask
from utils.schedule import Schedule
import os
from utils.config import config
from utils.instructions import *

if config.getboolean("Main", "start_with_profiler"):
    pid = os.getpid()
    os.system("cd utils && profiler.bat " + str(pid))

api = Flask(__name__)

frames_result = []


@api.route('/all', methods=['GET'])
# get all sensor information
def get_all():
    print(frames_result)
    return ujson.dumps(frames_result)


def thread_rest_api_server():
    if __name__ == '__main__':
        api.run(host="0.0.0.0", port=5154, debug=False)


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


# if scheduler_optimization is True on config.ini, makes code execution faster but makes
# modifying database on the fly impossible, difficult to debug.
if config.getboolean("Main", "scheduler_optimization"):
    minimum_schedule_timestamp = execute_query("SELECT MIN(schedule_timestamp) "
                                               "FROM schedule")[0]['MIN(schedule_timestamp)']


def thread_scheduler():
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
            results = execute_query("SELECT serial_number, instruction, to_delete, type, schedule_id,"
                                    " re_insertion_time_seconds " "FROM schedule WHERE schedule_timestamp"
                                    " = " + str(int(ts)) + ";")

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
                                              int(ts),
                                     result['re_insertion_time_seconds']))

                minimum_schedule_timestamp = execute_query("SELECT MIN(schedule_timestamp) FROM schedule")[0][
                    'MIN(schedule_timestamp)']

                # if its just a one time schedule, delete it, if not, add more seconds to the timestamp to repeat it.
                if result['to_delete'] == 'TRUE':
                    print(result)
                    execute_query("DELETE FROM schedule WHERE schedule_timestamp = " + str(int(ts)) +
                                  " AND schedule_Id = " + str(result['schedule_Id']) + ";")
                else:
                    execute_query("UPDATE schedule SET schedule_timestamp = "
                                  + str(int((ts + result['re_insertion_time_seconds'])))
                                  + " WHERE schedule_timestamp = " + str(int(ts)) + ";")


if __name__ == '__main__':
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
