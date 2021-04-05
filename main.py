#!/usr/bin/env python

import asyncio
import websockets
import threading
import time
import sqlite3
from flask import Flask, json, render_template, request
import datetime
import pytz
from schedule import schedule
from pathfinding import pathfinding
import builtins

framesReceive = []
api = Flask(__name__)

DATABASE = 'C:\sqlite3\hydroponicDatabase.db'

framesResult = []
scheduleList = []

builtins.room_map = [["Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z"],
                     ["G", "G", "G", "G", "G", "G", "G", "G", "G", "G"],
                     ["G", "Z", "Z", "Z", "Z", "Z", "G", "G", "G", "G"],
                     ["G", "G", "G", "G", "G", "G", "G", "G", "G", "G"],
                     ["G", "G", "G", "G", "G", "G", "G", "G", "G", "G"],
                     ["Z", "Z", "Z", "Z", "Z", "G", "Z", "Z", "Z", "Z"],
                     ["G", "G", "G", "G", "G", "G", "G", "G", "G", "G"],
                     ["G", "G", "G", "G", "G", "G", "G", "G", "G", "G"],
                     ["G", "G", "G", "G", "G", "G", "G", "G", "G", "G"],
                     ["G", "G", "G", "G", "G", "G", "G", "G", "G", "G"]]

builtins.crawlersInMotion = []

deviceHasPendingInstructions = []
#get all sensor information
@api.route('/all', methods=['GET'])
def get_all():
    #all = [{"temperature": 1, "name": "Company One"}, {"id": 2, "name": "Company Two"}]
    #connection = sqlite3.connect("C:\sqlite3\hydroponicDatabase.db")
    #cursor = connection.cursor()
    #cursor.execute("INSERT INTO esp3 values(85);")
    #connection.commit()
    #connection.close()
    print(framesResult)
    return json.dumps(framesResult)

def executeQuery(query):
    connection = sqlite3.connect("C:\sqlite3\hydroponicDatabase.db")
    connection.row_factory = lambda cursor, row: row[0]
    cursor = connection.cursor()
    queryResult = cursor.execute(query)
    connection.commit()
    return queryResult.fetchall()
    # connection.close()

def cutNoneElements(list):
    tempList = []
    for element in list:
        if(element != None):
            tempList.append(element)

    return tempList

def frameBreakdown(frame):
    dicctionaryItem = []
    allFrames = frame.split("&")
    for currentFrame in allFrames:

        dicctionaryItem = currentFrame.split("@")
        frameDictionary = {
            'device': dicctionaryItem[0],
            'id': int(dicctionaryItem[1]),
            'value': dicctionaryItem[2],
            'frametype': dicctionaryItem[3]
        }
        framesResult.append(frameDictionary)
    return framesResult

# process temperature and humidity frames
def processFrames(Result):
    #print(Result)
    for frame in Result:
        if frame['frametype'] == "temperature" or frame['frametype'] == "humidity":
            executeQuery("INSERT INTO " + frame['frametype'] + " (id, value, timestamp) VALUES(" + str(frame['id']) + ", " + str(int(frame['value'])) +", " + str(int(datetime.datetime.now(pytz.timezone('Europe/Berlin')).timestamp()))+  ");")

        # if frame['frametype'] == "crawlerstart":
        #     path = pathfinding({"y": 8, "x": 1}, {"y": 1, "x": 1})
        #     path.aStarStart()

def prepareToSendInstructions(id):
    global deviceHasPendingInstructions
    global scheduleList
    #if there are no instructions for this esp "" will be sent
    instructionToSend = ""

    if(int(id) in deviceHasPendingInstructions):
        i = 0
        for schedule in scheduleList:
            print(schedule)
            if schedule.id == id:
                instructionToSend = schedule.instruction
                scheduleList[i] = None
                break
            i = i + 1
        e = 0
        for schedule in scheduleList:
            if(schedule != None and schedule.id == id):
                e = e + 1
        if e == 0:
            deviceHasPendingInstructions[deviceHasPendingInstructions.index(id)] = None
    # if the instruction is about starting the crawler, change the contents of the instruction to the directions it should
    # be moving
    for instruction in instructionToSend:
        if "GOTO" in instruction:
            # get next available crawler's data
            crawlersDirections = executeQuery("SELECT directions FROM crawlers WHERE status = 'available'")[0]
            startingPositionX = executeQuery("SELECT restingpositionx FROM crawlers WHERE status = 'available'")[0]
            startingPositionY = executeQuery("SELECT restingpositiony FROM crawlers WHERE status = 'available'")[0]
            destinationX = instruction[5]
            destinationY = instruction[7]

            dd = pathfinding({"y": startingPositionY, "x": startingPositionX}, {"y": destinationY, "x": destinationX}, schedule.timestamp)
            dd.aStarStart()

    return instructionToSend

# Socket Server
async def receiver(websocket, path):
    framesReceive = (await websocket.recv())
    #print(framesReceive)
    global framesResult
    framesResult = frameBreakdown(framesReceive)
    processFrames(framesResult)
    instructionToSend = prepareToSendInstructions(framesResult[0]['id'])
    framesResult = []
    await websocket.send(instructionToSend)

# Socket Server thread
def ThreadSocketServer():
    asyncio.set_event_loop(asyncio.new_event_loop())
    start_server = websockets.serve(receiver, "192.168.1.58", 5153)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
    api.run()

def restApiServer():
    if __name__ == '__main__':
        api.run(host="0.0.0.0", port=5154, debug=False)

# crawlers = []
# # get list of crawlers from database
# def updateCrawlerList():
#     global crawlers
#     queryResult = executeQuery("SELECT * FROM crawlers")
#     for column in queryResult:
#         crawlers.appe


def scheduler():
    cycleCounter = 0
    global scheduleList
    while(True):
        ct = datetime.datetime.now(pytz.timezone('Europe/Berlin'))
        #print("current time:-", ct)
        ts = ct.timestamp()
        # prevents timestamp from skipping a second due cpu delay
        if((ts%1) < 0.97):
            time.sleep(1)
        else:
            time.sleep(1-(ts%1))

        print(ts)
        if(executeQuery("SELECT MIN(scheduleTimestamp) FROM schedule")[0] == int(ts)):
            idQuery = "SELECT id FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + ";"
            instructionQuery = "SELECT instruction FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + ";"
            toDeleteQuery = "SELECT to_delete FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + ";"
            typeQuery = "SELECT type FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + ";"
            idsForTimestamp = executeQuery(idQuery)
            instructionsForTimestamp = executeQuery(instructionQuery)
            toDeleteForTimestamp = executeQuery(toDeleteQuery)
            typeForTimestamp = executeQuery(typeQuery)
            if(len(idsForTimestamp) > 1):
                for id in idsForTimestamp:
                    if(id not in deviceHasPendingInstructions):
                        deviceHasPendingInstructions.append(id)
            else:
                #print("query: " + str(executeQuery("SELECT espid FROM schedule WHERE scheduleTimestamp = " + str(timestamp) + ";")[0]))
                print(executeQuery(idQuery))
                #instructionPile[executeQuery("SELECT espid FROM schedule WHERE scheduleTimestamp = " + str(timestamp) + ";")[0]] = executeQuery("SELECT instruction FROM schedule WHERE scheduleTimestamp = " + str(timestamp) + ";")[0]
                if(executeQuery(idQuery)[0] not in deviceHasPendingInstructions):
                    deviceHasPendingInstructions.append(executeQuery(idQuery)[0])

            if(executeQuery(toDeleteQuery)[0] == "TRUE"):
                executeQuery("DELETE FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + ";")

            i = 0
            while (i < len(idsForTimestamp)):
                print('lololol')
                print(idsForTimestamp)
                scheduleList.append(schedule(idsForTimestamp[i], instructionsForTimestamp[i], toDeleteForTimestamp[i], typeForTimestamp[i], int(ts)))
                i = i + 1

        # cut 'none' elements after 10 cycles
        if(cycleCounter == 20):
            scheduleList = cutNoneElements(scheduleList)
            cycleCounter = 0

        cycleCounter = cycleCounter + 1

threadServer = threading.Thread(target=ThreadSocketServer, args=())
threadServer.start()

apiServer = threading.Thread(target=restApiServer, args=())
apiServer.start()

threadScheduler = threading.Thread(target=scheduler, args=())
threadScheduler.start()

# temporary, test purposes
# dd = pathfinding({"y": 8, "x": 1}, {"y": 1, "x": 1})
# dd.aStarStart()