# odb_json_service
Provides API within an HTTPS environment using OrientDB 2.2 and Pyorient with OAuth, email confirmation and tokenized/timed sessions to control user access.

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