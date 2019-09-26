import pyorient
import json
import random
import click
import pandas as pd
import os
import time
from apiserver.utils import get_datetime, HOST_IP, change_if_number, clean, get_time_based_id, format_graph


class ODB:

    def __init__(self, db_name="GratefulDeadConcerts"):

        self.client = pyorient.OrientDB(HOST_IP, 2424)
        self.user = 'root'
        self.pswd = 'admin'
        self.db_name = db_name
        self.path = os.getcwd()
        self.datapath = os.path.join(self.path, 'data')
        self.ICON_PERSON = "sap-icon://person-placeholder"
        self.ICON_OBJECT = "sap-icon://add-product"
        self.ICON_ORGANIZATION = "sap-icon://manager"
        self.ICON_INFO_SOURCE = "sap-icon://newspaper"
        self.ICON_LOCATION = "sap-icon://map"
        self.ICON_EVENT = "sap-icon://date-time"
        self.ICON_HUMINT = "sap-icon://collaborate"
        self.ICON_GEOINT = "sap-icon://geographic-bubble-chart"
        self.ICON_SOCINT = "sap-icon://hello-world"
        self.ICON_CONFLICT = "sap-icon://alert"
        self.ICON_CASE = "sap-icon://folder"
        self.ICON_STATUSES = ["Warning", "Error", "Success"]
        self.ICON_TWEET = "sap-icon://jam"
        self.ICON_TWITTER_USER = "sap-icon://customer-view"
        self.ICON_HASHTAG = "sap-icon://number-sign"
        self.models = {
            "Vertex": {
                "key": "integer",
                "tags": "string",
                "class": "V"
            },
            "Line":{
                "class": "E",
                "tags": "string"
            }
        }
        self.standard_classes = ['OFunction', 'OIdentity', 'ORestricted',
                                 'ORole', 'OSchedule', 'OSequence', 'OTriggered',
                                 'OUser', '_studio' ]

    def create_edge(self, **kwargs):
        if change_if_number(kwargs['fromNode']) and change_if_number(kwargs['toNode']):
            sql = '''
            create edge {edgeType} from 
            (select from {fromClass} where key = {fromNode}) to 
            (select from {toClass} where key = {toNode})
            '''.format(edgeType=kwargs['edgeType'], fromNode=kwargs['fromNode'], toNode=kwargs['toNode'],
                       fromClass=kwargs['fromClass'], toClass=kwargs['toClass'])

        elif change_if_number(kwargs['fromNode']):
            sql = '''
            create edge {edgeType} from 
            (select from {fromClass} where key = {fromNode}) to 
            (select from {toClass} where key = '{toNode}')
            '''.format(edgeType=kwargs['edgeType'], fromNode=kwargs['fromNode'], toNode=kwargs['toNode'],
                       fromClass=kwargs['fromClass'], toClass=kwargs['toClass'])
        elif change_if_number(kwargs['toNode']):
            sql = '''
            create edge {edgeType} from 
            (select from {fromClass} where key = '{fromNode}') to 
            (select from {toClass} where key = {toNode})
            '''.format(edgeType=kwargs['edgeType'], fromNode=kwargs['fromNode'], toNode=kwargs['toNode'],
                       fromClass=kwargs['fromClass'], toClass=kwargs['toClass'])
        else:
            sql = '''
            create edge {edgeType} from 
            (select from {fromClass} where key = '{fromNode}') to 
            (select from {toClass} where key = '{toNode}')
            '''.format(edgeType=kwargs['edgeType'], fromNode=kwargs['fromNode'], toNode=kwargs['toNode'],
                       fromClass=kwargs['fromClass'], toClass=kwargs['toClass'])

        try:
            self.client.command(sql)
            return True
        except Exception as e:
            return str(e)

    def create_node(self, **kwargs):
        """
        Use the idseq to iterate the key and require a class name to create the node
        Go through the properties and add a new piece to the sql statement for each using a label and values for insert
        Only insert statements return values and the key is needed
        While creating the sql, save attributes for formatting to a SAPUI5 node
        If there is a key, set the key as the label but wait to determine if the key is a number or string before
        adding to the values part of the sql insert statement
        :param kwargs: str(db_name), str(class_name), list(properties{property: str, value: str)
        :return:
        """
        attributes = []
        # In the case attributes as an array is received instead of directly in kwargs, fix and then pop attributes out
        if 'attributes' in kwargs.keys():
            if type(kwargs['attributes']) == list:
                attributes = kwargs['attributes']
                for a in kwargs['attributes']:
                    kwargs[a['label']] = a['value']
                kwargs.pop('attributes')
        if 'class_name' in kwargs.keys():
            if "key" in kwargs.keys():
                labels = "(key"
                values = "("
                hadKey = True
                thisKey = kwargs['key']
            else:
                labels = "(key"
                values = "(sequence('idseq').next()"
                hadKey = False
                thisKey = None
            icon = title = status = None

            for k in kwargs.keys():
                if list(kwargs.keys())[-1] == k:
                    # Close the labels and values with a ')'
                    if hadKey:
                        if change_if_number(kwargs[k]):
                            values = values + "{value})".format(value=kwargs['key'])
                        else:
                            values = values + "'{value}')".format(value=clean(kwargs['key']))
                        hadKey = False
                    else:
                        labels = labels + ", {label})".format(label=k)
                        if change_if_number(kwargs[k]):
                            values = values + ", {value})".format(value=kwargs[k])
                        else:
                            values = values + ", '{value}')".format(value=clean(kwargs[k]))
                else:
                    if hadKey:
                        if change_if_number(kwargs[k]):
                            values = values + "{value}".format(value=kwargs['key'])
                        else:
                            values = values + "'{value}'".format(value=clean(kwargs['key']))
                        # Change key since after first pass, the sql statement is the same in either case
                        hadKey = False
                    else:
                        labels = labels + ", {label}".format(label=k)
                        if change_if_number(kwargs[k]):
                            values = values + ", {value}".format(value=kwargs[k])
                        else:
                            values = values + ", '{value}'".format(value=clean(kwargs[k]))

                if k == 'icon':
                    icon = kwargs[k]
                if k == 'title':
                    title = kwargs[k]
                if k == 'status':
                    status = kwargs[k]
                if k != 'passWord':
                    attributes.append({"label": k, "value": kwargs[k]})
            # If there is a key, a new record is not created but rather the formatted version.
            # However, a Case is assigned a key and therefore should not be applied here.
            # For cases within cases, fix below where Duplicate record will be triggered for case with same name
            if thisKey:
                formatted_node = self.format_node(
                    key=thisKey,
                    class_name=kwargs['class_name'],
                    title=title,
                    status=status,
                    icon=icon,
                    attributes=attributes
                )
                message = '[%s_%s_create_node] Node %s exists' % (get_datetime(), self.db_name, thisKey)
                return {"message": message, "data": formatted_node}
            else:
                sql = '''
                insert into {class_name} {labels} values {values} return @this.key
                '''.format(class_name=kwargs['class_name'], labels=labels, values=values)
                try:
                    key = self.client.command(sql)[0].oRecordData['result']
                    formatted_node = self.format_node(
                        key=key,
                        class_name=kwargs['class_name'],
                        title=title,
                        status=status,
                        icon=icon,
                        attributes=attributes
                    )
                    message = '[%s_%s_create_node] Create node %s' % (get_datetime(), self.db_name, key)
                    return {"message": message, "data": formatted_node}

                except Exception as e:
                    if str(type(e)) == str(type(e)) == "<class 'pyorient.exceptions.PyOrientORecordDuplicatedException'>":
                        if kwargs['title'] == "Case":
                            node = self.get_node(val=kwargs['Name'], var="Name", class_name="Case")
                            return {"data" : self.format_node(
                                key=node['key'],
                                icon=node['icon'],
                                status=node['status'],
                                title=node['title'],
                                class_name=node['class_name'],
                                attributes=attributes
                            )}
                    message = '[%s_%s_create_node] ERROR %s\n%s' % (get_datetime(), self.db_name, str(e), sql)
                    click.echo(message)
                    return message

        else:
            return None

    def create_db(self):
        """
        Build the schema in OrientDB using the models established in __init__
        1) Cycle through the model configuration
        2) Use custom rules as part of the model to trigger an index
        :return:
        """
        self.client.db_create(self.db_name, pyorient.DB_TYPE_GRAPH)
        click.echo('[%s_%s_create_db] Starting process...' % (get_datetime(), self.db_name))
        sql = ""
        for m in self.models:
            sql = sql+"create class %s extends %s;\n" % (m, self.models[m]['class'])
            for k in self.models[m].keys():
                if k != 'class':
                    sql = sql+"create property %s.%s %s;\n" % (m, k, self.models[m][k])
                    # Custom rules for establishing indexing
                    if (str(k)).lower() in ["key", "id", "uid", "userid"] \
                            or (self.db_name == "Users" and str(k).lower == "username")\
                            or (m == "Case" and k == "Name"):
                        sql = sql + "create index %s_%s on %s (%s) UNIQUE ;\n" % (m, k, m, k)

        sql = sql + "create sequence idseq type ordered;"
        click.echo('[%s_%s_create_db]'
                   ' Initializing db with following batch statement'
                   '\n***************   SQL   ***************\n'
                   '%s\n***************   SQL   ***************\n' % (get_datetime(), self.db_name, sql))

        try:
            self.client.batch(sql)
            click.echo('[%s_create_db_%s] Completed process' % (self.db_name, get_datetime()))
            created = True
        except Exception as e:
            click.echo('[%s_create_db_%s] ERROR: %s' % (self.db_name, get_datetime(), str(e)))
            created = False

        return created

    def open_db(self):
        self.client.connect(self.user, self.pswd)
        if self.client.db_exists(self.db_name):
            self.client.db_open(self.db_name, self.user, self.pswd)
        else:
            self.create_db()

    def get_node(self, **kwargs):

        sql = ('''
        select * from {class_name} where {var} = '{val}'
        ''').format(class_name=kwargs['class_name'], var=kwargs['var'], val=kwargs['val'])
        r = self.client.command(sql)

        if len(r) > 0:
            return r[0].oRecordData
        else:
            return None

    def get_db_stats(self):

        return({
            "name": self.db_name,
            "size": self.client.db_size(),
            "records": self.client.db_count_records(),
            "details": self.get_db_details(self.db_name)})

    def get_db_details(self, db_name):

        schema = self.client.command('''select expand(classes) from metadata:schema ''')
        details = []
        for s in schema:
            s = s.oRecordData
            if s['name'] not in self.standard_classes:
                try:
                    props = s['properties']
                    f_props = ""
                    prop_list = []
                    for p in props:
                        f_props = f_props + p['name'] + "\n"
                        prop_list.append(p['name'])
                    details.append(
                      {'name': s['name'],
                       'clusterIds': s['clusterIds'],
                       'properties': f_props,
                       'prop_dict': props,
                       'prop_list': prop_list
                       }
                    )
                except:
                    pass

        return details

    def get_data(self):
        return self.open_file(os.path.join(self.datapath, "netgraph.json"))

    def open_file(self, filename):
        """
        Open any file type and normalize into an dictionary object with the payload stored in
        a pandas dataframe or a json
        :param filename:
        :return: dict data
        """

        ftype = filename[filename.rfind('.'):]
        data = {'status': True, 'filename': filename, 'ftype': ftype}
        if ftype == '.csv':
            data['d'] = pd.read_csv(filename)
        elif ftype == '.xls' or type == '.xlsx':
            data['d'] = pd.read_excel(filename)
        elif ftype == '.json':
            try:
                with open(filename, 'r') as f:
                    data['d'] = json.load(f)
            except Exception as e:
                click.echo('[%s_%s_open_file] Failed to open %s\n%s' % (get_datetime(), self.db_name, filename, str(e)))

        elif ftype == '.txt':
            with open(filename) as f:
                for line in f:
                    (key, val) = line.split()
                    data[int(key)] = val
        else:
            data['status'] = False
            data['d'] = "File %s not in acceptable types" % ftype

        data['basename'] = os.path.basename(filename)
        data['file_size'] = os.stat(filename).st_size
        data['create_date'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.stat(filename).st_atime))

        return data

    def update(self, **kwargs):

        sql = ('''
          update {class_name} set {var} = '{val}' where key = {key}
          ''').format(class_name=kwargs['class_name'], var=kwargs['var'], val=kwargs['val'], key=kwargs['key'])
        r = self.client.command(sql)

        if len(r) > 0:
            return r
        else:
            return None

    def delete_node(self, **kwargs):

        sql = ('''
          delete vertex {class_name} where key = {key}
          ''').format(class_name=kwargs['class_name'], key=kwargs['key'])
        r = self.client.command(sql)

        if len(r) > 0:
            return r
        else:
            return None

    def format_node(self, **kwargs):
        """
        Create a SAPUI5 formatted node
        :param kwargs:
        :return:
        """
        if not kwargs['icon']:
            kwargs['icon'] = "sap-icon://add"
        if not kwargs['class_name']:
            kwargs['class_name'] = 'No class name'
        if not kwargs['title']:
            kwargs['title'] = kwargs['class_name']
        if not kwargs['status']:
            kwargs['status'] = random.choice(['Information', 'Success', 'Error', 'Warning', 'None'])

        node_format = {
            "key": kwargs['key'],
            "title": kwargs['title'],
            "status": kwargs['status'],
            "icon": kwargs['icon'],
            "attributes": kwargs['attributes']
        }

        return node_format

    def quality_check(self, graph):
        """
        Create a chrono view and geo view from a graph
        :param graph:
        :return:
        """

        node_keys = []
        group_keys = [{"key": "NoGroup", "title": "NoGroup" }]

        if "groups" in graph.keys():
            for g in graph['groups']:
                if ({"key": g['key'], "title": g['title']}) not in graph['groups']:
                    group_keys.append({"key": g['key'], "title": g['title']})

        graph['groups'] = group_keys

        if "nodes" in graph.keys() and "lines" in graph.keys():
            for n in graph['nodes']:
                node_keys.append(n['key'])
                if "group" in n.keys():
                    if {"key": n['group'], "title": n['group']} not in group_keys:
                        graph['groups'].append({'key': n['group'], 'title': n['group']})
                else:
                    n['group'] = "NoGroup"
            for l in graph['lines']:
                if l['to'] not in node_keys:
                    click.echo("Relationship TO with %s not found in nodes. Creating dummy node.")
                    graph['nodes'].append(self.create_node(key=l['to'], class_name="Object"))
                if l['from'] not in node_keys:
                    click.echo("Relationship TO with %s not found in nodes. Creating dummy node.")
                    graph['nodes'].append(self.create_node(key=l['from'], class_name="Object"))
        else:
            click.echo("Missing nodes or lines")
            return None
        return graph

    def key_comparison(self, keys):
        """
        Using the keys from a node, check the Databases models for the one with the most similar keys to
        determine the class_name. For each model, use the list of keys to compare against the input keys. Each time
        there is a matching key, increase the similarity score
        :param keys:
        :return:
        """
        simScores = {}
        c_keys = []
        for k in keys:
            c_keys.append(str(k).lower())
        click.echo('[%s_%s] Running similarity on attributes:\n\t%s' % (get_datetime(), "home.key_comparison", keys))
        for m in self.models:
            simScores[m] = 0
            m_keys = []
            for k in list(self.models[m].keys()):
                m_keys.append(str(k).lower())
            for k in c_keys:
                if k in m_keys:
                    simScores[m]+=1

            #click.echo('[%s_%s] Compared %s\nScore: %s' % (get_datetime(), "home.key_comparison", m_keys, simScores[m]))
        class_name = max(simScores, key=simScores.get)
        click.echo('[%s_%s] Most likely class is %s with score %d.' % (
            get_datetime(), "home.key_comparison", class_name, simScores[max(simScores)]))

        return class_name

    def save(self, **kwargs):
        """
        Expects a request with graphCase containing the graph from the user's canvas and assumes that all nodes have an
        attribute "key". The creation of a node is only if the node is new and taken from a source that doesn't exist in
        POLE yet.
        If it is an existing case, set the LastUpdate to the current date time.
        QUERY 1 Checks if the Case already exists and if not, creates it.
        QUERY 2 Gets existing keys if the Nodes sent in the graphCase are already "Attached" to the Case from QUERY 1
        QUERY 3 Compares edges between the new case and old case and only adds a new relation where one doesn't exist
        Run a match query that returns only those nodes in the case and their relationships. The query uses the book-end
        method in a manner: Case-Attached->Vertex1-(any)->Vertex2-Attached->Case. Return v1, v2 and the type of relation
        TODO: Relation duplication quality - Include all edge attributes beyond description
        TODO: Implement classification on related nodes

        Owner/Member relations are maintained by storing the unique UserName of the user in the Case.Owners/Members
        string. The string is split into a list to compare with the incoming keys. If there is a gap, the string is
        updated. When the user logs in from the User Database side, it can call each other database to find out which
        cases the user belongs to and return those in an object.
        :param kwargs: graphCase, graphName, Classification, Owners, Members, CreatedBy
        :return: graph (in the UI form), message (summary of actions)
        """
        # The graph being saved
        fGraph = kwargs['graphCase']
        if "groups" in fGraph.keys():
            groups = fGraph['groups']
        else:
            groups = []
        # The new graph to be returned which includes nodes from fGraph with new keys if they are not stored yet
        graph = {
            "nodes": [],
            "lines": [],
            "groups": groups
        }
        # QUERY 1: Get the case by Name and Classification in the case there is no case key
        sql = ('''
            select key, class_name, Name, Owners, Classification, Members, StartDate, CreatedBy  
            from Case where Name = '%s' and Classification = '%s'
        ''' % (clean(kwargs['graphName']), kwargs['Classification'])
               )
        click.echo('[%s_%s] Q1: Getting Case:\n\t%s' % (get_datetime(), "home.save", sql))
        case = self.client.command(sql)
        # Array for the node keys related to the case if it exists returned from Query 2
        current_nodes = []
        # UPDATE CASE if it was found
        ownersString = str(kwargs['Owners']).strip('[]').replace("'", "")
        membersString = str(kwargs['Members']).strip('[]').replace("'", "")
        if len(case) > 0:
            # Settings for the update
            updateCaseWorkers = False
            casedata = dict(case[0].oRecordData)

            # CHECK users to see if there are new ones to be added
            for user in kwargs['Owners']:
                if user not in casedata['Owners'].split(","):
                    ownersString+=",%s" % user
                    updateCaseWorkers = True
            if updateCaseWorkers:
                print("update attribute")
            for user in kwargs['Members']:
                if user not in casedata['Members'].split(","):
                    membersString+=",%s" % user
                    updateCaseWorkers = True
            if updateCaseWorkers:
                print("update attribute")

            # Store the other variables for the return value
            case = dict(key=casedata['key'], icon=self.ICON_CASE, status="CustomCase", title=casedata['Name'])
            # UPDATE the LastUpdate attribute and carry the variable over to the return value
            LastUpdate = get_datetime()
            self.update(class_name="Case", var="LastUpdate", val=LastUpdate, key=case['key'])
            case['attributes'] = [
                {"label": "Owners", "value": casedata['Owners']},
                {"label": "Members", "value": casedata['Members']},
                {"label": "Classification", "value": casedata['Classification']},
                {"label": "StartDate", "value": casedata['StartDate']},
                {"label": "LastUpdate", "value": LastUpdate},
                {"label": "className", "value": "Case"},
                {"label": "CreatedBy", "value": casedata['CreatedBy']}
            ]
            # Carry the case_key over to the relationship creation
            case_key = str(case['key'])
            message = "Updated %s" % case['title']
            # QUERY 2: Get the node keys related to the case that was found T
            # TODO don't get just keys but attributes and compare
            sql = '''
            match {class: Case, as: u, where: (key = '%s')}.out(Attached)
            {class: V, as: e} return e.key
            '''  % case_key
            click.echo('[%s_%s] Q2: Getting Case nodes:\n\t%s' % (get_datetime(), "home.save", sql))
            Attached = self.client.command(sql)
            for k in Attached:
                current_nodes.append(k.oRecordData['e_key'])
        # SAVE CASE if it was not found
        else:
            message = "Saved %s" % kwargs['graphName']
            case = self.create_node(
                class_name="Case",
                Name=clean(kwargs["graphName"]),
                CreatedBy=clean(kwargs["CreatedBy"]),
                Owners=ownersString,
                Members=membersString,
                Classification=kwargs["Classification"],
                StartDate=get_datetime(),
                LastUpdate=get_datetime(),
                NodeCount=len(fGraph['nodes']),
                EdgeCount=len(fGraph['lines'])
            )['data']
            case_key = str(case['key'])
            click.echo('[%s_%s_create_db] Created Case:\n\t%s' % (get_datetime(), "home.save", case))
        # Attach the Case record to the nodes
        graph['nodes'].append(case)
        # ATTACHMENTS of Nodes and Edges from the Request.
        newNodes = newLines = 0
        if "nodes" in fGraph.keys() and "lines" in fGraph.keys():
            for n in fGraph['nodes']:
                # If the new Case node is not in the keys from the collection create a node
                if n['key'] not in current_nodes:
                    newNodes += 1
                    # To add the Node with a new key, need to pop this node's key out and then replace in the lines
                    oldKey = n['key']
                    try:
                        n['class_name'] = self.get_node_att(n, 'className')
                    except:
                        n['class_name'] = self.get_node_att(n, 'class_name')
                    if not n['class_name']:
                        keys_to_compare = []
                        for k in n.keys():
                            keys_to_compare.append(k)
                        if 'attributes' in n.keys():
                            for a in n['attributes']:
                                keys_to_compare.append(a['label'])
                        n['class_name'] = self.key_comparison(keys_to_compare)
                    # Save the class name for use in the relationship since it is otherwise buried in the attributes
                    class_name = n['class_name']
                    n.pop("key")
                    n = self.create_node(**n)
                    n_key = str(n['data']['key'])
                    # Go through the lines and change the key to this new key
                    for l in fGraph['lines']:
                        if l['to'] == oldKey:
                            l['to'] = n_key
                        elif l['from'] == oldKey:
                            l['from'] = n_key
                    if {"from": case_key, "to": n_key, "description": "Attached"} not in graph['lines']:
                        self.create_edge(fromNode=case_key, toNode=n['data']['key'],
                                         edgeType="Attached", fromClass="Case", toClass=class_name)
                        graph['lines'].append({"from": case_key, "to": n_key, "description": "Attached"})

                    # Add the node to the graph
                    graph['nodes'].append(n['data'])
                # Otherwise just add it as is to the new graph that will be sent back
                else:
                    graph['lines'].append({"from": str(case_key), "to": str(n['key']), "description": "Attached"})
                    graph['nodes'].append(n)

            # QUERY 3: Compare the edges between nodes from the saved case and the new case
            # to determine if new edge is needed
            oldRels = graph['lines']
            sql = ('''
            match
            {class:Case, as:c, where: (key = '%s')}.out("Attached")
            {class:V, as:v1}.outE(){as:v2e}.inV()
            {class:V, as:v2}.in("Attached")
            {class:Case, where: (key = '%s')}
            return v1.key as from_key, v2.key as to_key, v2e.@class as description
            ''' % (case_key, case_key))
            rels = self.client.command(sql)
            # Compare the rels that are currently stored with the ones in that were added during Case creation step 1
            click.echo('[%s_%s] Q3: Compare existing case to new:\n\t%s' % (get_datetime(), "home.save", sql))
            for rel in rels:
                rel = rel.oRecordData
                oldRels.append({"from": rel['from_key'], "to": rel['to_key'], "description": rel['description']})
            for l in graph['lines']:
                if {"from": l['from'], "to": l['to'], "description": l['description']} not in oldRels:
                    newLines += 1
                    self.create_edge(fromNode=l['from'], fromClass=self.get_class_name(graph, l['from']),
                                     toNode=l['to'], toClass=self.get_class_name(graph, l['to']),
                                     edgeType=l['description'])
            # Final Comparison of relations using the fGraph where keys of ne nodes are changed
            for r in fGraph['lines']:
                if {"from": r['from'], "to": r['to'], "description": r['description']} not in graph['lines']:
                    graph['lines'].append({"from": r['from'], "to": r['to'], "description": r['description']})
                    self.create_edge(fromNode=r['from'], fromClass=self.get_class_name(graph, r['from']),
                                     toNode=r['to'], toClass=self.get_class_name(graph, r['to']),
                                     edgeType=r['description'])

            if newNodes == 0 and newLines == 0:
                message = "No new data received. Case %s is up to date." % clean(kwargs["graphName"])
            else:
                message = "%s with %d nodes and %d edges." % (message, newNodes, newLines)
        click.echo('[%s_%s] %s' % (get_datetime(), "home.save", message))
        return graph, message

    @staticmethod
    def get_class_name(graph, key):
        """
        Needed for the SAPUI5 graph because relations/lines do not have class_names and this is needed to create an edge
        :param graph:
        :param key:
        :return:
        """
        for n in graph['nodes']:
            try:
                if str(n['key']) == str(key):
                    if 'class_name' in n.keys():
                        return n['class_name']
                    elif 'attributes' in n.keys():
                        for a in n['attributes']:
                            if a['label'] == 'class_name' or a['label'] == 'className':
                                return a['value']
            except Exception as e:
                click.echo("ERROR in get_class_name: %s" % str(e) )
        return

    @staticmethod
    def get_node_att(node, att):

        try:
            for a in node['attributes']:
                if a['label'] == att:
                    return a['value']
            return None
        except:
            print(node)


