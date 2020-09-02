import json
import os
import redis
import requests

from datetime import datetime
from mythic import *
from sys import exit

MYTHIC_USERNAME = os.environ["MYTHIC_USERNAME"]
MYTHIC_PASSWORD = os.environ["MYTHIC_PASSWORD"]
MYTHIC_IP = os.environ["MYTHIC_IP"]

GHOSTWRITER_API_KEY = os.environ["GHOSTWRITER_API_KEY"]
GHOSTWRITER_URL = os.environ["GHOSTWRITER_URL"]
GHOSTWRITER_OPLOG_ID = os.environ["GHOSTWRITER_OPLOG_ID"]
AUTH = {}

rconn = redis.Redis(host="redis", port=6379, db=0)
headers = {'Authorization': f"Api-Key {GHOSTWRITER_API_KEY}", "Content-Type": "application/json"}


def mythic_response_to_ghostwriter_message(message):
    gw_message = mythic_task_to_ghostwriter_message(message['task'])
    gw_message['output'] = message['response']
    return gw_message

def mythic_task_to_ghostwriter_message(message):

    gw_message = {}
    if "status_timestamp_submitted" in message and message["status_timestamp_submitted"]:
        start_date = datetime.strptime(message["status_timestamp_submitted"], "%m/%d/%Y %H:%M:%S")
        gw_message["start_date"] = start_date.strftime("%Y-%m-%d %H:%M:%S")
    if "status_timestamp_processed" in message and message["status_timestamp_processed"]:
        end_date = datetime.strptime(message["status_timestamp_processed"], "%m/%d/%Y %H:%M:%S")
        gw_message["end_date"] = end_date.strftime("%Y-%m-%d %H:%M:%S")
    # gw_message['start_date'] = message['status_timestamp_submitted']
    # gw_message['end_date'] = message['status_timestamp_processed']
    gw_message["user_context"] = message.get("user", "")
    gw_message["command"] = f"{message.get('command', '')} {message.get('params', '')}"
    gw_message["comments"] = message.get("comment", "")
    gw_message["operator_name"] = message.get("operator", "")
    gw_message["oplog_id"] = GHOSTWRITER_OPLOG_ID
    
    return gw_message


def createEntry(message):
    print(f"[*] Adding task: {message['agent_task_id']}")
    gw_message = mythic_task_to_ghostwriter_message(message)
    try:
        response = requests.post (
            f"{GHOSTWRITER_URL}/oplog/api/entries/", data=json.dumps(gw_message), headers=headers, verify=False
        )

        if response.status_code != 201:
            print(f"[!] Error posting to Ghostwriter: {response.status_code}")
        else:
            created_obj = json.loads(response.text)
            rconn.set(message["agent_task_id"], created_obj["id"])

    except Exception as e:
        print(e)


def updateEntry(message, entry_id):
    print(f"[*] Updating task: {message['agent_task_id']} : {entry_id}")
    gw_message = mythic_task_to_ghostwriter_message(message)
    try:
        response = requests.put (
            f"{GHOSTWRITER_URL}/oplog/api/entries/{entry_id}/?format=json", data=json.dumps(gw_message), headers=headers, verify=False
        )

        if response.status_code != 200:
            print(f"[!] Error posting to Ghostwriter: {response.status_code}")
        
    except Exception as e:
        print(e)


async def handle_task(mythic, data):
    payloads = await mythic.get_payloads()

    message = json.loads(data)
    entry_id = rconn.get(message["agent_task_id"])
    if entry_id != None:
        updateEntry(message, entry_id.decode())
    else:
        createEntry(message)
    
async def handle_response(token, data):

    message = json.loads(data)

    entry_id = rconn.get(message["task"]["agent_task_id"])
    if not entry_id:
        print(f"[!] Received a response for a task that doesn't exist.")
        return

    gw_message = mythic_response_to_ghostwriter_message(message)

    print(f"[*] Updating entry with response data: {entry_id.decode()}")

    response = requests.put(
        f"{GHOSTWRITER_URL}/oplog/api/entries/{entry_id.decode()}/?format=json",
        data=json.dumps(gw_message),
        headers=headers,
        verify=False
    )

    if response.status_code !=  200:
        print(f"[!] Error updating ghostwriter entry: {response.status_code}")

async def scripting():
    mythic = Mythic(username=MYTHIC_USERNAME, password=MYTHIC_PASSWORD,
                    server_ip=MYTHIC_IP, server_port="7443", ssl=True, global_timeout=-1)

    await mythic.login()
    resp = await mythic.set_or_create_apitoken()

    await mythic.listen_for_all_tasks(handle_task)
    await mythic.listen_for_all_responses(handle_response)

async def main():
    await scripting()
    try:
        while True:
            pending = asyncio.Task.all_tasks()
            if len(pending) == 0:
                exit(0)
            else:
                await asyncio.gather(*pending)

    except KeyboardInterrupt:
        pending = asyncio.Task.all_tasks()
        for p in pending:
            p.cancel()

print("[*] Starting sync")
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
