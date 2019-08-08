import os
import random
import numpy as np
from apiserver.blueprints.home.models import ODB
from apiserver.utils import get_datetime

sPlayer = "Player"
sResource = "Resource"
sGame = "Game"
sMove = "Move"


class Game(ODB):

    def __init__(self, db_name="Game"):
        ODB.__init__(self, db_name)
        self.db_name = db_name
        self.norm = {'mean': 50, 'stdev': 18}
        self.datapath = os.path.join(os.path.join(os.getcwd(), 'data'))
        self.models = {
            sPlayer: {
                "key": "integer",
                "created": "datetime",
                "name": "string",
                "score": "string",
                "resources": "string",
                "class": "V"
            },
            sResource: {
                "key": "integer",
                "class": "V",
                "name": "string",
                "ascope": "string",
                "crimefilled": "string",
                "type": "string",
                "category": "string",
                "created": "datetime",
                "deleted": "datetime",
                "description": "string",
                "icon": "string",
                "value": "float",
                "offence": "integer",
                "defence": "integer",
                "hitpoints": "integer",
                "speed": "integer",
                "xpos": "float",
                "ypos": "float",
                "zpos": "float",
                "active": "boolean",
            },
            sMove: {
                "key": "integer",
                "name": "string",
                "created": "datetime",
                "ended": "datetime",
                "icon": "string",
                "description": "string",
                "player": "string",
                "class": "V"
            }
        }
        self.content = {
            "resources": [
                {"ascope": "Person", "crimefilled": "Cyber", "type": "Hacker", "category": "Whistleblower"},
                {"ascope": "Area", "crimefilled": "Cyber", "type": "Network", "category": "Website"},
                {"ascope": "Area", "crimefilled": "Cyber", "type": "Network", "category": "WAN"},
                {"ascope": "Organisation", "crimefilled": "Research", "type": "Government", "category": "University"},
                {"ascope": "Person", "crimefilled": "Research", "type": "Educator", "category": "University"},
                {"ascope": "Person", "crimefilled": "Research", "type": "Administrator", "category": "University"},
                {"ascope": "Capability", "crimefilled": "Diplomatic", "type": "Treaty", "category": "Travel"},
                {"ascope": "Capability", "crimefilled": "Diplomatic", "type": "Treaty", "category": "Trade"},
                {"ascope": "Area", "crimefilled": "Environment", "type": "Zone", "category": "Tourist"},
                {"ascope": "Area", "crimefilled": "Information", "type": "Network", "category": "Television"},
                {"ascope": "Capability", "crimefilled": "Diplomatic", "type": "Treaty", "category": "Technology"},
                {"ascope": "Organisation", "crimefilled": "Research", "type": "International",
                 "category": "Technology"},
                {"ascope": "Event", "crimefilled": "Research", "type": "Discovery", "category": "Technology"},
                {"ascope": "Area", "crimefilled": "Research", "type": "Field", "category": "Technology"},
                {"ascope": "Capability", "crimefilled": "Diplomatic", "type": "Treaty", "category": "Strategic"},
                {"ascope": "Person", "crimefilled": "Diplomatic", "type": "Ambassador", "category": "State"},
                {"ascope": "Person", "crimefilled": "Legal", "type": "Judge", "category": "State"},
                {"ascope": "Event", "crimefilled": "Research", "type": "Discovery", "category": "Space"},
                {"ascope": "Organisation", "crimefilled": "Research", "type": "International", "category": "Space"},
                {"ascope": "Organisation", "crimefilled": "Diplomatic", "type": "Political", "category": "Socialist"},
                {"ascope": "Person", "crimefilled": "Information", "type": "Maven", "category": "Social media"},
                {"ascope": "Area", "crimefilled": "Economic", "type": "Zone", "category": "Shared trade"},
                {"ascope": "Event", "crimefilled": "Diplomatic", "type": "Message",
                 "category": "Sensational (Curiosity)"},
                {"ascope": "Person", "crimefilled": "Cyber", "type": "Hacker", "category": "Script Kiddie"},
                {"ascope": "Person", "crimefilled": "Economic", "type": "Director", "category": "Reserve"},
                {"ascope": "Organisation", "crimefilled": "Diplomatic", "type": "Political", "category": "Republican"},
                {"ascope": "Organisation", "crimefilled": "Diplomatic", "type": "Humanitarian", "category": "Relief"},
                {"ascope": "Area", "crimefilled": "Law Enforcement", "type": "Jurisdiction", "category": "Regional"},
                {"ascope": "Person", "crimefilled": "Environment", "type": "Activist", "category": "Rebel"},
                {"ascope": "Area", "crimefilled": "Information", "type": "Network", "category": "Radio"},
                {"ascope": "Person", "crimefilled": "Cyber", "type": "Administrator", "category": "Public Sector"},
                {"ascope": "Person", "crimefilled": "Cyber", "type": "Developer", "category": "Public Sector"},
                {"ascope": "Person", "crimefilled": "Research", "type": "Administrator", "category": "Public School"},
                {"ascope": "Person", "crimefilled": "Research", "type": "Educator", "category": "Public School"},
                {"ascope": "Area", "crimefilled": "Financial", "type": "Market", "category": "Public"},
                {"ascope": "Area", "crimefilled": "Environment", "type": "Zone", "category": "Protected"},
                {"ascope": "Area", "crimefilled": "Legal", "type": "Zone", "category": "Protected"},
                {"ascope": "Person", "crimefilled": "Legal", "type": "Lawyer", "category": "Prosecutor"},
                {"ascope": "Person", "crimefilled": "Research", "type": "Administrator", "category": "Private School"},
                {"ascope": "Person", "crimefilled": "Research", "type": "Educator", "category": "Private School"},
                {"ascope": "Person", "crimefilled": "Cyber", "type": "Administrator", "category": "Private"},
                {"ascope": "Person", "crimefilled": "Cyber", "type": "Developer", "category": "Private"},
                {"ascope": "Area", "crimefilled": "Financial", "type": "Market", "category": "Private"},
                {"ascope": "Area", "crimefilled": "Information", "type": "Network", "category": "Print Distribution"},
                {"ascope": "Structure", "crimefilled": "Diplomatic", "type": "Building",
                 "category": "Political Headquarters"},
                {"ascope": "Person", "crimefilled": "Environment", "type": "Activist", "category": "Policy maker"},
                {"ascope": "Organisation", "crimefilled": "Research", "type": "International", "category": "Physics"},
                {"ascope": "Event", "crimefilled": "Research", "type": "Discovery", "category": "Physics"},
                {"ascope": "Area", "crimefilled": "Research", "type": "Field", "category": "Physics"},
                {"ascope": "Person", "crimefilled": "Law Enforcement", "type": "Police", "category": "Patrol"},
                {"ascope": "Person", "crimefilled": "Environment", "type": "Activist", "category": "Organizer"},
                {"ascope": "Structure", "crimefilled": "Intelligence", "type": "Network", "category": "Operations"},
                {"ascope": "Person", "crimefilled": "Intelligence", "type": "Operator", "category": "Official"},
                {"ascope": "Person", "crimefilled": "Research", "type": "Scientist", "category": "Nuclear"},
                {"ascope": "Organisation", "crimefilled": "Intelligence", "type": "National",
                 "category": "Non-Official"},
                {"ascope": "Person", "crimefilled": "Information", "type": "Maven", "category": "News"},
                {"ascope": "Area", "crimefilled": "Military", "type": "Base", "category": "Navy"},
                {"ascope": "Person", "crimefilled": "Diplomatic", "type": "Ambassador", "category": "National"},
                {"ascope": "Person", "crimefilled": "Legal", "type": "Judge", "category": "National"},
                {"ascope": "Organisation", "crimefilled": "Research", "type": "International", "category": "Medicine"},
                {"ascope": "Area", "crimefilled": "Research", "type": "Field", "category": "Medical"},
                {"ascope": "Organisation", "crimefilled": "Diplomatic", "type": "Humanitarian", "category": "Medical"},
                {"ascope": "Event", "crimefilled": "Research", "type": "Discovery", "category": "Medical"},
                {"ascope": "Structure", "crimefilled": "Intelligence", "type": "Network", "category": "Logistics"},
                {"ascope": "Area", "crimefilled": "Law Enforcement", "type": "Jurisdiction", "category": "Local"},
                {"ascope": "Person", "crimefilled": "Legal", "type": "Judge", "category": "Local"},
                {"ascope": "Person", "crimefilled": "Legal", "type": "Lawyer", "category": "Litigation"},
                {"ascope": "Person", "crimefilled": "Military", "type": "Officer", "category": "Lieutenant"},
                {"ascope": "Organisation", "crimefilled": "Diplomatic", "type": "Political", "category": "Libertarian"},
                {"ascope": "Area", "crimefilled": "Cyber", "type": "Network", "category": "LAN"},
                {"ascope": "Person", "crimefilled": "Financial", "type": "Director",
                 "category": "Investment Management"},
                {"ascope": "Event", "crimefilled": "Diplomatic", "type": "Message", "category": "Inspirational (Hope)"},
                {"ascope": "Person", "crimefilled": "Diplomatic", "type": "Ambassador", "category": "Industry"},
                {"ascope": "Organisation", "crimefilled": "Intelligence", "type": "National", "category": "Industrial"},
                {"ascope": "Person", "crimefilled": "Cyber", "type": "Hacker", "category": "Hacktivist"},
                {"ascope": "Person", "crimefilled": "Cyber", "type": "Hacker", "category": "Green Hat"},
                {"ascope": "Person", "crimefilled": "Military", "type": "Officer", "category": "General"},
                {"ascope": "Area", "crimefilled": "Financial", "type": "Market", "category": "Futures"},
                {"ascope": "Person", "crimefilled": "Environment", "type": "Activist", "category": "Fund raising"},
                {"ascope": "Person", "crimefilled": "Law Enforcement", "type": "Police", "category": "Forensics"},
                {"ascope": "Organisation", "crimefilled": "Intelligence", "type": "National", "category": "Foreign"},
                {"ascope": "Event", "crimefilled": "Diplomatic", "type": "Message", "category": "Factual"},
                {"ascope": "Area", "crimefilled": "Economic", "type": "Zone", "category": "Exclusive trade"},
                {"ascope": "Organisation", "crimefilled": "Diplomatic", "type": "Humanitarian",
                 "category": "Equal Rights"},
                {"ascope": "Organisation", "crimefilled": "Research", "type": "International",
                 "category": "Environment"},
                {"ascope": "Event", "crimefilled": "Research", "type": "Discovery", "category": "Environment"},
                {"ascope": "Area", "crimefilled": "Research", "type": "Field", "category": "Environment"},
                {"ascope": "Person", "crimefilled": "Information", "type": "Maven", "category": "Entertainment"},
                {"ascope": "Area", "crimefilled": "Environment", "type": "Zone", "category": "Endangered"},
                {"ascope": "Structure", "crimefilled": "Diplomatic", "type": "Building", "category": "Embassy"},
                {"ascope": "Person", "crimefilled": "Cyber", "type": "Hacker", "category": "Electromagnetic"},
                {"ascope": "Person", "crimefilled": "Research", "type": "Scientist", "category": "Electromagnetic"},
                {"ascope": "Event", "crimefilled": "Diplomatic", "type": "Message", "category": "Dreadful (Fear)"},
                {"ascope": "Organisation", "crimefilled": "Intelligence", "type": "National", "category": "Domestic"},
                {"ascope": "Area", "crimefilled": "Information", "type": "Network",
                 "category": "Digitial Distribution"},
                {"ascope": "Person", "crimefilled": "Law Enforcement", "type": "Police", "category": "Detective"},
                {"ascope": "Organisation", "crimefilled": "Diplomatic", "type": "Political", "category": "Democrat"},
                {"ascope": "Person", "crimefilled": "Legal", "type": "Lawyer", "category": "Defence"},
                {"ascope": "Area", "crimefilled": "Cyber", "type": "Network", "category": "Deepnet"},
                {"ascope": "Area", "crimefilled": "Cyber", "type": "Network", "category": "Darknet"},
                {"ascope": "Person", "crimefilled": "Cyber", "type": "Hacker", "category": "Cyber"},
                {"ascope": "Person", "crimefilled": "Research", "type": "Scientist", "category": "Cyber"},
                {"ascope": "Area", "crimefilled": "Intelligence", "type": "Region", "category": "Culture"},
                {"ascope": "Area", "crimefilled": "Diplomatic", "type": "Zone", "category": "Cultural"},
                {"ascope": "Area", "crimefilled": "Financial", "type": "Market", "category": "Commodities"},
                {"ascope": "Person", "crimefilled": "Cyber", "type": "Administrator", "category": "Commercial"},
                {"ascope": "Person", "crimefilled": "Cyber", "type": "Developer", "category": "Commercial"},
                {"ascope": "Person", "crimefilled": "Economic", "type": "Director", "category": "Commerce"},
                {"ascope": "Person", "crimefilled": "Military", "type": "Officer", "category": "Colonel"},
                {"ascope": "Person", "crimefilled": "Environment", "type": "Activist", "category": "Citizen"},
                {"ascope": "Person", "crimefilled": "Military", "type": "Officer", "category": "Chief of Staff"},
                {"ascope": "Person", "crimefilled": "Law Enforcement", "type": "Police", "category": "Chief"},
                {"ascope": "Person", "crimefilled": "Cyber", "type": "Hacker", "category": "Chemical"},
                {"ascope": "Person", "crimefilled": "Research", "type": "Scientist", "category": "Chemical"},
                {"ascope": "Person", "crimefilled": "Military", "type": "Officer", "category": "Captain"},
                {"ascope": "Area", "crimefilled": "Diplomatic", "type": "Zone", "category": "Border"},
                {"ascope": "Person", "crimefilled": "Cyber", "type": "Hacker", "category": "Biological"},
                {"ascope": "Person", "crimefilled": "Research", "type": "Scientist", "category": "Biological"},
                {"ascope": "Organisation", "crimefilled": "Law Enforcement", "type": "Professional",
                 "category": "Benefits Association"},
                {"ascope": "Person", "crimefilled": "Cyber", "type": "Hacker", "category": "Behavioral"},
                {"ascope": "Person", "crimefilled": "Research", "type": "Scientist", "category": "Behavioral"},
                {"ascope": "Person", "crimefilled": "Financial", "type": "Director", "category": "Bank"},
                {"ascope": "Area", "crimefilled": "Military", "type": "Base", "category": "Army"},
                {"ascope": "Area", "crimefilled": "Legal", "type": "Zone", "category": "Annex"},
                {"ascope": "Area", "crimefilled": "Military", "type": "Base", "category": "Air Force"},
                {"ascope": "Organisation", "crimefilled": "Environment", "type": "Protection", "category": "Activism"},
            ],
            "nations": {
                "Heyanh Do": {"nwx": 0, "nwy": 0, "nex": 5, "ney": 0, "swx": 0, "swy": 6, "sex": 5, "sey": 6},
                "Van Hua": {"nwx": 5, "nwy": 0, "nex": 11, "ney": 0, "swx": 5, "swy": 6, "sex": 11, "sey": 6},
                "Mazhenda": {"nwx": 11, "nwy": 0, "nex": 14, "ney": 0, "swx": 11, "swy": 18, "sex": 14, "sey": 18},
                "Nava Omrodiye": {"nwx": 14, "nwy": 0, "nex": 18, "ney": 0, "swx": 14, "swy": 21, "sex": 18, "sey": 21},
                "Narednalen": {"nwx": 18, "nwy": 0, "nex": 21, "ney": 0, "swx": 18, "swy": 8, "sex": 21, "sey": 8},
                "Bleszec": {"nwx": 18, "nwy": 8, "nex": 21, "ney": 8, "swx": 18, "swy": 21, "sex": 21, "sey": 21},
                "Sintao": {"nwx": 0, "nwy": 18, "nex": 14, "ney": 18, "swx": 0, "swy": 21, "sex":14, "sey": 21},
                "Dospazha": {"nwx": 3, "nwy": 12, "nex": 11, "ney": 12, "swx": 3, "swy": 18, "sex": 11, "sey": 18},
                "Elonia": {"nwx": 3, "nwy": 6, "nex": 11, "ney": 6, "swx": 3, "swy": 11, "sex": 11, "sey": 11},
                "Vanainen": {"nwx": 0, "nwy": 6, "nex": 3, "ney": 6, "swx": 0, "swy": 18, "sex": 3, "sey": 18}
            }
        }
        self.cache = {
            "nations": [],
            "players": [],
            "resources": [],
            "scoreboard": []
        }
        self.d3data = {
            "nodes": [],
            "links": []
        }

    def node_to_d3(self, **kwargs):
        """
        Expecting the node with attributes, flattens everything into a single level doc

        :param kwargs:
        :return:
        """
        d3 = {}
        for k in kwargs:
            if k != "attributes":
                if k == "key":
                    d3["id"] = kwargs['key']
                else:
                    d3[k] = kwargs[k]
            else:
                i = 0
                for a in kwargs[k]:
                    d3[a['label']] = a['value']
                    i+=1

        return d3

    def create_resource(self, **kwargs):
        """
        Create a random resource or based on specifics in the kwargs
        :param self:
        :param kwargs:
        :return:
        """
        r = random.choice(self.content['resources'])
        xpos, ypos = self.get_nation_based_location(nation=kwargs['homeNation'])
        resource = self.create_node(
            class_name=sResource,
            name="%s %s %s" % (kwargs['homeNation'], r['ascope'], r['crimefilled']),
            ascope=r['ascope'],
            crimefilled=r['crimefilled'],
            type=r['type'],
            category=r['category'],
            created=get_datetime(),
            description="%s %s %s" % (r['type'], r['ascope'], r['crimefilled']),
            icon="TBD",
            offence=int(np.random.normal(loc=self.norm['mean'], scale=self.norm['stdev'])),
            defence=int(np.random.normal(loc=self.norm['mean'], scale=self.norm['stdev'])),
            hitpoints=int(np.random.normal(loc=self.norm['mean'], scale=self.norm['stdev'])),
            speed=int(np.random.normal(loc=self.norm['mean'], scale=self.norm['stdev'])),
            xpos=xpos,
            ypos=ypos,
            group=kwargs['homeNation'],
            zpos=int(np.random.normal(loc=self.norm['mean'], scale=self.norm['stdev'])),
            active=True
        )
        return resource

    def get_nation_based_location(self, **kwargs):
        posx = 0.0
        posy = 0.0
        if 'nation' in kwargs.keys():
            if kwargs['nation'] in self.content['nations'].keys():
                xMin = self.content['nations'][kwargs['nation']]['nwx']
                xMax = self.content['nations'][kwargs['nation']]['nex']
                yMin = self.content['nations'][kwargs['nation']]['ney']
                yMax = self.content['nations'][kwargs['nation']]['sey']
                posx = float(random.randint(xMin, xMax)) + np.random.random()
                posy = float(random.randint(yMin, yMax)) + np.random.random()
        else:
            kwargs['nation'] = random.choice(self.content['nations'].keys())
            xMin = self.content['nations'][kwargs['nation']]['nwx']
            xMax = self.content['nations'][kwargs['nation']]['nex']
            yMin = self.content['nations'][kwargs['nation']]['ney']
            yMax = self.content['nations'][kwargs['nation']]['sey']
            posx = float(random.randint(xMin, xMax)) + np.random.random()
            posy = float(random.randint(yMin, yMax)) + np.random.random()

        return posx, posy

    def create_player(self, **kwargs):
        """
        Using the player name and home country create the player and assign resources
        player and resource data returned as:
         {'message', 'data' { 'key', 'title', 'status', 'attributes' [ {label, value}]}}
        xpos and ypos dependent on the Nation area. Also gives the player access to randomized foreign resources
        :param self:
        :param kwargs:
        :return:
        """
        # Choose the home nation for the player if not selected. Ensure it is not already chosen
        playerd3 = {"nodes": [], "links": []}
        homeNation = "None"
        if 'homeNation' not in kwargs.keys():
            inCache = False
            while not inCache:
                homeNation = random.choice(list(self.content['nations'].keys()))
                if homeNation not in self.cache['nations']:
                    self.cache['nations'].append(homeNation)
                    inCache = True
        else:
            homeNation = kwargs['homeNation']

        # Create the player
        player = self.create_node(
            class_name=sPlayer,
            created=get_datetime(),
            name=kwargs['name'],
            score=0,
            group=homeNation,
            icon="TBD",
            title=kwargs['name']
        )
        player = self.node_to_d3(**player['data'])
        playerd3['nodes'].append(player)

        # Create the resources
        i = 0
        while i < 50:
            r = self.create_resource(homeNation=homeNation)
            self.create_edge(
                fromNode=player['id'],
                fromClass=sPlayer,
                toNode=r['data']['key'],
                toClass=sResource,
                edgeType="Owns"
            )
            r = self.node_to_d3(**r['data'])
            playerd3['links'].append({
                "source": player['id'],
                "target": r['id'],
                "value": random.randint(1,3)
            })
            playerd3['nodes'].append(r)
            i+=1

        i = 0
        while i < 25:
            r = self.create_resource(homeNation=random.choice(list(self.content['nations'].keys())))
            self.create_edge(
                fromNode=player['id'],
                fromClass=sPlayer,
                toNode=r['data']['key'],
                toClass=sResource,
                edgeType="Owns"
            )
            r = self.node_to_d3(**r['data'])
            playerd3['links'].append({
                "source": player['id'],
                "target": r['id'],
                "value": random.randint(1,3)
            })
            playerd3['nodes'].append(r)
            i+=1

        return playerd3

    def setup_game(self, **kwargs):
        """
        Using the player count, create players and return the game state as a collection of players and their resources
        :param self:
        :param kwargs:
        :return:
        """
        gameState = {
            'players': []
        }
        i = 0
        while i < kwargs['playerCount']:
            gameState['players'].append(self.create_player(name="Player%d" % (i+1)))
            i+=1

        return gameState
