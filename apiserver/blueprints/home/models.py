import click, os
import requests, json
import pandas as pd
from apiserver.utils import get_datetime, clean, change_if_date, TWITTER_AUTH, format_graph
from apiserver.blueprints.home.models import ODB
from requests_oauthlib import OAuth1
import urllib3
urllib3.disable_warnings()


class OSINT(ODB):

    def __init__(self, db_name="OSINT"):
        ODB.__init__(self, db_name)
        self.db_name = db_name
        self.ICON_PERSON = "sap-icon://person-placeholder"
        self.ICON_OBJECT = "sap-icon://add-product"
        self.ICON_ORGANIZATION = "sap-icon://manager"
        self.ICON_LOCATION = "sap-icon://map"
        self.ICON_EVENT = "sap-icon://date-time"
        self.ICON_CASE = "sap-icon://folder"
        self.ICON_STATUSES = ["Warning", "Error", "Success"]
        self.datapath = os.path.join(os.path.join(os.getcwd(), 'data'))
        self.basebook = None
        self.models = {
            "Person": {
                "key": "integer",
                "DateOfBirth": "datetime",
                "PlaceOfBirth": "string",
                "FirstName": "string",
                "LastName": "string",
                "MidName": "string",
                "icon": "string",
                "Gender": "string",
                "class": "V"
            },
            "Object": {
                "key": "integer",
                "class": "V",
                "Category": "string",
                "Description": "string",
                "Tags": "string"
            },
            "Organization": {
                "key": "integer",
                "class": "V",
                "Category": "string",
                "Description": "string",
                "Tags": "string",
                "Members": "integer",
                "Founded": "datetime",
                "Name": "string",
                "OtherNames": "string",
                "UCDP_id": "string",
                "ACLED_id": "string",
                "Source": "string"
            },
            "Profile": {
                "key": "integer",
                "class": "V",
                "Category": "string",
                "Description": "string",
                "Tags": "string",
                "Friends": "integer",
                "Followers": "integer",
                "Name": "string",
                "OtherNames": "string",
                "Posts": "integer",
                "DateCreated": "datetime",
                "url": "string",
                "Source": "string"
            },
            "Post": {
                "key": "integer",
                "class": "V",
                "Category": "string",
                "Description": "string",
                "Tags": "string",
                "DateCreated": "datetime",
                "RePosts": "integer",
                "Likes": "integer",
                "Author": "string",
                "url": "string",
                "Source": "string"
            },
            "Location": {
                "key": "integer",
                "class": "V",
                "Category": "string",
                "Description": "string",
                "Tags": "string",
                "Latitude": "float",
                "Longitude": "float",
                "city": "string",
                "pop": "integer",
                "country": "string",
                "iso3": "string",
                "province": "string"
            },
            "Event": {
                "key": "integer",
                "class": "V",
                "Category": "string",
                "Description": "string",
                "Tags": "string",
                "StartDate": "datetime",
                "EndDate": "datetime"
            },
            "Case": {
                "key": "string",
                "class": "V",
                "Name": "string",
                "Owner": "string",
                "Classification": "string"
            }
        }
        # In memory DB used for creating simulation data in the format for network graph UX rendering
        self.DB = {'nodes': {},
                   'lines': [],
                   'groups': [],
                   'node_keys': [],
                   'group_index': [],
                   'ucdp_org': {},
                   'ucdp_obj': {}}
        click.echo('[%s_SimServer_init] Complete' % (get_datetime()))
        self.ACLED_Base_URL = "https://api.acleddata.com/acled/read?terms=accept"
        self.UCDP_Page_Size = 50
        self.UCDP_Base_URL = "https://ucdpapi.pcr.uu.se/api/gedevents/19.1?pagesize=%s" % self.UCDP_Page_Size
        self.UCDP_Country_URL = "%s&Country=" % self.UCDP_Base_URL
        self.UCDP_Time_URL = "%s&StartDate=" % self.UCDP_Base_URL
        self.TWITTER_AUTH = TWITTER_AUTH
        self.base_twitter_url = "https://api.twitter.com/1.1/"
        self.default_number_of_tweets = 200


    @staticmethod
    def ucdp_conflict_type(row):

        if row['type_of_violence'] == str(1):
            return "State-based Conflict"
        elif row['type_of_violence'] == str(2):
            return "Non-state Conflict"
        else:
            return "One-sided Conflict"

    def check_base_book(self):
        """
        Check if the Organizations have been set by UCDP
        :return:
        """
        click.echo('[%s_SimServer_init] Checking base OSINT settings' % (get_datetime()))
        r = self.client.command('select * from Organization where UCDP_id != "" limit 50')
        if len(r) == 0:
            if not self.basebook:
                click.echo('[%s_SimServer_init] Initializing basebook UCDP codes' % (get_datetime()))
                self.basebook = pd.ExcelFile(os.path.join(self.datapath, 'Base_Book.xlsx'))
                UCDP = self.basebook.parse('UCDP')
                a = c = 0
                for index, row in UCDP.iterrows():
                    if row['table'] == 'actor':
                        self.create_node(
                            title="Organization %s" % row['name'],
                            class_name="Organization",
                            UCDP_id=row['new_id'],
                            UCDP_old=row['old_id'],
                            Name=row['name'],
                            Source="UCDP"
                        )
                        a+=1
                    else:
                        conflict_type = self.ucdp_conflict_type(row)
                        self.create_node(
                            title="%s %s" % (conflict_type, row['name']),
                            class_name="Object",
                            Category="Conflict",
                            UCDP_id=row['new_id'],
                            UCDP_old=row['old_id'],
                            Name=row['name'],
                            Source="UCDP"
                        )
                        c+=1

                click.echo('[%s_SimServer_init] Complete with UCDP setup including %s actors and %s conflicts'
                           % (get_datetime(), a, c))

    def fill_db(self):

        r = self.client.command('select key, UCDP_id, Name from Organization where UCDP_id != "" ')
        for i in r:
            self.DB['ucdp_org'][i.oRecordData['UCDP_id']] = {
                "Name": i.oRecordData['Name'],
                "key": i.oRecordData['key']
            }

        r = self.client.command('select key, UCDP_id from Object where UCDP_id != "" ')
        for i in r:
            self.DB['ucdp_obj'][i.oRecordData['UCDP_id']] = {
                "Name": i.oRecordData['Name'],
                "key": i.oRecordData['key']
            }
        r = self.client.command('select key, UCDP_id, Category, Description, Sources, StartDate, EndDate, Deaths, Origin, Civilians from Event where UCDP_id != "" ')
        for i in r:
            self.DB['ucdp_obj'][i.oRecordData['UCDP_id']] = {
                "Name": i.oRecordData['Name'],
                "key": i.oRecordData['key']
            }

    def get_acled(self):
        """
        Using the ACLED API transform results into a graph format
        Variable data is a list of dictionary elements as follows:
            1.actor1            11.event_id_cnty        21.latitude
            2.actor2            12.event_id_no_cnty     22.location
            3.admin1            13.event_type           23.longitude
            4.admin2            14.fatalities           24.notes
            5.admin3            15.geo_precision        25.region
            6.assoc_actor_1     16.inter1               26.source
            7.assoc_actor_2     17.inter2               27.source_scale
            8.country           18.interaction          28.sub_event_type
            9.data_id           19.iso                  29.time_precision
            10.event_date       20.iso3                 30.timestamp
                                                        31.year

        :return:
        """
        data = requests.get(self.ACLED_Base_URL).json()['data']
        return data

    def get_ucdp(self):
        """
        Using the UCDP API get the results and for each row extract columns into OSINT DB entities
            1.id                11.dyad_new_id          21.source_office            31.longitude            41.deaths_a
            2.relid             12.dyad_name            22.source_date              32.geom_wkt             42.deaths_b
            3.year              13.side_a_dset_id       23.source_headline          33.priogrid_gid         43.deaths_civilian
            4.active_year       14.side_a_new_id        24.source_original          34.country              44.deaths_unknown
            5.code_status       15.side_a               25.where_prec               35.country_id           45:best
            6.type_of_violence  16.side_b_dset_id       26.where_coordinates        36.region               46:high
            7.conflict_dset_id  17.side_b_new_id        27.where_description        37.event_clarity        47:low
            8.conflict_new_id   18.side_b               28.adm_1                    38.date_prec            48.gwnoa
            9.conflict_name     19.number_of_sources    29.adm_2                    39.date_start           49.gwnob
            10.dyad_dset_id     20.source_article       30.latitude                 40.date_end

        :return:
        """
        results = requests.get(self.UCDP_Base_URL).json()
        data = results['Result']
        graph_build = {"nodes": [], "lines": [], "groups": []}
        geo = []
        for row in data:
            # Get the sources who reported the event
            source_keys = []
            sources = list(set(row['source_office'].split(";")))
            for s in sources:
                if s in self.DB['ucdp_org'].keys():
                    source_keys.append(self.DB['ucdp_org']['key'])
                else:
                    source_node = self.create_node(
                        class_name="Organization",
                        Category="Information Source",
                        Name=s,
                        title="%s information source" % s,
                        icon=self.ICON_ORGANIZATION
                    )
                    graph_build['nodes'].append(source_node['data'])
                    source_keys.append(source_node['data']['key'])
            # Get the Event
            StartDate = change_if_date(row['date_start'])
            EndDate = change_if_date(row['date_end'])
            event_node = self.create_node(
                class_name="Event",
                Category=self.ucdp_conflict_type(row),
                UCDP_id=row['id'],
                Description=("Headline: %s Article: %s" % (
                    row['source_headline'],
                    row['source_article'])).replace("'", ""),
                Sources=len(sources),
                StartDate=StartDate,
                EndDate=EndDate,
                Deaths=row['best'],
                Origin=clean(row['source_original']),
                Civilans=row['deaths_civilians']
            )
            graph_build['nodes'].append(event_node['data'])
            # Wire up the Sources as reporting on the Event
            for k in source_keys:
                self.create_edge(
                    fromClass="Organization",
                    toClass="Event",
                    edgeType="ReportedOn",
                    fromNode=k,
                    toNode=event_node['data']['key']
                )
                graph_build['lines'].append({"from": k, "to": event_node['data']['key'], "title": "GeoSpatial"})
            # Get the 2 conflicting organizations
            if row['side_a_new_id'] in self.DB.keys():
                side_a_key = self.DB[row['side_a_new_id']]['key']
            else:
                side_a_node = self.create_node(
                    class_name="Organization",
                    title="Organization %s" % row['side_a'],
                    UCDP_id=row['side_a_new_id'],
                    UCDP_old=row['side_a_dset_id'],
                    Name=row['side_a']
                )
                graph_build['nodes'].append(side_a_node['data'])
                side_a_key = side_a_node['data']['key']
            if row['side_b_new_id'] in self.DB.keys():
                side_b_key = self.DB[row['side_b_new_id']]['key']
            else:
                side_b_node = self.create_node(
                    class_name="Organization",
                    title="Organization %s" % row['side_b'],
                    UCDP_id=row['side_b_new_id'],
                    UCDP_old=row['side_b_dset_id'],
                    Name=row['side_b']
                )
                graph_build['nodes'].append(side_b_node['data'])
                side_b_key = side_b_node['data']['key']
            # Wire up the Organizations with the Event
            self.create_edge(
                fromClass="Organization",
                toClass="Event",
                fromNode=side_a_key,
                toNode=event_node['data']['key'],
                edgeType="Involved"
            )
            graph_build['lines'].append({"from": side_a_key, "to": event_node['data']['key'], "title": "Event"})
            self.create_edge(
                fromClass="Organization",
                toClass="Event",
                fromNode=side_b_key,
                toNode=event_node['data']['key'],
                edgeType="Involved"
            )
            graph_build['lines'].append({"from": side_b_key, "to": event_node['data']['key'], "title": "Event"})
            # Get the Location
            if row['adm_1'] != "":
                city = row['adm_1']
            elif row['adm_2'] != "":
                city = row['adm_2']
            elif row['where_coordinates'] != "":
                city = row['where_coordinates']
            else:
                city = "Unknown"
            location_node = self.create_node(
                class_name="Location",
                Category="Conflict site",
                Description="%s %s %s %s" % (row['adm_1'], row['adm_2'], row['country'], row['region']),
                Latitude=row['latitude'],
                Longitude=row['longitude'],
                city=city,
                country=row['country']
            )
            geo.append({
                "pos": "%f;%f;0" % (row['longitude'], row['latitude']),
                "tooltip": city,
                "type": "Error"
            })
            graph_build['nodes'].append(location_node['data'])
            location = location_node['data']['key']
            # Wire up the Event to Location (OccurredAt)
            self.create_edge(
                fromClass="Event",
                fromNode=event_node['data']['key'],
                toClass="Location",
                toNode=location,
                edgeType="OccurredAt"
            )
            graph_build['lines'].append({"from": event_node['data']['key'], "to": location, "title": "OccurredAt"})
            # Wire up the Organizations to the Location (ReportedAt)
            self.create_edge(
                fromClass="Organization",
                fromNode=side_a_key,
                toClass="Location",
                toNode=location,
                edgeType="OccurredAt"
            )
            graph_build['lines'].append({"from": side_a_key, "to": location, "title": "OccurredAt"})
            self.create_edge(
                fromClass="Organization",
                fromNode=side_b_key,
                toClass="Location",
                toNode=location,
                edgeType="OccurredAt"
            )
            graph_build['lines'].append({"from": side_b_key, "to": location, "title": "OccurredAt"})

        message = {
            "graph": self.quality_check(graph_build),
            "raw": data,
            "geo": {
                "Spots": {
                    "items": geo
                }
            }
        }
        return message

    def create_profile(self):

        return

    def fill_cache(self):
        """
        Fill the self.DB with existing entities to prevent unnecessary calls to the DB. Select * from OSINT
        :return:
        """

        return

    def get_twitter(self, **kwargs):
        """
        Optional uses of the Twitter API as configured in the settings. Process the tweets into a graph and then a thread
        to process them in the back end. Query for existing keys to Nodes
        1) statuses/user_timeline: get all the tweets by username
        2)
        :param kwargs:
        :return:
        """

        if "max_id" not in kwargs.keys():
            kwargs['max_id'] = None
        if "number_of_tweets" not in kwargs.keys():
            kwargs['number_of_tweets'] = self.default_number_of_tweets
        if "request" not in kwargs.keys():
            kwargs['request'] = 0

        client_key = self.TWITTER_AUTH['client_key']
        client_secret = self.TWITTER_AUTH['client_secret']
        token = self.TWITTER_AUTH['token']
        token_secret = self.TWITTER_AUTH['token_secret']
        oauth  = OAuth1(client_key, client_secret, token, token_secret)

        if "username" in kwargs.keys():
            api_url  = "%s/statuses/user_timeline.json?" % self.base_twitter_url
            api_url += "screen_name=%s&" % kwargs['username']
            api_url += "count=%d" % kwargs['number_of_tweets']

            if kwargs['max_id'] is not None:
                api_url += "&max_id=%d" % kwargs['max_id']
            # send request to Twitter
            response = requests.get(api_url, auth=oauth, verify=False) # if ssl error use verify=False
            kwargs['request']+=1
            tweets = self.responseHandler(response, kwargs['username'])
            return tweets


    def processTweets(self, **kwargs):

        return

    def responseHandler(self, response, searchterm):

        if response.status_code == 401:
            return "[!] <401> User %s protects tweets" % searchterm

        if response.status_code == 200:
            tweets = json.loads(response.text)
            return tweets

        if response.status_code == 429:
            return "[!] <429> Too many requests to Twitter. Sleep for 15 minutes started at: %s" % get_datetime()

        if response.status_code == 503:
            return "[!] <503> The Twitter servers are up, but overloaded with requests. Try again later: %s" % get_datetime()

        else:
            return None
