import imaplib
import email
from bs4 import BeautifulSoup
import csv
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import selenium.common.exceptions as scroll_errors
import os
import time
from datetime import datetime

webdriver_path = os.path.join(os.getcwd(), 'chromedriver.exe')
chrome_options = Options()
chrome_options.add_argument("--headless")
driver = webdriver.Chrome(executable_path=webdriver_path, chrome_options=chrome_options)
last_height = driver.execute_script("return document.body.scrollHeight")
"""

"""
source_hunchly = "Hunchly"
source_alien = "AlienVault"
hunch_url = "https://automatingosint.us10.list-manage.com/track/click?u="
hunch_url_2 = "&id="
hunch_url_3 = ""
hunch_click = "click?u"
hunch_click2 = "ck?u"
hunch_id = ";id"
hunch_id_2 = "19&e"
hunch_id_3 = "&e"
hunch_id_4 = "amp;id"
hunch_id_5 = "mp;id"
hunch_id_6 = "3&amp;id"
hunch_id_7 = "&amp;id"
hunch_id_8 = "p;id"
hunch_id_9 = "233&amp;id"
hunch_id_10 = "33&amp;id"
alien_url = "https://otx.alienvault.com/pulse/"
imap_ssl_host = 'imap.gmail.com'
imap_ssl_port = 993
username = "opennetgraphservice"
password = "xfsmqraszmvdvhdb"
server = imaplib.IMAP4_SSL(imap_ssl_host, imap_ssl_port)

chrome_options = Options()
chrome_options.add_argument("--headless")
driver = webdriver.Chrome(executable_path=webdriver_path, chrome_options=chrome_options)
email_payload = []


def format_date(ind):
    """
    Change a date based on the indicator row which has fixed positions for Month Day Year and PM/AM
    :param ind:
    :return:
    """
    try:
        f_date = datetime.strptime('%s %s %s %s %s' % (ind[2], ind[3].replace(",", ""), ind[4].replace(",", ""), ind[5],
                                                       ind[6]), '%b %d %Y %I:%M:%S %p')
    except:
        f_date = datetime.now()
    return f_date


def get_indicators(indicators_raw):
    """
    Change a raw web element into an indicator object which can be put into the database using the fixed positions of
    attributes when transformed into a list
    :param indicators_raw:
    :return:
    """
    try:
        indicators = [{
        "type": ind[0],
        "indicator": ind[1],
        "date": format_date(ind),
        "related pulses": ind[7]
    } for ind in indicators_raw]
    except:
        indicators = []
    return indicators


server.login(username, password)
# Load all the messages in the inbox into the server
server.select()
# Get all the unread messages. Messages that are extracted with "fetch" are then automatically read
status, message_ids = server.search(None, 'UNSEEN')
if status == "OK":
    # Setup the object for passing for url processing
    url_process = {}
    # Cycle through all the messages collected in the server
    for msg_id in message_ids[0].split():
        _, raw = server.fetch(msg_id, '(RFC822)')
        # Change the message into a bytes format for processing
        msg = email.message_from_bytes(raw[0][1])
        # Create a record in the url_process object containing basic information
        url_process[msg_id] = {
            "from": msg.get("from"),
            "date": msg.get("date"),
            "subject": msg.get("subject")
        }
        # Dlag for exiting the scrape to prevent unnecessary looping. Set to False when match made or parts complete
        scrape = True
        while scrape:
            if msg.is_multipart():
                multipart_payload = msg.get_payload()
                for sub_message in multipart_payload:
                    # The actual text/HTML email contents, or attachment data
                    soup = BeautifulSoup(sub_message.get_payload(), 'html.parser')
                    links = soup.find_all("a")
                    if len(links) > 0:
                        try:
                            for link in links:
                                if "Download Report for" in link.decode_contents():
                                    # The links contain ASCII encodings (3D) which need to be removed.
                                    # Use the bs4 link attributes to find the hunchly report URL parts
                                    # There are different issues for the URL build but should result in a click and id
                                    url_process[msg_id]["source"] = "Hunchly"
                                    if hunch_click in list(link.attrs.keys()):
                                        url_click = link.attrs[hunch_click].replace("3D", "")
                                    elif hunch_click2 in list(link.attrs.keys()):
                                        url_click = link.attrs[hunch_click2].replace("3D", "")
                                    else:
                                        url_click = ""
                                    # Set up the ID
                                    if hunch_id in list(link.attrs.keys()):
                                        url_id = hunch_url_2 + link.attrs[hunch_id].replace("3D", "")
                                    elif hunch_id_2 in list(link.attrs.keys()):
                                        url_click = url_click[0:-1] + hunch_id_2 + "="
                                        url_id = link.attrs[hunch_id_2].replace("3D", "")
                                    elif hunch_id_3 in list(link.attrs.keys()):
                                        url_id = link.attrs[hunch_id_3].replace("3D", "")
                                    elif hunch_id_4 in list(link.attrs.keys()):
                                        url_click = url_click[0:-1]
                                        url_id = "id=" + link.attrs[hunch_id_4].replace("3D", "")
                                    elif hunch_id_5 in list(link.attrs.keys()):
                                        url_click = url_click[0:-2]
                                        url_id = "id=" + link.attrs[hunch_id_5].replace("3D", "")
                                    elif hunch_id_6 in list(link.attrs.keys()):
                                        url_click = url_click[0:-1]
                                        url_id = "3&id=" + link.attrs[hunch_id_6].replace("3D", "")
                                    elif hunch_id_7 in list(link.attrs.keys()):
                                        url_click = url_click[0:-1]
                                        url_id = "&id=" + link.attrs[hunch_id_7].replace("3D", "")
                                    elif hunch_id_8 in list(link.attrs.keys()):
                                        url_click = url_click[0:-3]
                                        url_id = "&id=" + link.attrs[hunch_id_8].replace("3D", "")
                                    elif hunch_id_9 in list(link.attrs.keys()):
                                        url_click = url_click[0:-1]
                                        url_id = "233&id=" + link.attrs[hunch_id_9].replace("3D", "")
                                    elif hunch_id_10 in list(link.attrs.keys()):
                                        url_click = url_click[0:-1]
                                        url_id = "33&id=" + link.attrs[hunch_id_10].replace("3D", "")
                                    else:
                                        url_id = ""
                                    url_process[msg_id]["url"] = hunch_url + url_click + url_id
                                    scrape = False
                                if "https://otx.alienvault.com/puls=" in link.decode_contents():
                                    # The link string cuts the e and ends in with an /, i.e:
                                    # 'https://otx.alienvault.com/puls=\r\ne/5ec8375aca8f622daf866b49/'
                                    url_process[msg_id]["source"] = "AlienVault"
                                    url_process[msg_id]["url"] = alien_url + link.string[link.string.find("e/")+2:-1]
                                    scrape = False
                        except KeyError as e:
                            print(e)
                        except Exception as e:
                            print(e)
                # If the scrape flag is still true then it didn't meet the requirements for processing so pop it
                if scrape:
                    url_process.pop(msg_id)
                    scrape = False
            else:  # Not a multipart message, payload is simple string
                scrape = False

print(url_process)
for i in url_process:
    if url_process[i]['source'] == source_hunchly:
        with requests.Session() as s:
            download = s.get(url_process[i]['url'])
            if download.status_code == 200:
                decoded_content = download.content.decode('utf-8')
                cr = csv.reader(decoded_content.splitlines(), delimiter=',')
                my_list = list(cr)
                for row in my_list:
                    print(row)
    elif url_process[i]['source'] == source_alien:
        driver.get(url_process[i]['url'])
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        # Get the main details for the page
        title = driver.find_element_by_class_name('info').text
        details = driver.find_element_by_class_name('pulse-details')
        # Get the related indicators and then create a list for each row that can be normalized into an object
        #indicators_raw = [indicator.text.split(" ") for indicator in driver.find_elements_by_class_name('show-row')]
        indicators = get_indicators(
            [indicator.text.split(" ") for indicator in driver.find_elements_by_class_name('show-row')])
        navigations = driver.find_elements_by_class_name('page-change')
        # There are many navigation buttons so take only the one that says next and keep iterating while it exists
        next = [nxt for nxt in navigations if nxt.text == 'NEXT']
        while len(next) > 0:
            nxt_button = next[0]
            nxt_button.click()
            time.sleep(2)
            try:
                indicators_loop = get_indicators(
                    [indicator.text.split(" ") for indicator in driver.find_elements_by_class_name('show-row')])
            except:
                time.sleep(1)
                try:
                    indicators_loop = get_indicators(
                        [indicator.text.split(" ") for indicator in driver.find_elements_by_class_name('show-row')])
                except:
                    indicators_loop = []
            indicators += indicators_loop
            navigations = driver.find_elements_by_class_name('page-change')
            next = [nxt for nxt in navigations if nxt.text == 'NEXT']

        email_payload.append({"title": title, "details": details, "indicators": indicators})

print(email_payload)
