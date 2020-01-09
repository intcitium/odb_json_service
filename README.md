# odb_json_service
Provides API within an HTTPS environment using OrientDB 2.2 and Pyorient with OAuth, email confirmation and tokenized/timed sessions to control user access.

## OrientDB Service Setup
Install Orientdb 2.2 on the system.
Using Docker:
```javascript
sudo docker run -d --name orientdb -v /opt/orientdb/config -v /opt/orientdb/databases -v /opt/orientdb/backup -p 2424:2424 -p 2480:2480 -e ORIENTDB_ROOT_PASSWORD=<your password> orientdb:2.2.37 

sudo docker run -d --name orientdb -v config_path:/opt/orientdb/config -v databases_path:/opt/orientdb/databases -v backup_path:/opt/orientdb/backup -p 2424:2424 -p 2480:2480 -e ORIENTDB_ROOT_PASSWORD=<your password> orientdb:2.2.37
```
Detailed instructions at the link or follow the 2 steps below.
https://orientdb.com/docs/last/Unix-Service.html
### Create a service file
```python
# vi /etc/systemd/system/orientdb.service

#
# Copyright (c) OrientDB LTD (http://http://orientdb.com/)
#

[Unit]
Description=OrientDB Server
After=network.target
After=syslog.target

[Install]
WantedBy=multi-user.target

[Service]
User=ORIENTDB_USER
Group=ORIENTDB_GROUP
ExecStart=$ORIENTDB_HOME/bin/server.sh
```
### Enable the service
Then enable the service to startup on system reset
```python
# systemctl start orientdb.service
```
## API Service Setup
With an orientDB 2.2 set up behind an HTTPS server, modify the config.py file within the apiserver to your settings:
```python
HOST_IP = "YOUR SERVER IP THAT IS EXPOSED TO THE INTERNET"
HTTPS = "https://%s" % HOST_IP
SECRET_KEY = 'AweseomelySecretKeyThatNobodyCanGuessJustTryandCrack!tComeon'
MAIL_USERNAME = 'YOUR GMAIL'
MAIL_PASSWORD = 'YOUR GMAIL PASSWORD'
COPILOT_URL = 'https://api.cai.tools.sap/auth/v1/owners/YOUR ACCOUNT'
COPILOT_AUTH = 'YOUR TOKEN'
COPILOT_DEV_TOKEN = 'Token YOUR TOKEN'
```
Then start the api server. 
```javascript
sudo docker-compose up -d
 ```
You should get a message to initialize the databases.
```javascript
website_1  | [2020-01-09 09:40:04 +0000] [1] [INFO] Starting gunicorn 19.9.0
website_1  | [2020-01-09 09:40:04 +0000] [1] [INFO] Listening at: http://0.0.0.0:8000 (1)
website_1  | [2020-01-09 09:40:04 +0000] [1] [INFO] Using worker: sync
website_1  | [2020-01-09 09:40:04 +0000] [9] [INFO] Booting worker with pid: 9
website_1  | [2020-01-09 09:40:04 +0000] [11] [INFO] Booting worker with pid: 11
website_1  | [2020-01-09 09:40:04 +0000] [13] [INFO] Booting worker with pid: 13
website_1  | [2020-01-09 09:40:04 +0000] [15] [INFO] Booting worker with pid: 15
website_1  | [2020-01-09 09:40:05_Home_init] Setup required
website_1  | [2020-01-09 09:40:05_User_init] Setup required
website_1  | [2020-01-09 09:40:05_Home_init] Setup required
website_1  | [2020-01-09 09:40:05_User_init] Setup required
website_1  | [2020-01-09 09:40:05_Home_init] Setup required
website_1  | [2020-01-09 09:40:05_Home_init] Setup required
website_1  | [2020-01-09 09:40:05_User_init] Setup required
website_1  | [2020-01-09 09:40:05_User_init] Setup required
 ```
Go to the db_init urls to start up the systems. Then reset the api server by stopping the and restarting the docker container.
 
This will build the application, run it on a Gunicorn exposed on 8000. You can then set your proxy such as Nginx to direct all traffic through an SSL to serve HTTPS. This enables you to connect the JsonData service to your web applications. It returns data in a graph format with nodes, lines and groups that can be used by the SAP UI5 NetworkGraph Library.
