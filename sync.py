#!/usr/bin/env python
import json
import os
import re
import redis
import requests
import ssl
import time
import websocket
from datetime import datetime


MYTHIC_USERNAME = os.environ["MYTHIC_USER"]
MYTHIC_PASSWORD = os.environ["MYTHIC_PASSWORD"]
MYTHIC_IP = os.environ["MYTHIC_IP"]

GHOSTWRITER_API_KEY = os.environ["GHOSTWRITER_API_KEY"]
GHOSTWRITER_URL = os.environ["GHOSTWRITER_URL"]
GHOSTWRITER_OPLOG_ID = os.environ["GHOSTWRITER_OPLOG_ID"]
AUTH = {}

HTTP = "http"
WS = "ws"


class CommandLogger(object):
    def __init__(self, endpoint):
        self.login()
        self.ws = websocket.WebSocketApp(
            endpoint,
            on_message=lambda ws, msg: self.on_message(ws, msg),
            on_error=lambda ws, msg: self.on_error(ws, msg),
            on_close=lambda ws: self.on_close(ws),
            on_open=lambda ws: self.on_open(ws),
            cookie=f"access_token={AUTH['access_token']}",
        )
        self.rconn = redis.Redis(host="redis", port=6379, db=0)

    def getMessage(self, task_id):
        return self.rconn.get(task_id)

    def addMessage(self, message, oplog_id):
        try:
            # First, add to GW
            gw_message = {}
            if "status_timestamp_submitted" in message and message["status_timestamp_submitted"]:
                start_date = datetime.strptime(message["status_timestamp_submitted"], "%m/%d/%Y %H:%M:%S")
                gw_message["start_date"] = start_date.strftime("%Y-%m-%d %H:%M:%S")
            if "status_timestamp_processed" in message and message["status_timestamp_processed"]:
                end_date = datetime.strptime(message["status_timestamp_processed"], "%m/%d/%Y %H:%M:%S")
                gw_message["end_date"] = end_date.strftime("%Y-%m-%d %H:%M:%S")
            # gw_message['start_date'] = message['status_timestamp_submitted']
            # gw_message['end_date'] = message['status_timestamp_processed']
            gw_message["source_ip"] = ""
            gw_message["dest_ip"] = ""
            gw_message["tool"] = ""
            gw_message["user_context"] = message.get("user", "")
            gw_message["command"] = f"{message.get('command', '')} {message.get('params', '')}"
            gw_message["description"] = ""
            gw_message["comments"] = message.get("comment", "")
            gw_message["operator_name"] = message.get("operator", "")
            gw_message["oplog_id"] = GHOSTWRITER_OPLOG_ID
            gw_message["output"] = ""

            if message["status"] == "processed":
                url = f"{HTTP}://{MYTHIC_IP}/api/v1.4/tasks/{message['id']}"
                response = requests.get(
                    url,
                    headers={"Authorization": f"Bearer {AUTH['access_token']}", "Content-Type": "application/json"},
                )
                data = json.loads(response.text)
                if "callback" in data:
                    gw_message["dest_ip"] = data["callback"].get("ip", "")
                    gw_message["tool"] = data["callback"].get("payload_type", "")
                if "responses" in data:
                    output = ""
                    for task_rep in data["responses"]:
                        output += json.dumps(task_rep)
                    gw_message["output"] = output

            headers = {"Authorization": f"Api-Key {GHOSTWRITER_API_KEY}", "Content-Type": "application/json"}
        except Exception as e:
            print(e)

        if not oplog_id:
            print("Adding message")
            response = requests.post(
                f"{GHOSTWRITER_URL}/oplog/api/entries/", data=json.dumps(gw_message), headers=headers
            )
        else:
            print("Updating message")
            response = requests.put(
                f"{GHOSTWRITER_URL}/oplog/api/entries/{oplog_id}/?format=json",
                data=json.dumps(gw_message),
                headers=headers,
            )

        if not response.status_code == 201:
            print(f"[!] Error posting to Ghostwriter: {response.status_code}")
        else:
            created_obj = json.loads(response.text)
            self.rconn.set(message["agent_task_id"], created_obj["id"])

    def on_message(self, ws, message):
        if len(message) > 0:
            print(message)
            message = json.loads(message)
            task_id = message["agent_task_id"]
            oplog_id = self.getMessage(task_id)
            if not oplog_id:
                self.addMessage(message, oplog_id)
            else:
                self.addMessage(message, oplog_id.decode())

    def on_error(self, ws, msg):
        print(msg)

    def on_close(self, ws):
        pass

    def on_open(self, ws):
        print("socket opened")

    def run_forever(self, opts):
        self.ws.run_forever(sslopt=opts)

    def login(self):
        url = f"{HTTP}://{MYTHIC_IP}/auth"
        data = {"username": MYTHIC_USERNAME, "password": MYTHIC_PASSWORD}
        resp = requests.post(url, data=json.dumps(data))
        if resp.status_code == 200:
            if "Set-Cookie" in resp.headers:
                cookie_dict = {}
                cookie = resp.headers["Set-Cookie"]
                pairs = re.split(";|,", cookie)
                for pair in pairs:
                    try:
                        key, value = pair.split("=")
                        cookie_dict[key.strip()] = value.strip()
                    except ValueError:
                        continue

                AUTH["access_token"] = cookie_dict["access_token"]
                AUTH["refresh_token"] = cookie_dict["refresh_token"]


if __name__ == "__main__":
    command_logger = CommandLogger(f"{WS}://{MYTHIC_IP}/ws/task_feed/current_operation")
    command_logger.run_forever({"cert_reqs": ssl.CERT_NONE, "check_hostname": False})

