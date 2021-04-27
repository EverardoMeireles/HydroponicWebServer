import builtins
import datetime
import sqlite3
import random
import pytz
from database import select_crawler, update_crawler


class PathFinding:
    # 2d array where the G cost, H cost, F cost and status will be stored.
    def __init__(self, room_destination):
        self.current_crawler = self.select_crawler_to_move()
        try:
            self.room_starting_position = {"y": self.current_crawler["resting_position_y"],
                                           "x": self.current_crawler["resting_position_x"]}
        except TypeError:
            self.room_starting_position = {}

        self.room_destination = room_destination
        # set starting node to be opened
        self.current_position = self.room_starting_position
        self.node_list = []
        self.closed_nodes = []
        self.sorted_nodes_by_weight = []
        self.direction_coordinates = []
        self.final_directions = []
        self.room_map = builtins.room_map

    def return_direction_values(self, direction_key):
        directions_dict = {
            0: {"y": 0, "x": -1},
            1: {"y": -1, "x": 0},
            2: {"y": 0, "x": 1},
            3: {"y": 1, "x": 0}
        }
        return directions_dict[direction_key]

    def open_surrounding_nodes(self):
        for direction_key in range(4):
            direction = self.return_direction_values(direction_key)
            y_difference = self.current_position["y"] + direction["y"]
            x_difference = self.current_position["x"] + direction["x"]
            if y_difference >= 0 and x_difference >= 0:
                self.calculate_node_list_and_open(y_difference, x_difference)

    def calculate_node_list_and_open(self, y, x):
        try:
            if self.room_map[y][x] not in ["Z", "O"]:
                # problem here with the cost values??? try adding abs() to both sides of the equation
                g_cost = abs(self.room_starting_position["y"] - y) + abs(self.room_starting_position["x"] - x)
                h_cost = abs(self.room_destination["y"] - y) + abs(self.room_destination["x"] - x)
                print("G and H: " + str(y) + " " + str(x))
                f_cost = g_cost + h_cost
                new_node = {"g_cost": g_cost,
                            "h_cost": h_cost,
                            "f_cost": f_cost,
                            "weight": 1,
                            "y": y,
                            "x": x}
                do_not_add = False
                for node in self.node_list:
                    if node == new_node:
                        do_not_add = True

                for node in self.closed_nodes:
                    if node == new_node:
                        do_not_add = True

                if do_not_add is False:
                    self.node_list.append(new_node)

        except IndexError:
            print("List overflowed")

    # close the node with the lowest F Cost and set new current_node, if there are multiple identical F Costs, select
    # the one with the lowest H Cost
    def close_the_next_node(self):
        node_to_close = 0
        lowest_f_cost = min([e['f_cost'] for e in self.node_list])
        lowest_h_cost = max([e['h_cost'] for e in self.node_list]) + 1
        i = 0
        for node in self.node_list:
            if node["f_cost"] == lowest_f_cost:
                if node["h_cost"] < lowest_h_cost:
                    lowest_h_cost = node["h_cost"]
                    node_to_close = i
                    node_to_add = node
            i += 1

        self.current_position = {"y": node_to_add["y"], "x": node_to_add["x"]}
        self.closed_nodes.append(node_to_add)
        self.node_list.pop(node_to_close)
        self.room_map[node_to_add["y"]][node_to_add["x"]] = "D"

    def apply_weights(self):
        for node in self.closed_nodes:
            new_weight = 0
            for direction_key in range(4):
                direction = self.return_direction_values(direction_key)
                temp_y = node["y"] + direction["y"]
                temp_x = node["x"] + direction["x"]
                for node_loop in self.closed_nodes:
                    if node_loop["y"] == temp_y and node_loop["x"] == temp_x:
                        new_weight = new_weight + node_loop["weight"]
            node["weight"] = new_weight

    def trace_backwards_path(self):
        self.closed_nodes.reverse()
        lowest_weight = max([x['weight'] for x in self.closed_nodes]) + 1
        next_node = self.closed_nodes[0]
        for node in self.closed_nodes:
            if node == next_node:
                for direction_key in range(4):
                    direction = self.return_direction_values(direction_key)
                    temp_y = node["y"] + direction["y"]
                    temp_x = node["x"] + direction["x"]
                    for node_loop in self.closed_nodes:
                        if node_loop["y"] == temp_y and node_loop["x"] == temp_x:
                            if node_loop["weight"] < lowest_weight:
                                lowest_weight = node_loop["weight"]
                                next_node = node_loop
                                self.direction_coordinates.append([node_loop["y"], node_loop["x"]])

                if next_node not in self.sorted_nodes_by_weight:
                    self.sorted_nodes_by_weight.append(next_node)

        # add first and last nodes
        self.sorted_nodes_by_weight.insert(0, {
            "g_cost": abs(self.room_starting_position["y"] - self.room_destination["y"]) + abs(
                self.room_starting_position["x"] - self.room_destination["x"]),
            "h_cost": 0,
            "f_cost": 0 + (abs(self.room_destination["y"] - self.room_starting_position["y"]) + abs(
                self.room_destination["x"] - self.room_starting_position["x"])),
            "weight": self.sorted_nodes_by_weight[0]["weight"] + 1,
            "y": self.room_destination["y"],
            "x": self.room_destination["x"]})
        self.direction_coordinates.insert(0, [self.room_destination["y"], self.room_destination["x"]])

        self.sorted_nodes_by_weight.append({"g_cost": 0,
                                            "h_cost": abs(
                                                self.room_destination["y"] - self.room_starting_position["y"]) + abs(
                                                self.room_destination["x"] - self.room_starting_position["x"]),
                                            "f_cost": 0 + (abs(
                                                self.room_destination["y"] - self.room_starting_position["y"]) + abs(
                                                self.room_destination["x"] - self.room_starting_position["x"])),
                                            "weight": 1,
                                            "y": self.room_starting_position["y"],
                                            "x": self.room_starting_position["x"]})
        self.direction_coordinates.append([self.room_starting_position["y"], self.room_starting_position["x"]])
        print()

    def determine_raw_directions(self):
        directions_dict = {
            (0, -1): "left",
            (-1, 0): "up",
            (0, 1): "right",
            (1, 0): "down"
        }

        previous_node = {}
        raw_directions = []
        for current_node in self.sorted_nodes_by_weight:
            if current_node != self.sorted_nodes_by_weight[0]:
                # determine raw directions by taking x and y values of the nodes and inverting them
                dictionary_direction_value = directions_dict[
                    ((current_node['y'] - previous_node["y"])*-1, (current_node["x"] - previous_node["x"])*-1)]
                raw_directions.append(dictionary_direction_value)
            previous_node = current_node

        # reverse the directions since we were tracing the backwards path
        raw_directions.reverse()
        self.direction_coordinates.reverse()
        return raw_directions

    def add_crawler_rotation(self, raw_directions):
        directions_with_rotations = []
        previous_direction = raw_directions[0]
        for direction in raw_directions:
            if direction != previous_direction:
                directions_with_rotations.append(("rotate-" + direction))
                directions_with_rotations.append(direction)
            else:
                directions_with_rotations.append(direction)
            previous_direction = direction
        return directions_with_rotations

    # randomly selects the crawler to move from available crawlers
    def select_crawler_to_move(self):
        list_of_available_crawlers = select_crawler({"status": "available"})
        try:
            return list_of_available_crawlers[random.randint(0, len(list_of_available_crawlers) - 1)]
        except ValueError:
            # if there are no available crawlers
            return "crawler unavailable"

    # check if the current crawler will collide with one of the crawlers already moving
    def check_for_collisions(self):
        current_crawler_coordinates = self.direction_coordinates
        list_of_moving_crawlers = select_crawler({"status": "moving"})
        ct = datetime.datetime.now(pytz.timezone('Europe/Berlin'))
        ts = int(ct.timestamp())
        for current_coordinate in current_crawler_coordinates:
            for moving_crawler in list_of_moving_crawlers:
                timestamp_counter = 0
                for moving_coordinate in moving_crawler["coordinates"]:
                    if current_coordinate == moving_coordinate and (ts + timestamp_counter) == \
                            (moving_crawler["time_started_moving"] + timestamp_counter):
                        self.room_map[moving_coordinate[0]][moving_coordinate[1]] = "Z"
                        return True
                    timestamp_counter += 1

        return False

    def a_star_start(self):
        run_again = True
        while run_again:
            self.node_list = []
            self.closed_nodes = []
            self.sorted_nodes_by_weight = []
            self.direction_coordinates = []
            self.final_directions = []
            self.current_position = self.room_starting_position
            self.room_map[self.room_starting_position["y"]][self.room_starting_position["x"]] = "O"
            while (self.current_position["y"], self.current_position["x"]) != (
                    self.room_destination["y"], self.room_destination["x"]):
                self.open_surrounding_nodes()
                self.close_the_next_node()

            self.apply_weights()
            self.trace_backwards_path()
            raw_directions = self.determine_raw_directions()
            #raw_directions = self.reverse_directions(raw_directions)
            self.final_directions = self.add_crawler_rotation(raw_directions)
            # if the crawler collides with another crawler, mark this spot as blocked and rerun the pathfinding
            run_again = self.check_for_collisions()
        print(self.direction_coordinates)
        ct = datetime.datetime.now(pytz.timezone('Europe/Berlin'))
        ts = int(ct.timestamp())
        update_crawler(self.current_crawler["serial_number"], {"status": "moving", "time_started_moving": ts, "coordinates": self.direction_coordinates})
        print("the end")