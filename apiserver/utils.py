import time, string, random, socket, pyorient
import click, smtplib, ssl, json, os
from datetime import datetime
from dateutil.parser import parse
from werkzeug.utils import secure_filename
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apiserver.config import HOST_IP, SECRET_KEY, MAIL_PASSWORD,\
    MAIL_USERNAME, COPILOT_URL, COPILOT_AUTH, COPILOT_DEV_TOKEN, HTTPS, TWITTER_AUTH

HOST_IP = HOST_IP
HTTPS = HTTPS
SERVER_NAME = 'localhost:8000'
SECRET_KEY = SECRET_KEY
SIGNATURE_EXPIRED = 'Signature expired'
BLACK_LISTED = 'Blacklisted token'
DB_ERROR = "Database error"
PROTECTED = ["password"]
ALLOWED_EXTENSIONS = ['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx']


# mail settingspy
MAIL_SERVER = 'smtp.googlemail.com'
MAIL_PORT = 465
MAIL_USE_TLS = False
MAIL_USE_SSL = True

# gmail authentication
MAIL_USERNAME = MAIL_USERNAME
MAIL_PASSWORD = MAIL_PASSWORD
COPILOT_URL = COPILOT_URL
COPILOT_AUTH = COPILOT_AUTH
COPILOT_DEV_TOKEN = COPILOT_DEV_TOKEN
COPILOT_POST = 'https://api.cai.tools.sap/build/v1/dialog'
ADMINS = [MAIL_USERNAME]

# mail accounts
MAIL_DEFAULT_SENDER = 'from@example.com'

# osint API tokens
TWITTER_AUTH = TWITTER_AUTH

def send_mail(**kwargs):

    message = MIMEMultipart("alternative")
    message["Subject"] = kwargs['Subject']
    message["From"] = MAIL_USERNAME
    message["To"] = kwargs['Recipient']
    message.attach(MIMEText(kwargs['tMessage'], "plain"))
    if kwargs['hMessage']:
        message.attach(MIMEText(kwargs['hMessage'], "html"))
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL(MAIL_SERVER , MAIL_PORT, context=context) as server:
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_USERNAME, kwargs['Recipient'], message.as_string())
    except Exception as e:
        click.echo(str(e))

    return True


def get_datetime():
    """
    Utility function for returning a common standard datetime
    :return:
    """
    return datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')


def get_time_based_id():
    """
    Create a time based ID with a random 16 digit tail in the case of many requests at the same time including micro-second
    :return:
    """
    return int(
        "%s%s" %
        (datetime.now().strftime('%Y%m%d%H%M%S%f'),
         random.randint(1000000000000000, 9999999999999999))
    )


def clean_concat(content):
    """
    Utility function for returning cleaned strings into a normalized format for keys
    :param content:
    :return:
    """
    try:
        content = content.lower().translate(str.maketrans('', '', string.punctuation)).replace(" ", "")
    except Exception as e:
        click.echo('%s %s' % (get_datetime(), str(e)))
        content = None

    return content


def clean(content):
    """
    Utility function for cleaning strings for inserting into sql
    :param content:
    :return:
    """
    try:
        if str(type(content)) == "<class 'datetime.datetime'>":
            return content
        clean_content = change_if_date(content)
        if clean_content:
            return clean_content
        else:
            clean_content = str(content.replace("\\", ""))
            clean_content = str(clean_content.replace("'", "\\'").replace('"', '').replace("\n", " "))
    except Exception as e:
        try:
            clean_content = change_if_number(content)
        except Exception as ee:
            click.echo('%s %s, %s' % (get_datetime(), str(e), str(ee)))
            clean_content = None

    return clean_content


def change_if_number(number_string):

    try:
        if "." in str(number_string):
            return float(number_string)
        else:
            return int(number_string)
    except:
        return None


def change_if_date(date_string, fuzzy=False):
    """
    Return a date if the string is possibly in a date format within the list of date_formats.

    :param date_string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    date_formats = [
        '%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z', '%A, %D %B %Y %H:%M:%S %z', '%A, %D %B %Y %H:%M:%S %Z',
        '%A, %D %B %y %h:%m:%s %z', '%a, %d %b %y %h:%m:%s %z', '%a, %d %b %y %h:%m:%s %Z','%a, %D %b %Y %H:%M:%S %Z',
        '%m/%d/%y, %I:%M %p', '%M/%d/%y, %I:%M %p', '%M/%D/%y, %I:%M %p', '%M/%D/%Y, %I:%M %p', '%m/%d/%Y/%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S','%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y', '%Y-%M-%D', '%Y/%M/%D', '%D-%M-%Y',
        '%D/%M/%Y', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%d-%m-%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S',
        '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M', '%d-%m-%Y %H:%M', '%d/%m/%Y %H:%M'
    ]
    try:
        parse(date_string, fuzzy=fuzzy)
        try:
            for df in date_formats:
                try:
                    dt = datetime.strptime(date_string, df)
                    return dt
                except:
                    pass
        except Exception as e:
            click.echo('%s %s' % (get_datetime(), str(e)))
        return False

    except ValueError:
        return False

def randomString(stringLength=15):

    letters = string.ascii_lowercase + string.hexdigits + string.ascii_uppercase + '!@#$%^&*()_,.>,<'
    return ''.join(random.choice(letters) for i in range(stringLength))


def get_host(user, pswd):
    click.echo('[OrientModel_init__%s] Pausing to allow ODB setup' % (get_datetime()))
    time.sleep(20)
    click.echo('[OrientModel_init__%s] Complete to allow ODB setup' % (get_datetime()))
    possible_hosts = socket.gethostbyname_ex(socket.gethostname())[-1]
    if len(possible_hosts) > 0:
        hostname = possible_hosts[0][:possible_hosts[0].rfind('.')]
        i = 2
        possible_hosts = ["localhost"]
        while i < 6:
            possible_hosts.append("%s.%d" % (hostname, i))
            i += 1
    for h in possible_hosts:

        client = pyorient.OrientDB("%s" % h, 2424)
        try:
            session_id = client.connect(user, pswd)
            click.echo('[OrientModel_init__%s] successfully connected to %s' % (get_datetime(), h))
            return {"client": client, "session_id": session_id}
        except Exception as e:
            click.echo('[OrientModel_init__%s] %s failed\n%s' % (get_datetime(), h, str(e)))

    return {"client": None, "session_id": None}


def get_request_payload(request):
    """
    Some requests come in as form, binary, raw, or other...
    :param request: 
    :return:
    """
    debug = True
    r = request.form.to_dict(flat=True)
    if debug:
        click.echo("\n\n\n\n\n\n\nRequest")
        click.echo(request)
        click.echo("\n\n\n\n\n\n\nRequest.Form")
        click.echo(r)
        click.echo("\n\n\n\n\n\n\nRequest.Args")
        click.echo(request.args)
        click.echo("Received request with %d keys\n%s" % (len(r.keys()), r.keys()))
    if len(r.keys()) == 0:
        # CAI sends POST as raw so need to get data
        click.echo("Attempting JSON loads of request.data")
        click.echo()
        try:
            r = json.loads(request.data)
        except Exception as e:
            click.echo("error %s" % e)
            r = str(request.args.to_dict()).replace("'", '"')
            click.echo(r)
            try:
                r = json.loads(r)
                return r
            except Exception as e:
                click.echo("Second error %s" % str(e))

    if len(r.keys()) == 1:
        click.echo("Attempting misformed JSON\n%s" % str(r))
        newR = str(r).replace('\'', "")
        # Check begining of dictionary and ensure not {'{
        front = False
        chips = 0
        while not front:
            chips+=1
            if newR[0:8] == '{"nodes"':
                front = True
            elif newR[0:9] == '{"groups"':
                front = True
            elif newR[0:8] == '{"lines"':
                front = True
            elif newR[0:11] == '{"userName"':
                front = True
            elif newR[0:2] == '{"':
                front = True
            else:
                newR = newR[1:]
                click.echo("%s... chipping off front" % newR[0:8])
            if chips > 100:
                return None
        # Check for the end of the string if proper for dict
        chips = 0
        while newR[-3:-1] != '"}':
            chips += 1
            if chips > 100:
                return None
            newR = newR[:-1]
            click.echo("%s... chipping off end" % newR[-3:-1])
        r = newR
        # Automated Cleaning with rules implemented in debugging
        current_error = ""
        cleaned = False
        corrections = 0
        while not cleaned:
            try:
                newR = newR.replace("\\", "")
                r = json.loads(newR)
                cleaned = True
            except Exception as e:
                corrections+=1
                # If the error repeated it is something else than the first correction attempt
                e = str(e)
                if e == current_error:
                    # Error string end with (char nnnn). Below finds the ( ) and uses char length to trim. Then int it and -1
                    error_index = int(e[e.find("(") + 6:e.find("}")]) - 1
                    if newR[error_index] == '"':
                        # Use the method of replacement finding <a tags for " "
                        error_index_end = newR[error_index + 1:].find('"') + error_index + 2
                        cleaned_part = newR[error_index:newR[error_index + 1:].find('"') + error_index + 2].replace('"', "")
                        newR = newR[0:error_index] + cleaned_part + newR[error_index_end:]
                else:
                    if "Extra data" in e:
                        newR = newR[:-1]
                    else:
                        # Try to change it based on the href tags
                        newR = newR.replace(
                            newR[newR.find("<a"):(newR.find("<a") + newR[newR.find("<a") + 1:].find("/a>") + 4)],
                            "")
                current_error = e
        click.echo("Completed with automated formatting after %d corrections to make the JSON fit\n%s" % (corrections, r))

    return r


def format_graph(g):

    newDict = {'nodes': [], 'lines': g['lines'], 'groups': [{"key": "NoGroup", "title": "NoGroup"}]}
    for n in g['nodes']:
        newNode = {}
        if "key" in n.keys():
            newNode['key'] = n['key']
        if "title" in n.keys():
            newNode['title'] = n['title']
        if "status" in n.keys():
            newNode['status'] = n['status']
        if "icon" in n.keys():
            newNode['icon'] = n['icon']
        if "group" in n.keys():
            newNode['group'] = n['group']
        else:
            newNode['group'] = "NoGroup"
        if "attributes" in n.keys():
            for a in n['attributes']:
                if a['label'] == 'className':
                    newNode['class_name'] = a['value']
                else:
                    newNode[str(a['label']).replace(" ", "_")] = a['value']
        newDict['nodes'].append(newNode)
    return newDict


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def check_for_file(request, server):
    """
    Full check of a file and all the situations that can arise
    Returns no data if the file is no accepted otherwise saves the file and returns the secure name
    :param request:
    :return:
    """

    if "file" not in request.files:
        keys = ""
        for k in request.files.keys():
            keys+=k + ","

        if "file" not in request.files:
            keys = ""
            for k in request.files.keys():
                keys += k + ","

        return {
            "status": 200,
            "message": "No file parts found. Ensure 'file' is within the keys of the payload sent. Found: %s" % keys,
            "data": None
        }

    else:
        file = request.files['file']
        if file.filename == '':
            return {
                "status": 200,
                "message": "No filename found for the selection.",
                "data": None
            }
        else:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(server.datapath, filename))
                return {
                    "status": 200,
                    "data": filename,
                }
            else:
                return {
                    "status": 200,
                    "message": "File extension on %s not allowed" % file.filename,
                    "data": None,
                }

