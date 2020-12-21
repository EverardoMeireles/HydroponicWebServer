#!/usr/bin/env python

import asyncio
import websockets
import threading
import time
import sqlite3
from flask import Flask, json, render_template, request

framesReceive = []
api = Flask(__name__)

DATABASE = 'C:\sqlite3\hydroponicDatabase.db'

frameResult = {};

#get all sensor information
@api.route('/all', methods=['GET'])
def get_all():
    #all = [{"temperature": 1, "name": "Company One"}, {"id": 2, "name": "Company Two"}]
    #connection = sqlite3.connect("C:\sqlite3\hydroponicDatabase.db")
    #cursor = connection.cursor()
    #cursor.execute("INSERT INTO esp3 values(85);")
    #connection.commit()
    print('lelhgkhjkg')
    #connection.close()
    print(frameResult)
    return json.dumps(frameResult)

def frameBreakdown(frame):
    ESPId = frame[0] + frame[1] + frame[2]
    temperature = frame[3] + frame[4] + frame[5]
    frameResult = {
        "ESPId": ESPId,
        "temperature": temperature
    }
    print("DSQDQSDQSDDQD")
    return frameResult

def makeQueries():
    print("placeholder")

# Socket Server
async def receiver(websocket, path):
    framesReceive = (await websocket.recv())
    print(framesReceive)
    global frameResult
    frameResult = frameBreakdown(framesReceive)
    connection = sqlite3.connect("C:\sqlite3\hydroponicDatabase.db")
    cursor = connection.cursor()
    cursor.execute("INSERT INTO temperature (espid, value) VALUES(" + frameResult["ESPId"] + ", " + str(int(frameResult["temperature"])/10) + ");")
    connection.commit()
    #process the operation
    #time.sleep(15.4)
    #await websocket.send("pong")
    await websocket.send("pong" + framesReceive)

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

threadServer = threading.Thread(target=ThreadSocketServer, args=())
threadServer.start()

apiServer = threading.Thread(target=restApiServer, args=())
apiServer.start()