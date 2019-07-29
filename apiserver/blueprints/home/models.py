import pyorient
import json, random
import click
from apiserver.utils import get_datetime, HOST_IP, change_if_number, clean
import pandas as pd
import os
import time


class ODB:

    def __init__(self, db_name="GratefulDeadConcerts"):

        self.client = pyorient.OrientDB(HOST_IP, 2424)
        self.user = 'root'
        self.pswd = 'admin'
        self.db_name = db_name
        self.path = os.getcwd()
        self.data = os.path.join(self.path, "data")
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
        if 'class_name' in kwargs.keys():
            if "key" in kwargs.keys():
                labels = "(key"
                values = "("
                hadKey = True
            else:
                labels = "(key"
                values = "(sequence('idseq').next()"
                hadKey = False
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
                message = '[%s_%s_create_node] ERROR %s\n%s' % (get_datetime(), self.db_name, str(e), sql)
                click.echo(message)
                return message

        else:
            return None

    def create_db(self):
        """
        Build the schema in OrientDB using the models established in __init__
        1) Cycle through the model configuration
        2) Use a rule that if 'id' is part of the model, then it should have an index
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
                    if (str(k)).lower() in ["key", "id", "uid", "userid"]:
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
        return self.open_file(os.path.join(self.data, "netgraph.json"))

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
                group_keys.append({"key": g['key'], "title": g['title']})
        else:
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


