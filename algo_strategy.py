import gamelib
import random
import math
import warnings
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        random.seed(1234)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global FILTER, ENCRYPTOR, DESTRUCTOR, PING, EMP, SCRAMBLER
        FILTER = config["unitInformation"][0]["shorthand"]
        ENCRYPTOR = config["unitInformation"][1]["shorthand"]
        DESTRUCTOR = config["unitInformation"][2]["shorthand"]
        PING = config["unitInformation"][3]["shorthand"]
        EMP = config["unitInformation"][4]["shorthand"]
        SCRAMBLER = config["unitInformation"][5]["shorthand"]
        # This is a good place to do initial setup
        self.scored_on_locations = []

    
        

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """


    def starter_strategy(self, game_state):

        """
        For defense we will use a spread out layout and some Scramblers early on.
        We will place destructors near locations the opponent managed to score on.
        For offense we will use long range EMPs if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Pings to try and score quickly.
        """
        # First, place basic defenses
        self.build_defences(game_state)
        # Now build reactive defenses based on where the enemy scored
        self.build_reactive_defense(game_state)
        self.stall_with_scramblers(game_state)
        if game_state.get_resource(game_state.CORES) >= 20:
            self.use_extra_cores(game_state)

        # If the turn is less than 5, stall with Scramblers and wait to see enemy's base
        #if game_state.turn_number < 5:

        #else:
        # Now let's analyze the enemy base to see where their defenses are concentrated.
        # If they have many units in the front we can build a line for our EMPs to attack them at long range.

        # They don't have many units in the front so lets figure out their least defended area and send Pings there.

        # Only spawn Ping's every other turn
        # Sending more at once is better since attacks can only hit a single ping at a time
        if game_state.turn_number % 5 == 1:
            if game_state.turn_number % 2 == 1:
                emp_spawn_location_options = [[13, 0], [14, 0]]
                best_location = self.least_damage_spawn_location(game_state, emp_spawn_location_options)
                game_state.attempt_spawn(EMP, best_location, 3)
            # To simplify we will just check sending them from back left and right
            ping_spawn_location_options = [[13, 0], [14, 0]]
            best_location = self.least_damage_spawn_location(game_state, ping_spawn_location_options)
            game_state.attempt_spawn(PING, best_location, 1000)


    def use_extra_cores(self, game_state):
        destructor_spawn_location = [[8,9], [10,9],[12,9], [14,9], [16,9], [18,9]]
        for location in destructor_spawn_location:
            if (game_state.get_resource(game_state.CORES) >= game_state.type_cost(DESTRUCTOR)):
                filter_location = [[location[0], location[1]+1],[location[0]-1, location[1]+1]]
                game_state.attempt_spawn(FILTER, filter_location)
            game_state.attempt_spawn(DESTRUCTOR, location)

        if (game_state.get_resource(game_state.CORES) >= 20):
            encryptor_spawn_location_options = [[13, 2], [14, 2], [13,3], [14,3]]
            game_state.attempt_spawn(ENCRYPTOR, encryptor_spawn_location_options)
        # while (game_state.get_resource(game_state.CORES) >= 20):
        #     build_location = [random.randint(6, 21), random.randint(4,10)]
        #     if(game_state.get_resource(game_state.CORES) >= game_state.type_cost(DESTRUCTOR)):
        #         filter_location = [[build_location[0], build_location[1] + 1], [build_location[0] - 1, build_location[1]],[build_location[0] + 1, build_location[1]]]
        #         game_state.attempt_spawn(FILTER, filter_location)
        #     game_state.attempt_spawn(DESTRUCTOR, build_location)


    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy EMPs can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place destructors that attack enemy units
        destructor_locations = [[0, 13],[1,12],[26,12],[27, 13]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(DESTRUCTOR, destructor_locations)
        filter_locations = [[1, 13], [2, 12], [25, 12], [26, 13]]
        game_state.attempt_spawn(FILTER, filter_locations)
        # Place filters in front of destructors to soak up damage for them
        #filter_locations = [[8, 12], [19, 12]]
        #game_state.attempt_spawn(FILTER, filter_locations)

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build destructor one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+1]
            if (game_state.get_resource(game_state.CORES) >= game_state.type_cost(DESTRUCTOR)):
                filter_location = [[build_location[0], build_location[1]+1],[build_location[0]-1, build_location[1]],[build_location[0]+1, build_location[1]]]
                game_state.attempt_spawn(FILTER, filter_location)
            game_state.attempt_spawn(DESTRUCTOR, build_location)

    def stall_with_scramblers(self, game_state):
        """
        Send out Scramblers at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        i =0
        for location in self.scored_on_locations:
            if( i < 3 and game_state.get_resource(game_state.BITS) >= game_state.type_cost(SCRAMBLER) and game_state.turn_number % 3 == 0):
                i= i+1
                game_state.attempt_spawn(SCRAMBLER, location)
        # Remove locations that are blocked by our own firewalls 
        # since we can't deploy units there.
        #deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        # While we have remaining bits to spend lets send out scramblers randomly.
        #while game_state.get_resource(game_state.BITS) >= game_state.type_cost(SCRAMBLER) and len(deploy_locations) > 0:
            # Choose a random deploy location.
        #    deploy_index = random.randint(0, len(deploy_locations) - 1)
        #    deploy_location = deploy_locations[deploy_index]
            
        #    game_state.attempt_spawn(SCRAMBLER, deploy_location)
        #    """
        #    We don't have to remove the location since multiple information
        #    units can occupy the same space.
        #    """

    def emp_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our EMP's can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [FILTER, DESTRUCTOR, ENCRYPTOR]
        cheapest_unit = FILTER
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost < gamelib.GameUnit(cheapest_unit, game_state.config).cost:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our EMPs from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn EMPs next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(EMP, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy destructors that can attack the final location and multiply by destructor damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(DESTRUCTOR, game_state.config).damage
            damages.append(damage)

        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at: https://docs.c1games.com/json-docs.html
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
