import os
import random
import click
import numpy as np
from apiserver.blueprints.home.models import ODB
from apiserver.utils import get_datetime, change_if_number, clean
from apiserver.blueprints.game.content import content

sPlayer = "Player"
sResource = "Resource"
sGame = "Game"
sMove = "Move"
sEffect = "Effect"
sIncludes = "Includes"
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
                "round": "integer",
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
                "current_round": "integer",
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
        game = self.create_node(class_name=sGame, name=kwargs["gameName"], created=get_datetime(), current_round=0)
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
                elif type(kwargs[k]) == bool:
                    sql = sql + "%s = '%s', " % (k, kwargs[k])
                else:
                    sql = sql + "%s = '%s', " % (k, clean(kwargs[k]))
        sql = sql[:len(sql)-2] + " where key = %s" % kwargs['id']# remove last comma and put filter
        click.echo("[%s_game_update_node]: Running sql\n%s" % (get_datetime(), sql))
        self.client.command(sql)

    def create_move(self, **kwargs):
        """
        Create a move that will be run through the effects application engine when the
        Game current round = the move assigned round to give players availability to delay

        :param kwargs:
        :return:
        """
        move = {
            "created": get_datetime(),
            "round": kwargs['round'],
            "class_name": sMove,
            "description": "string",
            "player": kwargs['playerKey']
        }
        m = self.create_node(**move)
        for e in kwargs['effectKeys']:
            self.create_edge(fromClass=sMove, toClass=sEffect, fromNode=m['data']['key'], toNode=e, edgeType=sIncludes)
        for t in kwargs['targetKeys']:
            self.create_edge(fromClass=sMove, toClass=sResource, fromNode=m['data']['key'], toNode=t, edgeType=sIncludes)
        for r in kwargs['resourceKeys']:
            self.create_edge(fromClass=sMove, toClass=sResource, fromNode=m['data']['key'], toNode=r, edgeType=sIncludes)

        newGameState = self.get_game(gameKey=kwargs['gameKey'])
        newGameState['result'] = move['round']
        return newGameState

    def run_move(self, **kwargs):
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
        offenceWin = "Unknown"
        if len(self.gameState['nodes']) < 1:
            # Exception Handling one
            return {'result': 'No game with key %s' % kwargs['gameKey']}
        # Assign to a Move dictionary
        move = {
            'resources': [],
            'targets': [],
            'effects': [],
            'result': "Effects:",
            'totalOffence': 0,
            'totalDefence': 0,
        }
        # Check effects and load full data into new dictionary
        for e in kwargs['effectKeys']:
            effect = self.get_node(e)
            if not effect:
                # Exception Handling two
                return {'result': 'No effect with key %s in game %s' % (e, kwargs['gameKey'])}
            move['effects'].append(effect)
            move['result'] = "\n[%s] Value: %s Goal: %s" % (e, effect['value'], effect['goal'])
        move['result'] = move['result'] + "\nResources:"
        # Check resources and load full data into new dictionary
        for r in kwargs['resourceKeys']:
            r = self.get_node(r)
            move['resources'].append(r)
            move['totalOffence'] = move['totalOffence'] + r['offence']
            move['result'] = move['result'] + "\n%s: %s " % (r['name'], r['hitpoints'])
        move['result'] = move['result'] + "\nMove Targets"
        # Check targets and load full data into new dictionary
        for r in kwargs['targetKeys']:
            r = self.get_node(r)
            if r['class_name'] == sResource:
                move['totalDefence'] = move['totalDefence'] + r['defence']
                move['targets'].append(r)
                move['result'] = move['result'] + "\n%s: %s " % (r['name'], r['hitpoints'])
            # Else it's an effect and can be related to this effect?
        # Check who the winner is
        if move['totalOffence'] > move['totalDefence']:
            move['result'] = move['result'] + "\nOffence wins:"
            for r in move['targets']:
                r['hitpoints'] = r['hitpoints'] - random.randint(0, int(move['totalOffence']/len(move['resources'])))
                if r['hitpoints'] < 0:
                    r['active'] = False
                else:
                    r['active'] = True
                move['result'] = move['result'] + "\n%s: %s " % (r['name'], r['hitpoints'])
                # Update the node
                self.update_node(**r)
                offenceWin = True
        elif move['totalOffence'] < move['totalDefence']:
            move['result'] = move['result'] + "\nDefence wins:"
            for r in move['resources']:
                r['hitpoints'] = r['hitpoints'] - random.randint(0, int(move['totalDefence']/len(move['targets'])))
                if r['hitpoints'] < 0:
                    r['active'] = False
                else:
                    r['active'] = True
                move['result'] = move['result'] + "\n%s: %s " % (r['name'], r['hitpoints'])
                # Update the node
                self.update_node(**r)
                offenceWin = False
        else:
            move['result'] = move['result'] + "\nStalemate:"
        if offenceWin != "Unknown":
            move['result'] = move['result'] + "\nEffect results:"
            for effect in move['effects']:
                effect = self.apply_effect(effect, offenceWin)
                move['result'] = move['result'] + "\n[%s]: %s" % (effect['id'], effect['value'])


    def apply_effect(self, effect, result):
        """
        E 1469
        R 1481, 1485, 1489
        T 1592
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
        self.update_node(**effect)
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

    @staticmethod
    def load_record(m, currentMove):
        if m.oRecordData['e_key'] not in currentMove['effectKeys']:
            currentMove['effectKeys'].append(m.oRecordData['e_key'])
        if m.oRecordData['r_key'] not in currentMove['resourceKeys'] and m.oRecordData['r_player'] == currentMove[
            'player']:
            currentMove['resourceKeys'].append(m.oRecordData['r_key'])
        if m.oRecordData['r_key'] not in currentMove['targetKeys'] and m.oRecordData['r_player'] != currentMove[
            'player']:
            currentMove['targetKeys'].append(m.oRecordData['r_key'])
        return currentMove

    def get_moves(self):
        """
        Get the moves based on match of resources and effects. Query returns all moves in the same format they are passed
        into the run_move and create_move function from the UX.
        Use a round_count dictionary to determine the trigger for running the moves. When all players have entered at least
        one move, then the round can iterate to the next.
            round_count{ 1: [player1, player2], 2: [player1], current_round_moves[player1Move, player2Move]}
            If the current_round is 1 and the total amount of players is 2, then the above example will trigger to run
            the moves. The moves are run in order in which they were received based on the timestamp and updated with a
            new timestamp for end time.
        If the trigger criteria is met, then determine the gameState current round and run all moves for that round.

        Added Value: Players can set up the same move for multiple rounds and can continue adding moves to any given round
        until all players have entered at least 1 move. TODO prevent same move being added to the same round.
        :return:
        """

        query = self.client.command('''
        match {class: Resource, as: r}.in('Includes')
        {class: Move, as: m}.out('Includes')
        {class: Effect, as: e} 
        return m.key, m.round, r.key, e.key, m.player, r.player, m.created
        ''')
        round_count = {'current_round': self.gameState['current_round'], 'moves': []}
        Moves = []
        currentMove = {'key': 0}
        for m in query:
            if m.oRecordData['m_key'] == currentMove['key']:
                currentMove = self.load_record(m, currentMove)
            else:
                # Iteration 1, don't fill the array, switch to the new one and continue on. It 2, first move is appended
                if currentMove['key'] != 0:
                    Moves.append(currentMove)
                    if currentMove['round'] == self.gameState['current_round']:
                        round_count['moves'].append(currentMove)
                currentMove = {
                    'key': m.oRecordData['m_key'],
                    'player': m.oRecordData['m_player'],
                    'round': m.oRecordData['m_round'],
                    'created': m.oRecordData['m_created'],
                    'gameKey': self.gameState['key'],
                    'effectKeys': [],
                    'resourceKeys': [],
                    'targetKeys': []
                }
                currentMove = self.load_record(m, currentMove)
            if m.oRecordData['m_round'] in round_count.keys():
                if m.oRecordData['m_player'] not in round_count[m.oRecordData['m_round']]:
                    # Only execute if the player is not there, enabling multiple moves for any player and the most for the fastest
                    round_count[m.oRecordData['m_round']].append(m.oRecordData['m_player'])
            else:
                round_count[m.oRecordData['m_round']] = []

        if self.gameState['current_round'] in round_count.keys():
            if len(round_count[self.gameState['current_round']]) % len(self.gameState['players']) == 0:
                # Stage the moves and the sort them by create_date
                round_count['moves'].sort(key=lambda item: item['created'])
                for m in round_count['moves']:
                    self.run_move(**m)
                self.gameState['current_round']+=1
                self.update_node(class_name=sGame, id=self.gameState['key'], current_round=self.gameState['current_round'])

        return Moves

    def get_game(self, **kwargs):
        """
        Get a game that was saved to the Database in the following structure:
        Game -> Players -> Resources
        and return the same format of a GameState as in the Game setup. When filling the moves, the gameState may change
        based on that function's trigger to update the round and run moves with effects.
        :return:
        """
        self.gameState = {
            "nodes": [],
            "links": [],
            "players": [],
            "gameName": None,
            "moves": [],
            "stability": 0,
            "current_round": 0
        }
        sql = ('''
        match {class: Game, as: g, where: (key = '%s')}.out(HasPlayer){class: V, as: p}.out(){class: V, as: r} 
        return g.name, g.current_round, p.key, p.name, p.created, p.group, p.score, p.status, p.icon, 
        r.key, r.name, r.ascope, r.crimefilled, r.type, r.category, r.created, r.description, r.player, 
        r.icon, r.offence, r.defence, r.hitpoints, r.speed, r.xpos, r.ypos, r.zpos, r.group, r.active, r.deleted, r.value,
        r.class_name, r.color, r.objective, r.phase, r.measure, r.indicator, r.strat, r.goal, r.fontColor, r.symbolType
        ''' % kwargs['gameKey'])
        nodeKeys = [] # Quality check to ensure no duplicates sent
        self.gameState['key'] = kwargs['gameKey']

        click.echo("[%s_gameserver_get_game] SQL: %s" % (get_datetime(), sql))
        for o in self.client.command(sql):
            if not self.gameState['gameName']:
                self.gameState['gameName'] = o.oRecordData['g_name']
                self.gameState['current_round'] = o.oRecordData['g_current_round']
                current_round = int(o.oRecordData['g_current_round'])
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
        self.gameState['moves'] = self.get_moves()
        # Running moves might change the gameState so check to see if there was a change and then update
        if self.gameState['current_round'] != current_round:
            self.get_game(gameKey=kwargs['gameKey'])

        return self.gameState

    def get_move(self, **kwargs):
        """
        Get a single move by key
        Use the load record method to get the keys properly aligned based on the links to resources and effects
        :param kwargs:
        :return:
        """

        query = self.client.command('''
        match {class: Resource, as: r}.in('Includes')
        {class: Move, as: m, where:(key = '%s')}.out('Includes')
        {class: Effect, as: e} 
        return m.key, m.round, r.key, e.key, m.player, r.player, m.created
        ''' % kwargs['moveKey'])
        Move = {
            'key': kwargs['moveKey'],
            'key': query[0].oRecordData['m_key'],
            'player': query[0].oRecordData['m_player'],
            'round': query[0].oRecordData['m_round'],
            'created': query[0].oRecordData['m_created'],
            'gameKey': kwargs['gameKey'],
            'effectKeys': [],
            'resourceKeys': [],
            'targetKeys': []
        }
        for m in query:
            Move = self.load_record(m, Move)

        return Move

    def update_move(self, **kwargs):
        """
        Allow a user to add or remove resources, targets, or effects in Moves
        :param kwargs:
        :return:
        """
        Move = self.get_move(moveKey=kwargs['moveKey'], gameKey=kwargs['gameKey'])
        if kwargs['round'] != Move['round']:
            self.update_node(class_name=sMove, id=Move['key'], round=kwargs['round'])
        for e in kwargs['effectKeys']:
            if e in Move['effectKeys']:
                self.delete_edge(edgeType=sIncludes, fromClass=sMove, toClass=sEffect, fromNode=kwargs['gameKey'], toNode=e)
            else:
                self.create_edge(edgeType=sIncludes, fromClass=sMove, toClass=sEffect, fromNode=kwargs['gameKey'], toNode=e)
        for e in kwargs['resourceKeys']:
            if e in Move['resourceKeys']:
                self.delete_edge(edgeType=sIncludes, fromClass=sMove, toClass=sResource, fromNode=kwargs['gameKey'], toNode=e)
            else:
                self.create_edge(edgeType=sIncludes, fromClass=sMove, toClass=sResource, fromNode=kwargs['gameKey'], toNode=e)
        for e in kwargs['targetKeys']:
            if e in Move['targetKeys']:
                self.delete_edge(edgeType=sIncludes, fromClass=sMove, toClass=sResource, fromNode=kwargs['gameKey'], toNode=e)
            else:
                self.create_edge(edgeType=sIncludes, fromClass=sMove, toClass=sResource, fromNode=kwargs['gameKey'], toNode=e)

        self.get_game(gameKey=kwargs['gameKey'])
        return self.gameState

