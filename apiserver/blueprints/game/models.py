import os
import random
import click
import numpy as np
from apiserver.blueprints.home.models import ODB
from apiserver.utils import get_datetime, change_if_number
from apiserver.blueprints.game.content import content

sPlayer = "Player"
sResource = "Resource"
sGame = "Game"
sMove = "Move"
sEffect = "Effect"
#TODO UserType to determine if regular player or master for view options in UX
#TODO color, fontColor, size (200), symbolType (circle, cross, diamond, square, star, triangle, wye)


class Game(ODB):

    def __init__(self, db_name="Game"):
        ODB.__init__(self, db_name)
        self.db_name = db_name
        self.norm = {'mean': 50, 'stdev': 18}
        self.datapath = os.path.join(os.path.join(os.getcwd(), 'data'))
        self.no_update = ['id', 'key', 'class_name', 'color', 'created', 'deleted', 'icon', 'offence', 'defence']
        self.styling = {
            "Area": "square",
            "Structure": "cross",
            "Capability": "circle",
            "Organisation": "diamond",
            "Person": "star",
            "Event": "triangle",
            "Cyber": "#f50505",
            "Research": "#ff1241",
            "Information": "#47102f",
            "Military": "#214710",
            "Economic": "#097015",
            "Financial": "#35ff08",
            "Intelligence": "#02041f",
            "Legal": "#0894ff",
            "Law Enforcement": "#140dff",
            "Environment": "#fff30f",
            "Diplomatic": "#ffa008"
        }
        self.models = {
            sPlayer: {
                "key": "integer",
                "created": "datetime",
                "name": "string",
                "score": "string",
                "resources": "string",
                "class": "V",
                "category": "string"
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
                "player": "string",
                "color": "string",
                "fontColor": "string",
                "symbolType": "string"
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
            },
            sGame: {
                "key": "integer",
                "name": "string",
                "created": "datetime",
                "ended": "datetime",
                "icon": "string",
                "class": "V"
            },
            sEffect: {
                "key": "integer",
                "name": "string",
                "player": "string",
                "class": "V",
                "measure": "string",
                "indicator": "string",
                "objective": "string",
                "phase": "string",
                "strat": "string",
                "value": "integer",
                "goal": "integer"
            }
        }
        self.game_names_a = ["Lunar", "Solar", "Jupiter", "Neptune", "Mercury", "Venus", "Pluto", "Saturn", "Uranus"]
        self.game_names_b = ["Blue", "Black", "Yellow", "Red", "Green", "Orange"]
        self.game_names_c = list("ABDCEFGHIJKLMNOPQRSTUVWZYZ")
        self.content = {
            "mpice": content['mpice'],
            "resources": content['resources'],
            "nations": content['nations']
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
        self.gameState = {
            "nodes": [],
            "links": [],
            "players": [],
            "gameName": None,
            "moves": [],
            "stability": 0
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
        Assign colors based on CRIMEFILLED and symbolTypes as ASCOPE
        :param self:
        :param kwargs:
        :return:
        """
        r = random.choice(self.content['resources'])
        # color, fontColor, size (200), symbolType (circle, cross, diamond, square, star, triangle, wye)

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
            active=True,
            player=kwargs['player'],
            color=self.styling[r['crimefilled']],
            symbolType=self.styling[r['ascope']],
            value=int(np.random.normal(loc=self.norm['mean'], scale=self.norm['stdev']))
        )
        return resource

    def create_effect(self, **kwargs):
        e = random.choice(self.content['mpice'])
        effect = self.create_node(
            class_name=sEffect,
            name="%s %s" % (e['Measure'], kwargs['player']),
            objective=e['Objective'],
            phase=e['Phase'],
            value=random.randint(-100, 100),
            goal=random.randint(-100, 100),
            strat=e['Strategy'],
            indicator=e['Indicator'],
            measure=e['Measure'],
            player=kwargs['player']
        )
        return effect

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
        TODO create dungeon master type player: gets dashboard view with inject and arbitration monitoring
        Using the player name and home country create the player and assign resources and priority MPICE effects
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
        playerd3['player'] = player
        playerd3['nodes'].append(player)

        # Assign MPICE priorities
        i = 0
        while i < 10:
            e = self.create_effect(player=kwargs['name'])
            self.create_edge(
                fromNode=player['id'],
                fromClass=sPlayer,
                toNode=e['data']['key'],
                toClass=sEffect,
                edgeType="Owns"
            )
            e = self.node_to_d3(**e['data'])
            playerd3['links'].append({
                "source": player['id'],
                "target": e['id'],
                "value": random.randint(1,3)
            })
            playerd3['nodes'].append(e)
            i+=1

        # Create the resources
        i = 0
        while i < 50:
            r = self.create_resource(homeNation=homeNation, player=kwargs['name'])
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
            r = self.create_resource(player=kwargs['name'],
                                     homeNation=random.choice(list(self.content['nations'].keys())))
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

        playerd3['stability'] = random.randint(-999, 999)

        return playerd3

    def setup_game(self, **kwargs):
        """
        Using the player count, create players and return the game state as a collection of players and their resources
        :param self:
        :param kwargs:
        :return:
        """
        gameState = {
            'gameName': "%s %s-%s%s" % (
                random.choice(self.game_names_a), random.choice(self.game_names_b),
                random.choice(self.game_names_c), random.randint(100, 999)),
            'players': [],
            'moves': [],
            'stability': 0,
            'nodes': [],
            'links': []
        }
        game = self.create_game(gameName=gameState['gameName'])
        gameState['gameKey'] = game['id']
        i = 0
        while i < kwargs['playerCount']:
            player = self.create_player(name="Player%d" % (i + 1))
            self.create_edge(
                fromNode=game['id'],
                fromClass=sGame,
                toNode=player['nodes'][0]['id'],
                toClass=sPlayer,
                edgeType="HasPlayer"
            )
            gameState['players'].append(player['nodes'][0])
            gameState['nodes'] = gameState['nodes'] + player['nodes']
            gameState['links'] = gameState['links'] + player['links']
            i+=1

        return gameState

    def create_game(self, **kwargs):
        """
        Create a node that represents the game so all resources and player nodes can be linked to it
        :param kwargs:
        :return:
        """
        game = self.create_node(class_name=sGame, name=kwargs["gameName"], created=get_datetime())
        return self.node_to_d3(**game['data'])

    def get_game_names(self):
        """
        Get the game names and keys to return for a user select
        :return:
        """
        names = []
        for n in self.client.command("select name, key from Game"):
            names.append({"id": n.oRecordData["key"], "name": n.oRecordData["name"]})

        return names

    def get_node(self, node_id):
        for n in self.gameState['nodes']:
            if n['id'] == int(node_id):
                return n

    def update_node(self, **kwargs):
        """
        Update a game node with attributes
        :param kwargs:
        :return:
        """
        sql = "update %s set " % (kwargs['class_name'])
        for k in kwargs:
            if k not in self.no_update:
                if change_if_number(kwargs[k]):
                    sql = sql + "%s = %s, " % (k, kwargs[k])
                else:
                    sql = sql + "%s = '%s', " % (k, kwargs[k])
        sql = sql[:len(sql)-2] + " where key = %s" % kwargs['id']# remove last comma and put filter
        click.echo("[%s_game_update_node]: Running sql\n%s" % (get_datetime(), sql))
        self.client.command(sql)

    def create_move(self, **kwargs):
        """
        Get the current game state, create a move that uses the resources, targets, and effects
        The move elements' attributes are collected and then the arbitration engine results in
        updated element attributes including a new stability score and other effects
        Move Rules:
        1) Align domains to library similar to CookBook or Rock/Paper/Scissors (Multipliers of offense?)
        2) Use Offense Defense attributes
        3) Update the Database with results
        4) Re-get the game

        :param kwargs:
        :return:
        """
        # Get the latest values for all game pieces involved
        self.get_game(gameKey=kwargs['gameKey'])
        # Assign to a Move dictionary
        effect = self.get_node(kwargs['effectKeys'][0])
        move = {
            'resources' : [],
            'targets': [],
            'totalOffence': 0,
            'totalDefence': 0,
            'effect': effect,
            'result': "Move Effect:\nValue: %s Goal: %s" % (effect['value'], effect['goal'])
        }
        move['result'] = move['result'] + "\nResources:"
        for r in kwargs['resourceKeys']:
            r = self.get_node(r)
            move['resources'].append(r)
            move['totalOffence'] = move['totalOffence'] + r['offence']
            move['result'] = move['result'] +"\n%s: %s " % (r['name'], r['hitpoints'])
        move['result'] = move['result'] + "\nMove Targets"
        for r in kwargs['targetKeys']:
            r = self.get_node(r)
            if r['class_name'] == sResource:
                move['totalDefence'] = move['totalDefence'] + r['defence']
                move['targets'].append(r)
                move['result'] = move['result'] + "\n%s: %s " % (r['name'], r['hitpoints'])
            # Else it's an effect and can be related to this effect?

        # TODO update effect to move towards goal
        if move['totalOffence'] > move['totalDefence']:
            move['result'] = move['result'] + "\nOffence wins:"
            for r in move['targets']:
                r['hitpoints'] = r['hitpoints'] - random.randint(0, int(move['totalOffence']/len(move['resources'])))
                if r['hitpoints'] < 0:
                    r['active'] = False
                move['result'] = move['result'] + "\n%s: %s " % (r['name'], r['hitpoints'])
                # Update the node
                self.update_node(**r)
            move['effect'] = self.apply_effect(move['effect'], True)
            move['result'] = move['result'] + "\nEffect: %s" % (move['effect']['value'])
        elif move['totalOffence'] < move['totalDefence']:
            move['result'] = move['result'] + "\nDefence wins:"
            for r in move['resources']:
                r['hitpoints'] = r['hitpoints'] - random.randint(0, move['totalDefence']/len(move['targets']))
                if r['hitpoints'] < 0:
                    r['active'] = False
                move['result'] = move['result'] + "\n%s: %s " % (r['name'], r['hitpoints'])
                # Update the node
                self.update_node(**r)
            move['effect'] = self.apply_effect(move['effect'], False)
            self.update_node(**effect)
            move['result'] = move['result'] + "\nEffect: %s" % (move['effect']['value'])
        else:
            move['result'] = move['result'] + "\nStalemate:"
        newGameState = self.get_game(gameKey=kwargs['gameKey'])
        newGameState['result'] = move['result']
        return newGameState

    def apply_effect(self, effect, result):
        """
        Using the effect goal, value and result of move, update the effect value
        :param effect:
        :param result:
        :return:
        """
        if result:
            if effect['value'] > effect['goal']:
                effect['value'] = effect['value'] - random.randint(1, 10)
            else:
                effect['value'] = effect['value'] + random.randint(1, 10)
        else:
            if effect['value'] > effect['goal']:
                effect['value'] = effect['value'] + random.randint(1, 10)
            else:
                effect['value'] = effect['value'] - random.randint(1, 10)

        return effect

    def delete_game(self, **kwargs):
        """
        Get a game by the ID and delete all associated nodes
        :param kwargs:
        :return:
        """
        sql = '''
        delete vertex from (select expand( out().out()) from Game where key = %d);
        delete vertex from (select expand( out()) from Game where key = %d);
        delete vertex from Game where key = %d;
        ''' % (kwargs['gameKey'],kwargs['gameKey'], kwargs['gameKey'])
        try:
            message = self.client.batch(sql)
            if message[0] == 1:
                message = "Game %d deleted" % kwargs['gameKey']
            else:
                message = "Game %d doesn't exist" % kwargs['gameKey']
        except Exception as e:
            message = str(e)

        data = {"message": message}

        return data

    def get_game(self, **kwargs):
        """
        Get a game that was saved to the Database in the following structure:
        Game -> Players -> Resources
        and return the same format of a GameState as in the Game setup
        TODO Get moves
        :return:
        """
        self.gameState = {
            "nodes": [],
            "links": [],
            "players": [],
            "gameName": None,
            "moves": [],
            "stability": 0
        }
        sql = ('''
        match {class: Game, as: g, where: (key = '%s')}.out(HasPlayer){class: V, as: p}.out(){class: V, as: r} 
        return g.name, p.key, p.name, p.created, p.group, p.score, p.status, p.icon, 
        r.key, r.name, r.ascope, r.crimefilled, r.type, r.category, r.created, r.description, r.player, 
        r.icon, r.offence, r.defence, r.hitpoints, r.speed, r.xpos, r.ypos, r.zpos, r.group, r.active, r.deleted, r.value,
        r.class_name, r.color, r.objective, r.phase, r.measure, r.indicator, r.strat, r.goal, r.fontColor, r.symbolType
        ''' % kwargs['gameKey'])
        click.echo("[%s_gameserver_get_game] Game state: %s" % (get_datetime(), self.gameState))
        click.echo()
        nodeKeys = [] # Quality check to ensure no duplicates sent
        self.gameState['key'] = kwargs['gameKey']
        click.echo("[%s_gameserver_get_game] SQL: %s" % (get_datetime(), sql))
        for o in self.client.command(sql):
            if not self.gameState['gameName']:
                self.gameState['gameName'] = o.oRecordData['g_name']
                click.echo("[%s_gameserver_get_game] Game name: %s" % (get_datetime(), o.oRecordData['g_name']))
            Player = {
                "id": o.oRecordData['p_key'],
                "name": o.oRecordData['p_name'],
                "icon": o.oRecordData['p_icon'],
                "group": o.oRecordData['p_group'],
                "score": o.oRecordData['p_score'],
                "status": o.oRecordData['p_status'],
                "class_name": "Player"
            }
            if Player not in self.gameState['players']:
                self.gameState['players'].append(Player)
                self.gameState['nodes'].append(Player)
                click.echo("[%s_gameserver_get_game] Player: %s" % (get_datetime(), Player))
            if o.oRecordData['r_class_name'] == sResource:
                Node = {
                    "id": o.oRecordData['r_key'],
                    "name": o.oRecordData['r_name'],
                    "ascope": o.oRecordData['r_ascope'],
                    "crimefilled": o.oRecordData['r_crimefilled'],
                    "type": o.oRecordData['r_type'],
                    "category": o.oRecordData['r_category'],
                    "created": o.oRecordData['r_created'],
                    "description": o.oRecordData['r_description'],
                    "icon": o.oRecordData['r_icon'],
                    "offence": o.oRecordData['r_offence'],
                    "defence": o.oRecordData['r_defence'],
                    "hitpoints": o.oRecordData['r_hitpoints'],
                    "speed": o.oRecordData['r_speed'],
                    "xpos": o.oRecordData['r_xpos'],
                    "ypos": o.oRecordData['r_ypos'],
                    "zpos": o.oRecordData['r_zpos'],
                    "group": o.oRecordData['r_group'],
                    "active": o.oRecordData['r_active'],
                    "deleted": o.oRecordData['r_deleted'],
                    "value": o.oRecordData['r_value'],
                    "player": o.oRecordData['r_player'],
                    "class_name": o.oRecordData['r_class_name'],
                    "color": o.oRecordData['r_color']
                }
            elif o.oRecordData['r_class_name'] == sEffect:
                Node = {
                    "id": o.oRecordData['r_key'],
                    "name": o.oRecordData['r_name'],
                    "class_name": sEffect,
                    "indicator": o.oRecordData['r_indicator'],
                    "measure": o.oRecordData['r_measure'],
                    "objective": o.oRecordData['r_objective'],
                    "phase": o.oRecordData['r_phase'],
                    "player": o.oRecordData['r_player'],
                    "strat": o.oRecordData['r_strat'],
                    "value": o.oRecordData['r_value'],
                    "goal": o.oRecordData['r_goal'],
                }
            if Node['id'] not in nodeKeys:
                self.gameState['nodes'].append(Node)
                self.gameState['links'].append({
                    "source": Player['id'],
                    "target": Node['id'],
                    "value": random.randint(1,3)
                })

        return self.gameState



