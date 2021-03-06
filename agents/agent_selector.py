#!/usr/bin/python3
# https://chatbotslife.com/building-a-basic-pysc2-agent-b109cde1477c
# Debug imports
from pprint import pprint
from time import gmtime, strftime, localtime
import sys
import os
import argparse
import random
import signal
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np
from collections import defaultdict

# python-sc2 imports
import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer

# agent imports
from loser_agent import *
from saferoach_agent import SafeRoachAgent
from zerglingBanelingRush_agent import ZerglingBanelingRushAgent
from mutalisk_agent import MutaliskAgent
from dumbagent import DumbAgent
from NeuralNetwork import NeuralNetwork
from strategies import Strategies


# Coloring for terminal output
# https://stackoverflow.com/questions/287871/print-in-terminal-with-colors
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class AgentSelector(LoserAgent):
    #TODO Implement previous known enemy list so that we dont lose info over time
    def __init__(self, is_logging = False, is_printing_to_console = False, isMainAgent = False):
        super().__init__(is_logging, is_printing_to_console, isMainAgent, "AgentSelector_")
        print(bcolors.OKGREEN + "###AgentSelector Constructor" + bcolors.ENDC)

        # List of build orders
        self.agents = [MutaliskAgent(), ZerglingBanelingRushAgent(), SafeRoachAgent(), DumbAgent()]
        self.nAgents = len(self.agents)

        # Make agent list global
        global listOfAgents
        listOfAgents = self.agents

        # Choose RandomBuild
        self.chooseRandomBuild()

        # Number of strategies
        self.strategies = Strategies
        self.nStrategies = 11

        # Choose RandomStrategy
        self.chooseRandomStrategy()

        # Properties
        self.stepsPerAgent = 100
        self.curAgentIndex = 0
        self.strategiesIndex = 0
        self.curStep = 0
        self.timesSwitched = 0
        self.last_known_enemies = None
        self.correctChoice = 0

        ''' Variables initialized by setupInputs() when game starts'''
        self.nInputs = 0
        self.prevInputs = []
        self.agentNN = None
        self.strategyNN = None

        self.prevAgent = 0
        self.prevStrategy = 0
        self.lastFitness = 0

    def chooseRandomBuild(self):
        self.curAgentIndex = random.randint(0, self.nAgents-1)
        print(bcolors.OKGREEN + "###RandomBuildIndex: {}".format(self.agents[self.curAgentIndex]) + bcolors.ENDC)

    def chooseRandomStrategy(self):
        self.strategiesIndex = random.randint(0, self.nStrategies)
        print(bcolors.OKGREEN + "###RandomStrategyIndex: {}".format(self.strategiesIndex) + bcolors.ENDC)

    def total_worker_count(self):
        return self.mainAgent.workers.amount

    def idle_worker_count(self):
        return self.mainAgent.workers.idle.amount

    def vespene_worker_count(self):
        workers = 0
        for extractor in self.mainAgent.units(EXTRACTOR):
            workers = workers + extractor.assigned_harvesters
        return workers

    def mineral_worker_count(self):
        workers = 0
        bases = self.mainAgent.units(HATCHERY) + self.mainAgent.units(LAIR) + self.mainAgent.units(HIVE)
        for base in bases:
            workers += base.assigned_harvesters
        if self.total_worker_count() < (workers + self.vespene_worker_count()):
            workers -= self.mainAgent.units(EXTRACTOR).amount
        return workers

    '''
    Gathers the remaining workers that are not gathering a resource or is idle
    ex: workers that are moving, scouting, attacking, or building
    '''
    def remaining_worker_count(self):
        remainder = self.total_worker_count() - self.idle_worker_count() - self.mineral_worker_count() - self.vespene_worker_count()
        if remainder < 0:
            remainder = 0
        return remainder

    '''
    Establishes the unit lists that are used for unit breakdowns for each race. These lists
    include standard units, special units that we want to be counted as other units (ex: burrowed stuff)
    and ignored_units (which is only used for Zerg because we dont really care about eggs, larva, etc.)
    '''
    # TODO Should mules, auto-turrets, and point defense drones be counted in inputs? Does MarineStimpack, MauraderLifeBoost and upgrades in general ever show?
    # TODO How should nydus worms/networks be dealt with?
    def unit_setter(self, player_race):
        if player_race == 1:
            unit_names = [
                'SCV', 'Mules', 'Marine', 'Marauder', 'Reaper', 'Ghost', 'HellionTank', 'Hellbat', 'SiegeTank', 'Cyclone', 'WidowMine', 'Thor',
                'AutoTurret', 'Viking', 'Medivac', 'Liberator', 'Raven', 'Banshee', 'Battlecruiser', 'PointDefenseDrone', 'CommandCenter',
                'PlanetaryFortress', 'OrbitalCommand', 'SupplyDepot', 'Refinery', 'Barracks', 'EngineeringBay', 'Bunker', 'SensorTower',
                'MissileTurret', 'Factory', 'GhostAcademy', 'Starport', 'Armory', 'FusionCore', 'CommandCenterFlying', 'OrbitalCommandFlying',
                'BarracksFlying', 'FactoryFlying', 'StarportFlying', 'Hellion', 'TechLab', 'rest'
            ]
            special_units = {
                'SiegeTankSieged': 'SiegeTank', 'WidowMineBurrowed': 'WidowMine', 'VikingFighter': 'Viking', 'VikingAssault': 'Viking', 'BansheeCloak': 'Banshee',
                'CommandCenterReactor': 'CommandCenter', 'SupplyDepotDrop': 'SupplyDepot', 'SupplyDepotLowered': 'SupplyDepot',
                'BarracksReactor': 'Barracks', 'BarracksTechLab': 'Barracks', 'BarracksTechReactor': 'Barracks', 'FactoryTechLab': 'Factory', 'FactoryReactor': 'Factory',
                'FactoryTechReactor': 'Factory', 'StarportTechLab': 'Starport', 'StarportTechReactor': 'Starport', 'StarportReactor': 'Starport'
            }
            ignored_units = ['KD8Charge', 'MULE', 'Hellion']
            # Building fitness breakdown
            defensive_buildings = {'Bunker': 0, 'MissileTurret': 0, 'PlanetaryFortress': 0}
            production_buildings = {'Barracks': 0, 'BarracksFlying': 0, 'BarracksReactor': 0, 'BarracksTechLab': 0, 'BarracksTechReactor': 0}
            upgrade_buildings = {'EngineeringBay': 0, 'Armory': 0}
            technology_buildings = {'EngineeringBay': 0, 'Armory': 0, 'GhostAcademy': 0, 'FusionCore': 0}
            remaining_basic_buildings = {'CommandCenter': 0, 'SupplyDepot': 0, 'Refinery': 0, 'SensorTower': 0, 'SupplyDepotDrop': 0, 'SupplyDepotLowered': 0, 'Reactor': 0}
            remaining_advanced_buildings = {'PlanetaryFortress': 0, 'Factory': 0, 'Starport': 0, 'FactoryTechLab': 0, 'FactoryReactor': 0, 'FactoryTechReactor': 0, 'StarportTechLab': 0, 'StarportTechReactor': 0, 'StarportReactor': 0, 'TechLab': 0}
            other_buildings = {'OrbitalCommand': 0, 'OrbitalCommandFlying': 0}
            # Army fitness breakdown
            # TODO figure out better breakdown for army fitness
            army = [
                'Marine', 'Marauder', 'Reaper', 'Ghost', 'HellionTank', 'Hellbat', 'SiegeTank', 'Cyclone', 'WidowMine', 'Thor', 'Hellion',
                'AutoTurret', 'Viking', 'Medivac', 'Liberator', 'Raven', 'Banshee', 'Battlecruiser', 'PointDefenseDrone', 'SiegeTankSieged'
                'WidowMineBurrowed', 'VikingFighter', 'VikingAssault', 'BansheeCloak', 'SiegeTankSieged'
            ]
            workers = {'SCV': 0}
            fitness_ignored = ['KD8Charge', 'MULE']
        elif player_race == 2:
            unit_names = [
                'Cocoon', 'Drone', 'Queen', 'Zergling', 'Baneling', 'Roach', 'Ravager', 'Hydralisk', 'Lurker', 'Infestor', 'SwarmHostMP', 'Ultralisk',
                'LocustMP', 'Broodling', 'BroodlingEscort', 'Changeling', 'InfestorTerran', 'Overlord', 'Overseer', 'Mutalisk', 'Corruptor', 'BroodLord', 'Viper', 'Hatchery',
                'SpineCrawler', 'SporeCrawler', 'Extractor', 'SpawningPool', 'EvolutionChamber', 'RoachWarren', 'BanelingNest', 'CreepTumor', 'Lair',
                'HydraliskDen', 'LurkerDenMP', 'InfestationPit', 'Spire', 'Hive', 'GreaterSpire', 'UltraliskCavern', 'rest'
            ]
            special_units = {
                'RavagerCocoon': 'Cocoon', 'BanelingCocoon': 'Cocoon', 'OverlordCocoon': 'Cocoon', 'BroodLordCocoon': 'Cocoon', 'TransportOverlordCocoon': 'Cocoon', 'DroneBurrowed': 'Drone', 'QueenBurrowed': 'Queen',
                'ZerglingBurrowed': 'Zergling', 'BanelingBurrowed': 'Baneling', 'RoachBurrowed': 'Roach', 'RavagerBurrowed': 'Ravager', 'HydraliskBurrowed': 'Hydralisk', 'LurkerMPBurrowed': 'Lurker', 'LurkerMP': 'Lurker',
                'InfestorBurrowed': 'Infestor', 'SwarmHostBurrowedMP': 'SwarmHostMP', 'UltraliskBurrowed': 'Ultralisk', 'LocustMPFlying': 'Locust', 'ChangelingMarine': 'Changeling', 'ChangelingZealot': 'Changeling',
                'ChangelingZergling': 'Changeling', 'InfestorTerranBurrowed': 'InfestorTerran', 'OverlordTransport': 'Overlord', 'OverseerSiegeMode': 'Overseer', 'SpineCrawlerUprooted': 'SpineCrawler',
                'SporeCrawlerUprooted': 'SporeCrawler', 'CreepTumorBurrowed': 'CreepTumor', 'ChangelingZerglingWings': 'Changeling'
            }
            ignored_units = ['Larva', 'Egg', 'LurkerMPEgg', 'InfestedTerransEgg', 'CreepTumorQueen']
            # building lists for fitness
            defensive_buildings = {'SpineCrawler': 0, 'SporeCrawler': 0} #TODO what do we do with the uprooted ones
            production_buildings = {' ': 0}
            upgrade_buildings = {'EvolutionChamber': 0, 'Spire': 0}
            technology_buildings = {'SpawningPool': 0, 'RoachWarren': 0, 'BanelingNest': 0, 'HydraliskDen': 0, 'LurkerDenMP': 0, 'Spire': 0, 'GreaterSpire': 0, 'UltraliskCavern': 0}
            remaining_basic_buildings = {'Hatchery': 0, 'Extractor': 0, 'Overlord': 0, 'OverlordTransport': 0}
            remaining_advanced_buildings = {'Lair': 0,'InfestationPit': 0, 'Overseer': 0, 'OverseerSiegeMode': 0}
            other_buildings = {'Hive': 0}
            # army lists for Fitness
            # TODO figure out better breakdown for army fitness
            army = [
                'Queen', 'Zergling', 'Baneling', 'Roach', 'Ravager', 'Hydralisk', 'Lurker', 'Infestor', 'SwarmHostMP', 'Ultralisk',
                'LocustMP', 'Broodling', 'BroodlingEscort', 'Changeling', 'InfestorTerran', 'Overlord', 'Overseer', 'Mutalisk', 'Corruptor', 'BroodLord', 'Viper',
                'QueenBurrowed', 'ZerglingBurrowed', 'BanelingBurrowed', 'RoachBurrowed', 'RavagerBurrowed', 'HydraliskBurrowed', 'LurkerMPBurrowed', 'LurkerMP',
                'InfestorBurrowed', 'SwarmHostBurrowedMP', 'UltraliskBurrowed', 'LocustMPFlying', 'ChangelingMarine', 'ChangelingZealot', 'ChangelingZergling', 'InfestorTerranBurrowed',
                'ChangelingZerglingWings'
            ]
            workers = {'Drone': 0, 'DroneBurrowed': 0}
            fitness_ignored = [
                'Larva', 'Egg', 'LurkerMPEgg', 'InfestedTerransEgg', 'Cocoon', 'RavagerCocoon', 'BanelingCocoon', 'OverlordCocoon', 'BroodLordCocoon', 'TransportOverlordCocoon',
                'CreepTumor', 'CreepTumorBurrowed', 'CreepTumorQueen'
            ]
        else:
            unit_names = [
                'Probe', 'Zealot', 'Stalker', 'Sentry', 'Adept', 'HighTemplar', 'DarkTemplar', 'Immortal', 'Colossus', 'Interceptor'
                'Disruptor', 'Archon', 'Observer', 'WarpPrism', 'Phoenix', 'VoidRay', 'Oracle', 'Carrier', 'Tempest',
                'MothershipCore', 'Mothership', 'Nexus', 'Pylon', 'Assimilator', 'Gateway', 'Forge', 'CyberneticsCore',
                'PhotonCannon', 'RoboticsFacility', 'WarpGate', 'Stargate', 'TwilightCouncil', 'RoboticsBay',
                'FleetBeacon', 'TemplarArchive', 'DarkShrine', 'rest'
            ]
            special_units = {
                'ImmortalBarrier': 'Immortal', 'ObserverSiegeMode': 'Observer', 'PylonOvercharged': 'Pylon'
            }
            ignored_units = [' ']
            # Building fitness breakdown
            defensive_buildings = {'PhotonCannon': 0}
            production_buildings = {'Gateway': 0, 'RoboticsFacility': 0, 'Stargate': 0}
            upgrade_buildings = {'Forge': 0, 'CyberneticsCore': 0}
            technology_buildings = {'Forge': 0, 'CyberneticsCore': 0, 'TwilightCouncil': 0, 'RoboticsBay': 0, 'FleetBeacon': 0, 'TemplarArchive': 0, 'DarkShrine': 0}
            remaining_basic_buildings = {'Nexus': 0, 'Pylon': 0, 'PylonOvercharged': 0, 'Assimilator': 0}
            remaining_advanced_buildings = {'WarpGate': 0}
            other_buildings = {' ': 0}
            # Army fitness breakdown
            # TODO figure out better breakdown for army fitness
            army = [
                'Zealot', 'Stalker', 'Sentry', 'Adept', 'HighTemplar', 'DarkTemplar', 'Immortal', 'Colossus', 'Interceptor'
                'Disruptor', 'Archon', 'Observer', 'WarpPrism', 'Phoenix', 'VoidRay', 'Oracle', 'Carrier', 'Tempest',
                'MothershipCore', 'Mothership'
            ]
            workers = {'Probe': 0}
            fitness_ignored = [' ']
        unit_breakdown = {key: 0 for key in unit_names}
        army_breakdown = {key: 0 for key in army}
        return unit_breakdown, special_units, ignored_units, defensive_buildings, production_buildings, upgrade_buildings, technology_buildings, remaining_basic_buildings, \
            remaining_advanced_buildings, other_buildings, army_breakdown, workers, fitness_ignored

    '''
    Creates the actual counts of units known at the time for either self or enemy.
    '''
    def unit_breakdown(self, owned, player_race):
        unit_breakdown, special_units, ignored_units, defensive_buildings, production_buildings, upgrade_buildings, technology_buildings, remaining_basic_buildings, \
            remaining_advanced_buildings, other_buildings, army_breakdown, workers, fitness_ignored = self.unit_setter(player_race)
        if owned:
            player = self.mainAgent.units
        else:
            # player = self.mainAgent.known_enemy_units
            if len(self.mainAgent.known_enemy_units) != 0:
                player = self.mainAgent.known_enemy_units
                self.last_known_enemies = player #Update last known last_known_enemies
            elif self.last_known_enemies != None:
                player = self.last_known_enemies
            else:
                player = self.mainAgent.known_enemy_units

        for unit in player:
            if unit.name in ignored_units:
                continue
            try:
                unit_breakdown[unit.name] += 1
            except KeyError:
                try:
                    unit_breakdown[special_units[unit.name]] += 1
                except KeyError:
                    self.log("Names not covered: {0}".format(str(unit.name)))
                    self.log("Known enemy list: {}".format(str(self.mainAgent.known_enemy_units)))
                    unit_breakdown['rest'] += 1
        # return unit_breakdown -> only use for debugging if you want to see what the values look like
        return [unit_breakdown[key] for key in unit_breakdown]

    '''
    Creates and normalize all inputs for NN. These include total unit breakdown for both self and enemy,
    worker breakdown, and current resources. All units and buildings are divided by 200 which should keep everything
    normalized fairly well and resources are divided by 1000 which may need to be changed later.
    '''
    def create_inputs(self):
        # Create ownded unit inputs
        owned = self.unit_breakdown(True, 2)
        idle_workers = self.idle_worker_count()
        vespene_workers = self.vespene_worker_count()
        mineral_workers = self.mineral_worker_count()
        remaining_workers = self.remaining_worker_count()
        # Inserts worker breakdown by total drone count
        owned.insert(2, remaining_workers)
        owned.insert(2, vespene_workers)
        owned.insert(2, mineral_workers)
        owned.insert(2, idle_workers)
        # Normalize unit count
        normalized_owned = [unit / 200 for unit in owned]
        # Gather resource info and append onto owned inputs
        resources = [self.mainAgent.minerals/1000, self.mainAgent.vespene/1000]
        normalized_owned.extend(resources)
        # Create enemy unit inputs
        enemy = self.unit_breakdown(False, self.mainAgent.game_info.player_races[2])
        normalized_enemy = [unit / 200 for unit in enemy]
        inputs = normalized_owned + normalized_enemy
        return inputs

    def fitness(self):
        # TODO: Implement calculations, w alias for weights
        """Agent Selector Fitness"""
        self_fitness = sum(self.fitness_breakdown(True, 2)) - self.idle_worker_count()

        # Resource Calculation - drop off score if hoarding too much resource
        ## log(mineral_count + vespene_count)

        """Enemy Fitness"""
        enemy_fitness = sum(self.fitness_breakdown(False, self.mainAgent.game_info.player_races[2]))

        return self_fitness - enemy_fitness

    def fitness_breakdown(self, owned, player_race):
        unit_breakdown, special_units, ignored_units, defensive_buildings, production_buildings, upgrade_buildings, technology_buildings, remaining_basic_buildings, \
            remaining_advanced_buildings, other_buildings, army_breakdown, workers, fitness_ignored = self.unit_setter(player_race)
        if owned:
            player = self.mainAgent.units
        else:
            # player = self.mainAgent.known_enemy_units
            if len(self.mainAgent.known_enemy_units) != 0:
                player = self.mainAgent.known_enemy_units
                self.last_known_enemies = player #Update last known last_known_enemies
            elif self.last_known_enemies != None:
                player = self.last_known_enemies
            else:
                player = self.mainAgent.known_enemy_units

        for unit in player:
            try:
                if unit.name in fitness_ignored:
                    continue
                elif unit.name in defensive_buildings:
                    defensive_buildings[unit.name] += 4
                elif unit.name in production_buildings:
                    production_buildings[unit.name] += 2
                elif unit.name in upgrade_buildings:
                    upgrade_buildings[unit.name] += 2
                elif unit.name in technology_buildings:
                    technology_buildings[unit.name] += 3
                elif unit.name in remaining_basic_buildings:
                    remaining_basic_buildings[unit.name] += 1
                elif unit.name in remaining_advanced_buildings:
                    remaining_advanced_buildings[unit.name] += 2
                elif unit.name in other_buildings:
                    other_buildings[unit.name] += 3
                elif unit.name in army_breakdown:
                    army_breakdown[unit.name] += 1
                else:
                    workers[unit.name] += 1
            except KeyError:
                self.log("Fitness names not covered: {0}".format(str(unit.name)))
        fitness_breakdown = {
            **defensive_buildings, **production_buildings, **upgrade_buildings, **technology_buildings, **remaining_basic_buildings, \
            **remaining_advanced_buildings, **other_buildings, **army_breakdown, **workers
        }
        return [fitness_breakdown[key] for key in fitness_breakdown]


    # https://stackoverflow.com/questions/32922909/how-to-stop-an-infinite-loop-safely-in-python
    """
    Handles signal interrupts when user uses CTRL-C in the terminal
    """
    def signal_handler(self, signal, frame):
        global interrupted
        interrupted = True
        print(bcolors.FAIL + "###Interrupt Received" + bcolors.ENDC)

    async def on_step(self, iteration):
        # Run first time setup
        if (iteration == 0):
            self.setupInputs()
            # Setup signal handler
            signal.signal(signal.SIGINT, self.signal_handler)

        # Run fitness on a certain number of steps
        if (iteration % self.stepsPerAgent == 0):
            # self.log("Flying: {0} Buildings: {1} Workers: {2}".format(str(flying_army), str(buildings), str(workers)))
            # In case you want to check my work, these are some helpful print statements
            # print(bcolors.OKGREEN + "Self units: %s" % str(self.mainAgent.units))
            # print(bcolors.OKGREEN + "Length of inputs: %s" % str(len(self.create_inputs())))
            # print(bcolors.OKBLUE + "Inputs: {} ".format(self.create_inputs()))
            # print(bcolors.OKGREEN + "Ownded units breakdown: %s" % str(self.owned_units()))
            # print(bcolors.OKBLUE + "Enemies: {} ".format(self.last_known_enemies))
            # print(bcolors.OKGREEN + "Fitness breakdown: {} ".format(self.fitness_breakdown(True, 2)))
            print(bcolors.OKBLUE + "Total: {}, Idle: {}, Mineral: {}, Vespene: {}, Other: {}".format(self.total_worker_count(), self.idle_worker_count(), self.mineral_worker_count(), self.vespene_worker_count(), self.remaining_worker_count()) + bcolors.ENDC)
            # print(bcolors.OKGREEN + "###Fitness function: {}".format(iteration) + bcolors.ENDC)

            # Check if we need to enter neural network based on fitness
            self.checkFitness(iteration)

            print(bcolors.WARNING + "### Selecting new Agent and Strategy" + bcolors.ENDC)
            self.learn()
            self.selectNewAgentsAndStrategies()

        # Call the current agent on_step
        await self.agents[self.curAgentIndex].on_step(iteration, self.strategiesIndex)

    def checkFitness(self, iteration):
        # Retrieve fitness score
        curFitness = self.fitness()

        # Append fitness score to graph
        xAxis.append(iteration)
        yAxis.append(curFitness)

        print(bcolors.OKBLUE + "### Cur Fitness: " + str(curFitness) + bcolors.ENDC)

        # Calculate Change
        fit_diff = curFitness - self.lastFitness
        if self.lastFitness != 0:
            fit_proportion = float(fit_diff) / self.lastFitness
        else:
            fit_proportion = float(fit_diff)
        fit_percent_change = fit_proportion * 100
        print(bcolors.OKBLUE + "### Percent fitness change: {:0.2f}%".format(fit_percent_change) + bcolors.ENDC)

        # Check if current fitness has dropped lower than or equal to 10%
        if fit_percent_change <= -10:
            self.correctChoice = 0
        else:
            self.correctChoice = 1

        # Update last fitness
        self.lastFitness = curFitness

    def setupInputs(self):
        # Dry run through input creation to get idea of curInput size
        curInputs = self.mainAgent.create_inputs()

        # Initialize number of input and previous neural input list
        self.nInputs = len(curInputs)
        self.prevInputs = [0] * self.nInputs

        # inputs = nData inputs + nAgents (for last agent selected) + nStrategies (for last strategy selected)
        # outputs = nAgents
        opponent_race = self.mainAgent.game_info.player_races[2]
        self.agentNN = NeuralNetwork(self.nInputs + self.nAgents + self.nStrategies, self.nAgents, 1, 1, 100, opponent_race, "agent")

        self.agentNN.loadWeights()

        # inputs = nData inputs + 2 * nAgents (for last and current agent selected) + nStrategies (for last strategy selected)
        # outputs = nStrategies
        self.strategyNN = NeuralNetwork(self.nInputs + 2 * self.nAgents + self.nStrategies, self.nStrategies, 1, 1, 100, opponent_race, "strategy")
        self.strategyNN.loadWeights()
        print(bcolors.OKBLUE + "### One time neural input setup" + bcolors.ENDC)
        print(bcolors.OKBLUE + "### Enemy is " + str(self.mainAgent.game_info.player_races[2]) + bcolors.ENDC)


    def learn(self):
        #create list for all the inputs to the neural network
        prevAgent = [0] * self.nAgents
        prevStrategy = [0] * self.nStrategies
        curAgent = [1 - self.correctChoice] * self.nAgents
        curStrategy = [1 - self.correctChoice] * self.nStrategies

        #this is for the predicted agent that was used as input for the strategy NN. Must be 1 hot like it was during prediction
        predAgent = [0] * self.nAgents

        #set the 1 hot encoding for prev agents and certainty that the current choice was correct
        #these are part of the X's that are used to teach the NN
        prevAgent[self.prevAgent] = 1
        prevStrategy[self.prevStrategy] = 1
        predAgent[self.curAgentIndex] = 1

        #set certainty that the choice was correct
        #these are the y's
        curAgent[self.curAgentIndex] = self.correctChoice
        curStrategy[self.strategiesIndex] = self.correctChoice

        #appends all the input lists together, also puts them into lists of lists for the NN
        # ie [1, 2, 3] + [4, 5] => [[1, 2, 3, 4 ,5]]
        agentInputList = [self.prevInputs + prevAgent + prevStrategy]
        agentOutputList = [curAgent]
        strategyInputList = [self.prevInputs + predAgent + prevAgent + prevStrategy]
        strategyOutputList = [curStrategy]
        # self.log("Training agentNN with inputs: {0} and outputs {1}".format(str(agentInputList), str(agentOutputList)))
        # self.log("Training strategyNN with inputs: {0} and outputs {1}".format(str(strategyInputList), str(strategyOutputList)))
        self.agentNN.train(agentInputList, agentOutputList)
        self.strategyNN.train(strategyInputList, strategyOutputList)

    def selectNewAgentsAndStrategies(self):
        #define other inputs to NN
        curInputs = self.mainAgent.create_inputs()

        #create list for all the inputs to the neural network
        curAgent = [0] * self.nAgents
        curStrategy = [0] * self.nStrategies

        #set previous choices as 1 hot
        curAgent[self.curAgentIndex] = 1
        curStrategy[self.strategiesIndex] = 1

        #appends all the input lists together, also puts them into lists of lists for the NN
        # ie [1, 2, 3] + [4, 5] => [[1, 2, 3, 4 ,5]]
        agentInputList = [curInputs + curAgent + curStrategy]
        # print(bcolors.WARNING + "###agentInputList: {}".format(agentInputList) + bcolors.ENDC)
        # self.log("Predicting agentNN with inputs: {0}".format(str(agentInputList)))

        nextAgent = self.agentNN.predict(agentInputList)[0].tolist() #extract first row from returned numpy array
        nextAgentIndex = nextAgent.index(max(nextAgent))
        nextAgent = [nextAgent[i] if i == nextAgentIndex else 0 for i in range(len(nextAgent))]

        strategyInputList = [curInputs + nextAgent + curAgent + curStrategy]
        # self.log("Predicting strategyNN with inputs: {0}".format(str(strategyInputList)))
        nextStrategy = self.strategyNN.predict(strategyInputList)[0].tolist() #extract first row from returned numpy array

        self.prevAgent = self.curAgentIndex
        self.prevStrategy = self.strategiesIndex
        self.prevInputs = curInputs
        self.curAgentIndex = nextAgentIndex
        self.strategiesIndex = nextStrategy.index(max(nextStrategy))

        self.agentNN.saveWeights()
        self.strategyNN.saveWeights()

        # Add to agent frequency
        agentName = str(self.agents[self.curAgentIndex]).split(".")[1].split(" ")[0]
        agentFreq[agentName] += 1

        # Add to agent strategy
        strategyname = str(self.strategies(self.strategiesIndex)).split(".")[1]
        stratFreq[strategyname] += 1

"""
Parse command line arguments
List options: python3 agent_selector.py -h
Example: python3 agent_selector.py -r protoss -d easy -n 2
"""
def readArguments():
    parser = argparse.ArgumentParser(description="""A bot that chooses agents and strategies using a neural network -
     Example: python3 agent_selector.py -r protoss -d easy -n 2""")

    # Race
    parser.add_argument("-r", "--race", help="The opponent bot's race: Terran, Zerg, Protoss, Random", type=str)

    # Difficulty
    parser.add_argument("-d", "--difficulty", help="""The opponent bot's difficulty level:
     VeryEasy, Easy, Medium, MediumHard, Hard, Harder, VeryHard, CheatVision, CheatMoney, CheatInsane""", type=str)

    # Number
    parser.add_argument("-n", "--number", help="Number of games the bot will play", type=int)

    return parser.parse_args()

def checkNParseArgs(args):
    # Race
    if args.race == None:
        race = "random"
    else:
        if args.race.lower() == "terran":
            race = Race.Terran
        elif args.race.lower() == "zerg":
            race = Race.Zerg
        elif args.race.lower() == "protoss":
            race = Race.Protoss
        elif args.race.lower() == "random":
            race = "random"
        else:
            raise ValueError("Unknown race: '{}'. Must be terran, zerg, protoss, or random".format(args.race))

    # Difficulty
    if args.difficulty == None:
        difficulty = Difficulty.Medium
    else:
        if args.difficulty.lower() == "veryeasy":
            difficulty = Difficulty.VeryEasy
        elif args.difficulty.lower() == "easy":
            difficulty = Difficulty.Easy
        elif args.difficulty.lower() == "medium":
            difficulty = Difficulty.Medium
        elif args.difficulty.lower() == "mediumhard":
            difficulty = Difficulty.MediumHard
        elif args.difficulty.lower() == "hard":
            difficulty = Difficulty.Hard
        elif args.difficulty.lower() == "harder":
            difficulty = Difficulty.Harder
        elif args.difficulty.lower() == "veryhard":
            difficulty = Difficulty.VeryHard
        elif args.difficulty.lower() == "cheatvision":
            difficulty = Difficulty.CheatVision
        elif args.difficulty.lower() == "cheatmoney":
            difficulty = Difficulty.CheatMoney
        elif args.difficulty.lower() == "cheatinsane":
            difficulty = Difficulty.CheatInsane
        else:
            raise ValueError("""Unknown difficulty: '{}'. Must be
            VeryEasy, Easy, Medium, MediumHard, Hard, Harder, VeryHard, CheatVision, CheatMoney, CheatInsane""".format(args.difficulty))

    # Number
    if args.number == None:
        number = 1
    else:
        if args.number >= 1:
            number = args.number
        else:
            raise ValueError("Number must be greater than 0, got '{}'".format(args.number))

    return (race, difficulty, number)

def graphFitnessIndividual(enemyRace, difficulty, idx):
    global figureCount

    # Get string name from enum
    fileRace = str(enemyRace).split(".")[1]
    fileDifficulty = str(difficulty).split(".")[1]

    # Add axis to the total axis
    totalAxis.append((xAxis, yAxis, idx, fileRace))

    # Add axis to terran
    if fileRace == "Terran":
        terranAxis.append((xAxis, yAxis, idx, fileRace))
    # Add axis to zerg
    elif fileRace == "Zerg":
        zergAxis.append((xAxis, yAxis, idx, fileRace))
    # Add axis to protoss
    else:
        protossAxis.append((xAxis, yAxis, idx, fileRace))

    # Separate each game
    plt.figure(figureCount)

    # Plot the points
    plt.plot(xAxis, yAxis)

    # Naming the x axis
    plt.xlabel('Game Steps')
    # Naming the y axis
    plt.ylabel('Fitness Score')

    # Give a title to the graph
    plt.title("Game-{}_{}_{}".format(idx, fileRace, fileDifficulty))

    # Create filename
    filename = gamesFitnessFolder + "/Game-{} {}_{}.png".format(idx, fileRace, fileDifficulty)

    # Save the plot
    plt.savefig(filename, bbox_inches="tight")

    plt.close('all')

def graphFitnessAll(difficulty):
    global figureCount

    fileDifficulty = str(difficulty).split(".")[1]

    # Graph all games
    plt.figure(figureCount)
    filename = fitnessFolder + "/0Fitness_Total.png"
    for x, y, idx, race in totalAxis:
        plt.plot(x, y, label="Game-{}_{}".format(idx, race))
    plt.xlabel('Game Steps')
    plt.ylabel('Fitness Score')
    plt.title("Games Total {}".format(fileDifficulty))
    plt.legend(loc="upper left", bbox_to_anchor=(1,1))
    plt.savefig(filename, bbox_inches="tight")
    plt.close('all')

    # Graph terran games
    plt.figure(figureCount)
    filename = fitnessFolder + "/1Fitness_Terran.png"
    for x, y, idx, race in terranAxis:
        plt.plot(x, y, label="Game-{}".format(idx))
    plt.xlabel('Game Steps')
    plt.ylabel('Fitness Score')
    plt.title("Games Terran {}".format(fileDifficulty))
    plt.legend(loc="upper left", bbox_to_anchor=(1,1))
    plt.savefig(filename, bbox_inches="tight")
    plt.close('all')

    # Graph zerg games
    plt.figure(figureCount)
    filename = fitnessFolder + "/2Fitness_Zerg.png"
    for x, y, idx, race in zergAxis:
        plt.plot(x, y, label="Game-{}".format(idx))
    plt.xlabel('Game Steps')
    plt.ylabel('Fitness Score')
    plt.title("Games Zerg {}".format(fileDifficulty))
    plt.legend(loc="upper left", bbox_to_anchor=(1,1))
    plt.savefig(filename, bbox_inches="tight")
    plt.close('all')

    # Graph protoss games
    plt.figure(figureCount)
    filename = fitnessFolder + "/3Fitness_Protoss.png"
    for x, y, idx, race in protossAxis:
        plt.plot(x, y, label="Game-{}".format(idx))
    plt.xlabel('Game Steps')
    plt.ylabel('Fitness Score')
    plt.title("Games Protoss {}".format(fileDifficulty))
    plt.legend(loc="upper left", bbox_to_anchor=(1,1))
    plt.savefig(filename, bbox_inches="tight")
    plt.close('all')

def trackWinLoss(enemyRace, result):
    global totalWinLoss
    global terranWinLoss
    global zergWinLoss
    global protossWinLoss

    # Get string name from enum
    fileRace = str(enemyRace).split(".")[1]

    # Determine score
    score = np.array([0, 0])
    if str(result) == "Result.Victory":
        score[0] += 1
    else:
        score[1] += 1

    # Add score to the total win/loss
    totalWinLoss += score

    # Add score to terran win/loss
    if fileRace == "Terran":
        terranWinLoss += score
    # Add score to zerg win/loss
    elif fileRace == "Zerg":
        zergWinLoss += score
    # Add score to protoss win/loss
    else:
        protossWinLoss += score

def graphWinLoss():
    global figureCount

    # data to plot
    n_groups = 3
    barWinLoss = list(zip(terranWinLoss, zergWinLoss, protossWinLoss))

    # create plot
    ax = plt.figure(figureCount).gca()
    
    plt.subplots()
    index = np.arange(n_groups)
    bar_width = 0.35

    plt.bar(index, barWinLoss[0], bar_width, label='Win')
    plt.bar(index + bar_width, barWinLoss[1], bar_width,label='Loss')


    plt.xlabel('Races')
    plt.ylabel('Win/Loss')
    plt.title('Win/Loss by race')
    plt.xticks(index + bar_width, ('Terran', 'Zerg', 'Protoss'))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend(loc="upper left", bbox_to_anchor=(1,1))

    plt.tight_layout()
    plt.savefig(winLossFolder + "/12WinLoss_Race.png")
    plt.close('all')

def graphAgentFreqIndividual(enemyRace, difficulty, idx):
    global figureCount

    # Get string name from enum
    fileRace = str(enemyRace).split(".")[1]
    fileDifficulty = str(difficulty).split(".")[1]

    # Put agent freq on the global list
    totalAgentFreq.append((agentFreq, idx, fileRace))

    # Add freq to terran
    if fileRace == "Terran":
        terranAgentFreq.append((agentFreq, idx, fileRace))
    # Add freq to zerg
    elif fileRace == "Zerg":
        zergAgentFreq.append((agentFreq, idx, fileRace))
    # Add freq to protoss
    else:
        protossAgentFreq.append((agentFreq, idx, fileRace))

    # Agent Frequency individual games
    ax = plt.figure(figureCount).gca()

    # labels for bars
    tick_label = list(agentFreq.keys())

    # Number of agents in used in the game
    numAgents = list(range(1, len(agentFreq.keys())+1))

    # plotting a bar chart
    plt.bar(numAgents, agentFreq.values(), tick_label = tick_label, width = 0.8)

    # Rotate the x labels
    plt.xticks(rotation=45, ha="right")

    # naming the x-axis
    plt.xlabel('Agents')
    # naming the y-axis
    plt.ylabel('Times used')

    # plot title
    plt.title('Agent Frequency Game-{}'.format(idx))

    # Integer based y-axis
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    plt.savefig(gamesAgentFolder + "/AgentFreq{}.png".format(idx), bbox_inches="tight")
    plt.close('all')

def graphAgentFreqAll(difficulty):
    global figureCount

    fileDifficulty = str(difficulty).split(".")[1]

    # Graph all games
    ax = plt.figure(figureCount).gca()
    for agent, idx, race in totalAgentFreq:
        agentList = [str(x).split(".")[1].split(" ")[0] for x in listOfAgents]
        freqCount = [0] * len(agentList)
        for x, y in agent.items():
            if x in agentList:
                freqCount[agentList.index(x)] = y
        numAgents = list(range(1, len(agentList)+1))
        plt.bar(numAgents, freqCount, label = "Game-{}_{}".format(idx, race), tick_label = agentList, width = 0.8, alpha=0.3)
    filename = agentFolder + "/4AgentFreq_Total.png"
    plt.xticks(rotation=45, ha="right")
    plt.xlabel('Agents')
    plt.ylabel('Times used')
    plt.title('Agent Frequency Total')
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend(loc="upper left", bbox_to_anchor=(1,1))
    plt.savefig(filename, bbox_inches="tight")
    plt.close('all')

    # Graph terran games
    ax = plt.figure(figureCount).gca()
    for agent, idx, race in terranAgentFreq:
        agentList = [str(x).split(".")[1].split(" ")[0] for x in listOfAgents]
        freqCount = [0] * len(agentList)
        for x, y in agent.items():
            if x in agentList:
                freqCount[agentList.index(x)] = y
        numAgents = list(range(1, len(agentList)+1))
        plt.bar(numAgents, freqCount, label = "Game-{}_{}".format(idx, race), tick_label = agentList, width = 0.8, alpha=0.3)
    filename = agentFolder + "/5AgentFreq_Terran.png"
    plt.xticks(rotation=45, ha="right")
    plt.xlabel('Agents')
    plt.ylabel('Times used')
    plt.title('Agent Frequency Terran')
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend(loc="upper left", bbox_to_anchor=(1,1))
    plt.savefig(filename, bbox_inches="tight")
    plt.close('all')

    # Graph zerg games
    ax = plt.figure(figureCount).gca()
    for agent, idx, race in zergAgentFreq:
        agentList = [str(x).split(".")[1].split(" ")[0] for x in listOfAgents]
        freqCount = [0] * len(agentList)
        for x, y in agent.items():
            if x in agentList:
                freqCount[agentList.index(x)] = y
        numAgents = list(range(1, len(agentList)+1))
        plt.bar(numAgents, freqCount, label = "Game-{}_{}".format(idx, race), tick_label = agentList, width = 0.8, alpha=0.3)
    filename = agentFolder + "/6AgentFreq_Zerg.png"
    plt.xticks(rotation=45, ha="right")
    plt.xlabel('Agents')
    plt.ylabel('Times used')
    plt.title('Agent Frequency Zerg')
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend(loc="upper left", bbox_to_anchor=(1,1))
    plt.savefig(filename, bbox_inches="tight")
    plt.close('all')

    # Graph protoss games
    ax = plt.figure(figureCount).gca()
    for agent, idx, race in protossAgentFreq:
        agentList = [str(x).split(".")[1].split(" ")[0] for x in listOfAgents]
        freqCount = [0] * len(agentList)
        for x, y in agent.items():
            if x in agentList:
                freqCount[agentList.index(x)] = y
        numAgents = list(range(1, len(agentList)+1))
        plt.bar(numAgents, freqCount, label = "Game-{}_{}".format(idx, race), tick_label = agentList, width = 0.8, alpha=0.3)
    filename = agentFolder + "/7AgentFreq_Protoss.png"
    plt.xticks(rotation=45, ha="right")
    plt.xlabel('Agents')
    plt.ylabel('Times used')
    plt.title('Agent Frequency Protoss')
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend(loc="upper left", bbox_to_anchor=(1,1))
    plt.savefig(filename, bbox_inches="tight")
    plt.close('all')

def graphStratFreqIndividual(enemyRace, difficulty, idx):
    global figureCount

    # Get string name from enum
    fileRace = str(enemyRace).split(".")[1]
    fileDifficulty = str(difficulty).split(".")[1]

    # Put agent strat on the global list
    totalStratFreq.append((stratFreq, idx, fileRace))

    # Add strat to terran
    if fileRace == "Terran":
        terranStratFreq.append((stratFreq, idx, fileRace))
    # Add strat to zerg
    elif fileRace == "Zerg":
        zergStratFreq.append((stratFreq, idx, fileRace))
    # Add strat to protoss
    else:
        protossStratFreq.append((stratFreq, idx, fileRace))

    # Agent Strategy individual games
    ax = plt.figure(figureCount).gca()

    # labels for bars
    tick_label = list(stratFreq.keys())

    # Number of agents in used in the game
    numAgents = list(range(1, len(stratFreq.keys())+1))

    # plotting a bar chart
    plt.bar(numAgents, stratFreq.values(), tick_label = tick_label, width = 0.8)

    # Rotate the x labels
    plt.xticks(rotation=45, ha="right")

    # naming the x-axis
    plt.xlabel('Agents')
    # naming the y-axis
    plt.ylabel('Times used')

    # plot title
    plt.title('Agent Strategy Game-{}'.format(idx))

    # Integer based y-axis
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    plt.savefig(gamesStrategyFolder + "/StratFreq{}.png".format(idx), bbox_inches="tight")
    plt.close('all')

def graphStratFreqAll(difficulty):
    global figureCount

    fileDifficulty = str(difficulty).split(".")[1]

    # Graph all games
    ax = plt.figure(figureCount).gca()
    for strat, idx, race in totalStratFreq:
        stratList = [str(x).split(".")[1] for x in list(Strategies)]
        freqCount = [0] * len(stratList)
        for x, y in strat.items():
            if x in stratList:
                freqCount[stratList.index(x)] = y
        numAgents = list(range(1, len(stratList)+1))
        plt.bar(numAgents, freqCount, label = "Game-{}_{}".format(idx, race), tick_label = stratList, width = 0.8, alpha=0.3)
    filename = strategyFolder + "/8StratFreq_Total.png"
    plt.xticks(rotation=45, ha="right")
    plt.xlabel('Strategies')
    plt.ylabel('Times used')
    plt.title('Agent Strategy Total')
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend(loc="upper left", bbox_to_anchor=(1,1))
    plt.savefig(filename, bbox_inches="tight")
    plt.close('all')

    # Graph terran games
    ax = plt.figure(figureCount).gca()
    for strat, idx, race in terranStratFreq:
        stratList = [str(x).split(".")[1] for x in list(Strategies)]
        freqCount = [0] * len(stratList)
        for x, y in strat.items():
            if x in stratList:
                freqCount[stratList.index(x)] = y
        numAgents = list(range(1, len(stratList)+1))
        plt.bar(numAgents, freqCount, label = "Game-{}_{}".format(idx, race), tick_label = stratList, width = 0.8, alpha=0.3)
    filename = strategyFolder + "/9StratFreq_Terran.png"
    plt.xticks(rotation=45, ha="right")
    plt.xlabel('Strategies')
    plt.ylabel('Times used')
    plt.title('Agent Strategy Terran')
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend(loc="upper left", bbox_to_anchor=(1,1))
    plt.savefig(filename, bbox_inches="tight")
    plt.close('all')

    # Graph zerg games
    ax = plt.figure(figureCount).gca()
    for strat, idx, race in zergStratFreq:
        stratList = [str(x).split(".")[1] for x in list(Strategies)]
        freqCount = [0] * len(stratList)
        for x, y in strat.items():
            if x in stratList:
                freqCount[stratList.index(x)] = y
        numAgents = list(range(1, len(stratList)+1))
        plt.bar(numAgents, freqCount, label = "Game-{}_{}".format(idx, race), tick_label = stratList, width = 0.8, alpha=0.3)
    filename = strategyFolder + "/10StratFreq_Zerg.png"
    plt.xticks(rotation=45, ha="right")
    plt.xlabel('Strategies')
    plt.ylabel('Times used')
    plt.title('Agent Strategy Zerg')
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend(loc="upper left", bbox_to_anchor=(1,1))
    plt.savefig(filename, bbox_inches="tight")
    plt.close('all')

    # Graph protoss games
    ax = plt.figure(figureCount).gca()
    for strat, idx, race in protossStratFreq:
        stratList = [str(x).split(".")[1] for x in list(Strategies)]
        freqCount = [0] * len(stratList)
        for x, y in strat.items():
            if x in stratList:
                freqCount[stratList.index(x)] = y
        numAgents = list(range(1, len(stratList)+1))
        plt.bar(numAgents, freqCount, label = "Game-{}_{}".format(idx, race), tick_label = stratList, width = 0.8, alpha=0.3)
    filename = strategyFolder + "/11StratFreq_Protoss.png"
    plt.xticks(rotation=45, ha="right")
    plt.xlabel('Strategies')
    plt.ylabel('Times used')
    plt.title('Agent Strategy Protoss')
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend(loc="upper left", bbox_to_anchor=(1,1))
    plt.savefig(filename, bbox_inches="tight")
    plt.close('all')


def main():
    # Axis for graphing
    global totalAxis
    global terranAxis
    global zergAxis
    global protossAxis
    totalAxis = []
    terranAxis = []
    zergAxis = []
    protossAxis = []

    # Win/Loss
    global totalWinLoss
    global terranWinLoss
    global zergWinLoss
    global protossWinLoss
    totalWinLoss = np.array([0, 0])
    terranWinLoss = np.array([0, 0])
    zergWinLoss = np.array([0, 0])
    protossWinLoss = np.array([0, 0])

    # Agent freq
    global totalAgentFreq
    global terranAgentFreq
    global zergAgentFreq
    global protossAgentFreq
    totalAgentFreq = []
    terranAgentFreq = []
    zergAgentFreq = []
    protossAgentFreq = []

    # Agent Freq values added when agent runs
    global agentFreq
    agentFreq = defaultdict(lambda: 0)

    # Agent strat
    global totalStratFreq
    global terranStratFreq
    global zergStratFreq
    global protossStratFreq
    totalStratFreq = []
    terranStratFreq = []
    zergStratFreq = []
    protossStratFreq = []

    # Agent Strat values added when agent runs
    global stratFreq
    stratFreq = defaultdict(lambda: 0)

    # x and y values added when agent runs
    global xAxis
    global yAxis
    xAxis = []
    yAxis = []

    # directory to store graphs
    global folderName
    folderName = ""

    # Keep track of figure
    global figureCount
    figureCount = 0

    # Make graphs folder
    if not os.path.exists("./graphs"):
        os.mkdir("./graphs")

    global fitnessFolder
    global agentFolder
    global strategyFolder
    global gamesFitnessFolder
    global gamesAgentFolder
    global gamesStrategyFolder
    global winLossFolder

    # Make subfolder for game session in graph
    folderName = strftime("%Y-%m-%d %H%M%S", localtime())
    if not os.path.exists("./graphs/{}".format(folderName)):
        os.mkdir("./graphs/{}".format(folderName))

    # Create subfolders for inside game session
    fitnessFolder = "./graphs/{}/0fitness".format(folderName)
    agentFolder = "./graphs/{}/1agent".format(folderName)
    strategyFolder = "./graphs/{}/2strategy".format(folderName)
    winLossFolder = "./graphs/{}/3winloss".format(folderName)
    gamesFitnessFolder = "./graphs/{}/4games_fitness".format(folderName)
    gamesAgentFolder = "./graphs/{}/5games_agent".format(folderName)
    gamesStrategyFolder = "./graphs/{}/6games_strategy".format(folderName)

    # Make subfolder for fitness
    if not os.path.exists(fitnessFolder):
        os.mkdir(fitnessFolder)

    # Make subfolder for agent
    if not os.path.exists(agentFolder):
        os.mkdir(agentFolder)

    # Make subfolder for strategy
    if not os.path.exists(strategyFolder):
        os.mkdir(strategyFolder)

    #Make subfolder for winloss
    if not os.path.exists(winLossFolder):
        os.mkdir(winLossFolder)

    # Make subfolder for games of fitness
    if not os.path.exists(gamesFitnessFolder):
        os.mkdir(gamesFitnessFolder)

    # Make subfolder for games of agent
    if not os.path.exists(gamesAgentFolder):
        os.mkdir(gamesAgentFolder)

    # Make subfolder for games of strategy
    if not os.path.exists(gamesStrategyFolder):
        os.mkdir(gamesStrategyFolder)

    # Read command line arguments
    args = readArguments()

    # Check which arguments are specified otherwise use defaults
    race, difficulty, number = checkNParseArgs(args)

    print(bcolors.OKGREEN + "###Enemy Race is " + bcolors.FAIL + "{}".format(race) + bcolors.ENDC)
    print(bcolors.OKGREEN + "###Difficulty is {}".format(difficulty) + bcolors.ENDC)
    print(bcolors.OKGREEN + "###Number of games is {}\n".format(number) + bcolors.ENDC)

    # Race of enemy opponent
    enemyRaceList = [Race.Terran, Race.Zerg, Race.Protoss]

    # Play number of games
    for idx in range(number):
        # Reset axis for each game before running agent
        xAxis = []
        yAxis = []
        # Reset agent frequency
        agentFreq = defaultdict(lambda: 0)
        # Reset agent strategy
        stratFreq = defaultdict(lambda: 0)

        # Generate Random Opponent
        if race == "random":
            enemyRace = random.choice(enemyRaceList)
        else:
            enemyRace = race

        print(bcolors.OKGREEN + "###Opponent is " + bcolors.FAIL + "{}: {}".format(enemyRace, enemyRaceList.index(enemyRace)) + bcolors.ENDC)

        # Start game with AgentSelector as the Bot, and begin logging
        result = sc2.run_game(sc2.maps.get("Abyssal Reef LE"), [
            Bot(Race.Zerg, AgentSelector(True, True, True)),
            # If you change the opponent race remember to change nInputs in the __init__ as well
            Computer(enemyRace, difficulty)
        ], realtime=False)

        # Graph individual games
        graphFitnessIndividual(enemyRace, difficulty, idx)

        # Keep track of win/loss
        trackWinLoss(enemyRace, result)

        # Graph individual agent frequencies
        graphAgentFreqIndividual(enemyRace, difficulty, idx)

        # Graph individual agent strategies
        graphStratFreqIndividual(enemyRace, difficulty, idx)

        # Handles Ctrl-C exit
        try:
            if interrupted:
                print(bcolors.FAIL + "Exiting Loop - Interrupt" + bcolors.ENDC)
                break
        # Handles X-Button exit
        except:
            if result == None:
                print(bcolors.FAIL + "Exiting Loop - Normal" + bcolors.ENDC)
                break

    # Graph all for total and for each race
    graphFitnessAll(difficulty)

    # Graph all for frequency
    graphAgentFreqAll(difficulty)

    # Graph all for strategy
    graphStratFreqAll(difficulty)

    # Graph win loss for each race
    graphWinLoss()

    os._exit(1)

if __name__ == '__main__':
    main()
