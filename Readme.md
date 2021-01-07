# mythic_sync
mythic_sync is a standalone tool that will connect to a mythic_server to ingest command events and will then post them to the Ghostwriter oplog API. This allows users to automatically have their mythic commands, comments, and output all automatically logged to Ghostwriter. 

## Usage
After checking out the repository, open the settings.env file and fill out the variables with appropriate values. The following is an example:
```
MYTHIC_IP=10.10.1.100
MYTHIC_USERNAME=apfell_user
MYTHIC_PASSWORD=SuperSecretPassword
GHOSTWRITER_API_KEY=f7D2nMPz.v8V5ioCNsSSoO19wNnBZsDhhZNmzzwNE
GHOSTWRITER_URL=https://ghostwriter.mydomain.com
GHOSTWRITER_OPLOG_ID=123
```

Once the environment variables are setup, you can launch the service by using docker-compose:
```
docker-compose up
```

## Troubleshooting
mythic_sync uses an internal redis database to sync what events have already been sent to Ghostwriter, avoiding duplicates. If you want to re-sync, you will need to delete the volume and run it again.

If the mythic_sync service goes down, it is safe to stand it back up and avoid duplicates as long as the redis container wasn't force killed. 
