# odb_json_service
Provides API within an HTTPS environment using OrientDB 2.2 and Pyorient with OAuth, email confirmation and tokenized/timed sessions to control user access.

## OrientDB Service Setup
Install Orientdb 2.2 on the system.
Using Docker:
```javascript
sudo docker run -d --name orientdb -v /opt/orientdb/config -v /opt/orientdb/databases -v /opt/orientdb/backup -p 2424:2424 -p 2480:2480 -e ORIENTDB_ROOT_PASSWORD=<your password> orientdb:2.2.37 
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
Then run
 - sudo docker-compose up -d
 
This will build the application, run it on a Gunicorn exposed on 8000. You can then set your proxy such as Nginx to direct all traffic through an SSL to serve HTTPS. This enables you to connect the JsonData service to your web applications. It returns data in a graph format with nodes, lines and groups that can be used by the SAP UI5 NetworkGraph Library.
