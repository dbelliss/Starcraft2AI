import random
import math

import numpy as np
import pandas as pd

from pysc2.agents import base_agent
from pysc2.lib import actions
from pysc2.lib import features

_NO_OP = actions.FUNCTIONS.no_op.id
_SELECT_POINT = actions.FUNCTIONS.select_point.id
_TRAIN_DRONE = actions.FUNCTIONS.Train_Drone_quick.id
_TRAIN_ZERGLING = actions.FUNCTIONS.Train_Zergling_quick.id
_TRAIN_ROACH = actions.FUNCTIONS.Train_Roach_quick.id
_TRAIN_OVERLORD = actions.FUNCTIONS.Train_Overlord_quick.id
_SELECT_LARVA = actions.FUNCTIONS.select_larva.id
_BUILD_SPAWNING_POOL = actions.FUNCTIONS.Build_SpawningPool_screen.id
_BUILD_ROACHWARREN = actions.FUNCTIONS.Build_RoachWarren_screen.id
_SELECT_ARMY = actions.FUNCTIONS.select_army.id
_ATTACK_MINIMAP = actions.FUNCTIONS.Attack_minimap.id

_PLAYER_RELATIVE = features.SCREEN_FEATURES.player_relative.index
_UNIT_TYPE = features.SCREEN_FEATURES.unit_type.index
_PLAYER_ID = features.SCREEN_FEATURES.player_id.index

_PLAYER_SELF = 1

_TERRAN_COMMANDCENTER = 18
_TERRAN_SCV = 45
_TERRAN_SUPPLY_DEPOT = 19
_TERRAN_BARRACKS = 21

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

_NOT_QUEUED = [0]
_QUEUED = [1]

ACTION_DO_NOTHING = 'donothing'
ACTION_SELECT_LARVA = 'selectlarva'
ACTION_SELECT_DRONE = 'selectdrone'
ACTION_BUILD_SPAWNINGPOOL = 'buildspawningpool'
ACTION_BUILD_ROACHWARREN = 'buildroackwarren'
ACTION_TRAIN_OVERLORD = 'trainoverlord'
ACTION_TRAIN_ZERGLING = 'trainzergling'
ACTION_TRAIN_ROACH = 'trainroach'
ACTION_SELECT_ARMY = 'selectarmy'
ACTION_ATTACK = 'attack'

smart_actions = [
    ACTION_DO_NOTHING,
    ACTION_SELECT_LARVA,
    ACTION_SELECT_DRONE,
    ACTION_BUILD_SPAWNINGPOOL,
    ACTION_BUILD_ROACHWARREN,
    ACTION_TRAIN_OVERLORD,
    ACTION_TRAIN_ZERGLING,
    ACTION_TRAIN_ROACH,
    ACTION_SELECT_ARMY,
    ACTION_ATTACK,
]

KILL_UNIT_REWARD = 0.2
KILL_BUILDING_REWARD = 0.5


# Stolen from https://github.com/MorvanZhou/Reinforcement-learning-with-tensorflow
class QLearningTable:
    def __init__(self, actions, learning_rate=0.01, reward_decay=0.9, e_greedy=0.9):
        self.actions = actions  # a list
        self.lr = learning_rate
        self.gamma = reward_decay
        self.epsilon = e_greedy
        self.q_table = pd.DataFrame(columns=self.actions, dtype=np.float64)

    def choose_action(self, observation):
        self.check_state_exist(observation)

        if np.random.uniform() < self.epsilon:
            # choose best action
            state_action = self.q_table.ix[observation, :]

            # some actions have the same value
            state_action = state_action.reindex(np.random.permutation(state_action.index))

            action = state_action.idxmax()
        else:
            # choose random action
            action = np.random.choice(self.actions)

        return action

    def learn(self, s, a, r, s_):
        self.check_state_exist(s_)
        self.check_state_exist(s)

        q_predict = self.q_table.ix[s, a]
        q_target = r + self.gamma * self.q_table.ix[s_, :].max()

        # update
        self.q_table.ix[s, a] += self.lr * (q_target - q_predict)

    def check_state_exist(self, state):
        if state not in self.q_table.index:
            # append new state to q table
            self.q_table = self.q_table.append(
                pd.Series([0] * len(self.actions), index=self.q_table.columns, name=state))


class SmartAgent(base_agent.BaseAgent):
    def __init__(self):
        super(SmartAgent, self).__init__()

        self.qlearn = QLearningTable(actions=list(range(len(smart_actions))))

        self.previous_killed_unit_score = 0
        self.previous_killed_building_score = 0

        self.previous_action = None
        self.previous_state = None

    
    def ResetBeliefState(self):
        self.previous_action = None


    def transformLocation(self, x, x_distance, y, y_distance):
        if not self.base_top_left:
            return [x - x_distance, y - y_distance]

        return [x + x_distance, y + y_distance]

    def step(self, obs):
        super(SmartAgent, self).step(obs)
        player_y, player_x = (obs.observation['minimap'][_PLAYER_RELATIVE] == _PLAYER_SELF).nonzero()
        self.base_top_left = 1 if player_y.any() and player_y.mean() <= 31 else 0

        unit_type = obs.observation['screen'][_UNIT_TYPE]

        overlord_y, overlord_x = (unit_type == OVERLORD).nonzero()
        overlord_count = 1 if overlord_y.any() else 0

        spawningpool_y, spawningpool_x = (unit_type == SPAWNING_POOL).nonzero()
        spawningpool_count = 1 if spawningpool_y.any() else 0

        roachwarren_y, roachwarren_x = (unit_type == ROACH_WARREN).nonzero()
        roachwarren_count = 1 if roachwarren_y.any() else 0

        supply_limit = obs.observation['player'][4]
        army_supply = obs.observation['player'][5]

        killed_unit_score = obs.observation['score_cumulative'][5]
        killed_building_score = obs.observation['score_cumulative'][6]

        current_state = [
            overlord_count,
            spawningpool_count,
            roachwarren_count,
            supply_limit,
            army_supply,
        ]

        if self.previous_action is not None:
            reward = 0

            if killed_unit_score > self.previous_killed_unit_score:
                reward += KILL_UNIT_REWARD

            if killed_building_score > self.previous_killed_building_score:
                reward += KILL_BUILDING_REWARD

            self.qlearn.learn(str(self.previous_state), self.previous_action, reward, str(current_state))

        rl_action = self.qlearn.choose_action(str(current_state))
        smart_action = smart_actions[rl_action]

        self.previous_killed_unit_score = killed_unit_score
        self.previous_killed_building_score = killed_building_score
        self.previous_state = current_state
        self.previous_action = rl_action

        if smart_action == ACTION_DO_NOTHING:
            return actions.FunctionCall(_NO_OP, [])

        
        elif smart_action == ACTION_SELECT_LARVA:
            unit_type = obs.observation['screen'][_UNIT_TYPE]
            unit_y, unit_x = (unit_type == LARVA).nonzero()

            if unit_y.any():
                i = random.randint(0, len(unit_y) - 1)
                target = [unit_x[i], unit_y[i]]

                return actions.FunctionCall(_SELECT_POINT, [_NOT_QUEUED, target])

        
        elif smart_action == ACTION_SELECT_DRONE:
            unit_type = obs.observation['screen'][_UNIT_TYPE]
            unit_y, unit_x = (unit_type == DRONE).nonzero()

            if unit_y.any():
                i = random.randint(0, len(unit_y) - 1)
                target = [unit_x[i], unit_y[i]]

                return actions.FunctionCall(_SELECT_POINT, [_NOT_QUEUED, target])



        elif smart_action == ACTION_BUILD_SPAWNINGPOOL:
            if _BUILD_SPAWNING_POOL in obs.observation['available_actions']:
                unit_type = obs.observation['screen'][_UNIT_TYPE]
                unit_y, unit_x = (unit_type == DRONE).nonzero()

                if unit_y.any():
                    target = self.transformLocation(int(unit_x.mean()), 20, int(unit_y.mean()), 0)

                    #crappy way of making sure building is in bounds
                    target[0] = 0 if target[0] < 0 else target[0]
                    target[1] = 0 if target[1] < 0 else target[1]
                    target[0] = 63 if target[0] > 63 else target[0]
                    target[1] = 63 if target[0] > 63 else target[1]
                    return actions.FunctionCall(_BUILD_SPAWNING_POOL, [_NOT_QUEUED, target])


        elif smart_action == ACTION_BUILD_ROACHWARREN:
            if _BUILD_ROACHWARREN in obs.observation['available_actions']:
                unit_type = obs.observation['screen'][_UNIT_TYPE]
                unit_y, unit_x = (unit_type == DRONE).nonzero()

                if unit_y.any():
                    target = self.transformLocation(int(unit_x.mean()), 20, int(unit_y.mean()), 0)

                    #crappy way of making sure building is in bounds
                    target[0] = 0 if target[0] < 0 else target[0]
                    target[1] = 0 if target[1] < 0 else target[1]
                    target[0] = 63 if target[0] > 63 else target[0]
                    target[1] = 63 if target[0] > 63 else target[1]
                    return actions.FunctionCall(_BUILD_ROACHWARREN, [_NOT_QUEUED, target])


        elif smart_action == ACTION_TRAIN_OVERLORD:
            if _TRAIN_OVERLORD in obs.observation['available_actions']:
                return actions.FunctionCall(_TRAIN_OVERLORD, [_NOT_QUEUED])


        elif smart_action == ACTION_TRAIN_ZERGLING:
            if _TRAIN_ZERGLING in obs.observation['available_actions']:
                return actions.FunctionCall(_TRAIN_ZERGLING, [_QUEUED])

        elif smart_action == ACTION_TRAIN_ROACH:
            if _TRAIN_ROACH in obs.observation['available_actions']:
                return actions.FunctionCall(_TRAIN_ROACH, [_QUEUED])

        elif smart_action == ACTION_SELECT_ARMY:
            if _SELECT_ARMY in obs.observation['available_actions']:
                return actions.FunctionCall(_SELECT_ARMY, [_NOT_QUEUED])

        elif smart_action == ACTION_ATTACK:
            if _ATTACK_MINIMAP in obs.observation["available_actions"]:
                if self.base_top_left:
                    return actions.FunctionCall(_ATTACK_MINIMAP, [_NOT_QUEUED, [39, 45]])

                return actions.FunctionCall(_ATTACK_MINIMAP, [_NOT_QUEUED, [21, 24]])

        return actions.FunctionCall(_NO_OP, [])