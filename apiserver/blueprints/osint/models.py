import click, os
import requests, json, random
import pandas as pd
from apiserver.utils import get_datetime, clean, change_if_date, TWITTER_AUTH, get_time_based_id, format_graph
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
        self.ICON_INFO_SOURCE = "sap-icon://newspaper"
        self.ICON_LOCATION = "sap-icon://map"
        self.ICON_EVENT = "sap-icon://date-time"
        self.ICON_CONFLICT = "sap-icon://alert"
        self.ICON_CASE = "sap-icon://folder"
        self.ICON_STATUSES = ["Warning", "Error", "Success"]
        self.ICON_TWEET = "sap-icon://jam"
        self.ICON_TWITTER_USER = "sap-icon://customer-view"
        self.ICON_HASHTAG = "sap-icon://number-sign"
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
                "Tags": "string",
                "icon": "string",
                "title": "string",
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
                "Source": "string",
                "icon": "string",
                "title": "string",
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
                "Source": "string",
                "icon": "string",
                "title": "string",
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
                "Source": "string",
                "icon": "string",
                "title": "string",
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
                "province": "string",
                "icon": "string",
                "title": "string",
            },
            "Event": {
                "key": "integer",
                "class": "V",
                "Category": "string",
                "Description": "string",
                "Tags": "string",
                "StartDate": "datetime",
                "EndDate": "datetime",
                "icon": "string",
                "title": "string",
                "Sources": "string",
                "Deaths": "string",
                "Civilians": "string",
                "Origin": "string",
                "UCDP_id": "string",
                "Source": "string"
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
                   'ucdp_sources': {},
                   'ucdp_events': {}
                   }
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
        click.echo('[%s_OSINTserver_check_base_book] Checking base OSINT settings' % (get_datetime()))
        r = self.client.command('select * from Organization where UCDP_id != "" limit 50')
        if len(r) == 0:
            if not self.basebook:
                click.echo('[%s_OSINTserver_check_base_book] Initializing basebook UCDP codes' % (get_datetime()))
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
                            Source="UCDP",
                            Category="Political",
                            icon=self.ICON_ORGANIZATION
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
                            Source="UCDP",
                            icon=self.ICON_CONFLICT
                        )
                        c+=1

                click.echo('[%s_OSINTserver_check_base_book] Complete with UCDP setup including %s actors and %s conflicts'
                           % (get_datetime(), a, c))

    def fill_db(self):

        # Fill UCDP Organisations
        r = self.client.command(
            'select key, UCDP_id, title, Name, Source, icon from Organization where Category = "Politcal" '
        )
        for i in r:
            self.DB['ucdp_org'][i.oRecordData['UCDP_id']] = {
                "title": i.oRecordData['title'],
                "key": i.oRecordData['key'],
                "class_name": "Organization",
                "group": "UCDP",
                "icon": i.oRecordData['icon'],
                "attributes": [
                    {"label": "Category", "value": i.oRecordData['Category']},
                    {"label": "UCDP_id", "value": i.oRecordData['UCDP_id']},
                    {"label": "Source", "value": i.oRecordData['Source']},
                    {"label": "Name", "value": i.oRecordData['Name']}
                ]
            }
        click.echo('[%s_OSINTserver_fill_db]  Complete with %d UCDP organizations'
                   % (get_datetime(), len(self.DB['ucdp_org'])))
        # Fill UCDP Information sources
        r = self.client.command(
            'select key, UCDP_id, title, Name, Source, icon from Organization where Category = "Information Source" '
        )
        for i in r:
            self.DB['ucdp_sources'][i.oRecordData['Name']] = {
                "title": i.oRecordData['title'],
                "key": i.oRecordData['key'],
                "group": "UCDP",
                "class_name": "Organization",
                "icon": i.oRecordData['icon'],
                "attributes": [
                    {"label": "Category", "value": "Information Source"},
                    {"label": "Name", "value": i.oRecordData['Name']}
                ]
            }
        click.echo('[%s_OSINTserver_fill_db]  Complete with %d UCDP information sources'
                   % (get_datetime(), len(self.DB['ucdp_org'])))
        # Fill UCDP Events
        r = self.client.command(
            ''' select key, UCDP_id, Category, icon, title, Description, Sources, StartDate, EndDate, Deaths, Origin,
             Civilians, Source from Event where UCDP_id != ""
             ''')
        for i in r:
            self.DB['ucdp_events'][i.oRecordData['UCDP_id']] = {
                "title": i.oRecordData['title'],
                "key": i.oRecordData['key'],
                "class_name": "Event",
                "group": "UCDP",
                "icon": i.oRecordData['icon'],
                "attributes": [
                    {"label": "Category", "value": i.oRecordData['Category']},
                    {"label": "Description", "value": i.oRecordData['Description']},
                    {"label": "Sources", "value": i.oRecordData['Sources']},
                    {"label": "StartDate", "value": i.oRecordData['StartDate']},
                    {"label": "EndDate", "value": i.oRecordData['EndDate']},
                    {"label": "Deaths", "value": i.oRecordData['Deaths']},
                    {"label": "Civilians", "value": i.oRecordData['Civilians']},
                    {"label": "Origin", "value": i.oRecordData['Origin']},
                    {"label": "UCDP_id", "value": i.oRecordData['UCDP_id']},
                    {"label": "Source", "value": i.oRecordData['Source']},
                ]
            }
        click.echo('[%s_OSINTserver_fill_db]  Complete with %d UCDP events'
                   % (get_datetime(), len(self.DB['ucdp_events'])))

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
        graph_build = {"nodes": [], "lines": [], "groups": [{"key": "UCDP", "title": "UCDP"}]}
        geo = []
        for row in data:
            # Get the sources who reported the event
            sources = list(set(row['source_office'].split(";")))
            sources.append(row['source_original'])
            source_keys = []
            for s in sources:
                if s != "":
                    if s in self.DB['ucdp_sources'].keys():
                        source_node = {"data" : self.DB['ucdp_sources'][s]}
                        if self.DB['ucdp_sources'][s] not in graph_build['nodes']:
                            graph_build['nodes'].append(self.DB['ucdp_sources'][s])
                    else:
                        source_node = self.create_node(
                            class_name="Organization",
                            Category="Information Source",
                            Name=s,
                            title="%s information source" % s,
                            icon=self.ICON_INFO_SOURCE,
                            Source="UCDP"
                        )
                        graph_build['nodes'].append(source_node['data'])
                source_keys.append(source_node['data']['key'])
            # Get the Event
            if row['id'] in self.DB['ucdp_events'].keys():
                event_node = {"data" : self.DB['ucdp_events'][row['id']]}
                if event_node['data'] not in graph_build['nodes']:
                    graph_build['nodes'].append(event_node['data'])
            else:
                StartDate = change_if_date(row['date_start'])
                EndDate = change_if_date(row['date_end'])
                Category = self.ucdp_conflict_type(row)
                event_node = self.create_node(
                    class_name="Event",
                    icon=self.ICON_CONFLICT,
                    Category=Category,
                    UCDP_id=row['id'],
                    title="%s %s, %s" % (Category, row['country'], row['source_original']),
                    Description=("Headline: %s Article: %s" % (
                        row['source_headline'],
                        row['source_article'])).replace("'", ""),
                    Sources=len(sources),
                    StartDate=StartDate,
                    EndDate=EndDate,
                    Deaths=row['best'],
                    Origin=clean(row['source_original']),
                    Civilians=row['deaths_civilians'],
                    Source="UCDP"
                )
                graph_build['nodes'].append(event_node['data'])
                self.DB['ucdp_events'][row['id']] = event_node['data']
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
            if row['side_a_new_id'] in self.DB['ucdp_org'].keys():
                side_a_key = self.DB['ucdp_org'][row['side_a_new_id']]['key']
                if self.DB[row['side_a_new_id']] not in graph_build['nodes']:
                    graph_build['nodes'].append(self.DB[row['side_a_new_id']])

            else:
                side_a_node = self.create_node(
                    class_name="Organization",
                    Category="Political",
                    title="Organization %s" % row['side_a'],
                    UCDP_id=row['side_a_new_id'],
                    UCDP_old=row['side_a_dset_id'],
                    Name=row['side_a'],
                    icon=self.ICON_ORGANIZATION,
                    Source="UCDP"
                )
                graph_build['nodes'].append(side_a_node['data'])
                side_a_key = side_a_node['data']['key']
                self.DB['ucdp_org'][row['side_a']] = side_a_node['data']

            if row['side_b_new_id'] in self.DB.keys():
                side_b_key = self.DB[row['side_b_new_id']]['key']
                if self.DB[row['side_b_new_id']] not in graph_build['nodes']:
                    graph_build['nodes'].append(self.DB[row['side_b_new_id']])
            else:
                side_b_node = self.create_node(
                    class_name="Organization",
                    title="Organization %s" % row['side_b'],
                    Category="Political",
                    UCDP_id=row['side_b_new_id'],
                    UCDP_old=row['side_b_dset_id'],
                    Name=row['side_b'],
                    icon=self.ICON_ORGANIZATION,
                    Source="UCDP"
                )
                graph_build['nodes'].append(side_b_node['data'])
                side_b_key = side_b_node['data']['key']
                self.DB['ucdp_org'][row['side_b']] = side_b_node['data']
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
                country=row['country'],
                icon=self.ICON_LOCATION
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

    def run_osint_simulation(self):
        """
        1) Choose from a random social media profile (TODO Make social media profiles from basebook twitter and other accounts)
        2) Create post based on social media profile type (TODO Get standard post types and content) - get tweets and label them
        3) Create re-tweets from profiles that follow the chosen profile
        :return:
        """
        # get social media profiles and their followers

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
        graphs = []
        locationsChecked = False
        message = "Retrieved twitter API: "

        if "username" in kwargs.keys():
            if kwargs['username'] != "":
                api_url  = "%s/statuses/user_timeline.json?" % self.base_twitter_url
                api_url += "screen_name=%s&" % kwargs['username']
                api_url += "count=%d" % kwargs['number_of_tweets']

                if kwargs['max_id'] is not None:
                    api_url += "&max_id=%d" % kwargs['max_id']
                # send request to Twitter
                response = requests.get(api_url, auth=oauth, verify=False) # if ssl error use verify=False
                kwargs['request']+=1
                tweets = self.responseHandler(response, kwargs['username'])
                if response.status_code != 401:
                    tweets = self.processTweets(tweets=tweets)
                    graphs.append(tweets)
                    message+= " %s tweets" % kwargs['username']
                else:
                    message+= " %s protects tweets" % kwargs['username']
                    graphs.append({
                        "nodes": [],
                        "lines": [],
                        "groups": [
                            {"key": 1, "title": "Profiles"},
                            {"key": 2, "title": "Posts"},
                            {"key": 3, "title": "Locations"},
                            {"key": 4, "title": "Hashtags"}
                    ]})

        if "hashtag" in kwargs.keys():
            if kwargs['hashtag'] != "":
                api_url = "%s/search/tweets.json?" % self.base_twitter_url
                api_url += "q=%%23%s&result_type=recent" % kwargs['hashtag']
                if "latitude" in kwargs.keys() and "longitude" in kwargs.keys() and kwargs['latitude'] != "":
                    api_url += "&geocode=%f,%f" % (float(kwargs['latitude']), float(kwargs['longitude']))
                    if "radius" in kwargs:
                        api_url += ",%dkm&count=%s" % (int(kwargs['radius']), kwargs['number_of_tweets'])
                    else:
                        api_url += ",5km&count=%s" % kwargs['number_of_tweets']
                    locationsChecked = True
                response = requests.get(api_url, auth=oauth, verify=False)
                tweets = self.responseHandler(response, kwargs['hashtag'])
                tweets = self.processTweets(tweets=tweets['statuses'])
                graphs.append(tweets)
                message+= " %s resulted in %d records" % (kwargs['hashtag'], len(tweets['graph']['nodes']))

        if "latitude" in kwargs.keys() and "longitude" in kwargs.keys()and not locationsChecked:
            if kwargs['latitude'] != "" and kwargs['longitude'] != "":
                api_url = "https://api.twitter.com/1.1/search/tweets.json?q=&geocode=%f,%f" % (
                    float(kwargs['latitude']), float(kwargs['longitude']))
                if "radius" in kwargs.keys():
                    if kwargs['radius'] != "":
                        api_url += ",%dkm&count=%s" % (int(kwargs['radius']), kwargs['number_of_tweets'])
                    else:
                        api_url += ",5km&count=%s" % kwargs['number_of_tweets']
                response = requests.get(api_url, auth=oauth, verify=False)
                tweets = self.responseHandler(response, "%s, %s" % (kwargs['latitude'], kwargs['longitude']))
                #graphs.append(tweets['statuses'])
                tweets = self.processTweets(tweets=tweets['statuses'])
                graphs.append(tweets)
                message += " %s resulted in %s, %d records" % (kwargs['latitude'], kwargs['latitude'], len(tweets['graph']['nodes']))

        return graphs, message

    def geo_spatial_view(self, **kwargs):
        """
        Create a record for every location->event->Vertex and for every location->Event. If there is a case in the
        request, only get those items related to case. By book-ending the query with the case, there is no risk in
        picking up data not part of the case. TODO Additional check on data to ensure classification does not break rule
            {position: l.latitude, l.longitude, e.startDate
            tooltip:
            DependentData: time?  , v.type, v.category, e.type
        Enables user in a geo view to filter on type, category and time windows (if position[2] in between time range or
        other filter

        :return:
        """
        if "caseKey" in kwargs.keys():
            sql = '''
            MATCH
            {class:Case, where: (key = '%s')}.out("Attached")
            {class:Location, as:l}.bothE(){as:l2e}.bothV()
            {class:Event, as:e}.bothE(){as:e2v}.bothV()
            {class:V, as:v}.in("Attached"){class:Case, where: (key = '%s')}
            RETURN 
            l.key, l.Longitude, l.Latitude, l.title, l.Category, l.Type, l.icon,  
            l2e.@class as EventLocation, 
            e.key, e.Description, e.Category, e.Civilians, e.Deaths, e.EndDate, e.icon, e.EndDate, e.Source,
            e2v.@class as EventVertex,
            v.key, v.title, v.icon, v.Description, v.Gender, v.LastName, v.FirstName, v.@class as class_name 
            ''' % (kwargs['caseKey'], kwargs['caseKey'])
        else:
            sql = '''
            MATCH
            {class:Location, as:l}.bothE(){as:l2e}.bothV()
            {class:Event, as:e}.bothE(){as:e2v}.bothV()
            {class:V, as:v}
            RETURN 
            l.key, l.Longitude, l.Latitude, l.title, l.Category, l.Type, l.icon,  
            l2e.@class as EventLocation, 
            e.key, e.Description, e.Category, e.Civilians, e.Deaths, e.EndDate, e.icon, e.EndDate, e.Source,
            e2v.@class as EventVertex,
            v.key, v.title, v.icon, v.Description, v.Gender, v.LastName, v.FirstName, v.@class as class_name 
            '''
        r = self.client.command(sql)
        curLocation = None
        curEvent = None
        index = []
        for i in r:

            click.echo(i.oRecordData)

    def save_osint(self, **kwargs):
        """
        Checks if the Case already exists and if not, creates it.
        Checks if the Nodes sent in the graphCase are already "Attached" to the Case if the Case does exist.
        Expects a request with graphCase containing the graph from the user's canvas and assumes that all nodes have an
        attribute "key". The creation of a node is only if the node is new and taken from a source that doesn't exist in
        POLE yet.
        TODO: Ensure duplicate relations not made. Need enhancement to get relation name
        TODO: Implement classification and Owner/Reader relations
        1) Match all
        :param r:
        :return:
        """

        fGraph = {"graphCase": {"nodes": kwargs['nodes'], "lines": kwargs['lines'], "groups": kwargs['groups']}}
        fGraph = self.quality_check(format_graph(fGraph['graphCase']))

        case, message = self.save(graphCase=fGraph,
                  userOwners=kwargs['userOwners'],
                  classification=kwargs['classification'],
                  graphName=kwargs['graphName'])
        data = {
            "graph": case,
            "geo": {
                "Spots": {
                    "items": []
                }
            }
        }
        graphs = [data]

        return graphs, message

    def processTweets(self, **kwargs):
        """
        Using the basic structure below, create a relationship between a user and all the tweets. Extract Hashtags
        from tweets where applicable. Extract Locations where applicable.
        Tweet structure:
            uid: id, id_str, quoted_status_id
        int:
            favorite_count, retweet_count
        dtg:
            created_at
        obj:
            retweeted_status, entities, user
        str:
            lang, text
        bin:
            favorited, in_reply_to_screen_name, in_reply_to_status_id, in_reply_to_user_id,
            is_quote_status, retweeted, truncated
        user:
            created_at, description, url, name, location, listed_count, profile_image_url_https

        Node structure:
            key=key,                            ## TweetID
            class_name=kwargs['class_name'],    ## Event Tweet, Object User
            title=title,
            status=status,                      ## TODO sentiment
            icon=icon,
            attributes=attributes               ## [label, value]

        :param kwargs:
        :return:
        """
        graph = {
            "nodes": [],
            "lines": [],
            "groups": [
                {"key": 1, "title": "Profiles"},
                {"key": 2, "title": "Posts"},
                {"key": 3, "title": "Locations"},
                {"key": 4, "title": "Hashtags"}
            ]
        }
        geo = []
        index = []
        if kwargs['tweets']:
            for t in kwargs['tweets']:
                twt_id = "TWT_%s" % t['id']
                if twt_id not in index:
                    index.append(twt_id)
                    hash_tags_str = ""
                    ht_count = 0
                    # Process Hashtags by creating a string and an entity. Then create a line to the HT from the Tweet
                    for ht in t['entities']['hashtags']:
                        if ht_count == len(t['entities']['hashtags']):
                            hash_tags_str = hash_tags_str + ht['text']
                        else:
                            hash_tags_str = hash_tags_str + ht['text']+ ", "
                        ht_count+=1
                        ht_id = "%s_hashtag_id" % ht['text']
                        if ht_id not in index:
                            index.append(ht_id)
                            graph['nodes'].append({
                                "key": ht_id,
                                "class_name": "Object",
                                "title": "#%s" % ht['text'],
                                "icon": self.ICON_HASHTAG,
                                "group": 4,
                                "attributes": [
                                    {"label": "Text", "value": ht['text']}
                                ]
                            })
                        graph['lines'].append(
                            {"to": ht_id, "from": twt_id, "description": "Included"}
                        )
                    # Process Locations
                    if "place" in t.keys():
                        if t['place']:
                            if len(t['place']['bounding_box']['coordinates'][0]) > 0:
                                loc_id = "TWT_Place_%s" % t['place']['id']
                                if loc_id not in index:
                                    index.append(loc_id)
                                    graph['nodes'].append({
                                        "key": loc_id,
                                        "class_name": "Location",
                                        "title": t['place']['name'],
                                        "status": random.choice(self.ICON_STATUSES),
                                        "icon": self.ICON_LOCATION,
                                        "group": 3,
                                        "attributes": [
                                            {"label": "Re-message", "value": t['place']['url']},
                                            {"label": "Country", "value": t['place']['country']},
                                            {"label": "Longitude", "value": t['place']['bounding_box']['coordinates'][0][0][0]},
                                            {"label": "Latitude", "value": t['place']['bounding_box']['coordinates'][0][0][1]},
                                            {"label": "Type", "value": t['place']['place_type']},
                                        ]
                                    })
                                    geo.append({
                                        "pos": "%f;%f:0" % (
                                            t['place']['bounding_box']['coordinates'][0][0][0],
                                            t['place']['bounding_box']['coordinates'][0][0][1]),
                                        "type": random.choice(self.ICON_STATUSES),
                                        "tooltip": t['place']['name']
                                    })
                                graph['lines'].append({"from": twt_id, "to": loc_id, "description": "TweetedFrom"})


                    # Process the User by creating an entity. Then create a line from the User to the Tweet
                    user_id = "TWT_%s" % t['user']['id']
                    if user_id not in index:
                        index.append(user_id)
                        graph['nodes'].append({
                            "key": user_id,
                            "class_name": "Object",
                            "title": t['user']['name'],
                            "status": "Alert",
                            "group": 1,
                            "icon": self.ICON_TWITTER_USER,
                            "attributes": [
                                {"label": "Screen name", "value": t['user']['screen_name']},
                                {"label": "Created", "value": t['user']['created_at']},
                                {"label": "Description", "value": t['user']['description']},
                                {"label": "Favorite", "value": t['user']['favourites_count']},
                                {"label": "Followers", "value": t['user']['followers_count']},
                                {"label": "Friends", "value": t['user']['friends_count']},
                                {"label": "Following", "value": t['user']['following']},
                                {"label": "listed_count", "value": t['user']['listed_count']},
                                {"label": "statuses_count", "value": t['user']['statuses_count']},
                                {"label": "Geo", "value": t['user']['geo_enabled']},
                                {"label": "Location", "value": t['user']['location']},
                                {"label": "Image", "value": t['user']['profile_image_url_https']},
                                {"label": "Verified", "value": t['user']['verified']},
                                {"label": "Source", "value": "Twitter"}
                            ]
                        })
                    graph['lines'].append(
                        {"from": user_id, "to": twt_id, "description": "Tweeted"}
                    )
                    graph['nodes'].append({
                        "key": twt_id,
                        "class_name": "Event",
                        "title": "Tweet from " + t['user']['name'],
                        "status": random.choice(self.ICON_STATUSES),
                        "icon": self.ICON_TWEET,
                        "group": 2,
                        "attributes": [
                            {"label": "Created", "value": t['created_at']},
                            {"label": "Text", "value": t['text']},
                            {"label": "Language", "value": t['lang']},
                            {"label": "Re-message", "value": t['retweet_count']},
                            {"label": "Favorite", "value": t['favorite_count']},
                            {"label": "URL", "value": t['source']},
                            {"label": "Geo", "value": t['coordinates']},
                            {"label": "Hashtags", "value": hash_tags_str},
                            {"label": "User", "value": t['user']['screen_name']},
                        ]
                    })

        data = {
            "graph": graph,
            "geo": {
                "Spots": {
                    "items": geo
                }
            }
        }

        return data

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
