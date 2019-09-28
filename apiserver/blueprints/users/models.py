from apiserver.blueprints.home.models import ODB, get_datetime
from apiserver.utils import SECRET_KEY, SIGNATURE_EXPIRED, BLACK_LISTED, DB_ERROR, PROTECTED, change_if_date,\
    send_mail, HTTPS, randomString
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer
import click

class userDB(ODB):

    def __init__(self, db_name="Users"):
        ODB.__init__(self, db_name)
        self.db_name = db_name
        self.ICON_SESSION = "sap-icon://activities"
        self.ICON_POST = "sap-icon://post"
        self.ICON_USER = "sap-icon://customer"
        self.ICON_BLACKLIST = "sap-icon://cancel"
        self.models = {
            "User": {
                "key": "integer",
                "createDate": "datetime",
                "userName": "string",
                "passWord": "string",
                "email": "string",
                "icon": "string",
                "confirmed": "boolean",
                "class": "V"
            },
            "Message": {
                "key": "integer",
                "class": "V",
                "text": "string",
                "title": "string",
                "tags": "string",
                "sender": "string",
                "receiver": "string",
                "icon": "string",
                "createDate": "datetime"
            },
            "Session": {
                "key": "integer",
                "user": "string",
                "startDate": "datetime",
                "endDate": "datetime",
                "ipAddress": "string",
                "token": "string",
                "icon": "string",
                "class": "V"
            },
            "Blacklist": {
                "key": "integer",
                "token": "string",
                "user": "string",
                "session": "string",
                "createDate": "string",
                "icon": "string",
                "class": "V"
            }
        }

    def check_standard_users(self):
        """
        Sets up the initial users as channels to fill Application dependent lists. Users serve standard functions
        that can be used in various automated situations
        :return:
        """
        users = []
        for r in self.client.command('''
        select userName from User 
        '''):
            users.append(r.oRecordData['userName'])

        if "GeoAnalyst" not in users:
            click.echo('[%s_UserServer_init] Creating standard user GeoAnalyst' % (get_datetime()))
            self.create_user({
                "userName": "GeoAnalyst",
                "email": "NetworkGraph@Support.mail",
                "passWord": randomString(16),
                "confirmed": "true",
                "icon": self.ICON_GEOINT
            })

        if "SocAnalyst" not in users:
            click.echo('[%s_UserServer_init] Creating standard user SocAnalyst' % (get_datetime()))
            self.create_user({
                "userName": "SocAnalyst",
                "email": "NetworkGraph@Support.mail",
                "passWord": randomString(16),
                "confirmed": "true",
                "icon": self.ICON_SOCINT
            })

        if "HumintAnalyst" not in users:
            click.echo('[%s_UserServer_init] Creating standard user HumintAnalyst' % (get_datetime()))
            self.create_user({
                "userName": "HumintAnalyst",
                "email": "NetworkGraph@Support.mail",
                "passWord": randomString(16),
                "confirmed": "true",
                "icon": self.ICON_HUMINT
            })

    def send_message(self, request):
        """
        Create a message and then wire relationships as following
        Session to message for Logging
        Sender to message for Activity of user
        Message to Receiver for Alerting
        :param request:
        :return:
        """
        if str(type(request)) == "<class 'werkzeug.local.LocalProxy'>":
            form = request.form.to_dict()
            sessionId = request.headers['SESSIONID']
        # For internal requests not coming from HTTP
        else:
            form = request
            sessionId = request['sessionId']
        # Create the Message Node
        msg = self.create_node(
            class_name="Message",
            text=form['text'],
            title=form['title'],
            sender=form['sender'],
            receiver=form['receiver'],
            createDate=get_datetime(),
            icon=self.ICON_POST)
        # Create relations from sender to post and post to receiver.
        try:
            senderKey = self.get_user(userName=form['sender'])[0].oRecordData['key']
        except:
            msg['message'] = "No sender identified with key %s" % form['sender']
            return msg
        try:
            receiverKey = self.get_user(userName=form['receiver'])[0].oRecordData['key']
        except:
            msg['message'] = "No receiver identified with key %s" % form['receiver']
            return msg
        msgKey = msg['data']['key']
        msg['message'] = "Message sent from %s with subject %s to %s on %s" % (
            form['sender'], form['title'], form['receiver'], get_datetime())
        self.create_edge(fromNode=sessionId, fromClass="Session", toNode=msgKey, toClass="Message", edgeType="Logged")
        self.create_edge(fromNode=senderKey, fromClass="User", toNode=msgKey, toClass="Message", edgeType="Sent")
        self.create_edge(fromNode=msgKey, fromClass="Message", toNode=receiverKey, toClass="User", edgeType="SentTo")
        # for tag in tags create a new node and relate it TODO
        return msg

    def get_messages(self, **kwargs):
        """
        Get messages associated with the userName and return a list of selectable items for each Sent and Received
        ODB 2.2 requires the select from a match to apply the sorting "order by".
        The sorting of the m_key sets sets the list so a chronology of the message life cycle is shown and loaded
        into the return value.
        The message can be determined as new for a user if there is nothing in the read column. To ensure this is
        consistent for messages received and read by other users, the condition for checking on sender or receiver
        equal to kwargs['userName'] is implemented.
        :param kwargs:
        :return:
        """
        msg_index = {}
        current_key = None
        for msg in self.client.command('''
            select from (match
            {class:User, as:u}.bothE()
            {class:E, as: e}.bothV()
            {class:Message, as:m, where: (sender = '%s')}
            return u.key, u.userName, 
            e.DTG, e.@class, 
            m.key, m.title, m.icon, m.text, m.sender, m.receiver, m.createDate)
            order by m.key
        ''' % kwargs['userName']):
            # If still the current message, add the new information
            if current_key == msg.oRecordData['m_key']:
                if msg.oRecordData['e_DTG'] and (
                        msg_index[current_key]['receiver'] == kwargs['userName'] or
                        msg_index[current_key]['sender'] == kwargs['userName']):
                    msg_index[current_key]['activity'].append({
                        "read_by": msg.oRecordData['m_receiver'],
                        "read_on": msg.oRecordData['e_DTG']
                    })
                    if msg_index[current_key]['read']:
                        new_date = change_if_date(msg.oRecordData['e_DTG'])
                        if new_date > change_if_date(msg_index[current_key]['read']):
                            msg_index[current_key]['read'] = msg.oRecordData['e_DTG']
                    else:
                        msg_index[current_key]['read'] = msg.oRecordData['e_DTG']
            else:
                current_key = msg.oRecordData['m_key']
                msg_index[current_key] = {
                    'key': msg.oRecordData['m_key'],
                    'sender': msg.oRecordData['m_sender'],
                    'receiver': msg.oRecordData['m_receiver'],
                    'title': msg.oRecordData['m_title'],
                    'icon': msg.oRecordData['m_icon'],
                    'text': msg.oRecordData['m_text'],
                    'sent': msg.oRecordData['m_createDate'],
                    'activity': [],
                    'read': False
                }
        data = {'data': []}
        for m in msg_index:
            data['data'].append(msg_index[m])
        data['message'] = "Found %s sent and %s received messages for %s" % (
            len(data['data']), len(data['data']), kwargs['userName'])
        return data

    def read_message(self, **kwargs):
        """
        Update a message as read by the receiver with a new edge from the UserKey to the MessageKey
        Return an updated list of messages to refresh the inbox
        :param kwargs:
        :return:
        """
        data = {
            "data": []
        }
        sql = '''
        create edge {edgeType} from 
        (select from {fromClass} where key = {fromNode}) to 
        (select from {toClass} where key = {toNode}) set DTG = '{DTG}'
        '''.format(edgeType="Read", fromNode=kwargs['userKey'], toNode=kwargs['msgKey'],
                   fromClass="User", toClass="Message", DTG=get_datetime())
        try:
            self.client.command(sql)
        except Exception as e:
            click.echo("Error reading message %s" % str(e))

        data['message'] = "Message %s read" % (kwargs['msgKey'])
        return data

    def create_session(self, form, ip_address, token):
        """
        Create an object to track the activities of a user
        :param form:
        :param ip_address:
        :param token:
        :return:
        """
        session = self.create_node(
            class_name="Session",
            startDate=get_datetime(),
            ipAddress=ip_address,
            token=token,
            createDate=get_datetime(),
            user=form['userName'],
            icon=self.ICON_SESSION
        )

        return session

    def get_user_cases(self, **kwargs):
        """
        Check each available database and get the cases that include that user in either Members, Owners, or CreatedBy
        The return should be the complete model for the user to get all related data from in other models. The keys
        TODO Put a status based on Classification Maybe in create class or keep as a CustomCase code dependent on View
        :param kwargs:
        :return:
        """
        from apiserver.blueprints.osint.models import OSINT
        osintserver = OSINT()
        osintserver.open_db()
        cases = {"data": [], "Unclassified": 0, "Confidential": 0}
        cOSINT = osintserver.client.command(
            '''select key, Name, CreatedBy, Owners, Members, Classification, StartDate, LastUpdate from Case
            ''')
        for c in cOSINT:
            role = None
            c = c.oRecordData
            # QUALITY check on records
            if 'Members' not in c.keys():
                 c['Members'] = ""
            if 'Owners' not in c.keys():
                c['Owners'] = ""
            if 'CreatedBy' not in c.keys():
                c['CreatedBy'] = ""
            # User linkage check
            if c['Members'] != "" and kwargs['userName'] in c['Members'].split(","):
                role = "Member"
            elif c['Owners'] != "" and kwargs['userName'] in c['Owners'].split(","):
                role = "Owner"
            elif kwargs['userName'] == c['CreatedBy']:
                role = "Owner"
            # If linked then add the case with the role
            if role:
                cases['data'].append({
                    "key": c['key'],
                    "Name": c['Name'],
                    "CreatedBy": c['CreatedBy'],
                    "Owners": c['Owners'],
                    "Members": c['Members'],
                    "Classification": c['Classification'],
                    "StartDate": c['StartDate'],
                    "LastUpdate": c['LastUpdate'],
                    "Role": role
                })
                if c['Classification'] == "Unclassified":
                    cases['Unclassified']+=1
                elif c['Classification'] == "Confidential":
                    cases['Confidential']+=1
        if len(cases['data']) == 1:
            c_count = "case"
        else:
            c_count = "cases"

        cases['message'] = "%d %s found for %s" % (len(cases['data']), c_count, kwargs['userName'])
        return cases

    def login(self, request):
        """
        Check the user confirmation status and password based on the supplied userName
        TODO - Select from Case where Case.Owners.containsText(userKey) to return the cases
        :param form:
        :return: token or none
        """
        try:
            response = {"received": str(request), "session": None}
            ip_address = request.remote_addr
            form = request.form.to_dict(flat=True)
            r = self.client.command('''
            select passWord, key, confirmed, email from User where userName = "{userName}"
            '''.format(userName=form["userName"]))
            if len(r) == 0:
                response["message"] = "No user exists with name {userName}".format(userName=form["userName"])

            if r[0].oRecordData['confirmed'] == False or str(r[0].oRecordData['confirmed']).lower() == 'false':
                self.confirm_user_email(userName=form['userName'], email=r[0].oRecordData['email'])
                response["message"] = ('''
                Unconfirmed user. A new confirmation message has been
                 sent to the registered email, %s''' % r[0].oRecordData['email'])
            else:
                password = r[0].oRecordData['passWord']
                key = r[0].oRecordData['key']
                if check_password_hash(password, form['passWord']):
                    token = self.serialize_token(userName=form['userName'])
                    session = self.create_session(form, ip_address, token)
                    self.create_edge(fromNode=key, fromClass="User", toNode=session['data']['key'],
                                     toClass="Session", edgeType="UserSession")
                    response["token"] = token
                    response["session"] = session["data"]["key"]
                    response["data"] = self.get_activity(userName=form['userName'])
                    response["data"]["cases"] = self.get_user_cases()
                else:
                    response["message"] = "Incorrect password"

        except Exception as e:
            response["message"] = "Unknown error %s" % str(e) + "\n%s" % str(request)

        return response

    def logout(self, request):
        """
        Look up a session and update the endDate with getTime
        Blacklist the token by creating a blacklist object with the token data
        :param request:
        :return:
        """
        # Look up the session and update the endDate with new getTime
        # Blacklist the token and associate with the Session

        r = request.form.to_dict(flat=True)
        dLOGOUT = get_datetime()
        try:
            self.update(class_name="Session", var="endDate", val=dLOGOUT, key=int(request.headers['SESSIONID']))
            blackListNode = self.create_node(
                class_name="Blacklist",
                createtDate=dLOGOUT,
                token=request.headers['AUTHORIZATION'],
                user=r['userName'],
                session=request.headers['SESSIONID'],
                icon=self.ICON_BLACKLIST
            )

            self.create_edge(edgeType="ClosedSession", fromNode=blackListNode['data']['key'], fromClass="Blacklist",
                             toNode=request.headers['SESSIONID'], toClass="Session")

            return "User {userName} logged out from session {session} at {date}".format(
                userName=r['userName'], session=request.headers['SESSIONID'], date=dLOGOUT)

        except Exception as e:
            if "ValueError" in str(e):
                return "User {userName} session with id {session} for {date} is not valid".format(
                    userName=r['userName'], session=request.headers['SESSIONID'], date=dLOGOUT)
            if request.headers['SESSIONID'] == '':
                return "User {userName} session is blank".format(
                    userName=r['userName'])

    def check_blacklist(self, token):
        """
        If there is a payload in getting a Blacklist with this token val, then it is Blacklisted
        :param token:
        :return:
        """
        bl = self.get_node(class_name="Blacklist", var="token", val=token)
        return bl

    def get_users(self):
        """
        Get all the non-system users and return them in the form of graph nodes for use in the application
        :return:
        """
        r = self.client.command('''
        select userName, key, email, createDate, icon, confirmed from User 
        ''')
        users = {"data": []}
        for u in r:
            u = u.oRecordData
            if u['email'] != "Chatbot@email.com" and u['userName'][:6] != "SYSTEM":
                users["data"].append(self.format_node(
                    key=u['key'],
                    icon=u['icon'],
                    class_name="User",
                    title="User %s" % u['userName'],
                    status="Information",
                    attributes=[
                        {"label": "Name", "value": u['userName']},
                        {"label": "Email", "value": u['email']},
                        {"label": "Confirmed", "value": u['confirmed']},
                        {"label": "Created", "value": u['createDate']},
                    ]
                ))

        users['message'] = "Found %d users" % len(users['data'])
        return users

    def get_user(self, **kwargs):

        if "userName" in kwargs.keys():
            r = self.client.command('''
            select userName, email, createDate, key from User where userName = "{userName}"
            '''.format(userName=kwargs["userName"]))
        else:
            r = self.client.command('''
            select userName, email, createDate, key from User where email = "{email}"
            '''.format(email=kwargs["email"]))

        if len(r) == 0:
            return None
        else:
            return r

    def get_activity(self, **kwargs):

        if 'request' in kwargs:
            userName = kwargs['request'].form.to_dict()['userName']
        else:
            userName = kwargs['userName']

        u = self.get_user(userName=userName)

        if u:
            sql = '''
            match {class: User, as: u, where: (key = %d)}.both(){class: V, as: e} return $elements
            ''' % (int(u[0].oRecordData['key']))
            r = self.client.command(sql)
            if len(r) > 0:
                nodes = []
                lines = []
                for i in r:
                    # Get the relationship types and each variable into the attributes array for a node
                    attributes = []
                    title = icon = status = class_name = None
                    for k in i.oRecordData.keys():
                        if str(type(i.oRecordData[k])) != "<class 'pyorient.otypes.OrientBinaryObject'>":
                            if k.lower() == 'key':
                                key = i.oRecordData[k]
                            elif k.lower() == 'icon':
                                icon = i.oRecordData[k]
                            elif k.lower() == 'title':
                                title = i.oRecordData[k]
                            elif k.lower() == 'status':
                                status = i.oRecordData[k]
                            elif k.lower() == 'class_name':
                                class_name = i.oRecordData[k]
                            elif k.lower() not in PROTECTED:
                                attributes.append({"value": i.oRecordData[k], "label": k})

                        else:
                            if i.oRecordData['key'] != u[0].oRecordData['key']:
                                if k.lower()[:2] == 'in':
                                    lines.append({'type': 'in', 'title': k[3:],
                                                  'to': i.oRecordData['key'],
                                                  'from': u[0].oRecordData['key']})
                                else:
                                    lines.append({'type': 'out', 'title': k[4:],
                                                  'from': i.oRecordData['key'],
                                                  'to': u[0].oRecordData['key']})


                    nodes.append(
                        self.format_node(key=key, title=title, class_name=class_name,
                        icon=icon, attributes=attributes, status=status))


                r = {"data": {'nodes': nodes, 'lines': lines}, "message": "%d activities found" % (len(nodes)-1)}
            else:
                r = {"data": u, "message": "No activity found"}

        else:
            r = {"data": None, "message": "No user named {userName} found".format(
                userName=self.get_user(userName=userName))}
        return r

    def create_user(self, form):
        """
        If a user does not exist, encrypt the password for storage and create the user

        :param form:
        :return:
        """
        if not self.get_user(userName=form['userName'], email=form['email']):
            passWord = self.encrypt_password(form['passWord'])
            if "icon" in form.keys():
                icon = form['icon']
            else:
                icon = self.ICON_USER

            userNode = self.create_node(
                class_name="User",
                passWord=passWord,
                userName=form['userName'],
                email=form['email'],
                createDate=get_datetime(),
                icon=icon,
                confirmed="False"
            )
            if userNode:
                self.confirm_user_email(userName=form['userName'], email=form['email'])
                return {
                    "message": "%s, confirm the registration process by using the link sent to %s" % (
                        form['userName'], form['email']),
                    "data": userNode
                }

    def delete_user(self, request):
        u = self.get_user(userName=request.form.to_dict()['userName'])
        if u:
            r = self.delete_node(class_name="User", key=int(u[0].oRecordData['key']))
            return {'data': r, 'message': "{userName} deleted".format(userName=request.form.to_dict()['userName'])}
        else:
            return {'data': None, 'message': "{userName} not found".format(userName=request.form.to_dict()['userName'])}

    def encrypt_password(self, plaintext_password):
        """
        Hash a plaintext string using PBKDF2. This is good enough according
        to the NIST (National Institute of Standards and Technology).

        :param plaintext_password: Password in plain text
        :type plaintext_password: str
        :return: str
        """
        if plaintext_password:
            return generate_password_hash(plaintext_password)

        return None

    def auth_user(self, token):
        auth = self.deserialize_token(token)
        if auth == SIGNATURE_EXPIRED:
            return {
                "status": 204,
                "message": SIGNATURE_EXPIRED
            }
        elif auth == BLACK_LISTED:
            return {
                "status": 204,
                "message": BLACK_LISTED
            }
        elif auth == DB_ERROR:
            return {
                "status": 500,
                "message": DB_ERROR
            }
        else:
            return None

    def deserialize_token(self, token):
        """
        Obtain a user from de-serializing a signed token.

        :param token: Signed token.
        :type token: str
        :return: User instance or None
        """
        private_key = TimedJSONWebSignatureSerializer(SECRET_KEY)
        try:
            if self.check_blacklist(token):
                return BLACK_LISTED
            else:
                decoded_payload = private_key.loads(token)
                return self.get_user(userName=decoded_payload.get('userName'))

        except Exception as e:
            if str(type(e)) == "<class 'itsdangerous.exc.SignatureExpired'>":
                return SIGNATURE_EXPIRED
            elif str(type(e)) == "<class 'pyorient.exceptions.PyOrientSQLParsingException'>":
                return DB_ERROR
            else:
                return None

    def serialize_token(self, userName, expiration=3600):
        """
        Sign and create a token that can be used for things such as resetting
        a password or other tasks that involve a one off token.

        :param expiration: Seconds until it expires, defaults to 1 hour
        :type expiration: int
        :return: JSON
        """
        private_key = SECRET_KEY

        serializer = TimedJSONWebSignatureSerializer(private_key, expiration)
        return serializer.dumps({'userName': userName}).decode('utf-8')

    def confirm(self, **kwargs):
        """
        Use the token sent from the confirm_user_email process to confirm the user
        If the user name is confirmed,
        1) Blacklist the token
        2) Update the user's confirmed statys
        3) Sign the user in through the email link with a new token

        :param kwargs:
        :return:
        """

        userName = self.deserialize_token(token=kwargs['token'])
        if userName not in [DB_ERROR, BLACK_LISTED, None, SIGNATURE_EXPIRED]:
            # Blacklist the token
            blackListNode = self.create_node(
                class_name="Blacklist",
                createtDate=get_datetime(),
                token=kwargs['token'],
                user=userName[0].oRecordData['userName'],
                session='Email confirmation',
                icon=self.ICON_BLACKLIST
            )
            self.create_edge(edgeType="ConfirmedEmail", fromNode=blackListNode['data']['key'], fromClass="Blacklist",
                             toNode=userName[0].oRecordData['key'], toClass="User")

            # Update user data with confirmed
            self.update(class_name="User", var="confirmed", val=True, key=userName[0].oRecordData['key'])

            # Log user in with a new token
            token = self.serialize_token(userName[0].oRecordData['userName'])
            session = self.create_session({"userName": userName[0].oRecordData['userName']}, 'Email', token)
            self.create_edge(
                fromNode=userName[0].oRecordData['key'], fromClass="User",
                toNode=session['data']['key'], toClass="Session",
                edgeType="UserSession")

            return {
                "status": 200,
                "token": token,
                "session": session,
                "activityGraph": self.get_activity(userName=userName[0].oRecordData['userName']),
                "message": "User %s confirmed email %s and logged in" % (
                    userName[0].oRecordData['userName'],
                    userName[0].oRecordData['email'])
                    }

        elif userName == None:
            return {
                "status": 204,
                "token": None,
                "message": "User not found"
            }
        else:
            return {
                "status": 204,
                "token": None,
                "message": userName
            }

    def confirm_user_email(self, **kwargs):
        """
        Expects a userName and email to which it will send a timed token in a link to the HOST_IP
        The email will come from the Configured EMAIL and the link will trigger an authentication process contained in
        the confirm function where...
        The token will be blacklisted and then the user will be updated with a confirmed = True
        :param kwargs:
        :return:
        """
        confirmToken = self.serialize_token(kwargs['userName'])
        confirmLink = "%s/users/confirm/%s" % (HTTPS, confirmToken)
        # Create a standard text format email
        tMessage = '''
        Hello %s,\n
        This email address (%s) was used to register access to the SAP open net graph service.
        Please use the link below to activate your account or use the token when you first log in.\n
        \tLink: %s \n
        \tToken: %s\n\n
        If you have any questions, feel free to reply back with them.\n\n
        Sincerely,\n
        Your case worker app team
        ''' % (kwargs['userName'], kwargs['email'], confirmLink, confirmToken)
        # Create an HTML format email
        hMessage = '''
        <html>
          <head></head>
          <body>
            <p>Hello %s,<br>
               This email address (%s) was used to register access to the SAP open net graph service. Please use the 
            link below to activate your account or use the token when you first log in.<br>
            <br>Link: 
            <a href="%s">User Activation email link</a>
            <br>Token:
            %s
            <br><br>
            If you have any questions, feel free to reply back with them.
            <br><br>
            Sincerely,
            <br>
            Your case worker app team
            </p>
          </body>
        </html>
        ''' % (kwargs['userName'], kwargs['email'], confirmLink, confirmToken)
        #TODO map link to the environment variables create a link between the user and the token to look up

        # Send the mail
        if send_mail(Recipient=kwargs['email'], tMessage=tMessage, hMessage=hMessage, Subject="Confirmation email"):
            return {
                "message": "email sent",
                "status": 200,
                "data": {
                    "confirmToken": confirmToken,
                    "confirmLink": confirmLink
                }
            }
        else:
            return {
                "message": "error",
                "status": 500}







