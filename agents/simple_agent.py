# https://chatbotslife.com/building-a-basic-pysc2-agent-b109cde1477c
from pysc2.agents import base_agent
from pysc2.lib import actions
from pysc2.lib import features

import time

# Functions
_NOOP = actions.FUNCTIONS.no_op.id
_SELECT_POINT = actions.FUNCTIONS.select_point.id
_RALLY_UNITS_MINIMAP = actions.FUNCTIONS.Rally_Units_minimap.id
_SELECT_ARMY = actions.FUNCTIONS.select_army.id
_ATTACK_MINIMAP = actions.FUNCTIONS.Attack_minimap.id

BUILD_SPAWNING_POOL = actions.FUNCTIONS.Build_SpawningPool_screen.id
TRAIN_OVERLORD = actions.FUNCTIONS.Train_Overlord_quick.id
TRAIN_DRONE = actions.FUNCTIONS.Train_Drone_quick.id
TRAIN_ZERGLING = actions.FUNCTIONS.Train_Zergling_quick.id
SELECT_LARVA = actions.FUNCTIONS.select_larva.id

# Features
_PLAYER_RELATIVE = features.SCREEN_FEATURES.player_relative.index
_UNIT_TYPE = features.SCREEN_FEATURES.unit_type.index

# Unit IDs
HATCHERY = 86
CREEP_TUMOR = 87
EXTRACTOR = 88
SPAWNING_POOL = 89
EVOLUTION_CHAMBER = 90
HYDRALISK_DEN = 91
SPIRE = 92
ULTRALISK_CAVERN = 93
INFESTATION_PIT = 94
NYDUS_NETWORK = 95
BANELING_NEST = 96
ROACH_WARREN = 97
SPINE_CRAWLER = 98
SPORE_CRAWLER = 99
LAIR = 100
HIVE = 101
GREATER_SPIRE = 102
EGG = 103
DRONE = 104
ZERGLING = 105
OVERLORD = 106
HYDRALISK = 107
MUTALISK = 108
ULTRALISK = 109
ROACH = 110
INFESTOR = 111
CORRUPTOR = 112
BROOD_LOAD_COCOON = 113
BROOD_LORD = 114
BANELING_BURROWED = 115
DRONE_BURROWED = 116
HYDRALISK_BURROWED = 117
ROACH_BURROWED = 118
ZERGLING_BURROWED = 119
INFESTOR_TERRAN_BURROWED = 120
QUEENBURROWED = 125
QUEEN = 126
INFESTOR_BURROWED = 127
OVERLORD_COCOON = 128
OVERSEER = 129
LARVA = 151

INFESTOR_TERRAN = 7
BANELING_COCOON = 8
BANELING = 9
CHANGELING = 12
CHANGELING_ZEALOT = 13
CHANGELING_MARINE_SHIELD = 14
CHANGELING_MARINE = 15
CHANGELING_ZERGLING = 16



# Parameters
_PLAYER_SELF = 1
_SUPPLY_USED = 3
_SUPPLY_MAX = 4
_NOT_QUEUED = [0]
_QUEUED = [1]

class SimpleAgent(base_agent.BaseAgent):
    base_top_left = None
    overlord_built = False
    larva_selected = False
    drone_selected = False
    spawning_pool_built = False
    spawning_pool_selected = False
    spawning_pool_rallied = False
    army_selected = False
    army_rallied = False

    def transformLocation(self, x, x_distance, y, y_distance):
        if not self.base_top_left:
            return [x - x_distance, y - y_distance]
        
        return [x + x_distance, y + y_distance]
    
    def ResetBeliefState(self):
        self.larva_selected = False
        self.drone_select = False
        self.army_selected = False

    def step(self, obs):
        super(SimpleAgent, self).step(obs)
        
        # time.sleep(0.5)
        
        if self.base_top_left is None:
            player_y, player_x = (obs.observation["minimap"][_PLAYER_RELATIVE] == _PLAYER_SELF).nonzero()
            self.base_top_left = player_y.mean() <= 31
            
        if not self.overlord_built:
            if not self.larva_selected:
                unit_type = obs.observation["screen"][_UNIT_TYPE]
                unit_y, unit_x = (unit_type == LARVA).nonzero()

                target = [unit_x[0], unit_y[0]]

                self.larva_selected = True

                return actions.FunctionCall(_SELECT_POINT, [_NOT_QUEUED, target])
            elif TRAIN_OVERLORD in obs.observation["available_actions"]:
                # Overlord can be built, and has not been built, so built it
                unit_type = obs.observation["screen"][_UNIT_TYPE]
                unit_y, unit_x = (unit_type == HATCHERY).nonzero()

                self.overlord_built = True
                self.larva_selected = False
                return actions.FunctionCall(TRAIN_OVERLORD, [_QUEUED])
        elif not self.spawning_pool_built:
            if not self.drone_selected:
                unit_type = obs.observation["screen"][_UNIT_TYPE]
                unit_y, unit_x = (unit_type == DRONE).nonzero()

                target = [unit_x[0], unit_y[0]]

                self.drone_selected = True

                return actions.FunctionCall(_SELECT_POINT, [_NOT_QUEUED, target])
            elif BUILD_SPAWNING_POOL in obs.observation["available_actions"]:
                unit_type = obs.observation["screen"][_UNIT_TYPE]
                unit_y, unit_x = (unit_type == HATCHERY).nonzero()
                
                target = self.transformLocation(int(unit_x.mean()), 20, int(unit_y.mean()), 0)
                self.drone_selected = False
                self.spawning_pool_built = True
                
                return actions.FunctionCall(BUILD_SPAWNING_POOL, [_NOT_QUEUED, target])
        elif not self.spawning_pool_rallied:
            if not self.spawning_pool_selected:
                unit_type = obs.observation["screen"][_UNIT_TYPE]
                unit_y, unit_x = (unit_type == SPAWNING_POOL).nonzero()
                
                if unit_y.any():
                    target = [int(unit_x.mean()), int(unit_y.mean())]
                
                    self.spawning_pool_selected = True
                
                    return actions.FunctionCall(_SELECT_POINT, [_NOT_QUEUED, target])
            else:
                self.spawning_pool_rallied = True

                #
                # if self.base_top_left:
                #     return actions.FunctionCall(_RALLY_UNITS_MINIMAP, [_NOT_QUEUED, [29, 21]])
                #
                # return actions.FunctionCall(_RALLY_UNITS_MINIMAP, [_NOT_QUEUED, [29, 46]])
        elif obs.observation["player"][_SUPPLY_USED] < obs.observation["player"][_SUPPLY_MAX]:
            if not self.larva_selected:
                unit_type = obs.observation["screen"][_UNIT_TYPE]
                unit_y, unit_x = (unit_type == LARVA).nonzero()
                if (len(unit_x) == 0):
                    # No larva at the moment
                    return actions.FunctionCall(_NOOP, [])
                target = [unit_x[0], unit_y[0]]

                self.larva_selected = True

                return actions.FunctionCall(_SELECT_POINT, [_NOT_QUEUED, target])

            elif TRAIN_ZERGLING in obs.observation["available_actions"]:
                self.larva_selected = False
                return actions.FunctionCall(TRAIN_ZERGLING, [_QUEUED])
        elif not self.army_rallied:
            if not self.army_selected:
                if _SELECT_ARMY in obs.observation["available_actions"]:
                    self.army_selected = True
                    self.spawning_pool_selected = False
                
                    return actions.FunctionCall(_SELECT_ARMY, [_NOT_QUEUED])
            elif _ATTACK_MINIMAP in obs.observation["available_actions"]:
                self.army_rallied = True
                self.army_selected = False
            
                if self.base_top_left:
                    return actions.FunctionCall(_ATTACK_MINIMAP, [_NOT_QUEUED, [39, 45]])
            
                return actions.FunctionCall(_ATTACK_MINIMAP, [_NOT_QUEUED, [21, 24]])

        return actions.FunctionCall(_NOOP, [])
