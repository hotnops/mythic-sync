# mythic_sync
mythic_sync is a standalone tool that will connect to a mythic_server to ingest command events and will then post them to the Ghostwriter oplog API. This allows users to automatically have their mythic commands, comments, and output all automatically logged to Ghostwriter. 

## Usage

1. After checking out the repository, open the settings.env file and fill out the variables with appropriate values. The following is an example:
```
MYTHIC_IP=10.10.1.100
MYTHIC_USER=apfell_user
MYTHIC_PASSWORD=SuperSecretPassword
GHOSTWRITER_API_KEY=f7D2nMPz.v8V5ioCNsSSoO19wNnBZsDhhZNmzzwNE
GHOSTWRITER_URL=https://ghostwriter.mydomain.com
GHOSTWRITER_OPLOG_ID=123
```

2. Once the environment variables are setup, you can launch the service by using docker-compose:
```
docker-compose up
```
3. Verify an initial entry in your Ghostwriter's oplog was created. You should see something like:
    > Initial entry from mythic_sync at: <server_ip>. If you're seeing this then oplog syncing is working for this C2 server!
4. If so, you're all set! Othwerwise, see "Troubleshooting"


## Without docker
First, install python virtual environments for python3 and redis
```
apt install python3-venv redis
```
Create a new tmux session and virtual environment for mythic-sync and install required modules
```
tmux
python3 -m venv .
source bin/activate
pip install -r requirements.txt
```

Set the environment variables and then run sync.py (ideally in a named Tmux session, tmux `new -s mythic_sync`)
```
source ./settings.sh
python sync.py
```


## Troubleshooting
mythic_sync uses an internal redis database to sync what events have already been sent to Ghostwriter, avoiding duplicates. If you want to re-sync, you will need to delete the volume and run it again.

If the mythic_sync service goes down, it is safe to stand it back up and avoid duplicates as long as the redis container wasn't force killed. 
