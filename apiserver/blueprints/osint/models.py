import click, os
import requests, json, random
import pandas as pd
import codecs
import time
import threading
from OTXv2 import OTXv2
from apiserver.models import OSINTModel as Models
from apiserver.utils import get_datetime, clean, change_if_date, TWITTER_AUTH, randomString
from apiserver.blueprints.home.models import ODB
from apiserver.blueprints.users.models import ODB as uDB
from requests_oauthlib import OAuth1
import urllib3
urllib3.disable_warnings()

"""
TODO Create a combined GEO view from ACLED and UCDP that can animate organizations in time
PoC of just any Location - Event based rel to create the view
"""


class OSINT(ODB):

    def __init__(self, db_name="OSINT"):
        ODB.__init__(self, db_name, models=Models)
        self.db_name = db_name
        self.basebook = None
        self.models = Models
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
        click.echo('[%s_OSINT_init] Complete' % (get_datetime()))
        self.ACLED_Base_URL = "https://api.acleddata.com/acled/read?terms=accept"
        self.UCDP_Page_Size = 200
        self.UCDP_Base_URL = "https://ucdpapi.pcr.uu.se/api/gedevents/19.1?pagesize=%s" % self.UCDP_Page_Size
        self.UCDP_Country_URL = "%s&Country=" % self.UCDP_Base_URL
        self.UCDP_Time_URL = "%s&StartDate=" % self.UCDP_Base_URL
        self.TWITTER_AUTH = TWITTER_AUTH
        self.base_twitter_url = "https://api.twitter.com/1.1/"
        self.monitors = {"twitter": False, "merger": False}
        self.default_number_of_tweets = 200
        self.cve = ["AttackPattern", "Campaign", "CourseOfAction", "Identity",
                    "Indicator", "IntrusionSet", "Malware", "ObservedData",
                    "Report", "Sighting", "ThreatActor", "Tool", "Vulnerability"]

    @staticmethod
    def ucdp_conflict_type(row):

        if row['type_of_violence'] == str(1):
            return "State-based Conflict"
        elif row['type_of_violence'] == str(2):
            return "Non-state Conflict"
        else:
            return "One-sided Conflict"

    def monitor_merges(self):
        """
        Crawler makes queries every hour to check the database for nodes with the same Ext_ID and then perform a merge
        on the first one found with the links of the others. TODO, include more attributes to crawl for and return
        likely nodes based on cases where similarity but not exact matches
        :return:
        """
        while self.monitors["merger"] == True:
            click.echo('[%s_OSINT_run_monitor_merges] Starting...' % (get_datetime()))
            index = {}
            r = self.client.command('''
            select @class, key, Ext_key from V where Ext_key != ""
            ''')
            for i in r:
                if i.oRecordData["Ext_key"] in index.keys():
                    index[i.oRecordData["Ext_key"]].append(i.oRecordData)
                else:
                    index[i.oRecordData["Ext_key"]] = [i.oRecordData]
            merges = 0
            for i in index:
                if len(index[i]) > 1:
                    merges+=1
                    # Check if each of them are in the same class by making buckets
                    class_buckets = {}
                    for o in index[i]:
                        if o["class"] in class_buckets.keys():
                            class_buckets[o["class"]].append(o["key"])
                        else:
                            class_buckets[o["class"]] = [o["key"]]
                    # Run through each bucket and if there is more than 1, then we still have entities needing merging
                    for bucket in class_buckets:
                        if len(class_buckets[bucket]) > 1:
                            # Run through the nodes in the bucket using an "ni" node iterator to determine if at first node
                            ni = 0
                            node_A = node_B = None
                            for n in class_buckets[bucket]:
                                if ni == 0:
                                    node_A = n
                                # this is skipped the first round as the source node is set
                                else:
                                    node_B = n
                                # only after both nodes are set, at ni > 0, merge the nodes
                                if ni > 0 and node_A and node_B:
                                    self.merge_nodes(node_A=node_A, node_B=node_B)
                                ni+=1
            click.echo('[%s_OSINT_run_monitor_merges] Complete with %d merge operations ' % (get_datetime(), merges))
            time.sleep(60*60*2)

    def run_otx(self):

        click.echo('[%s_OSINT_otx_init] Starting OTX feed download' % (get_datetime()))
        otx = OTXv2("4b11dfc51d0cd00e8cf01b268c3dbfde15090be65f6a2b58a5f102a600cfb8ee")
        events = otx.getall()
        click.echo('[%s_OSINT_otx_init] OTX feed download complete with %d events' % (get_datetime(), len(events)))
        graph = {"nodes": [], "edges": [], "index": []}
        j = 0
        r = 1
        for e in events:
            if "indicators" in e.keys() and "author_name" in e.keys():
                auth_node = {
                    "id": e["author_name"],
                    "tags": e["tags"],
                    "description": e["description"]
                }
                if auth_node["id"] not in graph["index"]:
                    graph["index"].append(e["author_name"])
                    graph["nodes"].append({"title": e["author_name"]})
                for i in e["indicators"]:
                    otx_node = {
                        "id": "otx_%s" % i["id"],
                        "description": i["description"],
                        "created": i["created"],
                        "expiration": i["expiration"],
                        "category": i["type"],
                        "ip_address": i["indicator"]
                    }
                    if otx_node["id"] not in graph["index"]:
                        graph["nodes"].append(otx_node)
                        graph["index"].append(otx_node["id"])
                        graph["edges"].append({"to": otx_node["id"], "from": auth_node["id"]})

            j+=1
            if i == 100:
                click.echo('[%s_OSINT_otx_init] Completed %d items' % (get_datetime(), 100*r))
                r+=1
                i=0

        return graph

    def create_CTI_node(self, **kwargs):

        attributes = kwargs['attributes']
        if attributes:
            att_sql = ""
            for a in attributes:
                try:
                    att_sql = att_sql + ", %s = '%s'" % (a['label'], a['value'])
                except Exception as e:
                    print(str(e))

            sql = ('''
            create vertex %s set key = '%s', title = '%s' %s
            ''' % (kwargs['class_name'], kwargs['key'], kwargs['title'], att_sql))
        else:
            sql = ('''
            create vertex %s set key = '%s', title = '%s'
            ''' % (kwargs['class_name'], kwargs['key'], kwargs['title']))
        try:
            self.client.command(sql)
        except Exception as e:
            if str(e) == "":
                return
            elif str(type(e)) == "<class 'pyorient.exceptions.PyOrientORecordDuplicatedException'>":
                return
            else:
                return

    def get_suggestion_items(self, **kwargs):
        """
        Using the LUCENE text indexing of the different classes available,
        return a small sample of matching items that can be chosen from a search list.
        :param kwargs:
        :return:
        """
        # Build the SQL that will be sent to the server
        sql = '''
        SELECT EXPAND( $models )
        LET 
        '''
        union = "$models = UNIONALL("
        i = 0
        for m in self.models.keys():
            sql = sql + '''
            $%s = (SELECT key, title, @class, description FROM %s WHERE [description] LUCENE "%s*" LIMIT 5),\n
            ''' % (m[0:3].lower(), m, kwargs['searchterms'])
            union = union + "$%s" % m[0:3].lower()
            if i != len(self.models.keys())-1:
                union = union + ", "
            else:
                union = union + ")"
            i+=1

        sql = sql + union
        r = self.client.command(sql)
        suggestionItems = []
        for i in r:
            try:
                suggestionItems.append({
                    "NODE_KEY": i.oRecordData["key"],
                    "NODE_TYPE": i.oRecordData["class"],
                    "NODE_NAME": i.oRecordData["title"]
                })
            except Exception as e:
                if e.args[0] == "title":
                    suggestionItems.append({
                        "NODE_KEY": i.oRecordData["key"],
                        "NODE_TYPE": i.oRecordData["class"],
                        "NODE_NAME": i.oRecordData["description"]
                    })
                else:
                    suggestionItems.append({
                        "NODE_KEY": i.oRecordData["key"],
                        "NODE_TYPE": i.oRecordData["class"],
                        "NODE_NAME": "Unknown title for " + i.oRecordData["class"]
                    })

        return suggestionItems
    
    def get_neighbors(self, **kwargs):
        """
        Get the neighbors of a selected Node and return a flat file only of the new neighbors
        and their relationships with cardinality
        NODE_KEY, NODE_TYPE, NODE_NAME, NODE_ATTR_ID, EDGE_SOURCE, EDGE_TARGET, EDGE_NAME
        :param kwargs:
        :return:
        """
        sql = '''
        MATCH
        {class:V, where: (key = '%s')}
        .bothE(){as:o2n}
        .bothV(){class:V, as:n}
        RETURN 
        o2n.@class as EDGE_TYPE, o2n.out.key as EDGE_SOURCE , o2n.in.key as EDGE_TARGET,
        n.key as NODE_KEY, n.title as NODE_NAME, n.@class as NODE_TYPE, n.description as NODE_ATTR_ID
        ''' % (kwargs["nodekey"])
        # Start a response object with data array and node_keys including the queried so it is not included
        response = {"data": [], "node_keys": [kwargs["nodekey"]]}
        for r in self.client.command(sql):
            r = r.oRecordData
            if r["EDGE_TARGET"] == kwargs["nodekey"]:
                r["EDGE_DIRECTION"] = "IN"
            else:
                r["EDGE_DIRECTION"] = "OUT"
            if r["NODE_KEY"] not in response["node_keys"]:
                response["data"].append(r)
                response["node_keys"].append(r["NODE_KEY"])
        response["message"] = "Get neighbors for %s resulted in %d nodes" % (kwargs["nodekey"], len(response["data"]))
        return response

    def check_base_book(self):
        """
        Check if the Organizations have been set by UCDP
        :return:
        """
        click.echo('[%s_OSINTserver_check_base_book] Checking base OSINT settings' % (get_datetime()))
        try:
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
        except Exception as e:
            click.echo('[%s_OSINTserver_check_base_book] Encountered non-critical error\n%s'
                       % (get_datetime(), str(e)))

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
            ''' select key, UCDP_id, Category, icon, title, description, Sources, StartDate, EndDate, Deaths, Origin,
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
                    {"label": "Description", "value": i.oRecordData['description']},
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
                            description="Organization from UCDP. %s" % s,
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
                    description=("Headline: %s Article: %s" % (
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
                try:
                    graph_build['nodes'].append(event_node['data'])
                except Exception as e:
                    print(str(e))
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
                    description="Political %s" % row['side_a'],
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
                    description="Political %s" % row['side_b'],
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
                description="%s %s %s %s" % (row['adm_1'], row['adm_2'], row['country'], row['region']),
                Latitude=row['latitude'],
                Longitude=row['longitude'],
                title="%s %s" % (city, row['country']),
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

    def create_monitor(self, searchValue="vulnerability", userName="SocAnalyst", name="Twitter", type="Search", description="hashtag"):
        '''

        insert into Monitor (key, name, searchValue, type, user, description) values (sequence('idseq').next(), "Twitter", null, "Channel", "SocAnalyst", "Hashtags, User timelines, and location based search") return @this.key
        insert into Monitor (key, name, searchValue, type, user, description) values (sequence('idseq').next(), "Twitter", "vulnerability", "Search", "SocAnalyst", "hashtag") return @this.key
        insert into Monitor (key, name, searchValue, type, user, description) values (sequence('idseq').next(), "Twitter", "realDonaldTrump", "Search", "SocAnalyst", "user") return @this.key

        :param kwargs:
        :return:
        '''
        # Check if the user exists within OSINT
        if len(self.client.command('''select key from User where userName = "%s"''' % userName)) == 0:
            self.client.command('''
            insert into User (key, userName) values (sequence('idseq').next(), "%s") return @this.key 
            ''' % userName)

        # Next check if the channel exists
        message = "%s adding channel %s with search %s." % (userName, name, searchValue)
        monitor_channel = self.client.command('''
        select key from Monitor where type = 'Channel' and name = '%s'
        ''' % (name))
        if len(monitor_channel) > 0:
            # Set the monitor channel key for relating to the searchTerm and user
            monitor_channel = monitor_channel[0].oRecordData["key"]
            # Check if the monitor is subscribed to be the user
            sql = '''
            match
            {class:Monitor, as:m, where: (name = '%s' and type = 'Channel')}.in("SubscribesTo")
            {class:User, as:u, where: (userName = '%s')}
            return m
            ''' % (name, userName)
            if len(self.client.command(sql)) == 0:
                message += "\n%s exists but user is now newly subscribed to it. " % name
                self.client.command('''
                create edge SubscribesTo from 
                (select from User where userName = '%s') to 
                (select from Monitor where key = %d )
                ''' % (userName, monitor_channel))
            else:
                message += "\n%s exists and user already subscribed. " % name
        else:
            # The monitor channel needs to be created...
            message += "\n%s doesn't exist so has been created with user subscribed. " % name
            monitor_channel = self.create_node(
                class_name="Monitor",
                name=name,
                searchValue=None,
                type="Channel",
                description=description
            )["data"]["key"]
            # ...and the user subscription to the monitor
            self.client.command('''
            create edge SubscribesTo from 
            (select from User where userName = '%s') to 
            (select from Monitor where key = %d )
            ''' % (userName, monitor_channel))

        # If the monitor is a search
        if type == "Search":
            # Check if it exists
            monitor_search = self.client.command('''
            select key from Monitor where name = "%s" and searchValue = "%s" and description = "%s"
            ''' % (name, searchValue, description))
            if len(monitor_search) == 0:
                # If not create it and relate it to the channel
                message += "\n%s doesn't exist so has been created with user subscribed. " % searchValue
                monitor_search = self.create_node(
                    class_name="Monitor",
                    name=name,
                    searchValue=searchValue,
                    type="Search",
                    description=description
                )["data"]["key"]
                # Relate to the channel
                self.client.command('''
                create edge SearchesOn from 
                (select from Monitor where key = %d) to 
                (select from Monitor where key = %d )
                ''' % (monitor_channel, monitor_search))
                # Make the user subscription relation
                self.client.command('''
                create edge SubscribesTo from 
                (select from User where userName = '%s') to 
                (select from Monitor where key = %d )
                ''' % (userName, monitor_search))
            else:
                monitor_search = monitor_search[0].oRecordData["key"]
                sql = '''
                match
                {class:Monitor, as:m, where: (key = %d and type = 'Search' and searchValue = '%s')}.in("SubscribesTo")
                {class:User, as:u, where: (userName = '%s')}
                return m
                ''' % (monitor_search, searchValue, userName)
                if len(self.client.command(sql)) == 0:
                    message += "%s is now subscribed to %s. " % (userName, searchValue)
                    # Make the user subscription relation
                    self.client.command('''
                    create edge SubscribesTo from 
                    (select from User where userName = '%s') to 
                    (select from Monitor where key = %d )
                    ''' % (userName, monitor_search))
                else:
                    message += "%s is already subcribed to %s." % (userName, searchValue)

        return message

    def start_merge_monitor(self):
        """
        Start a thread to run the monitor
        :return:
        """
        r = {}
        if self.monitors["merger"] == False:
            t = threading.Thread(target=self.monitor_merges)
            self.monitors["merger"] = True
            t.start()
            r["message"] = '[%s_OSINT_start_merge_monitor] Turned on' % (get_datetime())
            click.echo(r["message"])
        else:
            r["message"] = '[%s_OSINT_start_merge_monitor] Turned off' % (get_datetime())
            self.monitors["merger"] = False

        return r

    def create_report(self, **kwargs):
        """
        Create a record of summary activity from an automated process such as a crawler
        Store the record for later use including analysis of time stamps and production
        :param kwargs:
        :return:
        """
        pid = randomString(32)
        self.create_node(
            class_name="Process",
            category="Report",
            pid=pid,
            name=kwargs["name"],
            started=get_datetime(),
            summary=kwargs["summary"]
        )
        return pid

    def create_update(self, **kwargs):
        """
        Create a record that updates the report
        :param kwargs:
        :return:
        """
        update_key = self.create_node(
            class_name="Process",
            category="Update",
            pid=kwargs['pid'],
            name=kwargs["name"],
            started=get_datetime(),
            summary=kwargs["summary"]
        )

        self.client.command('''
        create edge UpdateTo from 
        (select from Process where key = %d) to 
        (select from Process where pid = '%s' and category = "Report")
        ''' % (update_key['data']['key'], kwargs['pid']))

        return update_key

    def update_report(self, **kwargs):
        """
        Using a new line for a summary report, update the report by its process pid

        :param kwargs:
        :return:
        """
        update_key = self.create_update(pid=kwargs['pid'], name=kwargs['name'], summary=kwargs['summary'])
        if "ended" in kwargs.keys():
            self.client.command('''
            update Process set ended = '%s' where pid = '%s'
            ''' % (get_datetime(), kwargs['pid']))

        return update_key["data"]["key"]

    def get_user_monitor(self, userName="SocAnalyst"):
        monitors = []
        sql = '''
        match
        {class:User, where: (userName = '%s')}.out("SubscribesTo")
        {class:Monitor, as:s}.in("SearchesOn")
        return s.key as key, s.description as label, s.searchValue as value, s.name as source
        ''' % (userName)
        for i in self.client.command(sql):
            monitors.append(i.oRecordData)
        message = "Retrieved %s monitored terms for %s" % (len(monitors), userName)

        return {"data": monitors, "message": message}

    def start_twitter_monitor(self, user="SocAnalyst"):
        """
        Start a thread to run the monitor. Using the username, get all the channels they are subscribed to on Twitter
        and start the monitor. SocAnalyst is standard user subscribed to all channels and can therefore be used for a
        full monitor. For all others, the channels can be made customized and only the channels they search for are
        returned.
        Example monitors for twitter:
        user_monitor = [
            "realDonaldTrump", "WhatsTrending", "BernieSanders", "PeteButtigieg", "benshapiro", "jeremycorbyn",
            "CVEcommunity", "BBCWorld", "AJEnglish"
        ]
        locations_monitor = [{"lat": 48.83, "lon": 2.3}, {"lat": 40.254, "lon": -73.93}, {"lat": 51.441, "lon": -0.002}]
        hashtags_monitor = ["bbc", "vulnerability", "MITRE"]
        :return:
        """
        # Get the user's monitors
        sql = '''
        match
        {class:User, where: (userName = '%s')}.out("SubscribesTo")
        {class:Monitor, as:s}.in("SearchesOn")
        {class:Monitor, as:channel, where: (name = 'Twitter')}
        return s.key, s.description, s.searchValue, s.type
        ''' % (user)
        monitors = self.client.command(sql)
        user_monitor = []
        locations_monitor = []
        hashtags_monitor = []
        for m in monitors:
            if m.oRecordData["s_description"] == "location":
                try:
                    locations_monitor.append(json.loads(m.oRecordData["s_searchValue"].replace("'", '"')))
                except:
                    click.echo('[%s_OSINT_start_twitter_monitor] Error with location %s' % (
                        get_datetime(), m.oRecordData["s_searchValue"]))
            elif m.oRecordData["s_description"] == "hashtag":
                hashtags_monitor.append(m.oRecordData["s_searchValue"])
            elif m.oRecordData["s_description"] == "user":
                user_monitor.append(m.oRecordData["s_searchValue"])

        r = {}
        t = threading.Thread(
            target=self.monitor_twitter,
            kwargs={
                "user_monitor": user_monitor,
                "locations_monitor": locations_monitor,
                "hashtags_monitor": hashtags_monitor
            })
        if self.monitors["twitter"] == False:
            self.monitors["twitter"] = True
            click.echo('[%s_OSINT_start_twitter_monitor] Turned on' % (get_datetime()))
            t.start()
            r["message"] = "Twitter monitor started"
        else:
            click.echo('[%s_OSINT_start_twitter_monitor] Turned off' % (get_datetime()))
            r["message"] = "Twitter monitor stopped"
            self.monitors["twitter"] = False

        return r

    def monitor_twitter(self, **kwargs):
        """
        The thread that runs until turned off. When started runs every 30 minutes.
        The thread is stored in the self.monitors{twitter: var}. The thread can be turned off
        by means of setting it to False. TODO create a higher level process that is monitor and relate the others to it
        :param kwargs:
        :return:
        """
        minutes = 30
        name = "Twitter"
        while self.monitors["twitter"]:
            pid = self.create_report(name=name, summary="Starting")
            update_key = self.update_report(pid=pid, summary="Getting users", name=name)
            for u in kwargs["user_monitor"]:
                graphs, message = self.get_twitter(number_of_tweets=100, username=u)
                for g in graphs:
                    self.process_graph(graph=g["graph"], update_key=update_key)

            update_key = self.update_report(pid=pid, summary="Getting locations", name=name)
            for l in kwargs["locations_monitor"]:
                graphs, message = self.get_twitter(number_of_tweets=100, latitude=l["lat"], longitude=l["lon"])
                for g in graphs:
                    self.process_graph(graph=g["graph"], update_key=update_key)
            update_key = self.update_report(pid=pid, summary="Getting hashtags", name=name)
            for l in kwargs["hashtags_monitor"]:
                graphs, message = self.get_twitter(number_of_tweets=100, hashtag=l)
                for g in graphs:
                    self.process_graph(graph=g["graph"], update_key=update_key)
            self.update_report(ended=True, pid=pid,
                               name=name, summary="Complete with requests. Sleeping for %d minutes" % minutes)
            time.sleep(60 * minutes)

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

        # TODO implement crawlers to get loads that don't break the API quota rules
        if "popular" in kwargs.keys():
            api_url = "https://api.twitter.com/1.1/trends/place.json?id=1&count=100"
            response = requests.get(api_url, auth=oauth, verify=False)
            tweets = self.responseHandler(response, "Popular, %s" % get_datetime())
            tweets = self.processTweets(tweets=tweets)
            graphs.append(tweets)

        return graphs, message

    def geo_spatial_view(self, **kwargs):
        """
        Create a record for every location->event->Vertex and for every location->Event. If there is a case in the
        request, only get those items related to case. By book-ending the query with the case, there is no risk in
        picking up data not part of the case. TODO Additional check on data to ensure classification does not break rule
            {position: l.latitude, l.longitude, e.startDate
            tooltip:
            DependentData: time?  , v.type, v.category, e.type
            {circle: position, tooltip, radius, color, colorborder, hotDeltaColor, click
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
        TODO: Implement classification and Owner/Reader relations
        1) Match all
        :param r:
        :return:
        """
        if "nodes" in kwargs.keys():
            fGraph = {"nodes": kwargs['nodes'], "lines": kwargs['lines'], "groups": kwargs['groups']}
        else:
            fGraph = {}
            for k in kwargs.keys():
                fGraph[k] = kwargs[k]

        case, message = self.save(
            graphCase=fGraph,
            Owners=kwargs['Owners'],
            Members=kwargs['Members'],
            CreatedBy=kwargs['CreatedBy'],
            Classification=kwargs['Classification'],
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
                {"key": "Profiles", "title": "Profiles"},
                {"key": "Posts", "title": "Posts"},
                {"key": "Locations", "title": "Locations"},
                {"key": "Hashtags", "title": "Hashtags"}
            ]
        }
        geo = []
        index = []
        if "tweets" in kwargs.keys():
            for t in kwargs['tweets']:
                twt_id = "TWT_%s" % t['id']
                hash_tags_str = ""
                if twt_id not in index:
                    index.append(twt_id)
                    node = {
                        "key": twt_id,
                        "class_name": "Event",
                        "title": "Tweet from " + t['user']['name'],
                        "status": random.choice(self.ICON_STATUSES),
                        "icon": self.ICON_TWEET,
                        "group": "Posts",
                        "attributes": [
                            {"label": "Created", "value": t['created_at']},
                            {"label": "Text", "value": t['text']},
                            {"label": "description", "value": "%s tweeted %s" % (t['user']['name'], t['text'])},
                            {"label": "Language", "value": t['lang']},
                            {"label": "Re_message", "value": t['retweet_count']},
                            {"label": "Favorite", "value": t['favorite_count']},
                            {"label": "URL", "value": t['source']},
                            {"label": "Geo", "value": t['coordinates']},
                            {"label": "Hashtags", "value": hash_tags_str},
                            {"label": "User", "value": t['user']['screen_name']},
                        ]
                    }
                    graph['nodes'].append(node)
                    if "PROCESS" in kwargs.keys():
                        TWT_NODE = self.create_node(**node)

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
                            node = {
                                "key": ht_id,
                                "class_name": "Object",
                                "title": "#%s" % ht['text'],
                                "icon": self.ICON_HASHTAG,
                                "group": 4,
                                "attributes": [
                                    {"label": "Text", "value": ht['text']},
                                    {"label": "description", "value": "Hashtag %s" % ht['text']}
                                ]
                            }
                            graph['nodes'].append(node)
                            if "PROCESS" in kwargs.keys():
                                HT_NODE = self.create_node(**node)
                                self.create_edge(toClass=node["class_name"], fromClass="Event", edgeType="Included",
                                                 toNode=HT_NODE["data"]["key"], fromNode=TWT_NODE["data"]["key"])
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
                                    node = {
                                        "key": loc_id,
                                        "class_name": "Locations",
                                        "title": t['place']['name'],
                                        "status": random.choice(self.ICON_STATUSES),
                                        "icon": self.ICON_LOCATION,
                                        "group": "Locations",
                                        "attributes": [
                                            {"label": "Re_message", "value": t['place']['url']},
                                            {"label": "Country", "value": t['place']['country']},
                                            {"label": "Longitude", "value": t['place']['bounding_box']['coordinates'][0][0][0]},
                                            {"label": "Latitude", "value": t['place']['bounding_box']['coordinates'][0][0][1]},
                                            {"label": "Type", "value": t['place']['place_type']},
                                            {"label": "description", "value": "%s %s %s,%s" % (
                                                t['place']['country'],
                                                t['place']['place_type'],
                                                t['place']['bounding_box']['coordinates'][0][0][0],
                                                t['place']['bounding_box']['coordinates'][0][0][1]
                                            )}
                                        ]
                                    }
                                    graph['nodes'].append(node)
                                    if "PROCESS" in kwargs.keys():
                                        LOC_NODE = self.create_node(**node)
                                        self.create_edge(toClass=node["class_name"], fromClass="Event",
                                                         edgeType="TweetedFrom",
                                                         toNode=LOC_NODE["data"]["key"],
                                                         fromNode=TWT_NODE["data"]["key"])
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
                        node = {
                            "key": user_id,
                            "class_name": "Object",
                            "title": t['user']['name'],
                            "status": "Alert",
                            "group": "Profiles",
                            "icon": self.ICON_TWITTER_USER,
                            "attributes": [
                                {"label": "Screen_name", "value": t['user']['screen_name']},
                                {"label": "Created", "value": t['user']['created_at']},
                                {"label": "description", "value": t['user']['description']},
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
                        }
                        graph['nodes'].append(node)
                        if "PROCESS" in kwargs.keys():
                            USR_NODE = self.create_node(**node)
                            self.create_edge(toClass="Event", fromClass=node["class_name"],
                                             edgeType="Tweeted",
                                             toNode=TWT_NODE["data"]["key"],
                                             fromNode=USR_NODE["data"]["key"])
                    graph['lines'].append(
                        {"from": user_id, "to": twt_id, "description": "Tweeted"}
                    )


        elif "user" in kwargs.keys():
            user_id = kwargs['user']['id']
            if user_id not in index:
                index.append(user_id)
                node = ({
                    "key": user_id,
                    "class_name": "Object",
                    "title": kwargs['user']['name'],
                    "status": "Alert",
                    "group": "Profiles",
                    "icon": self.ICON_TWITTER_USER,
                    "attributes": [
                        {"label": "Screen_name", "value": kwargs['user']['screen_name']},
                        {"label": "Created", "value": kwargs['user']['created_at']},
                        {"label": "description", "value": kwargs['user']['description']},
                        {"label": "Favorite", "value": kwargs['user']['favourites_count']},
                        {"label": "Followers", "value": kwargs['user']['followers_count']},
                        {"label": "Friends", "value": kwargs['user']['friends_count']},
                        {"label": "Following", "value": kwargs['user']['following']},
                        {"label": "listed_count", "value": kwargs['user']['listed_count']},
                        {"label": "statuses_count", "value": kwargs['user']['statuses_count']},
                        {"label": "Geo", "value": kwargs['user']['geo_enabled']},
                        {"label": "Location", "value": kwargs['user']['location']},
                        {"label": "Image", "value": kwargs['user']['profile_image_url_https']},
                        {"label": "Verified", "value": kwargs['user']['verified']},
                        {"label": "Source", "value": "Twitter"}
                    ]
                })
                if "PROCESS" in kwargs.keys():
                    self.create_node(**node)
            return node
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
            click.echo("[!] <429> Too many requests to Twitter. Sleep for 15 minutes started at: %s" % get_datetime())
            time.sleep(60*15)
            return

        if response.status_code == 503:
            return "[!] <503> The Twitter servers are up, but overloaded with requests. Try again later: %s" % get_datetime()

        else:
            return None

    def merge_osint(self, **kwargs):
        r = self.merge_nodes(node_A=kwargs['node_A'], node_B=kwargs['node_B'])
        return r

    def process_graph(self, **kwargs):
        '''
        :param graph: 
        :return: 
        '''
        entityKeyMap = {}
        odb_graph = {"nodes": [], "lines": []}
        for n in kwargs["graph"]["nodes"]:
            new_node = self.create_node(**n)["data"]
            # If the graph was created by an automated process, related the entities to the collection
            if "update_key" in kwargs.keys():
                self.create_edge(edgeType="CollectedFrom", fromNode=new_node["key"],
                                 toNode=kwargs["update_key"], fromClass=n["class_name"], toClass="Process")
            entityKeyMap[n["key"]] = {"key": new_node["key"], "class": n["class_name"]}
            odb_graph["nodes"].append(new_node)
        for n in kwargs["graph"]["lines"]:
            fromClass = entityKeyMap[n["from"]]["class"]
            toClass = entityKeyMap[n["to"]]["class"]
            self.create_edge(edgeType=n["description"], fromNode=entityKeyMap[n["from"]]["key"],
                             toNode=entityKeyMap[n["to"]]["key"], fromClass=fromClass, toClass=toClass)

    def getEntityData(self, user_ids, sourceID, reltype, username, graph):
        """
        Call the
        :param user_ids:
        :param sourceID:
        :param sourcename:
        :param reltype:
        :param username:
        :return:
        """
        client_key = self.TWITTER_AUTH['client_key']
        client_secret = self.TWITTER_AUTH['client_secret']
        token = self.TWITTER_AUTH['token']
        token_secret = self.TWITTER_AUTH['token_secret']
        oauth = OAuth1(client_key, client_secret, token, token_secret)
        i = 0
        # Set the url and build it from the names until 100 as a fail safe
        api_url = "https://api.twitter.com/1.1/users/lookup.json?user_id="
        while i < len(user_ids) and i < 100:
            api_url += ",%s" % user_ids[i]
            i+=1
        response = requests.get(api_url, auth=oauth, verify=False)
        users = self.responseHandler(response, username)
        if users == None:
            print("[*] No users in list.")
            return

        for user in users:
            graph["nodes"].append(self.processTweets(user=user))
            # Create the node in the database
            graph["lines"].append({
                "to": graph["nodes"][len(graph["nodes"])-1]["key"],
                "from": sourceID,
                "description": reltype
            })
            #self.create_edge(fromClass="Object", toClass="Object", fromNode=sourceID, toNode=O_GUID, edgeType=reltype)

        return graph

    def sendRequest(self, username, reltype, next_cursor=None):

        client_key = self.TWITTER_AUTH['client_key']
        client_secret = self.TWITTER_AUTH['client_secret']
        token = self.TWITTER_AUTH['token']
        token_secret = self.TWITTER_AUTH['token_secret']
        oauth = OAuth1(client_key, client_secret, token, token_secret)
        url = "https://api.twitter.com/1.1/%s/ids.json?screen_name=%s&count=5000" % (reltype, username)
        if next_cursor is not None:
            url += "&cursor=%s" % next_cursor
        click.echo('[%s_OSINT_sendRequest] %s' % (get_datetime(), url))
        response = requests.get(url, auth=oauth, verify=False)
        return self.responseHandler(response, username)

    def get_associates(self, username=None):
        """
        Get the friends and followers of a username
        Store the two types of relationships as associates' IDS which can then be looked up in bulk of 100
        User 2 internal functions to process the URL instead of 2 steps each time

        :param username:
        :return:
        """
        # Set up the API call
        graph = {
            "nodes": [],
            "lines": []
        }

        associate_list = []
        if username:
            userKey = self.client.command('''select key from Object where Screen_name = '%s' '''
                                          % username)[0].oRecordData["key"]

            for r in ["friends"]:
                associates = self.sendRequest(username, r, None)
                if associates is not None:
                    associate_list.extend(associates["ids"])
                    # while we have a cursor keep downloading friends/followers
                    while associates["next_cursor"] != 0 and associates["next_cursor"] != -1:
                        associates = self.sendRequest(username, r, associates["next_cursor"])
                        if associates is not None:
                            associate_list.extend(associates["ids"])
                        else:
                            break
                # Break down the associate list into groups of 100 to submit to UserInfo
                i = 0
                user_ids = []
                for user_id in associate_list:
                    user_ids.append(user_id)
                    if len(user_ids) == 100:
                        print("[*] 100 %s limit for entity. Request to Twitter." % r)
                        graph = self.getEntityData(user_ids, userKey, r, username, graph)
                        i = 0
                        del user_ids[:]
                    if i == len(associate_list) - 1:
                        print("[*] %d %s for entity info. Request to Twitter." % (len(user_ids), r))
                        graph = self.getEntityData(user_ids, userKey, r, username, graph)
                    i += 1

        return {"data": graph, "message": "Retrieved %d associates" % len(graph["nodes"])}

    def cve(self):
        """
        TODO Data quality. charmap breaks on for loop and miss half the rest of the data
        Data is master data only. Is there transaction data that create links and dynamic stuff
        :return:
        """
        path = os.path.join(self.datapath, "%s_cve.csv" % get_datetime()[:10])
        url = "https://cve.mitre.org/data/downloads/allitems.csv"
        data = self.get_url(url, path)
        if data:
            open(path, 'wb').write(data.content)

        with codecs.open(path, encoding="utf8", errors='ignore') as data_csv:
            click.echo('[%s_OSINT_cve] Cleaning raw data' % (get_datetime()))
            df = {}
            i = 0
            for row in data_csv:
                # Change the string into a list
                r = row.split(",")
                # Check if this is the headers row. Sometimes has double quotes
                if r[0] == 'Name' or r[0] == '"Name"':
                    for k in r:
                        df[k.replace('"', "")] = []
                # Only check the first column if the entry is longer than 3
                if len(r[0]) > 3:
                    if r[0][:4] == 'CVE-':
                        for k, l in zip(df.keys(), r):
                            df[k].append(l)
                i+=1
        click.echo('[%s_OSINT_cve] Complete with raw data cleaning' % (get_datetime()))
        return df

    def poisonivy(self):
        source = "%s_poisonivy.json" % get_datetime()[:10]
        path = os.path.join(self.datapath, source)
        url = 'https://oasis-open.github.io/cti-documentation/examples/example_json/poisonivy.json'
        data = self.get_url(url, path)
        rels = []
        if data:
            data = json.loads(data.content)
            with open(path, 'w') as fp:
                json.dump(data, fp)
        else:
            with open(path) as fp:
                data = json.load(fp)
        ctr = 0
        tm = 1
        for i in data['objects']:
            ctr+=1
            if ctr == 100:
                ctr = 0
                print("%s %d, %d" % (get_datetime(), tm, tm*ctr))
                tm+=1
            if i['type'] == 'attack-pattern':
                attributes = self.get_attributes(i, source)
                self.create_CTI_node(
                    class_name="AttackPattern",
                    key=i['id'],
                    title=i['name'],
                    CTI=True,
                    attributes = attributes
                )
            elif i['type'] == 'campaign':
                attributes = self.get_attributes(i, source)
                self.create_CTI_node(
                    class_name="Campaign",
                    key=i['id'],
                    title=i['name'],
                    CTI=True,
                    attributes = attributes
                )
            elif i['type'] == 'course-of-action':
                attributes = self.get_attributes(i, source)
                self.create_CTI_node(
                    class_name="CourseOfAction",
                    key=i['id'],
                    title=i['name'],
                    CTI=True,
                    attributes=attributes
                )
            elif i['type'] == 'identity':
                attributes = self.get_attributes(i, source)
                self.create_CTI_node(
                    class_name="Identity",
                    key=i['id'],
                    title=i['name'],
                    CTI=True,
                    attributes=attributes
                )
            elif i['type'] == 'indicator':
                attributes = self.get_attributes(i, source)
                self.create_CTI_node(
                    class_name="Indicator",
                    key=i['id'],
                    title=i['name'],
                    CTI=True,
                    attributes=attributes
                )
            elif i['type'] == 'intrusion-set':
                attributes = self.get_attributes(i, source)
                self.create_CTI_node(
                    class_name="IntrusionSet",
                    key=i['id'],
                    title=i['name'],
                    CTI=True,
                    attributes=attributes
                )
            elif i['type'] == 'malware':
                attributes = self.get_attributes(i, source)
                self.create_CTI_node(
                    class_name="Malware",
                    key=i['id'],
                    title=i['name'],
                    CTI=True,
                    attributes=attributes
                )
            elif i['type'] == 'observed-data':
                attributes = self.get_attributes(i, source)
                self.create_CTI_node(
                    class_name="ObservedData",
                    key=i['id'],
                    title="Observed data",
                    CTI=True,
                    attributes=attributes
                )
            elif i['type'] == 'report':
                attributes = self.get_attributes(i, source)
                self.create_CTI_node(
                    class_name="ObservedData",
                    key=i['id'],
                    title=i['name'],
                    CTI=True,
                    attributes=attributes
                )
            elif i['type'] == 'threat-actor':
                attributes = self.get_attributes(i, source)
                self.create_CTI_node(
                    class_name="ThreatActor",
                    key=i['id'],
                    title=i['name'],
                    CTI=True,
                    attributes=attributes
                )
            elif i['type'] == 'tool':
                attributes = self.get_attributes(i, source)
                self.create_CTI_node(
                    class_name="Tool",
                    key=i['id'],
                    title=i['name'],
                    CTI=True,
                    attributes=attributes
                )
            elif i['type'] == 'vulnerability':
                attributes = self.get_attributes(i, source)
                self.create_CTI_node(
                    class_name="Vulnerability",
                    key=i['id'],
                    title=i['name'],
                    CTI=True,
                    attributes=attributes
                )
            elif i['type'] == 'relationship':
                rels.append(i)


            print("%s_Cleaning raw data %s" % (get_datetime(), i))

        for r in rels:
            sql = '''
            create edge %s from 
            (select from V where key = '%s') to 
            (select from V where key = '%s')
            ''' % (r['relationship_type'], r['source_ref'], r['target_ref'])
            self.client.command(sql)

    def get_url(self, url, path):
        if not os.path.exists(path):
            print("%s_Fetching latest %s" % (get_datetime(), url))
            data = requests.get(url)
            return data
        else:
            print("%s_Latest data exists. No need to download" % get_datetime())
        return

    def get_attributes(self, record, source):
        attributes = [{"label": "source", "value": source}]
        for k in record.keys():
            if k not in ['id']:
                if type(record[k]) == list:
                    if type(record[k][0]) == dict:
                        val = ""
                        for a in record[k][0].keys():
                            val = val + "%s - %s " % (a, record[k][0][a])

                    else:
                        val = ','.join(map(str, record[k]))
                else:
                    try:
                        new_val = change_if_date(record[k])
                        if new_val:
                            val = new_val
                        else:
                            val = record[k]
                    except Exception as e:
                        print(str(e))
                if not new_val:
                    try:
                        val = val.replace("'", "")
                        date_val = change_if_date(val)
                        if date_val:
                            val = date_val
                    except:
                        pass
                attributes.append({"label": k, "value": val})

        return attributes

    def get_latest_cti(self):
        sql = '''
        MATCH
        {class:AttackPattern, as:a}.outE(){as:a2t}.inV()
        {class:V, as:t}
        RETURN a.key, a.title, a.type, a.created, a.modified, t.key, t.title, a2t.@class, a.@class, t.@class
        '''
        graph = {
            "nodes": [],
            "links": [],
            "index": []
        }
        r = self.client.command(sql)
        for i in r:
            o = i.oRecordData
            if o["a_key"] not in graph["index"]:
                graph["nodes"].append(self.create_d3_node(
                    id=o["a_key"],
                    n_type=o["a_@class"],
                    title=o["a_title"],
                    created=o["a_created"],
                    modified=o["a_modified"]
                ))
                graph["index"].append(o["a_key"])
            if o["t_key"] not in graph["index"]:
                graph["nodes"].append(self.create_d3_node(
                    id=o["t_key"],
                    n_type=o["t_@class"],
                    title=o["t_title"]
                ))
                graph["index"].append(o["t_key"])
            rel = {"source": o["a_key"], "target": o["t_key"], "label": o["a2t_@class"]}
            if(rel not in graph["links"]):
                graph['links'].append(rel)
        return graph

    def create_d3_node(self, **kwargs):
        node = {
            "id": None,
            "data": [],
            "n_type": None
        }
        if "id" in kwargs.keys():
            node["id"] = kwargs["id"]
        if "n_type" in kwargs.keys():
            node["n_type"] = kwargs["n_type"]
        for k in kwargs.keys():
            if k not in ["id", "n_type"]:
                node["data"].append({"label": k, "value": kwargs[k]})
                node[k] = kwargs[k]

        return node
