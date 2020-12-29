#!/usr/bin/env python

import asyncio
import websockets
import threading
import time
import sqlite3
from flask import Flask, json, render_template, request
import datetime;
import pytz


framesReceive = []
api = Flask(__name__)

DATABASE = 'C:\sqlite3\hydroponicDatabase.db'

frameResult = {}
instructionList = []
espIdList = []

espHasPendingInstructions = []
#get all sensor information
@api.route('/all', methods=['GET'])
def get_all():
    #all = [{"temperature": 1, "name": "Company One"}, {"id": 2, "name": "Company Two"}]
    #connection = sqlite3.connect("C:\sqlite3\hydroponicDatabase.db")
    #cursor = connection.cursor()
    #cursor.execute("INSERT INTO esp3 values(85);")
    #connection.commit()
    #connection.close()
    print(frameResult)
    return json.dumps(frameResult)

def frameBreakdown(frame):
    ESPId = frame[0] + frame[1] + frame[2]
    temperature = frame[3] + frame[4] + frame[5]
    frameResult = {
        "ESPId": int(ESPId),
        "temperature": int(temperature)
    }
    return frameResult

def executeQuery(query):
    connection = sqlite3.connect("C:\sqlite3\hydroponicDatabase.db")
    connection.row_factory = lambda cursor, row: row[0]
    cursor = connection.cursor()
    queryResult = cursor.execute(query)
    connection.commit()
    return queryResult.fetchall()
    connection.close()

def prepareToSendInstructions(espid):
    global espHasPendingInstructions
    global espIdList
    global instructionList
    #if there are no instructions for this esp "" will be sent
    instructionToSend = ""
    e = int(espid)
    b = str(int(espid))
    c = espHasPendingInstructions
    if(int(espid) in espHasPendingInstructions):
        e = int(espid)
        i = 0

        for id in espIdList:
            if(id == espid):
                instructionToSend = instructionList[i]
                espIdList[i] = None
                instructionList[i] = None
                break
            i = i + 1

        if(espIdList.count(espid) == 0):
            espHasPendingInstructions[espHasPendingInstructions.index(espid)] = None

    return instructionToSend

# Socket Server
async def receiver(websocket, path):
    framesReceive = (await websocket.recv())
    print(framesReceive)
    global frameResult
    frameResult = frameBreakdown(framesReceive)
    executeQuery("INSERT INTO temperature (espid, value) VALUES(" + str(frameResult["ESPId"]) + ", " + str(int(frameResult["temperature"])/10) + ");")
    instructionToSend = prepareToSendInstructions(frameResult["ESPId"])
    #print("FINAL: " + instructionToSend)

    await websocket.send(instructionToSend)

# Socket Server thread
def ThreadSocketServer():
    asyncio.set_event_loop(asyncio.new_event_loop())
    start_server = websockets.serve(receiver, "192.168.2.112", 5153)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
    api.run()

def restApiServer():
    if __name__ == '__main__':
        api.run(host="0.0.0.0", port=5154, debug=False)

# send instruction to esp as a response
def sendInstruction(espid):
    print("placeholder")
    #instructionPile

def cutNoneElements(list):
    tempList = []
    for element in list:
        if(element != None):
            tempList.append(element)
    return tempList

def scheduler():
    cycleCounter = 0
    global instructionList
    global espIdList
    while(True):
        ct = datetime.datetime.now(pytz.timezone('Europe/Berlin'))
        #print("current time:-", ct)
        ts = ct.timestamp()
        if((ts%1) < 0.97):
            time.sleep(1)
        else:
            time.sleep(1-(ts%1))

        print(ts)
        if(executeQuery("SELECT MIN(scheduleTimestamp) FROM schedule")[0] == int(ts)):
            print("espID: " + str(espIdList))
            print("instructions: " + str(instructionList))
            espIdQuery = "SELECT espid FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + ";"
            instructionQuery = "SELECT instruction FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + ";"
            espIdsForTimestamp = executeQuery(espIdQuery)
            instructionsForTimestamp = executeQuery(instructionQuery);
            if(len(espIdsForTimestamp) > 1):
                for espId in espIdsForTimestamp:
                    espIdList.append(espId)
                    if(espId not in espHasPendingInstructions):
                        espHasPendingInstructions.append(espId)
                for instruction in instructionsForTimestamp:
                    instructionList.append(instruction)
            else:
                #print("query: " + str(executeQuery("SELECT espid FROM schedule WHERE scheduleTimestamp = " + str(timestamp) + ";")[0]))
                print(executeQuery(espIdQuery))
                instructionList.append(executeQuery(instructionQuery)[0])
                espIdList.append(executeQuery(espIdQuery)[0])
                #instructionPile[executeQuery("SELECT espid FROM schedule WHERE scheduleTimestamp = " + str(timestamp) + ";")[0]] = executeQuery("SELECT instruction FROM schedule WHERE scheduleTimestamp = " + str(timestamp) + ";")[0]
                if(executeQuery(espIdQuery)[0] not in espHasPendingInstructions):
                    espHasPendingInstructions.append(executeQuery(espIdQuery)[0])
            if(executeQuery("SELECT to_delete FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + ";")[0] == "TRUE"):
                executeQuery("DELETE FROM schedule WHERE scheduleTimestamp = " + str(int(ts)) + ";")
            #print(espIdList)
            #print(instructionList)

        if(cycleCounter == 20):
            instructionList = cutNoneElements(instructionList)
            espIdList = cutNoneElements(espIdList)
            cycleCounter = 0
        cycleCounter = cycleCounter + 1
threadServer = threading.Thread(target=ThreadSocketServer, args=())
threadServer.start()

apiServer = threading.Thread(target=restApiServer, args=())
apiServer.start()

threadScheduler = threading.Thread(target=scheduler, args=())
threadScheduler.start()