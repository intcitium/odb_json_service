import pyorient
import json
import random
import click
import pandas as pd
import numpy as np
import os
import decimal
import time
import operator
import hashlib
from apiserver.utils import get_datetime, HOST_IP, change_if_number, clean, clean_concat


class ODB:

    def __init__(self, db_name="GratefulDeadConcerts", models=None):

        self.client = pyorient.OrientDB(HOST_IP, 2424)
        self.user = 'root'
        self.pswd = 'admin'
        self.db_name = db_name
        self.path = os.getcwd()
        self.datapath = os.path.join(self.path, 'data')
        self.mapspath = os.path.join(self.datapath, 'maps.json')
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
        self.index = {"nodes": {}, "edges": []}
        # Keeping the nodeKeys in this order assures that matches will be checked in the same consistent string
        self.nodeKeys = ['class_name', 'title', 'FirstName', 'LastName', 'Gender', 'DateOfBirth', 'PlaceOfBirth',
                    'Name', 'Owner', 'Classification', 'Category', 'Latitude', 'Longitude', 'Description',
                    'EndDate', 'StartDate', 'DateCreated']
        if not models:
            self.models = {
                "Vertex": {
                    "key": "integer",
                    "tags": "string",
                    "hash": "string",
                    "class": "V"
                },
                "Line":{
                    "class": "E",
                    "tags": "string"
                }
            }
        self.get_maps()
        self.standard_classes = ['OFunction', 'OIdentity', 'ORestricted',
                                 'ORole', 'OSchedule', 'OSequence', 'OTriggered',
                                 'OUser', '_studio' ]


        #self.create_index()

    def get_maps(self):
        """
        Called by the init function to load the models stored to the file system into
        the application for matching against incoming models needed for ETL graph
        translation
        :return:
        """
        with open(self.mapspath, 'r') as f:
            self.maps = json.load(f)

    def save_model_to_map(self, model):
        """
        Expects a model which will reference a file already in the system
        :return:
        """
        if model["Name"] in self.maps.keys():
            return

        self.maps[model["Name"]] = {
            "Entities": model["Entities"],
            "Relations": model["Relations"],
            "headers": model["headers"]
        }
        with open(self.mapspath, 'w') as f:
            json.dump(self.maps, f)

    def file_to_frame(self, filename):
        try:
            if filename[-4:] == "xlsx":
                return {"data": pd.read_excel(os.path.join(self.datapath, filename))}
            elif filename[-3:] == "csv":
                return {"data": pd.read_csv(os.path.join(self.datapath, filename))}
            else:
                return {
                    "data": None,
                    "headers": None,
                    "ftype": "Unknown",
                    "message": "Rejected %s." % (filename)
                }
        except Exception as e:
            if "No such file or directory" in str(e):
                return {
                    "data": None,
                    "headers": None,
                    "ftype": "Unknown",
                    "message": "No file loaded to the directory with name %s. Try uploading again." % (filename)
                }

    def file_to_graph(self, filename):
        """
        Based on acceptable file extensions but not necessarily known file types in terms of content, the function
        checks which of the acceptable extensions the file is so that it can change it into a standard format to read.
        In most cases tabular data is expected in which Pandas dataframes provide a way to get the headers and data into
        a dictionary/JSON friendly format.

        If the file is recognized based on keys and the matched model extraction is successfully completed, it will
        return data as a graph. If not the data is returned as a sample of the file to provide content for configuration.
        :param filename:
        :return:
        """
        file = self.file_to_frame(filename)
        if str(type(file["data"])) != "<class 'pandas.core.frame.DataFrame'>":
            return file
        else:
            file = file["data"]
        check = self.file_type_check(file.keys())
        check["size"] = str(os.stat(os.path.join(self.datapath, filename)).st_size) + " bytes"
        check["source"] = filename
        if check["score"] > .9999:
            click.echo(check["name"])
            click.echo(self.maps[check["name"]])
            data = self.graph_etl_model({
                "Name": check["name"],
                "Entities": self.maps[check["name"]]["model"]["Entities"],
                "Relations": self.maps[check["name"]]["model"]["Relations"],
            }, file)
            if check["name"] == 'eppm':
                data = self.graph_eppm(file)
            return {
                "data": data,
                "ftype": check,
                "message": "Uploaded file with file type model %s." % (check["name"])
            }
        elif check["score"] > 0:
            # Can check if the file run against the model works but do so with a try to return the result
            try:
                data = self.graph_eppm(file)
                message = "Uploaded file with model type %s." % (check["name"])
                return {
                    "data": data,
                    "ftype": check,
                    "message": message
                }
            except Exception as e:
                message = "Attempted with %s file type model but file is missing %s" % (
                    check["name"], str(e)
                )
                return {
                    "headers": list(file.columns),
                    "data": file.sample(n=10).fillna(value="null").to_dict(),
                    "ftype": check,
                    "message": message
            }
        else:
            return {
                "data": file.sample(n=10).fillna(value="null").to_dict(),
                "headers": list(file.columns),
                "ftype": check,
                "message": "Could not identify the file type. Prepared %s for configuration." % (filename)
            }

    def graph_etl_model(self, model, data):
        """
        The model should be a dictionary containing all the entities and their attributes. The attributes are mapped
        to headers within the data which is expected to be in a tabular format.
        Data
            Animal_name: [Abe, Babe...]
            Animal_color: [Red, Blue...]
        Model
            Entities:
                Animal: {Id: key, name : Animal_name}
                Color: {Id: key, label: Animal_color}
            Relations:
                HasColor: {from: Animal, to: Color}

        Includes a function for etl processing of node
        Includes checking if the model is saved for file_type_check and then calling that model
        TODO, change EPPM extraction to model based that is called from the server at initiation

        :param model:
        :param data:
        :return:
        """
        self.save_model_to_map(model)
        node_index = []
        graph = {"nodes": [], "lines": [], "n_index": []}
        # Ensure the data received is changed into a DataFrame if it is not already
        if str(type(data)) != "<class 'pandas.core.frame.DataFrame'>":
            file = self.file_to_frame(data)
            if str(type(file["data"])) != "<class 'pandas.core.frame.DataFrame'>":
                return file
            else:
                data = file["data"]

        def get_key(**kwargs):
            """
            Handles node creation based on the local node_index and the local create_node function.
            The node expects an icon and class_name (EntityType)
            expects an Icon with a key but if there is none it will create it
            :param kwargs:
            :return:
            """
            if "key" in kwargs.keys():
                if kwargs["key"] in node_index:
                    return kwargs["key"]
                else:
                    node_index.append(kwargs['key'])
                    graph["nodes"].append(self.create_node(**kwargs)["data"])
                    return kwargs["key"]
            else:
                h_key = self.hash_node(kwargs)
                if h_key in node_index:
                    return h_key
                else:
                    node_index.append(h_key)
                    kwargs["key"] = h_key
                    graph["nodes"].append(self.create_node(**kwargs)["data"])
                    return h_key

        for index, row in data.iterrows():
            if index != 0:
                # Based on the entities in the model, get IDs that can be used to create relationships
                rowConfig = {}
                for entity in model["Entities"]:
                    # The extracted entity is based on the model and mapped row value to entity attributes
                    extractedEntity = {"class_name": entity}
                    for att in model["Entities"][entity]:
                        if model["Entities"][entity][att] in row.keys():
                            extractedEntity[att] = row[model["Entities"][entity][att]]
                        else:
                            extractedEntity[att] = model["Entities"][entity][att]
                    # Check if this Entity has already been extracted and get the key.
                    # The function also adds the entity to the graph which will be exported
                    exEntityKey = get_key(**extractedEntity)
                    if exEntityKey in graph["n_index"]:
                        graph["n_index"].append(exEntityKey)
                    # Add the entity key to its spot within the mapping configuration so the lines can be built
                    rowConfig[entity] = exEntityKey
                # Use the entity names that are saved into the relation to and from to assign the row config entity key
                for line in model["Relations"]:
                    if({"to": rowConfig[model["Relations"][line]["to"]],
                        "from": rowConfig[model["Relations"][line]["from"]],
                        "description": line }) not in graph["lines"]:
                            graph["lines"].append({
                                "to": rowConfig[model["Relations"][line]["to"]],
                                "from": rowConfig[model["Relations"][line]["from"]],
                                "description": line,
                            })

        return graph

    def graph_eppm(self, data):
        print( '[%s_graph_eppm] Starting' % (get_datetime()))
        r = {
            "nodes": [],
            "lines": [],
            "groups": [
                {"key": "EPPMProjects", "title": "EPPM Projects"},
                {"key": "items", "title": "Items"},
                {"key": "elements", "title": "Portfolio Elements"},
                {"key": "InternalOrders", "title": "Internal Orders"},
                {"key": "Programs", "title": "Programs"},
                {"key": "portfolio", "title": "Portfolio"},
                {"key": "Products", "title": "Products"}
            ],

            "index": []
        }

        def get_latlon():
            return np.random.normal(0, 45)

        def get_status(status):

            if status in ["Active", "2", "10", "Created", "Approved", "Completed"]:
                return "Success"
            if status in ["Inactive", "Deletion Request", "Ready for Decision", "Canceled"]:
                return "Error"
            if status in ["To be Archived", "Closed", "Flagged for Archiving", "Released"]:
                return "Warning"

        def make_line(**kwargs):
            if({"to": kwargs['r_to'], "from": kwargs['r_from'], "description": kwargs['r_type']}) not in r['lines']:
                r['lines'].append({"to": kwargs['r_to'], "from": kwargs['r_from'], "description": kwargs['r_type']})

        def check_node(n_dict):
            newKey = self.hash_node(n_dict)
            if newKey not in r['index']:
                r['index'].append(n_dict['key'])
                r['nodes'].append(n_dict)

            return n_dict['key']

        for index, row in data.iterrows():
            i = 120
            portfolio = check_node({
                "key": str(row['ITM_PORTFOLIO_TEXT']),
                "title": str(row['ITM_PORTFOLIO_TEXT']),
                "group": "portfolio",
                "icon": "sap-icon://tree",
                "status": "CustomPortfolio",
                "attributes": [
                    {"label": "EntityType", "value": "Portfolio"},
                    {"label": "ExternalID", "value": str(row['ITM_PORTFOLIO_TEXT'])},
                    {"label": "Latitude", "value": get_latlon()},
                    {"label": "Longitude", "value": get_latlon()},
                ]
            })
            portfolio_element = check_node({
                "key": str(row['ITM_BUCKET_GUID']),
                "group": "elements",
                "status": get_status(str(row['BUCKET_STATUS_TEXT'])),
                "title": str(row['ITM_BUCKET_TEXT']),
                "icon": "sap-icon://manager-insight",
                "attributes": [
                    {"label": "EntityType", "value": "Portfolio Element"},
                    {"label": "ExternalID", "value": str(row['ITM_BUCKET_GUID'])},
                    {"label": "StartDate", "value": str(row['BUCKET_CP_START_DATE'])},
                    {"label": "EndDate", "value": str(row['BUCKET_CP_END_DATE'])},
                    {"label": "StartDate FP", "value": str(row['BUCKET_FP_START_DATE'])},
                    {"label": "EndDate FP", "value": str(row['BUCKET_FP_END_DATE'])},
                    {"label": "Category_id", "value": str(row['ITM_BUCKET_CATEGORY'])},
                    {"label": "Category", "value": str(row['BUCKET_CATEGORY_TEXT'])},
                    {"label": "ID", "value": str(row['ITM_BUCKET_ID'])},
                    {"label": "Status code", "value": str(row['BUCKET_STATUS'])},
                    {"label": "BucketID", "value": str(row['ITM_BUCKET_ID'])},
                    {"label": "Latitude", "value": get_latlon()},
                    {"label": "Longitude", "value": get_latlon()},
                ]
            })
            logical_product = check_node({
                "key": str(row['LPR_KEY']),
                "group": "Products",
                "status": "CustomLogicalProduct",
                "title": str(row['LPR_TEXT']),
                "icon": "sap-icon://product",
                "attributes": [
                    {"label": "EntityType", "value": "Logical Product"},
                    {"label": "ExternalID", "value": str(row['LPR_KEY'])},
                    {"label": "Environment", "value": str(row['PPORADM'])},
                    {"label": "Environment text", "value": str(row['PPORADM_TXT'])},
                    {"label": "startDate", "value": str(row['PPORACDAT'])},
                    {"label": "Product", "value": str(row['PPORAPC_TXT'])},
                    {"label": "startDate", "value": str(row['PPORACDAT'])},
                    {"label": "Product", "value": str(row['PPORAPC_TXT'])},
                    {"label": "Latitude", "value": get_latlon()},
                    {"label": "Longitude", "value": get_latlon()},
                ]
            })
            initiative = check_node({
                "key": str(row['ITM_INITIATIVE_GUID']),
                "group": "Initiatives",
                "status": get_status(str(row['INITIATIVE_STATUS_TEXT'])),
                "title": str(row['ITM_INITIATIVE_TEXT']),
                "icon": "sap-icon://begin",
                "attributes": [
                    {"label": "EntityType", "value": "Initiative"},
                    {"label": "GUID", "value": str(row['ITM_INITIATIVE_GUID'])},
                    {"label": "ExternalID", "value": str(row['ITM_INITIATIVE_GUID'])},
                    {"label": "ID", "value": str(row['ITM_INITIATIVE_ID'])},
                    {"label": "Category text", "value": str(row['INITIATIVE_CATEGORY_TEXT'])},
                    {"label": "Status", "value": str(row['INITIATIVE_STATUS_TEXT'])},
                    {"label": "startDate", "value": str(row['INITIATIVE_START_DATE'])},
                    {"label": "endDate", "value": str(row['INITIATIVE_END_DATE'])},
                    {"label": "Category", "value": str(row['INITIATIVE_CATEGORY'])},
                    {"label": "Status code", "value": str(row['INITIATIVE_STATUS'])},
                    {"label": "Latitude", "value": get_latlon()},
                    {"label": "Longitude", "value": get_latlon()},
                ]
            })
            # Should ITM_P# be their own entities?
            item = check_node({
                "key": str(row['ITM_GUID']),
                "group": "items",
                "status": get_status(str(row['ITM_STATUS_TEXT'])),
                "title": str(row['ITM_TEXT']),
                "icon": "sap-icon://checklist-item",
                "attributes": [
                    {"label": "EntityType", "value": "Item"},
                    {"label": "GUID", "value": str(row['ITM_GUID'])},
                    {"label": "ExternalID", "value": str(row['ITM_GUID'])},
                    {"label": "ID", "value": str(row['ITM_ID'])},
                    {"label": "Type code", "value": str(row['ITM_TYPE'])},
                    {"label": "Type", "value": str(row['ITM_TYPE_TEXT'])},
                    {"label": "StartDate", "value": str(row['ITEM_START_DATE'])},
                    {"label": "EndDate", "value": str(row['ITEM_END_DATE'])},
                    {"label": "P1 code", "value": str(row['ITM_P1'])},
                    {"label": "P1", "value": str(row['ITM_P1_TEXT'])},
                    {"label": "P2 code", "value": str(row['ITM_P2'])},
                    {"label": "P2", "value": str(row['ITM_P2_TEXT'])},
                    {"label": "P3 code", "value": str(row['ITM_P3'])},
                    {"label": "P3", "value": str(row['ITM_P3_TEXT'])},
                    {"label": "P4 code", "value": str(row['ITM_P4'])},
                    {"label": "P4", "value": str(row['ITM_P4_TEXT'])},
                    {"label": "Status code", "value": str(row['ITM_STATUS'])},
                    {"label": "Latitude", "value": get_latlon()},
                    {"label": "Longitude", "value": get_latlon()},
                ]
            })
            cproject = check_node({
                "key": str(row['ITM_EXTERNAL_ID']),
                "group": "EPPMProjects",
                "status": get_status(str(row['ITM_PROJECT_SYS_STATUS_TEXT'])),
                "title": str(row['ITM_PROJECT_TEXT']),
                "icon": "sap-icon://capital-projects",
                "attributes": [
                    {"label": "EntityType", "value": "Project"},
                    {"label": "ID", "value": str(row['ITM_EXTERNAL_ID'])},
                    {"label": "ExternalID", "value": str(row['ITM_EXTERNAL_ID'])},
                    {"label": "Responsible", "value": str(row['ITM_PROJECT_RESP'])},
                    {"label": "Name", "value": str(row['ITM_PROJECT_RESP_NAME'])},
                    {"label": "Status", "value": str(row['ITM_PROJECT_SYS_STATUS_TEXT'])},
                    {"label": "Latitude", "value": get_latlon()},
                    {"label": "Longitude", "value": get_latlon()},
                ]
            })
            internal_order = check_node({
                "key": str(row['ITM_INTERNAL_ORDER']),
                "group": "InternalOrders",
                "status": "CustomInternalOrders",
                "title": "IO %s" % str(row['ITM_INTERNAL_ORDER']),
                "icon": "sap-icon://customer-order-entry",
                "attributes": [
                    {"label": "EntityType", "value": "Internal Order"},
                    {"label": "Latitude", "value": get_latlon()},
                    {"label": "Longitude", "value": get_latlon()},
                ]
            })
            program = check_node({
                "key": str(row['ITM_ZPR_PRG_ID']),
                "group": "Programs",
                "status": "CustomProgram",
                "title": "Program %s" % str(row['ITM_ZPR_PRG_ID']),
                "icon": "sap-icon://program-triangles-2",
                "attributes": [
                    {"label": "EntityType", "value": "Program"},
                    {"label": "Latitude", "value": get_latlon()},
                    {"label": "Longitude", "value": get_latlon()},
                ]
            })
            classification = check_node({
                "key": str(row['BIC_PPORATAG']),
                "group": "Classifications",
                "status": "CustomClassification",
                "title": "Classification %s" % str(row['CAT_NAME']),
                "icon": "sap-icon://blank-tag",
                "attributes": [
                    {"label": "EntityType", "value": "Classification"},
                    {"label": "Latitude", "value": get_latlon()},
                    {"label": "Longitude", "value": get_latlon()},
                ]
            })
            delivery = check_node({
                "key": str(row['ITM_DELIVERY_NAME_LONG']),
                "group": "Delivery",
                "status": "CustomDelivery",
                "title": str(row['ITM_DELIVERY_NAME_LONG']),
                "icon": "sap-icon://supplier",
                "attributes": [
                    {"label": "EntityType", "value": "Delivery"},
                    {"label": "Latitude", "value": get_latlon()},
                    {"label": "Longitude", "value": get_latlon()},
                ]
            })
            # Break out person responsible

            make_line(r_to=portfolio, r_from=portfolio_element, r_type="PartOf")
            make_line(r_to=portfolio_element, r_from=logical_product, r_type="PartOf")
            make_line(r_to=logical_product, r_from=initiative, r_type="PartOf")
            make_line(r_to=initiative, r_from=item, r_type="PartOf")
            make_line(r_to=item, r_from=cproject, r_type="PartOf")
            make_line(r_to=internal_order, r_from=cproject, r_type="CollectsWith")
            make_line(r_to=cproject, r_from=program, r_type="PartOf")
            make_line(r_to=classification, r_from=portfolio_element, r_type="ClassifiedAs")
            make_line(r_to=cproject, r_from=delivery, r_type="DeliveredBy")
            if index > i:
                print('[%s_graph_eppm] Ending' % (get_datetime()))
                return({"graphs": [
                    {
                        "nodes": r['nodes'],
                        "lines": r['lines'],
                        "groups": r['groups']
                    }
                ]})

        print('[%s_graph_eppm] Ending' % (get_datetime()))
        return r

    def hash_node(self, node):

        node_id = ""
        for k in node.keys():
            node_id+=str(node[k])
            node_id = hashlib.md5(str(node_id).encode()).hexdigest()

        return node_id

    def file_type_check(self, key_list):
        """
        Expects a set of keys to compare to the known keys.
        Compares the lists to return the file type with the max score
        :param key_list:
        :return:
        """
        key_list = [x.lower().replace(' ', '') for x in key_list.to_list()]
        score = {}
        for ftype in self.maps:
            score[ftype] = 0
            for k in key_list:
                if k in self.maps[ftype]["headers"]:
                    score[ftype]+=1
        for ftype in score:
            if score[ftype] > 0:
                score[ftype] = len(key_list) / len(self.maps[ftype]["headers"])
        ftype = max(score.items(), key=operator.itemgetter(1))[0]
        if score[ftype] == 0:
            check = {
                "name": None,
                "score": 0
            }
        # Divide the length of the key_list with the length of the ftype.keys to return a probability rather than integer
        else:
            check = {
                "name": ftype,
                "score": score[ftype]
            }
        return check

    def create_edge(self, **kwargs):
        if self.check_index_edges("%sTo%sFrom%s" % (kwargs['edgeType'], kwargs['fromNode'], kwargs['toNode'])):
            return
        else:
            self.index['edges'].append("%sTo%sFrom%s" % (kwargs['edgeType'], kwargs['fromNode'], kwargs['toNode']))
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
        Create a hashkey that will be used to resolve entity keys on merged entities
        TODO Method to update the hashkey on merge and another method to add the multiple hashkeys to the index.
        index: {entity1: 1, entityOne, 1}
        Add the node to the index

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
        if 'class_name' in kwargs.keys() or 'EntityType' in kwargs.keys():
            if 'EntityType' in kwargs.keys():
                kwargs["class_name"] = kwargs["EntityType"]
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
            # Check the index
            hash_key, check = self.check_index_nodes(**kwargs)
            if check:
                formatted_node = self.format_node(
                    key=hash_key,
                    class_name=kwargs['class_name'],
                    title=title,
                    status=status,
                    icon=icon,
                    attributes=attributes
                )
                message = '[%s_%s_create_node] Node %s exists' % (get_datetime(), self.db_name, thisKey)
                return {"message": message, "data": formatted_node}
            labels = labels + ", hashkey"
            values = values + ", '%s'" % hash_key
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
                    # Update the index with the hash_key identified before and the key created by the DB
                    self.index['nodes'][hash_key] = key
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

    def check_index_nodes(self, **kwargs):
        """
        Use the nodeKeys to cycle through in sequential order and match the input attributes to build a hash string in
        the same format of previous nodes. If the node exists, return the key. Otherwise return None.
        self.nodeKeys = ['class_name', 'title', 'FirstName', 'LastName', 'Gender', 'DateOfBirth', 'PlaceOfBirth',
            'Name', 'Owner', 'Classification', 'Category', 'Latitude', 'Longitude', 'Description',
            'EndDate', 'StartDate', 'DateCreated']
        :param kwargs:
        :return:
        """
        hash_str = ""
        for k in self.nodeKeys:
            if k in kwargs.keys():
                if kwargs[k] != "":
                    # Remove commas since this will be a str treated as a list
                    hash_str += clean_concat(str(kwargs[k]).replace(",", ""))
        # Change the str to a hash string value TODO: evaluate method for robustness in terms of unique values produced
                hash_str = hashlib.md5(str(hash_str).encode()).hexdigest()
        if hash_str in self.index['nodes'].keys():
            return self.index['nodes'][hash_str], True
        else:
            return hash_str, False

    def check_index_edges(self, edge):
        """
        Use the edge hash to check if it is in the index
        :param kwargs:
        :return:
        """
        if edge in self.index['edges']:
            return True
        else:
            return False

    def get_hash_keys(self):
        """
        Get the key, hash_key pair that is used for the index
        :return:
        """
        r = self.client.command('''
        select key, hash from V
        ''')

    def create_index(self):
        """
        Fill the index of a database to be used for entity resolution in data collection
        :return:
        """

        self.open_db()
        r = self.client.command('''
        select key, hashkey, title, class_name,  
        DateOfBirth, PlaceOfBirth, FirstName, LastName, Gender, 
        Name, Owner, Classification,
        Category, Latitude, Longitude, Description, 
        EndDate, StartDate, DateCreated, 
        In().key as InKeys, OUT().key as OutKeys, OutE().@class, InE().@class from V
        ''')
        for i in r:
            hash = ""
            rec = i.oRecordData
            # Create a single string to assign to the key TODO change to get hashkey and sep where comma
            for k in self.nodeKeys:
                if k in rec.keys():
                    if rec[k] != "":
                        hash+=str(rec[k])
            hash = clean_concat(hash)
            if hash not in self.index.keys():
                self.index['nodes'][hash] = rec['key']
            # Make
            if len(rec['OutKeys']) > 0:
                if len(rec['OutKeys']) == len(rec['OutE']):
                    for rkey, rtyp in zip(rec['OutKeys'], rec['OutE']):
                        self.index['edges'].append("%sTo%sFrom%s" % (rtyp, rec['key'], rkey))
            if len(rec['InKeys']) > 0:
                if len(rec['InKeys']) == len(rec['InE']):
                    for rkey, rtyp in zip(rec['InKeys'], rec['InE']):
                        self.index['edges'].append("%sTo%sFrom%s" % (rtyp, rkey, rec['key']))

        click.echo('[%s_%s_create_index] Created index with %s nodes and %s edges' % (
            get_datetime(), self.db_name, len(self.index['nodes']), len(self.index['edges'])))

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
        if self.db_name == "OSINT":
            self.create_indexes()

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

    def merge_nodes(self, **kwargs):
        """
        Enforces the value of a 3 step process in which records are assigned a single key based on DB sequence but also
        a hashkey that represents several instances of the same record. The first step is to normalize all new records
        into a hashkey that uses basic attributes/fields of a record. The normalization process changes the record into
        a lowercase string with all spaces and punctuation removed. For example a person's names and DoB if available are
        reduced. Then the record is hashed and compared against an index of DB_key and hash pairs. A DB_Key to hash_pair
        is 1 to many. When a new record is created, the hash_key is compared to the index and assigned to the key of that
        hashed normalized string. This reduces entire bodies of text down to a single hash that can be compared. When
        merged, the B record is destroyed and replaced with the A key.
        Input: node_A key, node_B key
        Get the hash of each
        Update the node_A hash_str to be a combination of the 2 with a , sep
        Update the index by changing the key of the node_B hash to the node_A key
        :param kwargs:
        :return:
        """
        if 'node_A' in kwargs.keys() and 'node_B' in kwargs.keys():
            results = "Merged node %d into %d resulting in " % (kwargs['node_B'], kwargs['node_A'])
            # Get the relationships and hashkeys for both the A and B nodes
            r = self.client.command('''
                select hashkey, @class, key,
                In().key as InKeys, In().class_name as n_in_class, 
                Out().key as OutKeys, Out().class_name as n_out_class, OutE().@class, InE().@class 
                from V where key in [%d, %d]''' % (kwargs['node_A'], kwargs['node_B']))
            try:
                A = r[0].oRecordData
            except:
                return "No record for %d" % kwargs['node_A']
            try:
                B = r[1].oRecordData
            except:
                return "No record for %d" % kwargs['node_A']

            A['rels'] = []
            B['rels'] = []
            # Format A and B so relations can easily be compared through dictionaries within lists. Use a dir for direction
            for n in [A, B]:
                if (len(n['OutKeys']) == len(n['OutE'])) and len(n['OutKeys']) > 0:
                    for k, l, c in zip(n['OutKeys'], n['OutE'], n['n_out_class']):
                        n['rels'].append({
                            "to": k,
                            "edgeType": l,
                            "dir": "out",
                            "class": c
                        })
                # change of the from since it's an incoming edge
                if (len(n['InKeys']) == len(n['InE'])) and len(n['InKeys']) > 0:
                    for k, l, c in zip(n['InKeys'], n['InE'], n['n_in_class']):
                        n['rels'].append({
                            "from": k,
                            "edgeType": l,
                            "dir": "in",
                            "class": c
                        })

            # Check all the relationships for B and if it is not in A's relationships, create the rel using the dir
            i = 0
            for rel in B['rels']:
                if rel not in A['rels']:
                    i+=1
                    if rel['dir'] == "out":
                        self.create_edge(fromClass=A['class'], fromNode=A['key'], toClass=rel['class'],
                                         toNode=rel['to'], edgeType=rel['edgeType'])
                    else:
                        self.create_edge(fromClass=rel['class'], fromNode=rel['to'], toClass=A['class'],
                                         toNode=A['key'], edgeType=rel['edgeType'])
            results+= "%d new relations." % i

            # Update the hashkey of the A node for future indexing
            newHashKey = A['hashkey'] + "," + B['hashkey']
            self.update(key=A['key'], var="hashkey", val=newHashKey, class_name=A['class'])

            # Delete the B node
            self.delete_node(key=B['key'], class_name=B['class'])

        else:
            results = "Need both an A node and B node."
        return results

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


    def create_indexes(self):
        '''
        Create the indexes for each of the out-of-the-box classes
        '''
        click.echo('[%s_OSINTserver_create_indexes] Creating indexes' % (get_datetime()))
        # Event
        sql = '''
        CREATE INDEX Event.search_fulltext ON Event(Description, StartDate, EndDate) FULLTEXT ENGINE LUCENE METADATA
                  {
                    "default": "org.apache.lucene.analysis.standard.StandardAnalyzer",
                    "index": "org.apache.lucene.analysis.en.EnglishAnalyzer",
                    "query": "org.apache.lucene.analysis.standard.StandardAnalyzer",
                    "analyzer": "org.apache.lucene.analysis.en.EnglishAnalyzer",
                    "allowLeadingWildcard": true
                  }
        '''
        self.client.command(sql)
        # CVE Classes
        for cve in ["AttackPattern", "Campaign", "CourseOfAction", "Identity",
                    "Indicator", "IntrusionSet", "Malware", "ObservedData",
                    "Report", "Sighting", "ThreatActor", "Tool", "Vulnerability"]:
            sql = '''
            CREATE INDEX %s.search_fulltext ON Event(description) FULLTEXT ENGINE LUCENE METADATA
                      {
                        "default": "org.apache.lucene.analysis.standard.StandardAnalyzer",
                        "index": "org.apache.lucene.analysis.en.EnglishAnalyzer",
                        "query": "org.apache.lucene.analysis.standard.StandardAnalyzer",
                        "analyzer": "org.apache.lucene.analysis.en.EnglishAnalyzer",
                        "allowLeadingWildcard": true
                      }
            ''' % cve
            self.client.command(sql)
        click.echo('[%s_OSINTserver_create_indexes] Indexes complete' % (get_datetime()))

