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
from apiserver.blueprints.osint.geo import get_location
from requests_oauthlib import OAuth1
import urllib3
urllib3.disable_warnings()


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
        self.OSINT_index = { "Profile": {}, "Post": {}, "Location": {}, "Tag": {}}

    @staticmethod
    def ucdp_conflict_type(row):

        if row['type_of_violence'] == str(1):
            return "State-based Conflict"
        elif row['type_of_violence'] == str(2):
            return "Non-state Conflict"
        else:
            return "One-sided Conflict"

    def fill_locations(self, locations):
        for index, row in locations.iterrows():
            self.create_node(
                class_name="Location",
                Category="City",
                title="%s %s" % (row['city_ascii'], row['country']),
                city=row['city_ascii'],
                country=row['country'],
                description="%s %s %s located at %s %s in the province %s" % (
                    row['city_ascii'], row['country'], row['iso3'], row['lat'], row['lng'], row['province']),
                icon=self.ICON_LOCATION,
                Latitude=row['lat'],
                Longitude=row['lng'],
                iso3=row['iso3'],
                iso2=row['iso2'],
                population=row['pop'],
                source="Wikipedia"
            )

    def basebook_locations_init(self):
        if not self.basebook:
            self.basebook = pd.ExcelFile(os.path.join(self.datapath, 'Base_Book.xlsx'))
        locations = self.basebook.parse('Locations')
        # Start a thread for the long running process and send a message back with the summary
        t = threading.Thread(
            target=self.fill_locations,
            kwargs={
                "locations": locations
            })
        t.start()
        return "Started extracting %d locations from the Basebook" % locations['city'].size

    def get_location_lookup(self, location_name="Berlin"):
        """
        Get the location from the database or if it doesn't exist, pull from OpenStreetMap
        :param location_name:
        :return:
        """
        r = self.client.command('''
        SELECT @rid as key, * FROM Location WHERE [description] LUCENE "(%s)" LIMIT 1
        ''' % location_name)
        if len(r) == 0:
            url = "https://nominatim.openstreetmap.org/search/%s?format=json&addressdetails=1" % location_name
            r = requests.request(method="GET", url=url).json()
            if len(r) > 0:
                # Get the first result TODO get the best result
                r = r[0]
                r = self.create_node(
                    class_name="Location",
                    Category="City",
                    title="%s %s" % (r['address']['city'], r['address']['country']),
                    city=r['address']['city'],
                    country=r['address']['country'],
                    Latitude=r['lat'],
                    Longitude=r['lon'],
                    description="%s located at %s %s" % (r['display_name'], r['lat'], r['lon']),
                    icon=self.ICON_LOCATION,
                    source="OpenStreets"
                )['data']
        else:
            r = self.format_node(**r[0].oRecordData)
            r['key'] = r['key'].get_hash()
        return r

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

    def get_suggestion_items(self, searchterms=""):
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
        i = 1
        lucene_q = ""
        for q in searchterms.split(" "):
            q = q.strip().lower()
            if len(q) > 1:
                if i == len(searchterms.split(" ")):
                    lucene_q = "+%s*" % q
                else:
                    lucene_q = "+%s* " % q
            i+=1
        i = 0
        for m in self.models.keys():
            sql = sql + '''
            $%s = (SELECT @rid as key, @class, * FROM %s WHERE [description] LUCENE "(%s)" LIMIT 10),\n
            ''' % (m[0:4].lower(), m, lucene_q)
            union = union + "$%s" % m[0:4].lower()
            if i != len(self.models.keys())-1:
                union = union + ", "
            else:
                union = union + ")"
            i+=1

        sql = sql + union
        try:
            r = self.client.command(sql)
            click.echo('[%s_OSINTserver_get_suggestion_items] Getting suggestions on sql: %s' % (get_datetime(), sql))
        except Exception as e:
            click.echo('[%s_OSINTserver_get_suggestion_items] Error making call: %s\n%s' % (get_datetime(), str(e), sql))
            r = []
        suggestionItems = []
        for i in r:
            s_item = {
                "NODE_KEY": i.oRecordData["key"].get_hash(),
                "NODE_TYPE": i.oRecordData["class"],
                "ATTRIBUTES": [{}]
            }
            if "Category" in i.oRecordData.keys():
                s_item["NODE_NAME"] = i.oRecordData["Category"]
            elif "FirstName" in i.oRecordData.keys() and "LastName" in i.oRecordData.keys():
                s_item["NODE_NAME"] = i.oRecordData["FirstName"] + " " + i.oRecordData["LastName"]
            elif "title" in i.oRecordData.keys():
                s_item["NODE_NAME"] = i.oRecordData["title"]
            elif "description" in i.oRecordData.keys():
                s_item["NODE_NAME"] = i.oRecordData['description'][:24] + "..."
            else:
                s_item["NODE_NAME"] = i.oRecordData["NODE_TYPE"] + " " + i.oRecordData["NODE_KEY"]
            for att in i.oRecordData:
                # Ensure no edges or duplicates of key and class are ncluded
                if att not in ["key", "class"] and att[0:4] != "out_" and att[0:3] != "in_":
                    s_item["ATTRIBUTES"][0][att] = i.oRecordData[att]

            suggestionItems.append(s_item)
            '''   
            try:
                suggestionItems.append({
                    "NODE_KEY": i.oRecordData["key"].get_hash(),
                    "NODE_TYPE": i.oRecordData["class"],
                    "NODE_NAME": i.oRecordData["title"]
                })
            except Exception as e:
                if e.args[0] == "title":
                    suggestionItems.append({
                        "NODE_KEY": i.oRecordData["key"].get_hash(),
                        "NODE_TYPE": i.oRecordData["class"],
                        "NODE_NAME": i.oRecordData["Ext_key"]
                    })
                else:
                    suggestionItems.append({
                        "NODE_KEY": i.oRecordData["key"].get_hash(),
                        "NODE_TYPE": i.oRecordData["class"],
                        "NODE_NAME": "Unknown title for " + i.oRecordData["class"]
                    })
                    '''

        return suggestionItems

    def get_most_connected_references(self, description):
        sql = '''
        select Ext_key, out() from Object where description containstext("%s") and out().size() > 3
        ''' % description
        r = self.client.command(sql)
        return r

    def get_most_connected_vulnerabilities(self):
        sql = '''
        select Ext_key, in().size() from Vulnerability where in().size() > 10
        '''
        r = self.client.command(sql)
        return r

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
        source_keys = []
        for row in data:
            s = row['source']
            source_node = self.create_node(
                class_name="Organization",
                Category="Information Source",
                Name=s,
                title="%s information source" % s,
                icon=self.ICON_INFO_SOURCE,
                description="Organization from ACLED. %s" % s,
                Source="ACLED"
            )
            source_keys.append(source_node["data"]["key"])
            StartDate = change_if_date(row['event_date'])
            event_node = self.create_node(
                class_name="Event",
                icon=self.ICON_CONFLICT,
                Category=row["event_type"],
                Ext_key=row['data_id'],
                title="%s %s, %s" % (row["event_type"], row['country'], row['event_date']),
                description=("Headline: %s Article: %s" % (
                    row['event_date'],
                    row['notes'])).replace("'", ""),
                StartDate=StartDate,
                EndDate=StartDate,
                Deaths=row['fatalities'],
                Origin=clean(row['source']),
                Civilians=row['fatalities'],
                Source="ACLED"
            )
            self.create_edge_new(
                edgeType="References", fromNode=source_node["data"]["key"], toNode=event_node["data"]["key"])
            side_a_node = self.create_node(
                class_name="Organization",
                description="Organization %s %s" % (row['actor1'], row['assoc_actor_1']),
                title="Organization %s" % row['actor1'],
                Ext_key=row['actor1'],
                Name=row['actor1'],
                icon=self.ICON_ORGANIZATION,
                Source="ACLED"
            )
            self.create_edge_new(
                edgeType="Included", fromNode=event_node["data"]["key"], toNode=side_a_node["data"]["key"])
            side_b_node = self.create_node(
                class_name="Organization",
                description="Organization %s %s" % (row['actor2'], row['assoc_actor_2']),
                title="Organization %s" % row['actor2'],
                Ext_key=row['actor2'],
                Name=row['actor2'],
                icon=self.ICON_ORGANIZATION,
                Source="ACLED"
            )
            self.create_edge_new(
                edgeType="Included", fromNode=event_node["data"]["key"], toNode=side_b_node["data"]["key"])
            location_node = self.create_node(
                class_name="Location",
                Category="Conflict site",
                description="%s %s %s %s" % (row['admin1'], row['admin2'], row['country'], row['region']),
                Latitude=row['latitude'],
                Longitude=row['longitude'],
                title="%s" % row['country'],
                country=row['country'],
                icon=self.ICON_LOCATION
            )
            self.create_edge_new(
                edgeType="LocatedAt", fromNode=event_node["data"]["key"], toNode=location_node["data"]["key"])

        return "Graphed %d ACLED events" % len(data)

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
        click.echo()
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
                self.create_edge_new(
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
            self.create_edge_new(
                fromNode=side_a_key,
                toNode=event_node['data']['key'],
                edgeType="Involves"
            )
            graph_build['lines'].append({"from": side_a_key, "to": event_node['data']['key'], "title": "Event"})
            self.create_edge_new(
                fromNode=side_b_key,
                toNode=event_node['data']['key'],
                edgeType="Involves"
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
            self.create_edge_new(
                fromNode=event_node['data']['key'],
                toNode=location,
                edgeType="OccurredAt"
            )
            graph_build['lines'].append({"from": event_node['data']['key'], "to": location, "title": "OccurredAt"})
            # Wire up the Organizations to the Location (ReportedAt)
            self.create_edge_new(
                fromNode=side_a_key,
                toNode=location,
                edgeType="OccurredAt"
            )
            graph_build['lines'].append({"from": side_a_key, "to": location, "title": "OccurredAt"})
            self.create_edge_new(
                fromNode=side_b_key,
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
        A Monitor consists of a channel and a searchterm. For example, Twitter can be a channel and vulnerability can be
        the search term. The Monitor is SubscribedTo by a user. When creating a monitor, the function first checks if a
        user exists in the DB with that name. If not a representation is created of the user and then the same is checked
        for the monitor channel. Last, the search term is checked and once all entities have been created if they didn't
        exist already, the relations are created to ensure the user gets updates from the monitor.
        insert into Monitor (key, name, searchValue, type, user, description) values (sequence('idseq').next(),
            "Twitter", null, "Channel", "SocAnalyst", "Hashtags, User timelines, and location based search") return @this.key
        insert into Monitor (key, name, searchValue, type, user, description) values (sequence('idseq').next(),
            "Twitter", "vulnerability", "Search", "SocAnalyst", "hashtag") return @this.key
        insert into Monitor (key, name, searchValue, type, user, description) values (sequence('idseq').next(),
            "Twitter", "realDonaldTrump", "Search", "SocAnalyst", "user") return @this.key

        :param kwargs:
        :return:
        '''
        # Check if the user exists within OSINT
        if len(self.client.command('''select @rid from User where userName = "%s"''' % userName)) == 0:
            self.create_node(class_name="User", userName=userName)

        # Next check if the channel exists
        message = "%s adding channel %s with search %s." % (userName, name, searchValue)
        monitor_channel = self.client.command('''
        select @rid from Monitor where type = 'Channel' and name = '%s'
        ''' % (name))
        if len(monitor_channel) > 0:
            # Set the monitor channel key for relating to the searchTerm and user
            monitor_channel = monitor_channel[0].oRecordData["rid"]
            # Check if the monitor is subscribed to be the user
            sql = '''
            match
            {class:Monitor, as:m, where: (@rid = %s)}.in("SubscribesTo")
            {class:User, as:u, where: (userName = '%s')}
            return m
            ''' % (name, userName)
            if len(self.client.command(sql)) == 0:
                message += "\n%s exists but user is now newly subscribed to it. " % name
                self.client.command('''
                create edge SubscribesTo from 
                (select from User where userName = '%s') to 
                (select from %s )
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
            (select from %s )
            ''' % (userName, monitor_channel))

        # If the monitor is a search
        if type == "Search":
            # Check if it exists
            monitor_search = self.client.command('''
            select @rid as key, searchValue, description, icon, name, title, type, user
            from Monitor where name = "%s" and searchValue = "%s" and description = "%s"
            ''' % (name, searchValue, description))
            if len(monitor_search) == 0:
                # If not create it and relate it to the channel and to SocAnalyst
                message += "\n%s doesn't exist so has been created with user subscribed. " % searchValue
                monitor_search = self.create_node(
                    class_name="Monitor",
                    name=name,
                    searchValue=searchValue,
                    type="Search",
                    description=description
                )
                # Relate to the channel
                self.client.command('''
                create edge SearchesOn from 
                (select from %s) to 
                (select from %s )
                ''' % (monitor_channel, monitor_search["data"]["key"]))
                # Make the user subscription relation
                self.client.command('''
                create edge SubscribesTo from 
                (select from User where userName = '%s') to 
                (select from %s)
                ''' % (userName, monitor_search["data"]["key"]))
                # Make the user subscription relation
                self.client.command('''
                create edge SubscribesTo from 
                (select from User where userName = 'SocAnalyst') to 
                (select from %s)
                ''' % (monitor_search["data"]["key"]))
            else:
                monitor_search = monitor_search[0].oRecordData
                monitor_search["key"] = monitor_search["key"].get_hash()
                sql = '''
                match
                {class:Monitor, as:m, where: (@rid = %s)}.in("SubscribesTo")
                {class:User, as:u, where: (userName = '%s')}
                return m
                ''' % (monitor_search["key"], userName)
                if len(self.client.command(sql)) == 0:
                    message += "%s is now subscribed to %s. " % (userName, searchValue)
                    # Make the user subscription relation
                    self.client.command('''
                    create edge SubscribesTo from 
                    (select from User where userName = '%s') to 
                    (select from %s )
                    ''' % (userName, monitor_search["key"].get_hash()))
                else:
                    message += "%s is already subcribed to %s." % (userName, searchValue)

        return {"message": message, "monitor": monitor_search}

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
        key = self.create_node(
            class_name="Process",
            category="Report",
            pid=pid,
            name=kwargs["name"],
            started=get_datetime(),
            summary=kwargs["summary"]
        )['data']['key']
        return key

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
        )['data']['key']

        self.client.command('''
        create edge UpdateTo from 
        (select from %s) to 
        (select from %s)
        ''' % (update_key, kwargs['pid']))

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

        return update_key

    def get_user_monitor(self, userName="SocAnalyst"):
        monitors = []
        sql = '''
        match
        {class:User, where: (userName = '%s')}.out("SubscribesTo")
        {class:Monitor, as:s}.in("SearchesOn")
        return s.@rid as key, s.description as label, s.searchValue as value, s.name as source
        ''' % (userName)
        for i in self.client.command(sql):
            i.oRecordData['key'] = i.oRecordData['key'].get_hash()
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
        return s.@rid as key, s.description, s.searchValue, s.type
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
                        get_datetime(), m))
            elif m.oRecordData["s_description"] == "hashtag":
                hashtags_monitor.append(m)
            elif m.oRecordData["s_description"] == "user":
                user_monitor.append(m)

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
            self.update_report(pid=pid, summary="Getting users", name=name)
            for u in kwargs["user_monitor"]:
                self.get_twitter(
                    number_of_tweets=100,
                    username=u.oRecordData['s_searchValue'],
                    monitor=u.oRecordData['key'].get_hash()
                )
            self.update_report(pid=pid, summary="Getting locations", name=name)
            for l in kwargs["locations_monitor"]:
                self.get_twitter(
                    number_of_tweets=100,
                    latitude=l["lat"],
                    longitude=l["lon"],
                    monitor=l.oRecordData['key'].get_hash()
                )
            self.update_report(pid=pid, summary="Getting hashtags", name=name)
            for l in kwargs["hashtags_monitor"]:
                self.get_twitter(
                    number_of_tweets=100,
                    hashtag=l,
                    monitor=l.oRecordData['key'].get_hash()
                )
            self.update_report(ended=True, pid=pid,
                               name=name, summary="Complete with requests. Sleeping for %d minutes" % minutes)
            time.sleep(60 * minutes)

    def get_twitter(self, number_of_tweets=100, username=None, monitor=None, max_id=None, request=0, hashtag=None,
                    latitude=None, longitude=None, radius=None):
        """
        :param number_of_tweets:
        :param username:
        :param monitor:
        :param max_id:
        :param request:
        :param hashtag:
        :param latitude:
        :param longitude:
        :param radius:
        :return:
        """
        client_key = self.TWITTER_AUTH['client_key']
        client_secret = self.TWITTER_AUTH['client_secret']
        token = self.TWITTER_AUTH['token']
        token_secret = self.TWITTER_AUTH['token_secret']
        oauth  = OAuth1(client_key, client_secret, token, token_secret)
        locationsChecked = False
        message = "Retrieved twitter API: "

        if username:
            if username != "":
                api_url  = "%s/statuses/user_timeline.json?" % self.base_twitter_url
                api_url += "screen_name=%s&" % username
                api_url += "count=%d" % number_of_tweets
                click.echo('[%s_OSINT_get_twitter] Getting username with url: %s' % (get_datetime(), api_url))
                if max_id is not None:
                    api_url += "&max_id=%d" % max_id
                # send request to Twitter
                response = requests.get(api_url, auth=oauth, verify=False) # if ssl error use verify=False
                request+=1
                tweets = self.responseHandler(response, username)
                if response.status_code != 401:
                    message = self.graph_twitter(tweets=tweets, monitor=monitor)
                else:
                    message = " %s protects tweets" % username

        if hashtag:
            if hashtag != "":
                api_url = "%s/search/tweets.json?" % self.base_twitter_url
                api_url += "q=%%23%s&result_type=recent" % hashtag
                if latitude and longitude and latitude != "":
                    api_url += "&geocode=%f,%f" % (float(latitude), float(longitude))
                    if radius:
                        api_url += ",%dkm&count=%s" % (int(radius), number_of_tweets)
                    else:
                        api_url += ",5km&count=%s" % number_of_tweets
                    locationsChecked = True
                click.echo('[%s_OSINT_get_twitter] Getting hashtag: %s' % (get_datetime(), api_url))
                response = requests.get(api_url, auth=oauth, verify=False)
                tweets = self.responseHandler(response, hashtag)
                message = self.graph_twitter(tweets=tweets['statuses'], monitor=monitor)

        if latitude and longitude and not locationsChecked:
            if latitude != "" and longitude != "":
                api_url = "https://api.twitter.com/1.1/search/tweets.json?q=&geocode=%f,%f" % (
                    float(latitude), float(longitude))
                if radius:
                    if radius != "":
                        api_url += ",%dkm&count=%s" % (int(radius), number_of_tweets)
                    else:
                        api_url += ",5km&count=%s" % number_of_tweets
                click.echo('[%s_OSINT_get_twitter] Getting location with url: %s' % (get_datetime(), api_url))
                response = requests.get(api_url, auth=oauth, verify=False)
                tweets = self.responseHandler(response, "%s, %s" % (latitude, longitude))
                message = self.graph_twitter(tweets=tweets['statuses'], monitor=monitor)
        click.echo('[%s_OSINT_get_twitter] Complete with request' % (get_datetime()))
        return message

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
        for k in ["Members", "Owners", "groups"]:
            if k not in kwargs.keys():
                kwargs[k] = []
        for k in ["graphName", "Classification"]:
            if k not in kwargs.keys():
                kwargs[k] = randomString(6)

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

    def acled(self, **kwargs):



        return

    def graph_twitter(self, **kwargs):
        """
        Using the basic structure below, create a relationship between a user and all the tweets. Extract Hashtags
        from tweets where applicable. Extract Locations where applicable.
        :param kwargs:
        :return:
        """
        new_tweets = new_users = 0
        index = []
        if "tweets" in kwargs.keys():
            click.echo('[%s_OSINT_graph_twitter] Graphing %s tweets' % (get_datetime(), len(kwargs["tweets"])))
            for t in kwargs['tweets']:
                # Check if the tweet is in the OSINT index. If not add the record
                twt_id = "TWT_%s" % t['id']
                hash_tags_str = ""
                url = None
                if twt_id not in self.OSINT_index["Post"].keys():
                    try:
                        if len(t['entities']['urls']) == 0:
                            if 'retweeted_status' in t.keys():
                                if len(t['retweeted_status']['entities']['urls']) > 0:
                                    url = t['retweeted_status']['entities']['urls'][0]['url']
                            elif 'extended_entities' in t.keys():
                                url = t['extended_entities']['media'][0]['url']
                        else:
                            url = t['entities']['urls'][0]['url']
                    except:
                        click.echo(
                            '[%s_OSINT_graph_twitter] Could not get url from %s' % (get_datetime(), t))

                    node = {
                        "class_name": "Post",
                        "title": "Tweet from " + t['user']['name'],
                        "status": random.choice(self.ICON_STATUSES),
                        "icon": self.ICON_TWEET,
                        "group": "Posts",
                        "attributes": [
                            {"label": "Created", "value": t['created_at']},
                            {"label": "Category", "value": "Post"},
                            {"label": "Text", "value": t['text']},
                            {"label": "description", "value": "%s tweeted %s" % (t['user']['name'], t['text'])},
                            {"label": "Language", "value": t['lang']},
                            {"label": "Re_message", "value": t['retweet_count']},
                            {"label": "Favorite", "value": t['favorite_count']},
                            {"label": "url", "value": url},
                            {"label": "Geo", "value": t['coordinates']},
                            {"label": "Hashtags", "value": hash_tags_str},
                            {"label": "Screen_name", "value": t['user']['screen_name'].lower()},
                            {"label": "Ext_key", "value": twt_id},
                            {"label": "Source", "value": "Twitter"}
                        ]
                    }
                    twt_node = self.create_node(**node)
                    if "Node exists" not in twt_node["message"]:
                        new_tweets += 1
                        self.OSINT_index["Post"][twt_id] = twt_node["data"]["key"]
                    twt_node = twt_node["data"]["key"]

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
                                "class_name": "Tag",
                                "Category": "Hashtag",
                                "title": "#%s" % ht['text'],
                                "icon": self.ICON_HASHTAG,
                                "group": 4,
                                "attributes": [
                                    {"label": "Text", "value": ht['text']},
                                    {"label": "description", "value": "Hashtag %s" % ht['text']},
                                    {"label": "Source", "value": "Twitter"}
                                ]
                            }
                            ht_node = self.create_node(**node)["data"]["key"]
                            self.create_edge_new(edgeType="Included", toNode=ht_node, fromNode=twt_node)
                            if kwargs['monitor']:
                                self.create_edge_new(edgeType="References", toNode=ht_node, fromNode=kwargs['monitor'])
                    # Process Locations
                    if "place" in t.keys():
                        if t['place']:
                            if len(t['place']['bounding_box']['coordinates'][0]) > 0:
                                loc_id = "%s" % t['place']['id']
                                if loc_id not in self.OSINT_index["Location"].keys():
                                    loc_node = {
                                        "class_name": "Location",
                                        "title": t['place']['name'],
                                        "status": random.choice(self.ICON_STATUSES),
                                        "icon": self.ICON_LOCATION,
                                        "group": "Locations",
                                        "attributes": [
                                            {"label": "Re_message", "value": t['place']['url']},
                                            {"label": "Country", "value": t['place']['country']},
                                            {"label": "Ext_key", "value": loc_id},
                                            {"label": "Longitude", "value": t['place']['bounding_box']['coordinates'][0][0][0]},
                                            {"label": "Latitude", "value": t['place']['bounding_box']['coordinates'][0][0][1]},
                                            {"label": "Type", "value": t['place']['place_type']},
                                            {"label": "Source", "value": "Twitter"},
                                            {"label": "description", "value": "%s %s %s,%s" % (
                                                t['place']['country'],
                                                t['place']['place_type'],
                                                t['place']['bounding_box']['coordinates'][0][0][0],
                                                t['place']['bounding_box']['coordinates'][0][0][1]
                                            )}
                                        ]
                                    }
                                    loc_node = self.create_node(**loc_node)["data"]["key"]
                                    self.OSINT_index["Location"][loc_id] = loc_node
                                    self.create_edge_new(edgeType="TweetedFrom", toNode=loc_node, fromNode=twt_node)
                                    if kwargs['monitor']:
                                        self.create_edge_new(edgeType="References", toNode=loc_node,
                                                             fromNode=kwargs['monitor'])

                                else:
                                    print("Need to get that Ext_key and return the node formatted for graph")

                    # Process the User by creating an entity. Then create a line from the User to the Tweet
                    user_id = "TWT_%s" % t['user']['id']
                    usr_node = {
                        "class_name": "Profile",
                        "title": t['user']['name'],
                        "status": "Alert",
                        "group": "Profiles",
                        "icon": self.ICON_TWITTER_USER,
                        "attributes": [
                            {"label": "Screen_name", "value": t['user']['screen_name'].lower()},
                            {"label": "Category", "value": "Profile"},
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
                            {"label": "Ext_key", "value": user_id},
                            {"label": "url", "value": t['user']['url']},
                            {"label": "Source", "value": "Twitter"}
                        ]
                    }
                    usr_node = self.create_node(**usr_node)
                    if "Node exists" not in usr_node["message"]:
                        self.OSINT_index["Post"][twt_id] = usr_node["data"]["key"]
                        new_users += 1
                    usr_node = usr_node["data"]["key"]
                    # Check if there is a location
                    Location = None
                    if t["user"]["location"] != "":
                        Location = get_location(t["user"]["location"], self)
                        if Location:
                            if "key" in Location.keys():
                                if Location["key"] not in index:
                                    index.append(Location["key"])
                                self.create_edge_new(edgeType="LocatedAt", fromNode=twt_node, toNode=Location["key"])

                    # Else get the user_node
                    self.create_edge_new(edgeType="Tweeted", toNode=twt_node, fromNode=usr_node)
                    if kwargs['monitor']:
                        self.create_edge_new(edgeType="References", toNode=twt_node,
                                             fromNode=kwargs['monitor'])

        elif "user" in kwargs.keys():
            user_id = "TWT_%s" % kwargs['user']['id']
            node = ({
                "class_name": "Profile",
                "title": kwargs['user']['name'],
                "status": "Alert",
                "group": "Profiles",
                "icon": self.ICON_TWITTER_USER,
                "attributes": [
                    {"label": "Category", "value": "Profile"},
                    {"label": "Screen_name", "value": kwargs['user']['screen_name'].lower()},
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
                    {"label": "url", "value": kwargs['user']['url']},
                    {"label": "Ext_key", "value": user_id},
                    {"label": "Source", "value": "Twitter"}
                ]
            })
            node = self.create_node(**node)
            if "Node exists" not in node["message"]:
                new_users += 1
            self.OSINT_index["Profile"][user_id] = node["data"]["key"]
        message = '[%s_OSINT_graph_twitter] Complete with %s new users and %s new tweets' % (
            get_datetime(), new_users, new_tweets)
        click.echo(message)
        return message

    def refresh_indexes(self):
        """
        Get the Ext Keys of Posts, Users, and Locations to prevent unecessary lookups
        :return:
        """
        try:
            for osi in self.OSINT_index:
                click.echo('[%s_OSINT_refresh_indexes] Filling %s' % (get_datetime(), osi))
                sql = '''
                select @rid, Ext_key from %s where Ext_key != ""
                 ''' % (osi)
                r = self.client.command(sql)
                for i in r:
                    self.OSINT_index[osi][i.oRecordData["Ext_key"]] = i.oRecordData['rid'].get_hash()
            click.echo('[%s_OSINT_refresh_indexes] Indexes complete' % (get_datetime()))
        except Exception as e:
            click.echo('[%s_OSINT_refresh_indexes] Error setting up indexes. %s' % (get_datetime(), str(e)))

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

    def get_bulk_users(self, user_ids, sourceID, reltype, username):
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
            # Create the node in the database
            self.graph_twitter(user=user)
            # Create the edge based on the newly indexed node from the graph process
            self.create_edge_new(
                fromNode=sourceID, toNode=self.OSINT_index["Profile"]["TWT_%s" % user["id"]], edgeType=reltype)

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
        Get the friends of a twitter user given a username. Followers results in too many users for value so friends
        are the preferred meaningful detailed requirement while followers can be used on just the number. If followers
        are required they can be easily added into the options.
        Store the relationships as associates' IDS which can then be looked up in bulk of 100
        User 2 internal functions to process the URL instead of 2 steps each time

        :param username:
        :return:
        """
        # Set up the API call
        associate_list = []
        if username:
            # Get the userID from the index
            r = self.client.command("select from index:Profile_Screen_name where key = '%s' " % username.lower())
            if len(r) < 1:
                # If there is no userID get the user through the normal timeline request
                self.get_twitter(username=username)
            else:
                userKey = r[0].oRecordData["rid"]

            # Can add followers but often results in millions of users
            for r in ["friends"]:
                click.echo('[%s_OSINT_get_associates] Getting %s of %s' % (get_datetime(), r, username))
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
                new_users = existing_users = 0
                user_ids = []
                # Use the OSINT index to check if there have been any additions and not to get those users who are already in the index
                # Get EntityNode will create the user via the graph_twitter function.
                for user_id in associate_list:
                    user_idA = "TWT_%s" % user_id
                    if user_idA not in self.OSINT_index["Profile"].keys() and user_id not in user_ids:
                        new_users+=1
                        # Add the original ID to create a bulk request
                        user_ids.append(user_id)
                        if len(user_ids) == 100:
                            click.echo('[%s_OSINT_get_associates] 100 %s limit for entity. Sending bulk request to Twitter' % (
                                get_datetime(), r))
                            self.get_bulk_users(user_ids, userKey, r, username)
                            i = 0
                            del user_ids[:]
                        if i == len(associate_list) - 1:
                            print("[*] %d %s for entity info. Request to Twitter." % (len(user_ids), r))
                            self.get_bulk_users(user_ids, userKey, r, username)
                        i += 1
                    else:
                        existing_users+=1
                        self.create_edge_new(fromNode=userKey, toNode=self.OSINT_index["Profile"][user_idA], edgeType=r)
        message = '[%s_OSINT_get_associates] Graphed %s new and %s exisiting users with edges to %s' % (
            get_datetime(), new_users, existing_users, username)
        click.echo(message)
        return message

    def get_cve(self):
        """
        Get the full bulk from MITRE for vulnerability data. Use a timestamp based on the day and save the bulk CSV to
        the server. The timestamp can be used to check if the daily bulk was already downloaded earlier.
        Once the CSV is downloaded, change the results into a Pandas dataframe and start a thread that extracts the the
        data into a graph. Use Vulnerability references which are separated by "|" pipes.
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
        click.echo('[%s_OSINT_cve] Complete with raw data cleaning. Starting Extraction' % (get_datetime()))
        df = pd.DataFrame.from_dict(df)
        #self.graph_cve(df=df)
        t = threading.Thread(
            target=self.graph_cve,
            kwargs={
                "df": df,
            })
        t.start()

    def graph_cve(self, df=pd.DataFrame()):
        """
        Thread that is called to start the long extraction process
        :param df:
        :return:
        """
        pid = "CVE_graph_%s" % randomString(8)
        self.create_node(**{
            "class_name": "Process",
            "category": "Graphing",
            "name": "CVE",
            "started": get_datetime(),
            "pid": pid
        })
        class_name = "Vulnerability"
        source = "MITRE"
        i = 0
        c = 0
        pct = .1
        new_nodes = new_references = 0
        indexes = {}
        for index, row in df.iterrows():
            if i > df.shape[0]*pct:
                i = 0
                c+=1
                update = ('[%s_OSINT_cve] Completed %f percent. %d Vuls, %d Refs, %d Indexes' % (
                    get_datetime(), (index/df.shape[0])*100, new_nodes, new_references, len(indexes.keys())))
                click.echo(update)
                self.client.command('''
                update Process set summary = '%s' where pid = '%s'
                ''' % (update, pid))
            i+=1
            if 'Comments\n' in row.keys():
                comments = row['Comments\n']
            elif 'Comments' in row.keys():
                comments = row['Comments']
            else:
                comments = ""
            try:
                # Create the CVE node and then make relations to any entities if they don't exist
                cve_node = self.create_node(**{
                    "class_name": class_name,
                    "source": source,
                    "Ext_key": row["Name"],
                    "description": row["Description"] + " " + comments,
                    "labels": row["References"], # Make relations to each as a reporter
                    "votes": row["Votes"],
                    "status": row["Status"],
                    "phase": row["Phase"]
                })
                if cve_node["message"] != "duplicate blocked":
                    new_nodes+=1
                cve_node = cve_node["data"]
                references = [r.strip() for r in row["References"].split("|")]
                for r in references:
                # Check if in the index
                    ref_node = self.create_node(**{
                        "class_name": "Object",
                        "description": "Reference from CVE %s" % r,
                        "Category": "Vulnerability Reference",
                        "Ext_key": r,
                        "source": "MITRE"
                    })
                    if ref_node["message"] != "duplicate blocked":
                        new_references+=1
                    ref_node = ref_node["data"]
                    self.create_edge_new(
                        fromNode=ref_node["key"], edgeType="References", toNode=cve_node["key"]
                    )
            except Exception as e:
                click.echo('[%s_OSINT_cve] Error %s' % (get_datetime(), str(e)))
                pass

        msg = '[%s_OSINT_cve] Complete with graphing CVE at index %d' % (get_datetime(), index)
        click.echo(msg)
        self.client.command('''
        update Process set ended = '%s', description = '%s' where pid = '%s'
        ''' % (get_datetime(), msg, pid))

    def get_poisonivy(self):
        """
        Get the latest dump from the CTI url. The current URL is set to oasis github which delivers a small sample
        using the STIX model. The expected JSON from the URL is in a format of nodes with STIX 12 entity types and
        edges including relationships and sightings. The function calls graph_poisonivy to extract the JSON into a
        graph form and returns a message prior to starting that thread.
        nodes:
            "type": "campaign",
            "id": "campaign--8e2e2d2b-17d4-4cbf-938f-98ee46b3cd3f",
            "created": "2016-04-06T20:03:00.000Z",
            "name": "Green Group Attacks Against Finance",
            "description": "Campaign by Green Group against targets in the financial services sector."
        edges:

            "type": "sighting",
            "id": "sighting--ee20065d-2555-424f-ad9e-0f8428623c75",
            "created_by_ref": "identity--f431f809-377b-45e0-aa1c-6a4751cae5ff",
            "created": "2016-04-06T20:08:31.000Z",
            "modified": "2016-04-06T20:08:31.000Z",
            "sighting_of_ref": "indicator--8e2e2d2b-17d4-4cbf-938f-98ee46b3cd3f"

        :return:
        """
        source = "%s_poisonivy.json" % get_datetime()[:10]
        path = os.path.join(self.datapath, source)
        url = 'https://oasis-open.github.io/cti-documentation/examples/example_json/poisonivy.json'
        click.echo('[%s_OSINT_get_poisonivy] Getting %s' % (get_datetime(), url))
        data = self.get_url(url, path)
        if data:
            data = json.loads(data.content)
            with open(path, 'w') as fp:
                json.dump(data, fp)
        else:
            with open(path) as fp:
                data = json.load(fp)

        message = '[%s_OSINT_get_poisonivy] Getting %s' % (get_datetime(), url)
        click.echo(message)
        t = threading.Thread(
            target=self.graph_poisonivy,
            kwargs={
                "data": data
            })
        t.start()
        return message

    def graph_poisonivy(self, data):
        """
        Extract the expected format of CTI data documented at https://oasis-open.github.io/cti-documentation/stix/intro
        :param data:
        :return:
        """
        click.echo('[%s_OSINT_graph_poisonivy] Starting graph for poisonivy extract of %s' % (
            get_datetime(), len(data["objects"])))
        graph = {
            "nodes": [],
            "lines": [],
            "index": {}
        }
        for i in data['objects']:
            if i['type'] not in ["relationship", "sighting"]:
                node_prep = {
                    "class_name": i['type'].capitalize()
                }
                if node_prep["class_name"].lower() == "attack-pattern":
                    node_prep["class_name"] = "AttackPattern"
                elif node_prep["class_name"].lower() == "course-of-action":
                    node_prep["class_name"] = "CourseOfAction"
                for k in i.keys():
                    if k not in ["type"]:
                        if k in ["object_marking_refs", "labels", "sectors"]:
                            val = ', '.join(i[k])
                        elif k in ["kill_chain_phases"]:
                            for kcp in i["kill_chain_phases"]:
                                kcp_node = {
                                    "name": kcp["kill_chain_name"],
                                    "phase": kcp["phase_name"]
                                }
                                graph["nodes"].append(kcp_node)
                                graph["lines"].append({
                                    "to": node_prep, "from": kcp_node["name"]
                                })

                        elif k in ["first_seen", "modified", "created"]:
                            val = change_if_date(i[k])
                        else:
                            val = i[k]
                        node_prep[k] = val

            elif i['type'] == "relationship":
                graph["lines"].append(i)
            if node_prep["class_name"].lower() not in ["marking-definition"]:
                n = self.create_node(**node_prep)
                graph["nodes"].append(n["data"])
                graph["index"][i["id"]] = n["data"]["key"]
            else:
                graph["nodes"].append(node_prep)
        click.echo('[%s_OSINT_graph_poisonivy] Complete with %s entities. Starting %s edges.' % (
            get_datetime(), len(graph["nodes"]), len(graph["lines"])))
        for r in graph["lines"]:
            if "to" in r.keys():
                if type(r["to"]) == dict:
                    toNode = graph["index"][r["to"]["id"]]
                else:
                    if r["to"] in graph["index"].keys():
                        toNode = graph["index"][r["to"]]
                    else:
                        toNode = self.create_node(
                            class_name="Object", Ext_key=r["to"], description="CTI %s" % r["to"])["data"]["key"]
                if type(r["from"]) == dict:
                    fromNode = graph["index"][r["from"]["id"]]
                else:
                    if r["from"] in graph["index"].keys():
                        fromNode = graph["index"][r["from"]]
                    else:
                        fromNode = self.create_node(
                            class_name="Object", Ext_key=r["from"],
                            description="CTI %s" % r["from"])["data"]["key"]
                self.create_edge_new(fromNode=fromNode, toNode=toNode)
            else:
                if "source_ref" in r.keys():
                    self.create_edge_new(
                        fromNode=graph["index"][r["source_ref"]],
                        toNode=graph["index"][r["target_ref"]],
                        edgeType=r["relationship_type"]
                    )
                elif "sighting_of_ref" in r.keys():
                    if r["id"] in graph["index"].keys():
                        sNode = graph["index"][r["id"]]
                    else:
                        sNode = self.create_node(
                            class_name="Sighting", Ext_key=r["id"], createDate=r["created"], updateDate=r["modified"],
                            description="CTI Sighting of %s on %s" % (r["sighting_of_ref"], r["created"])
                        )["data"]["key"]
                    if r["created_by_ref"] in graph["index"].keys():
                        cNode = graph["index"][r["created_by_ref"]]
                    else:
                        cNode = self.create_node(
                            class_name="Identity", Ext_key=r["created_by_ref"],
                            description="CTI Identity %s" % r["created_by_ref"],
                        )["data"]["key"]
                    self.create_edge_new(fromNode=cNode, toNode=sNode, edgeType="Created")
                    if r["sighting_of_ref"] in graph["index"].keys():
                        oNode = graph["index"][r["sighting_of_ref"]]
                    else:
                        oNode = self.create_node(
                            class_name="Object", Ext_key=r["sighting_of_ref"],
                            description="CTI Sighting of %s on %s" % (r["sighting_of_ref"], r["created"])
                        )["data"]["key"]
                    self.create_edge_new(fromNode=sNode, toNode=oNode, edgeType="SightingOf")

        click.echo('[%s_OSINT_graph_poisonivy] Complete with extraction.')

    def get_url(self, url, path):
        if not os.path.exists(path):
            click.echo('[%s_OSINT_get_url] Getting %s' % (get_datetime(), url))
            data = requests.get(url)
            return data
        else:
            click.echo("[%s_OSINT_get_url]Latest data exists. No need to download" % get_datetime())
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
