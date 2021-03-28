import builtins
class pathfinding:
    # 2d array where the Gcost, Hcost, Fcost and status will be stored.
    def __init__(self, room_starting_position, room_destination):
        self.room_starting_position = room_starting_position
        self.room_destination = room_destination
        # set starting node to be opened
        self.current_position = room_starting_position
        self.nodeList = []
        self.closedNodes = []
        self.sortedNodesByWeight = []
        self.finalDirections = []

    def calculatenodeListAndOpen(self, y, x):

        try:
            if(builtins.room_map[y][x] != "Z" and builtins.room_map[y][x] != "O"):
                # problem here with the cost values??? try adding abs() to both sides of the equation
                GCost = abs(self.room_starting_position["y"] - y) + abs(self.room_starting_position["x"] - x)
                HCost = abs(self.room_destination["y"] - y) + abs(self.room_destination["x"] - x)
                print("G and H: " + str(y) + " " + str(x))
                FCost = GCost + HCost
                newNode = {"GCost": GCost,
                                    "HCost": HCost,
                                    "FCost": FCost,
                                    "weight": 1,
                                    "y": y,
                                    "x": x}
                doNotAdd = False
                for node in self.nodeList:
                    if node == newNode:
                        doNotAdd = True

                for node in self.closedNodes:
                    if node == newNode:
                        doNotAdd = True

                if doNotAdd == False:
                    self.nodeList.append(newNode)

        except IndexError:
            print("")

    def goThroughDirections(self, directionKey):
        directions = {
            0: {"y": 0, "x": -1},
            1: {"y": -1, "x": -1},
            2: {"y": -1, "x": 0},
            3: {"y": -1, "x": 1},
            4: {"y": 0, "x": 1},
            5: {"y": 1, "x": 1},
            6: {"y": 1, "x": 0},
            7: {"y": 1, "x": -1}
        }
        return directions[directionKey]

    def openSurroundingNodes(self):
        for directionKey in range(8):
            direction = self.goThroughDirections(directionKey)
            yDifference = self.current_position["y"] + direction["y"]
            xDifference = self.current_position["x"] + direction["x"]
            if yDifference >= 0 and xDifference >= 0:
                self.calculatenodeListAndOpen(yDifference, xDifference)

    # close the node with the lowest F Cost and set new currentNode, if there are multiple identical F Costs, select the one
    # with the lowest H Cost
    def closeTheNextNode(self):
        nodeToClose = 0
        #print(nodeList)
        lowestFcost = min([e['FCost'] for e in self.nodeList])
        lowestHcost = 100 #???
        i = 0
        for node in self.nodeList:
            if node["FCost"] == lowestFcost:
                if node["HCost"] < lowestHcost:
                    lowestHcost = node["HCost"]
                    nodeToClose = i
                    nodeToAdd = node
            i = i + 1

        self.current_position = {"y": nodeToAdd["y"], "x": nodeToAdd["x"]}
        self.closedNodes.append(nodeToAdd)
        self.nodeList.pop(nodeToClose)
        builtins.room_map[nodeToAdd["y"]][nodeToAdd["x"]] = "D"

    def applyWeights(self):
        #optimize later
        for node in self.closedNodes:
            newWeight = 0
            for directionKey in range(8):
                direction = self.goThroughDirections(directionKey)
                tempY = node["y"] + direction["y"]
                tempX = node["x"] + direction["x"]
                for nodeLoop in self.closedNodes:
                    if (nodeLoop["y"] == tempY and nodeLoop["x"] == tempX):
                        newWeight = newWeight + nodeLoop["weight"]
            node["weight"] = newWeight

            #sortedNodesByWeight = sorted(closedNodes, key = lambda i: i['weight'])
    def traceBackwardsPath(self):
        self.closedNodes.reverse()
        #global sortedNodesByWeight
        lowestWeight = 99999999999999999999999999
        nextNode = self.closedNodes[0]
        for node in self.closedNodes:
            if node == nextNode:
                for directionKey in range(8):
                    direction = self.goThroughDirections(directionKey)
                    tempY = node["y"] + direction["y"]
                    tempX = node["x"] + direction["x"]
                    for nodeLoop in self.closedNodes:
                        if nodeLoop["y"] == tempY and nodeLoop["x"] == tempX:
                            if nodeLoop["weight"] < lowestWeight:
                                lowestWeight = nodeLoop["weight"]
                                nextNode = nodeLoop

                if nextNode not in self.sortedNodesByWeight:
                    self.sortedNodesByWeight.append(nextNode)

        self.sortedNodesByWeight.insert(0, { "GCost": abs(self.room_starting_position["y"] - self.room_destination["y"]) + abs(self.room_starting_position["x"] - self.room_destination["x"]),
                                    "HCost": 0,
                                    "FCost": 0 + (abs(self.room_destination["y"] - self.room_starting_position["y"]) + abs(self.room_destination["x"] - self.room_starting_position["x"])),
                                    "weight": self.sortedNodesByWeight[0]["weight"] + 1,
                                    "y": self.room_destination["y"],
                                    "x": self.room_destination["x"]})

        self.sortedNodesByWeight.append({ "GCost": 0,
                                    "HCost": abs(self.room_destination["y"] - self.room_starting_position["y"]) + abs(self.room_destination["x"] - self.room_starting_position["x"]),
                                    "FCost": 0 + (abs(self.room_destination["y"] - self.room_starting_position["y"]) + abs(self.room_destination["x"] - self.room_starting_position["x"])),
                                    "weight": 1,
                                    "y": self.room_starting_position["y"],
                                    "x": self.room_starting_position["x"]})

    def determineFinalDirections(self):
        finalDirectionsDict = {
            (0, -1): "left",
            (-1, -1): "left-up",
            (-1, 0): "up",
            (-1, 1): "right-up",
            (0, 1): "right",
            (1, 1): "right-down",
            (1, 0): "down",
            (1, -1): "left-down"
        }
        previousNode = {}
        for currentNode in self.sortedNodesByWeight:
            if(currentNode != self.sortedNodesByWeight[0]):
                self.finalDirections.append(finalDirectionsDict[(currentNode['y'] - previousNode["y"], currentNode["x"] - previousNode["x"])])
            previousNode = currentNode


    def aStarStart(self):
        #calculatenodeListAndOpen(room_starting_position["y"], room_starting_position["x"], "closed")
        global room_y
        global room_x
        builtins.room_map[self.room_starting_position["y"]][self.room_starting_position["x"]] = "O"
        while (self.current_position["y"], self.current_position["x"]) != (self.room_destination["y"], self.room_destination["x"]):
            self.openSurroundingNodes()
            self.closeTheNextNode()

        self.applyWeights()
        self.traceBackwardsPath()
        self.determineFinalDirections()

        print("final position: " + str(self.current_position))
        print("the end")