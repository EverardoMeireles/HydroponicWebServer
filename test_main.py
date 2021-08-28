import unittest.mock
import utils.instructions
import utils.database
import utils.schedule
import utils.config
import ujson
import crawler.pathfinding


def update_local_list_of_crawlers():
    return 0


def save_crawlers_file():
    return 0


utils.instructions.update_local_list_of_crawlers = update_local_list_of_crawlers
utils.database.save_crawlers_file = save_crawlers_file
crawler.pathfinding.room_map = \
    [["Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z"],
     ["Z", "G", "Z", "Z", "G", "Z", "Z", "Z", "G", "Z"],
     ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
     ["Z", "Z", "G", "G", "G", "Z", "Z", "G", "G", "Z"],
     ["Z", "Z", "Z", "G", "Z", "Z", "G", "Z", "Z", "Z"],
     ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
     ["Z", "Z", "Z", "G", "G", "Z", "G", "Z", "G", "Z"],
     ["Z", "Z", "Z", "G", "Z", "Z", "G", "Z", "Z", "Z"],
     ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
     ["Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z"]]


class TestMain(unittest.TestCase):
    def test_prepare_to_send_instructions(self):
        # first test
        utils.instructions.device_has_pending_instructions = [1]
        utils.instructions.schedule_list.append(utils.schedule.Schedule(1,
                                                          '[{"instruction_type": "move_crawler_to", "destination_y":1, "destination_x":1}]',
                                                          'FALSE',
                                                          False,
                                                          'temperature',
                                                          1629755709))

        utils.database.list_of_crawlers = ujson.loads(
            ujson.dumps([{"serial_number": 2, "resting_position_x": 1, "resting_position_y": 8,
                          "status": "available", "time_started_moving": 16191176745454545458, "coordinates": []}]))

        second_value_compare = '[{"path":["rotate-right","forward","forward","rotate-up","forward","forward","forward",' \
                               '"forward","forward","rotate-left","forward","rotate-up","forward","rotate-left","forward",' \
                               '"rotate-up","forward"]}]'
        self.assertEqual(utils.instructions.prepare_to_send_instructions(1), second_value_compare)

        # second test
        utils.database.list_of_crawlers = ujson.loads(
            ujson.dumps([{"serial_number": 2, "resting_position_x": 1, "resting_position_y": 8,
                          "status": "available", "time_started_moving": 16191176745454545458, "coordinates": []},
                         {"serial_number": 2, "resting_position_x": 1, "resting_position_y": 8,
                          "status": "available", "time_started_moving": 16191176745454545458, "coordinates": []}]))

        utils.instructions.schedule_list.append(utils.schedule.Schedule(1,
                                                          '[{"instruction_type": "move_crawler_to", "destination_y":1, "destination_x":1}]',
                                                          'FALSE',
                                                          False,
                                                          'temperature',
                                                          1629755709))
        utils.instructions.device_has_pending_instructions = [1]

        self.assertEqual(utils.instructions.prepare_to_send_instructions(1), second_value_compare)
