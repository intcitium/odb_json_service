import json, random
import click
from apiserver.utils import get_datetime, clean
from apiserver.blueprints.home.models import ODB
import pandas as pd
import numpy as np
import os
import datetime
import json


class Pole(ODB):

    def __init__(self, db_name="POLE"):
        ODB.__init__(self, db_name)
        self.db_name = db_name
        self.ICON_PERSON = "sap-icon://person-placeholder"
        self.ICON_OBJECT = "sap-icon://add-product"
        self.ICON_LOCATION = "sap-icon://map"
        self.ICON_EVENT = "sap-icon://date-time"
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
            "BaseNames": {
                "key": "integer",
                "class": "V",
                "Name": "string",
                "NameType" : "string",
                "NameOrigin": "string"
            }
        }
        self.datapath = os.path.join(os.path.join(os.getcwd(), 'data'))
        self.basebook = None
        self.ParentA_Choices = ["F", "M"]
        self.ParentA_Weights = [.9, .1]
        self.Parent_SameGender_Choices = [True, False]
        self.Parent_SameGender_Weights = [.05, .95]
        self.ParentA_Ages = {'mean': 40, 'stdev': 4.7}
        self.Parent_Age_Difference = {'mean': 3, 'stdev': 4}
        self.Parent_SameLastName_Choices = [True, False]
        self.Parent_SameLastName_Weights = [.8, .2]
        self.Parent_Child_Age_Difference = {'mean': 27, 'stdev': 3.3}
        self.ChildrenCount = {'mean': 2.5, 'stdev': 2.5}
        self.Child_Gender_Choices = ["F", "M", "U"]
        self.Child_Gender_Weights = [.49, .49, .2]
        self.Names = []
        self.LastNames = []
        self.FemaleNames = []
        self.MaleNames = []
        self.Locations = []
        self.AverageAction = {'mean': 3, 'stdev': 1}
        self.Actions_All = ['Crime', 'Education', 'Abuse', 'Health', 'Employment', 'SocialMedia']
        self.Actions_Minor = ['Education', 'Abuse', 'Health', 'SocialMedia']
        self.Actions_Baby = ['Abuse', 'Health']
        self.SimStartDate = datetime.datetime.today().strftime('%Y-%m-%d') + " 00:00:00"
        self.SimRoundLengthMax = 60  # in minutes
        self.POLE = 'POLE_Fusion'
        # In memory DB used for creating simulation data in the format for network graph UX rendering
        self.DB = {'nodes': [],
                   'lines': [],
                   'groups': [],
                   'sims': [],
                   'node_index': [],
                   'group_index': []}
        click.echo('[%s_SimServer_init] Complete' % (get_datetime()))

    def fill_lists(self):

        if 'FemaleNames.json' not in os.listdir(self.datapath):
            click.echo('[%s_SimServer_fill_lists] Creating data file for female names' % (get_datetime()))
            r = self.client.command('select Name from BaseNames where NameType = "F"')
            self.FemaleNames = [n.oRecordData['Name'] for n in r]
            with open(os.path.join(self.datapath, 'FemaleNames.json'), 'w') as f:
                json.dump(self.FemaleNames, f)
        else:
            with open(os.path.join(self.datapath, 'FemaleNames.json'), 'r') as f:
                self.FemaleNames = json.load(f)
        f.close()
        if 'MaleNames.json' not in os.listdir(self.datapath):
            click.echo('[%s_SimServer_fill_lists] Creating data file for male names' % (get_datetime()))
            r = self.client.command('select Name from BaseNames where NameType = "M"')
            self.MaleNames = [n.oRecordData['Name'] for n in r]
            with open(os.path.join(self.datapath, 'MaleNames.json'), 'w') as f:
                json.dump(self.MaleNames, f)
        else:
            with open(os.path.join(self.datapath, 'MaleNames.json'), 'r') as f:
                self.MaleNames = json.load(f)
        f.close()
        if 'LastNames.json' not in os.listdir(self.datapath):
            click.echo('[%s_SimServer_fill_lists] Creating data file for last names' % (get_datetime()))
            r = self.client.command('select Name from BaseNames where NameType = "L"')
            self.LastNames = [n.oRecordData['Name'] for n in r]
            with open(os.path.join(self.datapath, 'LastNames.json'), 'w') as f:
                json.dump(self.LastNames, f)
        else:
            with open(os.path.join(self.datapath, 'LastNames.json'), 'r') as f:
                self.LastNames = json.load(f)
        f.close()
        if 'Locations.json' not in os.listdir(self.datapath):
            click.echo('[%s_SimServer_fill_lists] Creating data file for Locations' % (get_datetime()))
            r = self.client.command('select key, city, Latitude, Longitude, pop, country, icon, title from Location where pop > 0 and city != "" and country != "" ')
            self.Locations = [{
                "key": n.oRecordData['key'],
                "icon": n.oRecordData['icon'],
                "title": n.oRecordData['title'],
                "attributes": [
                    {"label": "city", "value": n.oRecordData['city']},
                    {"label": "Latitude", "value": n.oRecordData['Latitude']},
                    {"label": "Longitude", "value": n.oRecordData['Longitude']},
                    {"label": "pop", "value": n.oRecordData['pop']},
                    {"label": "country", "value": n.oRecordData['country']}
                ]
            } for n in r]
            with open(os.path.join(self.datapath, 'Locations.json'), 'w') as f:
                json.dump(self.Locations, f)
        else:
            with open(os.path.join(self.datapath, 'Locations.json'), 'r') as f:
                self.Locations = json.load(f)
        f.close()

    def check_base_book(self):
        """
        Check if the Names and Locations have been filled
        :return:
        """
        click.echo('[%s_SimServer_init] Checking base sim settings' % (get_datetime()))
        r = self.client.command('select * from BaseNames limit 50')
        if len(r) == 0:
            if not self.basebook:
                click.echo('[%s_SimServer_init] Initializing basebook' % (get_datetime()))
                self.basebook = pd.ExcelFile(os.path.join(self.datapath, 'Base_Book.xlsx'))
            self.set_names()
        r = self.client.command('select * from Location where iso3 != "" limit 50')
        if len(r) == 0:
            if not self.basebook:
                click.echo('[%s_SimServer_init] Initializing basebook' % (get_datetime()))
                self.basebook = pd.ExcelFile(os.path.join(self.datapath, 'Base_Book.xlsx'))
            self.set_locations()
        click.echo('[%s_SimServer_init] Basebook complete' % (get_datetime()))
        if len(self.Locations) == 0:
            self.fill_lists()
        if len(self.MaleNames) == 0:
            self.fill_lists()

        return

    def set_names(self):

        click.echo('[%s_SimServer_init] Starting Names' % (get_datetime()))
        self.Names = self.basebook.parse('Names')
        sql = ""
        i = 0
        for index, row in self.Names.iterrows():
            sql = (sql + '''
            create vertex BaseNames set key = sequence('idseq').next(), Name = '%s', NameType = '%s', NameOrigin = '%s';\n'''
            % (clean(row['Name']), row['Type'], row['Origin']))
            i += 1
        click.echo('[%s_SimServer_init] Running batch with %d Names' % (get_datetime(), i))
        self.client.batch(sql)

    def set_locations(self):
        click.echo('[%s_SimServer_init] Starting Locations' % (get_datetime()))
        self.Locations = self.basebook.parse('Locations')
        sql = ""
        i = 0
        for index, row in self.Locations.iterrows():
            country = clean(str(row['country']))
            city = clean(str(row['city']))
            title = "%s, %s" % (city, country)
            sql = (sql + '''create vertex Location set key = sequence('idseq').next(), city = '%s', icon = '%s', title = '%s', Latitude = %s, Longitude = %s, pop = %s, country = '%s', iso3 = '%s', province = '%s';\n'''
            % (city, self.ICON_LOCATION, title, row['lat'], row['lng'], row['pop'], country, row['iso3'], clean(str(row['province']))))
            i += 1
        click.echo('[%s_SimServer_init] Running batch with %d Locations' % (get_datetime(), i))
        self.client.batch(sql)

    def basebook_setup(self):

        if not self.basebook:
            click.echo('[%s_SimServer_init] Initializing basebook' % (get_datetime()))
            self.basebook = pd.ExcelFile(os.path.join(self.datapath, 'Base_Book.xlsx'))
            self.set_names()
            self.set_locations()
            click.echo('[%s_SimServer_init] Complete with basebook integration' % (get_datetime()))
            self.basebook = True
        else:
            click.echo('[%s_SimServer_init] Basebook already initialized %s' % (get_datetime(), self.basebook))

    def create_event(self, **kwargs):
        """
        Create an event for the ODB silo and simulation run which will produce a JSON
        Create an event for visualization
        Return the event for further use
        :param kwargs:
        :return:
        """
        # Set the standard event properties
        node = {
            'properties': {'icon': "sap-icon://accelerated"}
        }
        # Set the properties which will be returned as 'attributes'
        for k in kwargs:
            if k != 'DateTime':
                node['properties'][k] = kwargs[k]
            else:
                node['properties']['StartDate'] = kwargs[k]
        if 'Category' in kwargs.keys():
            node_title = kwargs['Category']
        else:
            node_title = kwargs['Type']

        # Insert into the appropriate DB
        node = self.create_node(
            **node['properties'],
            class_name='Event',
            source=kwargs['Type']
        )['data']
        node['group'] = kwargs['Type']
        node['status'] = 'Success'
        if node['key'] not in self.DB['node_index']:
            self.DB['nodes'].append(node)
            self.DB['node_index'].append(node['key'])
        # Ensure Groups are aligned
        if "%s%s" % ('Event', kwargs['Type']) not in self.DB['group_index']:
            self.DB['group_index'].append("%s%s" % ('Event', kwargs['Type']))
            self.DB['groups'].append({'title': kwargs['Type'], 'key': kwargs['Type']})

        return node

    def create_location(self, **kwargs):
        """
        :param kwargs:
        :return:
        """

        # Set the standard location properties using the **kwargs to predefine variables through a dictionary
        node = {
            'properties': {'icon': "sap-icon://map"}
        }
        for k in kwargs:
            node['properties'][k] = kwargs[k]
            if str(k).lower() == 'city':
                kwargs['city'] = kwargs[k]
            if str(k).lower() == 'country':
                kwargs['country'] = kwargs[k]
        if not kwargs['city']:
            kwargs['city'] = 'Unknown'
        if not kwargs['country']:
            kwargs['country'] = 'Country'
        node = self.create_node(
            **node['properties'],
            db_name=kwargs['Type'],
            class_name='Location',
            title="%s, %s" % (kwargs['city'], kwargs['country']),
        )['data']
        node['group'] = kwargs['country']
        node['status'] = 'Success'
        if node['key'] not in self.DB['node_index']:
            self.DB['nodes'].append(node)
            self.DB['node_index'].append(node['key'])
        if "%s%s" % ('Location', kwargs['country']) not in self.DB['group_index']:
            self.DB['group_index'].append("%s%s" % ('Location', kwargs['country']))
            self.DB['groups'].append({'title': kwargs['country'], 'key': kwargs['country']})

        return node

    def get_node_att(self, node, att):

        for a in node['attributes']:
            if a['label'] == att:
                return a['value']
        return None

    def update_node_att(self, node, att, val):
        for a in node['attributes']:
            if a['label'] == att:
                a['value'] = val
                return node
        return

    def create_person(self, **kwargs):
        """
        Create a person as a node which can be transferred to any network diagram visualization as a JSON based on
        the SimServer DB. Create the key based on the person's attributes by running the concat_clean operation. Then
        create the group as a family last name. If the family or group record already exists then it will not create it.
        :param kwargs: DateOfBirth, PlaceOfBirth, LastName, FirstName, Gender expected or will fail
        :return: a full record of the person but with a key for creating relations down stream
        """
        # All attributes are saved as label value pairs for display on visualizations

        # Set the standard person properties
        simAction = int(np.random.normal(loc=self.AverageAction['mean'], scale=self.AverageAction['stdev']))
        node = {
            'properties': {
                'icon': "sap-icon://person-placeholder",
                'simaction': simAction,
                'simclock': 0
            }
        }
        for k in kwargs:
            node['properties'][k] = kwargs[k]
        name = "Profile"
        node = self.create_node(
            **node['properties'],
            db_name=kwargs['Type'],
            class_name='Person',
            name=name
        )['data']

        age = self.check_age(datetime.datetime.now(), self.get_node_att(node, 'DateOfBirth'))
        if age in ['Toddler', 'Baby']:
            node['status'] = 'CustomChildStatus'
        elif age in ['Teen']:
            node['status'] = 'CustomTeenStatus'
        elif age in ['Not born']:
            node['status'] = 'CustomNotBornStatus'
        else:
            node['status'] = random.choice(['Success', 'Error'])

        if node['key'] not in self.DB['node_index']:
            self.DB['nodes'].append(node)
            self.DB['node_index'].append(node['key'])
        if kwargs['LastName'] not in self.DB['group_index']:
            self.DB['group_index'].append(kwargs['LastName'])
            self.DB['groups'].append({'title': kwargs['LastName'], 'key': kwargs['LastName']})

        # Sims have an action and clock. Clock is iterated during the simulation as an agent based time. Action is how
        # active the sim is. Higher the number, more likely they are to act given random selector in simulator
        self.DB['sims'].append(node)
        return node

    def create_relation(self, source, target, rtype, sub_net):
        self.DB['lines'].append({'from': source['key'], 'to': target['key'], 'type': rtype})
        self.create_edge(fromNode=source['key'], toNode=target['key'], target_atts=target, edgeType=rtype)
        try:
            sub_net['lines'].append({'from': source['key'], 'to': target['key'], 'type': rtype})
            return sub_net
        except:
            return

    def get_random_city(self):
        city = False
        while not city:
            City = random.choice(self.Locations)
            if "'label': 'city'" in str(City['attributes']):
                return City

    def create_family(self, **kwargs):
        """
        A Family is a group of Persons consisting of 2 parents and at least one child. The status of the family is not set.
        It starts with the core_age of one parent with that parent's gender determined by a variable.
        The core_age should be in the form of days old not years so that a more varied age can be applied to relatives.
        The core_age of parent A is determined through a normal distribution of parent ages
        The core_age of parent B is determined through a n dist of parent age differences and the core_age of parent A
        TODO: Make sim dob time more random and not based on computer time
        :param core_age (int that will determine how many days old and then randomizes DateOfBirth based on today
        :return:
        """
        # Process all the options and set to random lists if none provided.
        # Options are there for loops that re-run the function
        Family = {"lines": []}

        if not self.basebook:
            self.check_base_book()

        if 'core_age' in kwargs:
            core_age = kwargs['core_age'] * 365 + (random.randint(-180, 180))
        else:
            core_age = (int(np.random.normal(loc=self.ParentA_Ages['mean'], scale=self.ParentA_Ages['stdev'])) * 365
                        + random.randint(-180, 180))
        if 'LastName' in kwargs:
            LastName = kwargs['LastName']
        else:
            # TODO Change to random choice lookup
            LastName = random.choice(self.LastNames)

        Message = "Created the %s family:\n" % LastName

        # Create the first parent
        GenderA = random.choices(self.ParentA_Choices, self.ParentA_Weights)[0]
        if GenderA == 'F':
            FirstName = random.choice(self.FemaleNames)
            Message = Message + "Mother: %s born on " % FirstName
        else:
            FirstName = random.choice(self.MaleNames)
            Message = Message + "Father: %s born on " % FirstName
        # Get the place of birth from the simulation base cities
        POB_A = self.get_random_city()
        # Create the person record and key
        tPOB_A = "%s, %s" % (self.get_node_att(POB_A, "city"), self.get_node_att(POB_A, "country"))
        parentA = self.create_person(
            DateOfBirth=(datetime.datetime.now() - datetime.timedelta(days=core_age)).strftime('%Y-%m-%d %H:%M:%S'),
            PlaceOfBirth=tPOB_A,
            LastName=LastName,
            FirstName=FirstName,
            Gender=GenderA,
            Type=self.POLE,
            Category='SIM',
            title="%s %s" % (FirstName, LastName)
        )
        # Create the relation to place of birth
        self.create_relation(parentA, POB_A, 'BornIn', Family)
        # Create the event for birth
        aParentDOB = self.get_node_att(parentA, 'DateOfBirth')
        DOB_A = self.create_event(
            title="Birth %s %s" % (FirstName, LastName),
            Type=self.POLE,
            Category='Birth',
            DateTime=aParentDOB,
            Description='%s %s born on %s in %s.' % (FirstName,
                                                     LastName,
                                                     aParentDOB,
                                                     tPOB_A))
        self.create_relation(parentA, DOB_A, 'BornOn', Family)
        self.create_relation(DOB_A, POB_A, 'OccurredAt', Family)
        Message = Message + "%s in %s.\n" % (aParentDOB, tPOB_A)

        # Create the second parent based on the first parent and simulation settings
        b_core_age = ((core_age + int(np.random.normal(loc=self.Parent_Age_Difference['mean'],
                                                       scale=self.Parent_Age_Difference['stdev'])))
                      + (random.randint(-180, 180)))
        if random.choices(self.Parent_SameGender_Choices, self.Parent_SameGender_Weights)[0]:
            GenderB = GenderA
        else:
            if GenderA == 'F':
                GenderB = 'M'

            else:
                GenderB = 'F'

        if GenderB == 'F':
            # TODO Change to random choice lookup
            FirstName = random.choice(self.FemaleNames)
            Message = Message + "Mother: %s born on " % FirstName
        else:
            # TODO Change to random choice lookup anyrandom.choice
            FirstName = random.choice(self.MaleNames)
            Message = Message + "Father: %s born on " % FirstName
        LastNameB = random.choice(self.LastNames)

        POB_B = self.get_random_city()
        tPOB_B = "%s, %s" % (self.get_node_att(POB_A, "city"), self.get_node_att(POB_A, "country"))
        # Create the person record and key
        parentB = self.create_person(
            DateOfBirth=(datetime.datetime.now() - datetime.timedelta(days=b_core_age)).strftime('%Y-%m-%d %H:%M:%S'),
            PlaceOfBirth=tPOB_B,
            LastName=LastNameB,
            FirstName=FirstName,
            Gender=GenderB,
            Type=self.POLE,
            title="%s %s" % (FirstName, LastName)
        )
        # Create the relation to place of birth
        self.create_relation(parentB, POB_B, 'BornIn', Family)
        # Create the event for birth
        bParentDOB = self.get_node_att(parentB, 'DateOfBirth')
        DOB_B = self.create_event(
            title="Birth %s %s" % (FirstName, LastName),
            DateTime=bParentDOB,
            Type="Event",
            Category='Birth',
            Description='%s %s born on %s in %s.' % (FirstName,
                                                     LastName,
                                                     bParentDOB,
                                                     tPOB_B))
        self.create_relation(parentB, DOB_B, 'BornOn', Family)
        self.create_relation(DOB_B, POB_B, 'OccurredAt', Family)
        Message = Message + "%s in %s.\n" % (bParentDOB, tPOB_B)
        # TODO Create origin based location
        # TODO Create beahvior pattern variables for turn based simulation and agent based motivations

        # Create the relation between the parents
        self.create_relation(parentA, parentB, 'ChildrenWith', Family)
        Family["nodes"] = [parentA, parentB, DOB_A, DOB_B, POB_B, POB_A]

        # Create the children starting with the oldest based on an age derived from random parent age and Sim settings
        core_age = (random.choice([core_age, b_core_age]) / 365 - int(
            np.random.normal(loc=self.Parent_Child_Age_Difference['mean'],
                             scale=self.Parent_Child_Age_Difference['stdev']))) * 365
        i = 0
        children = {}
        LastName = random.choice([LastName, LastNameB])
        childrencount = int(np.random.normal(loc=self.ChildrenCount['mean'], scale=self.ChildrenCount['stdev']))
        if childrencount < 2:
            childrencount = 2
        while i < childrencount:
            Gender = random.choices(self.Child_Gender_Choices, self.Child_Gender_Weights)[0]
            if Gender == 'M':
                FirstName = random.choice(self.MaleNames)
            elif Gender == 'F':
                FirstName = random.choice(self.FemaleNames)
            else:
                FirstName = random.choice(self.FemaleNames)

            POB = random.choice([POB_A, POB_B])
            tPOB = self.get_node_att(POB, "title")
            child = self.create_person(
                DateOfBirth=(datetime.datetime.now() - datetime.timedelta(days=core_age)).strftime('%Y-%m-%d %H:%M:%S'),
                PlaceOfBirth=tPOB,
                LastName=LastName,
                FirstName=FirstName,
                Gender=Gender,
                Type=self.POLE,
                title="%s %s" % (FirstName, LastName)
            )
            Family["nodes"].append(child)
            # Create the relation to place of birth
            self.create_relation(child, POB, 'BornIn', Family)
            # Create the event for birth
            childDOB = self.get_node_att(child, 'DateOfBirth')
            DOB = self.create_event(
                Type=self.POLE,
                Category='Birth',
                DateTime=childDOB,
                Description='%s %s born on %s in %s.' % (FirstName,
                                                         LastName,
                                                         childDOB,
                                                         tPOB))
            Family["nodes"].append(DOB)
            self.create_relation(child, DOB, 'BornOn', Family)
            self.create_relation(DOB, POB, 'OccurredAt', Family)
            children[child['key']] = child
            # Create the relation between the parents
            self.create_relation(parentA, child, 'ParentOf', Family)
            self.create_relation(parentB, child, 'ParentOf', Family)
            Message = Message + "Child %d: %s born on %s in %s\n" % (i+1, FirstName, childDOB, tPOB)
            # Increment the age for next kid
            core_age = core_age - random.randint(300, 1500)
            i += 1
        # Create the sibling relationships
        for c in children:
            for cc in children:
                if cc != c:
                    self.create_relation(children[c], children[cc], 'SiblingOf', Family)

        return {"data": Family, "message": Message}

    @staticmethod
    def check_age(sim_time, DateOfBirth):
        # Check if minor
        DateOfBirth = str(DateOfBirth)
        date18 = datetime.datetime.strptime(DateOfBirth, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(
            days=365 * 18)
        if sim_time < date18:
            # Check if toddler
            date13 = datetime.datetime.strptime(DateOfBirth, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(
                days=365 * 13)
            if sim_time < date13:
                # Check if baby
                date2 = datetime.datetime.strptime(DateOfBirth, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(
                    days=365 * 2)
                if sim_time < date2:
                    # Check if alive yet
                    date0 = datetime.datetime.strptime(DateOfBirth, '%Y-%m-%d %H:%M:%S')
                    if sim_time < date0:
                        return ("Not born")
                    else:
                        return ("Baby")
                else:
                    return ("Toddler")
            else:
                return ("Teen")
        else:
            return ("Adult")

    def choose_action(self, age):

        if age == 'Baby' or age == 'Toddler':
            return random.choice(self.Actions_Baby)
        elif age == 'Teen':
            return random.choice(self.Actions_Minor)
        else:
            return random.choice(self.Actions_All)

    def export_json(self):

        dbjson = os.path.join(self.datapath, 'db.json')
        with open(dbjson, 'w') as db:
            json.dump(self.DB, db)

    def get_json(self):
        dbjson = os.path.join(self.datapath, 'db.json')
        with open(dbjson, 'r') as db:
            self.DB = json.load(db)

    def get_sims(self):
        if len(self.DB['sims']) == 0:
            r = self.client.command('select key, icon, simaction, simclock, DateOfBirth, PlaceOfBirth, LastName, FirstName, Gender, title from Person where name = "Profile" ')
            self.DB['sims'] = [{
                "key": n.oRecordData['key'],
                "icon": n.oRecordData['icon'],
                "title": n.oRecordData['title'],
                "attributes": [
                    {"label": "simaction", "value": n.oRecordData['simaction']},
                    {"label": "simclock", "value": n.oRecordData['simclock']},
                    {"label": "DateOfBirth", "value": n.oRecordData['DateOfBirth']},
                    {"label": "PlaceOfBirth", "value": n.oRecordData['PlaceOfBirth']},
                    {"label": "LastName", "value": n.oRecordData['LastName']},
                    {"label": "FirstName", "value": n.oRecordData['FirstName']},
                    {"label": "Gender", "value": n.oRecordData['Gender']},
                    {"label": "title", "value": n.oRecordData['title']}
                ]
            } for n in r]

    def run_simulation(self, rounds):

        if not self.basebook:
            self.check_base_book()
        if 'Sims.json' not in os.listdir(self.datapath):
            self.fill_lists()
        i = 0
        self.get_sims()
        Simulation = {
            "nodes": list(self.DB['sims']),
            "lines": []
        }
        sim_time = datetime.datetime.strptime(self.SimStartDate, '%Y-%m-%d %H:%M:%S')
        while i < int(rounds):
            '''
            1. Choose sims based on an action number range/filter
            2. Based on the age create an action.
                If child create a school or abuse related event
                If parent create a police or employment related event
            3. Create a location based on Sim Locations
                Choose home as first and add random. 
                If len of locations is < 3 append, else, random create new based on others or select one
            4. Insert the relation of event to person and to locations into the db based on event type

            '''
            for sim in self.DB['sims']:
                try:
                    simclock = int(self.get_node_att(sim, 'simclock'))
                except:
                    simclock = int(self.get_node_att(sim, 'simaction'))
                if simclock > random.randint(1, 9):
                    age = self.check_age(sim_time, self.get_node_att(sim, 'DateOfBirth'))
                    if age == 'Not born':
                        break
                    action = self.choose_action(age)
                    EVT = self.create_event(Type=action,
                                            DateTime=sim_time.strftime('%Y-%m-%d %H:%M:%S'),
                                            Description='%s %s, of %s age was involved with an event related to %s at %s'
                                                        % (self.get_node_att(sim, 'FirstName'),
                                                           self.get_node_att(sim, 'LastName'),
                                                           age, action, sim_time.strftime('%Y-%m-%d %H:%M:%S')))
                    Simulation['nodes'].append(EVT)
                    self.create_relation(EVT, sim, 'Involved', Simulation)
                    # Reset the time to a step in the future based on random time between 1 and max round length
                    # Set to seconds to allow for more interactions in a round
                    sim_time = datetime.datetime.strptime(
                        (sim_time + datetime.timedelta(seconds=random.randint(1, self.SimRoundLengthMax))
                         ).strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
                    # Reset the Sim's clock it's original setting
                    self.update_node_att(sim, 'simclock', int(self.get_node_att(sim, 'simaction')))
                else:
                    self.update_node_att(sim, 'simclock', simclock + 1)
            # Reset the time to a step in the future based on random time between 1 and max round length
            # Set to minutes to allow for a bigger time jump between each round treating the iteration of sims as "bullet time"
            sim_time = datetime.datetime.strptime(
                (sim_time + datetime.timedelta(hours=random.randint(1, self.SimRoundLengthMax))
                 ).strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
            i += 1

        return {'message': 'Simulation complete', 'data': Simulation}

