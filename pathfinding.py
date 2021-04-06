import builtins


class PathFinding:
    # 2d array where the G cost, H cost, F cost and status will be stored.
    def __init__(self, room_starting_position, room_destination, time_started_moving):
        self.room_starting_position = room_starting_position
        self.room_destination = room_destination
        self.time_started_moving = time_started_moving
        # set starting node to be opened
        self.current_position = room_starting_position
        self.node_list = []
        self.closed_nodes = []
        self.sorted_nodes_by_weight = []
        self.final_directions = []

    def return_direction_values(self, direction_key):
        directions_dict = {
            0: {"y": 0, "x": -1},
            1: {"y": -1, "x": -1},
            2: {"y": -1, "x": 0},
            3: {"y": -1, "x": 1},
            4: {"y": 0, "x": 1},
            5: {"y": 1, "x": 1},
            6: {"y": 1, "x": 0},
            7: {"y": 1, "x": -1}
        }
        return directions_dict[direction_key]

    def open_surrounding_nodes(self):
        for direction_key in range(8):
            direction = self.return_direction_values(direction_key)
            y_difference = self.current_position["y"] + direction["y"]
            x_difference = self.current_position["x"] + direction["x"]
            if y_difference >= 0 and x_difference >= 0:
                self.calculate_node_list_and_open(y_difference, x_difference)


    def calculate_node_list_and_open(self, y, x):
        try:
            if builtins.room_map[y][x] != "Z" and builtins.room_map[y][x] != "O":
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
            i = i + 1

        self.current_position = {"y": node_to_add["y"], "x": node_to_add["x"]}
        self.closed_nodes.append(node_to_add)
        self.node_list.pop(node_to_close)
        builtins.room_map[node_to_add["y"]][node_to_add["x"]] = "D"

    def apply_weights(self):
        for node in self.closed_nodes:
            new_weight = 0
            for direction_key in range(8):
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
                for direction_key in range(8):
                    direction = self.return_direction_values(direction_key)
                    temp_y = node["y"] + direction["y"]
                    temp_x = node["x"] + direction["x"]
                    for node_loop in self.closed_nodes:
                        if node_loop["y"] == temp_y and node_loop["x"] == temp_x:
                            if node_loop["weight"] < lowest_weight:
                                lowest_weight = node_loop["weight"]
                                next_node = node_loop

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

    def determine_raw_directions(self):
        # Replace diagonal movement with 4-direction movement(for example left-down becomes (left, down) or (down-left)
        def replace_diagonal_directions(node, direction):
            directions_conversion_dict = {
                "left": {"y": 0, "x": -1},
                "right": {"y": 0, "x": 1},
            }
            directions_list = direction.split("-")
            direction_compare = directions_conversion_dict[directions_list[0]]
            if builtins.room_map[(node["y"] + direction_compare["y"])][(node["x"] + direction_compare["x"])] != "Z":
                new_direction = directions_list[0], directions_list[1]
            else:
                new_direction = directions_list[1], directions_list[0]

            return new_direction

        directions_dict = {
            (0, -1): "left",
            (-1, -1): "left-up",
            (-1, 0): "up",
            (-1, 1): "right-up",
            (0, 1): "right",
            (1, 1): "right-down",
            (1, 0): "down",
            (1, -1): "left-down"
        }
        previous_node = {}
        raw_directions = []
        for current_node in self.sorted_nodes_by_weight:
            if current_node != self.sorted_nodes_by_weight[0]:
                dictionary_direction_value = directions_dict[
                    (current_node['y'] - previous_node["y"], current_node["x"] - previous_node["x"])]
                if "-" in dictionary_direction_value:
                    dictionary_direction_value = replace_diagonal_directions(previous_node, dictionary_direction_value)
                    raw_directions.append(dictionary_direction_value[0])
                    raw_directions.append(dictionary_direction_value[1])
                else:
                    raw_directions.append(dictionary_direction_value)
            previous_node = current_node
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

    def reverse_directions(self, raw_directions):
        reverse_direction_dict = {
            "left": "right",
            "right": "left",
            "up": "down",
            "down": "up"
        }
        new_directions = []
        for direction in raw_directions:
            new_directions.append(reverse_direction_dict[direction])

        new_directions.reverse()
        return new_directions

    def a_star_start(self):
        builtins.room_map[self.room_starting_position["y"]][self.room_starting_position["x"]] = "O"
        while (self.current_position["y"], self.current_position["x"]) != (
                self.room_destination["y"], self.room_destination["x"]):
            self.open_surrounding_nodes()
            self.close_the_next_node()

        self.apply_weights()
        self.trace_backwards_path()
        raw_directions = self.determine_raw_directions()
        raw_directions = self.reverse_directions(raw_directions)
        self.final_directions = self.add_crawler_rotation(raw_directions)
        print("the end")
