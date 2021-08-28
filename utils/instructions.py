
import datetime
import pytz
from crawler.pathfinding import PathFinding
import ujson
from utils.database import execute_query
from utils.database import select_crawler, update_crawler, update_local_list_of_crawlers
import random
import ast

schedule_list = []
device_has_pending_instructions = []


# pre-processing of the instruction to be sent according to its type
def process_instruction_before_sending(instructions):
    instruction_dicts = ast.literal_eval(instructions)
    processed_instructions = []  #instructions  # is this necessary????
    postpone = False
    # if the instruction is about starting the crawler, change the contents of the instruction to the directions
    # it should be moving
    for instruction_item in instruction_dicts:
        next_instruction = ujson.dumps(instruction_item)
        if instruction_item['instruction_type'] == "move_crawler_to":
            next_instruction = calculate_crawler_path(ujson.dumps(instruction_item))
            if next_instruction == "no crawler unavailable":
                postpone = True
                break

        processed_instructions.append(ujson.loads(next_instruction))

    return ujson.dumps(processed_instructions), postpone


# prepare to send instruction message to the device that sent the server a message
def prepare_to_send_instructions(serial_number):
    global device_has_pending_instructions
    global schedule_list

    # if there are no instructions for this device "" will be sent
    instruction_to_send = ""

    for schedule in schedule_list:
        if schedule.serial_number == serial_number:
            instruction_to_send, postpone_sending_instruction = process_instruction_before_sending(schedule.instruction)
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

    return instruction_to_send


# randomly selects the crawler to move from available crawlers
def select_crawler_to_move():
    update_local_list_of_crawlers()
    list_of_available_crawlers = select_crawler({"status": "available"})
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
    instruction_to_send = ujson.dumps({"path": path.final_directions})

    print(instruction_to_send)
    return instruction_to_send


#  log received data into database(mostly sensor data)
def log_into_database(frame):
    execute_query("INSERT INTO " + frame['instruction_type'] + " (serial_number, value, timestamp) "
                                                         "VALUES(" + str(frame['serial_number'])
                  + ", " + str(int(frame['value'])) + ", "
                  + str(int(datetime.datetime.now(pytz.timezone('Europe/Berlin')).timestamp())) + ");")


# apply processing type based on the type of frame when the frame is supposed to trigger an action
def process_received_instructions(result):
    for frame in result:
        # log into database(sensor data)
        if frame['instruction_type'] in ["temperature", "humidity"]:
            log_into_database(frame)

        # elif