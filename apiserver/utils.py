import time, string, random, socket, pyorient
import click, smtplib, ssl, json
from datetime import datetime
from dateutil.parser import parse
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

    r = request.form.to_dict(flat=True)
    if len(r.keys()) == 0:
        # CAI sends POST as raw so need to get data
        r = json.loads(request.data)

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
