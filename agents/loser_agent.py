# https://chatbotslife.com/building-a-basic-pysc2-agent-b109cde1477c
import asyncio
import random

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer

from pprint import pprint
from time import gmtime, strftime, localtime
import os

# For debugging purposes only
import sys

# Get strategy enums
from strategies import Strategies

from sc2.position import Point2
from sc2.data import race_townhalls

class LoserAgent(sc2.BotAI):
    mainAgent = None
    def __init__(self, is_logging = False, is_printing_to_console = False, isMainAgent = False, fileName = ""):
        super().__init__()

        if isMainAgent:
            # For debugging
            self.is_logging = is_logging  # Setting this to true to write information to log files in the agents/logs directory
            self.is_printing_to_console = is_printing_to_console  # Setting this to true causes all logs to be printed to the console

            # Make logs directory if it doesn't exist
            if not os.path.exists("./logs"):
                os.mkdir("./logs")
            self.log_file_name = "./logs/" + fileName + strftime("%Y-%m-%d %H%M%S", localtime()) + ".log"
            self.log_file = open(self.log_file_name, "w+")  # Create log file based on the time

            # Constants
            self.researched = 2  # If an upgrade has been research
            self.is_researching = 1  # If an upgrade is being researched
            self.not_researched = 0  # If an upgrade is not being researched and has not been researched

            # non-standard upgrade status
            self.can_burrow = 0
            self.zergling_speed = 0
            self.zergling_attack_boost = 0
            self.baneling_speed = 0
            self.roach_speed = 0
            self.roach_tunnel = 0
            self.overlord_speed = 0
            self.hydralisk_range = 0
            self.infestor_parasite = 0
            self.infestor_energy = 0
            self.ultralisk_defense = 0

            # standard upgrades
            # Ground melee
            self.melee1 = 0
            self.melee2 = 0
            self.melee3 = 0

            # Ground ranged
            self.ranged1 = 0
            self.ranged2 = 0
            self.ranged3 = 0

            # Ground defense
            self.carapace1 = 0
            self.carapace2 = 0
            self.carapace3 = 0

            # Flyer attack
            self.flyer_attack1 = 0
            self.flyer_attack2 = 0
            self.flyer_attack3 = 0

            # Flyer defense
            self.flyer_defense1 = 0
            self.flyer_defense2 = 0
            self.flyer_defense3 = 0

            # units built
            self.num_zerglings_built = 0
            self.num_drones_built = 0
            self.num_queens_built = 0
            self.num_roaches_built = 0
            self.num_hydralisks_built = 0
            self.num_banelines_built = 0
            self.num_lurkers_built = 0
            self.num_ravagers_built = 0
            self.num_mutalisks_built = 0
            self.num_corrupters_built = 0
            self.num_brood_lords_built = 0
            self.num_swarm_hosts_built = 0
            self.num_vipers_built = 0
            self.num_ultralisks_built = 0

            # Static defenses built
            self.num_spinecrawlers_built = 0
            self.num_sporecrawlers_built = 0

            # Structure built
            self.num_extractors_built = 0
            self.num_hatcheries_built = 0
            self.num_spawningpools_built = 0
            self.num_roachwarrens_built = 0
            self.num_hyraliskdens_built = 0
            self.num_lairs_built = 0
            self.num_infestation_pits_built = 0
            self.num_lurkerdens_built = 0
            self.num_hives_built = 0
            self.num_ultralisk_caverns_built = 0
            self.num_spires_built = 0
            self.num_greater_spires_built = 0

            # Units actively being used for things, gets set to null on strategy change
            self.strike_force = None

            # Previous strategy so you now when the strategy changes
            self.prev_strategy = None

            # True if strategy just changed in this iteration
            self.did_strategy_change = False
            LoserAgent.mainAgent = self

            # Way point for units to move to
            self.waypoint = None

            self.mutalisk_waypoint = None

            # Predict enemy will be in the first possible position
            self.predicted_enemy_position_num = -1

            # Position to search for enemy untis
            self.num_enemy_positions = -1

            # Position the bot begins
            self.mainAgent.start_location = None

            # Easier way to access map information, must be loaded in after game loads
            self.map_height = None
            self.map_width = None

            # Top left corner of the map for mutas
            self.map_corner = None

            # Set to true after army is requested to prevent duplicate queries in the same iteration
            # gets set to false in each perform_strategy call
            self.is_army_cached = False;

            # Saves army each iteration to prevent duplicate queries
            self.cached_army = None

    '''
    Base on_step function
    Uses basic_build and performs actions based on the current strategy
    For now, strategies will change ever 100 steps
    Harass strategies are not implemented yet
    '''
    async def on_step(self, iteration, strategy_num):
        # self.log("Step: %s Overlord: %s" % (str(iteration), str(self.mainAgent.units(OVERLORD).amount)))
        # self.log("Step: " + str(iteration))

        # TEMP: Until strategy is given by Q table
        #strategy_num = (int)(iteration / 75) % 12

        # Build lings, queen, overlords, drones, and meleeattack1
        await self.basic_build(iteration)

        # Perform actions based on given strategy
        if strategy_num == -1:
            # self.mainAgent.log("No given strategy")
            pass
        else:
            await self.perform_strategy(iteration, strategy_num)

    '''
    Builds a ton of lings
    Build drones and start gathering vespene
    Build a queen
    Build overlords as needed
    Builds a few hydralisks
    '''
    async def basic_build(self, iteration):

        hatchery = self.mainAgent.bases.ready.random
        # Build overlords if close to reaching cap
        if self.mainAgent.supply_used > self.mainAgent.supply_cap - 4 and self.mainAgent.num_larva > 0 and self.mainAgent.can_afford(OVERLORD):
            await self.mainAgent.do(self.mainAgent.random_larva.train(OVERLORD))
        else:
            # Build drones
            if self.mainAgent.units(DRONE).amount < 20 and self.mainAgent.can_afford(DRONE) and self.mainAgent.units(LARVA).amount > 0 and self.mainAgent.supply_used < self.mainAgent.supply_cap:
                await self.mainAgent.do(self.mainAgent.random_larva.train(DRONE))

            if self.mainAgent.units(SPIRE).ready.exists and self.mainAgent.units(MUTALISK).amount < 20 and self.mainAgent.supply_used < self.mainAgent.supply_cap - 3 \
                and self.mainAgent.can_afford(MUTALISK) and self.mainAgent.num_larva > 0:
                await self.mainAgent.do(self.mainAgent.random_larva.train(MUTALISK))

            if self.mainAgent.units(HYDRALISKDEN).ready.exists and self.mainAgent.units(HYDRALISK).amount < 20 and self.mainAgent.supply_used < self.mainAgent.supply_cap - 3 \
                    and self.mainAgent.can_afford(HYDRALISK) and self.mainAgent.num_larva > 0:
                await self.mainAgent.do(self.mainAgent.random_larva.train(HYDRALISK))

            # Build lings
            if self.mainAgent.units(ZERGLING).amount + self.mainAgent.already_pending(ZERGLING) < 5 and self.mainAgent.can_afford(ZERGLING) and self.mainAgent.num_larva > 0 and \
                    self.mainAgent.supply_used < self.mainAgent.supply_cap - 1 and self.mainAgent.units(SPAWNINGPOOL).ready.exists:
                await self.mainAgent.do(self.mainAgent.random_larva.train(ZERGLING))
        # Build Spawning pool
        if not self.mainAgent.units(SPAWNINGPOOL).exists and self.mainAgent.can_afford(SPAWNINGPOOL):
            p = hatchery.position.towards(self.mainAgent.game_info.map_center, 3)
            await self.mainAgent.build(SPAWNINGPOOL, near=p)

        if self.mainAgent.units(EXTRACTOR).amount < 2 and self.mainAgent.can_afford(EXTRACTOR) and self.mainAgent.already_pending(EXTRACTOR) < 2:
            self.mainAgent.num_extractors_built += 1
            drone = self.mainAgent.workers.random
            target = self.mainAgent.state.vespene_geyser.closest_to(drone.position)
            await self.mainAgent.do(drone.build(EXTRACTOR, target))

        # If Extractor does not have 3 drones, give it more drones
        for extractor in self.mainAgent.units(EXTRACTOR):
            if extractor.assigned_harvesters < extractor.ideal_harvesters and self.mainAgent.workers.amount > 0:
                await self.mainAgent.do(self.mainAgent.workers.random.gather(extractor))

        # # Build Evolution Chamber pool
        # if not self.mainAgent.units(EVOLUTIONCHAMBER).exists and self.mainAgent.can_afford(SPAWNINGPOOL):
        #     p = hatchery.position.towards(self.mainAgent.game_info.map_center, 3)
        #     await self.mainAgent.build(EVOLUTIONCHAMBER, near=p)
        # elif self.mainAgent.can_afford(RESEARCH_ZERGMELEEWEAPONSLEVEL1) and self.mainAgent.melee1 == 0 and self.mainAgent.units(EVOLUTIONCHAMBER).ready.exists:
        #     # Get melee1 upgrade
        #     self.mainAgent.melee1 = 1
        #     await self.mainAgent.do(self.mainAgent.units(EVOLUTIONCHAMBER).first(RESEARCH_ZERGMELEEWEAPONSLEVEL1))

        # Build a queen if you haven't
        if self.mainAgent.num_queens_built < 1 and self.mainAgent.units(SPAWNINGPOOL).ready.exists and self.mainAgent.can_afford(QUEEN) and \
                self.mainAgent.supply_used < self.mainAgent.supply_cap - 1:
            base = self.mainAgent.bases.random
            self.mainAgent.num_queens_built += 1
            await self.mainAgent.do(base.train(QUEEN))

        # Inject larva when possible
        elif self.mainAgent.units(QUEEN).amount > 0:
            queen = self.mainAgent.units(QUEEN).first
            abilities = await self.mainAgent.get_available_abilities(queen)
            if AbilityId.EFFECT_INJECTLARVA in abilities:
                await self.mainAgent.do(queen(EFFECT_INJECTLARVA, hatchery))

        # Upgrade to lair when possible
        if self.mainAgent.num_lairs_built == 0 and self.mainAgent.units(HATCHERY).amount > 0 and self.mainAgent.can_afford(AbilityId.UPGRADETOLAIR_LAIR) \
                and self.mainAgent.can_afford(UnitTypeId.LAIR) and self.mainAgent.units(SPAWNINGPOOL).ready.exists and self.mainAgent.units(QUEEN).amount > 0:
            hatchery = self.mainAgent.units(HATCHERY).first
            self.mainAgent.num_lairs_built += 1
            err = await self.mainAgent.do(hatchery(UPGRADETOLAIR_LAIR))
            if err:
                self.mainAgent.num_lairs_built -= 1

        # # Build hydralisk den when possible
        # if not self.mainAgent.units(HYDRALISKDEN).exists and self.mainAgent.units(LAIR).amount > 0 and self.mainAgent.can_afford(HYDRALISKDEN) \
        #         and self.mainAgent.num_hydralisks_built == 0:
        #     p = hatchery.position.towards(self.mainAgent.game_info.map_center, 3)
        #     self.mainAgent.num_hydralisks_built += 1
        #     await self.mainAgent.build(HYDRALISKDEN, near=p)
        #
        # # Build lurker den when possible
        # if self.mainAgent.num_lurkerdens_built == 0 and self.mainAgent.units(HYDRALISKDEN).ready.amount > 0 and \
        #         self.mainAgent.can_afford(UPGRADETOLURKERDEN_LURKERDEN):
        #     # await self.mainAgent.do(self.mainAgent.units(HYDRALISKDEN).first(UPGRADETOLURKERDEN_LURKERDEN ))
        #     self.mainAgent.num_lurkerdens_built += 1
        #     await self.mainAgent.do(self.mainAgent.units(HYDRALISKDEN).first(MORPH_LURKERDEN))

        if not self.mainAgent.units(SPIRE).exists and self.mainAgent.units(LAIR).amount > 0 and self.mainAgent.can_afford(SPIRE) \
            and not self.mainAgent.already_pending(SPIRE):
            p = hatchery.position.towards(self.mainAgent.game_info.map_center, 3)
            await self.mainAgent.build(SPIRE, near=p)


    '''
    Calls the correct strategy function given the strategy enum value
    Strategy functions can be override in base classes
    '''
    async def perform_strategy(self, iteration, strategy_num):
        self.mainAgent.clean_strike_force()  # Clear dead units from strike force
        self.mainAgent.is_army_cached = False  # Must re obtain army data
        if self.mainAgent.predicted_enemy_position_num == -1:
            # Initializing things that are needed after game data is loaded

            # Assume first position
            self.mainAgent.predicted_enemy_position = 0
            self.mainAgent.num_enemy_positions = len(self.mainAgent.enemy_start_locations)
            self.mainAgent.start_location = self.mainAgent.bases.ready.random.position # Should only be 1 hatchery at this time
            self.mainAgent.map_width = self.mainAgent.game_info.map_size[0]
            self.mainAgent.map_height = self.mainAgent.game_info.map_size[1]

            # Get a point in the corner of the map
            p = lambda: None  # https://stackoverflow.com/questions/19476816/creating-an-empty-object-in-python
            p.x = self.mainAgent.game_info.map_center.x * 1.9
            p.y = self.mainAgent.game_info.map_center.y * 1.9
            self.mainAgent.map_corner = Point2.from_proto(p)


        # Make sure given strategy num is valid
        if Strategies.has_value(strategy_num):
            # Valid strategy num, convert int into enum value
            strategy = Strategies(strategy_num)

            # Mark strategy as changed or not
            if strategy != self.mainAgent.prev_strategy:
                self.mainAgent.log("New strategy is " + str(strategy))
                self.mainAgent.did_strategy_change = True
                self.mainAgent.strike_force = None
            else:
                self.mainAgent.did_strategy_change = False

            self.mainAgent.prev_strategy = strategy  # Prepare for next iteration
        else:
            self.log_error(f"Unknown strategy number {strategy_num}")
            return

        # Call the proper strategy function

        # Attack
        if strategy == Strategies.HEAVY_ATTACK:
            await self.heavy_attack(iteration)
        elif strategy == Strategies.MEDIUM_ATTACK:
            await self.medium_attack(iteration)
        elif strategy == Strategies.LIGHT_ATTACK:
            await self.light_attack(iteration)

        # Scouting
        elif strategy == Strategies.HEAVY_SCOUTING:
            await self.heavy_scouting(iteration)
        elif strategy == Strategies.MEDIUM_SCOUTING:
            await self.medium_scouting(iteration)
        elif strategy == Strategies.LIGHT_SCOUTING:
            await self.light_scouting(iteration)

        # Defense
        elif strategy == Strategies.HEAVY_DEFENSE:
            await self.heavy_defense(iteration)
        elif strategy == Strategies.MEDIUM_DEFENSE:
            await self.medium_defense(iteration)
        elif strategy == Strategies.LIGHT_DEFENSE:
            await self.light_defense(iteration)

        # Harass
        elif strategy == Strategies.HEAVY_HARASS:
            await self.heavy_harass(iteration)
        elif strategy == Strategies.MEDIUM_HARASS:
            await self.medium_harass(iteration)
        elif strategy == Strategies.LIGHT_HARASS:
            await self.light_harass(iteration)

        # Unknown
        else:
            self.log("Unknown strategy was given: " + str(strategy))

    '''
    Send all combat units (including the queen) to a known enemy position
    Do NOT recall ever
    '''
    async def heavy_attack(self, iteration):
        await self.attack_with_percentage_of_army(0, 0)

    '''
    Send all combat units (including the queen) to a known enemy position
    Recall after a certain amount of units die
    Must keep track of units being used because order of units in self.units constantly changes
    '''
    async def medium_attack(self, iteration):
        await self.attack_with_percentage_of_army(.75, 15)
    '''
    Attack a known enemy position, but if you get attacked, retreat back to base
    '''

    async def light_attack(self, iteration):
        await self.attack_with_percentage_of_army(.9, .3)

    # If more than percentage_to_advance_group percent of strike force is
    async def attack_with_percentage_of_army(self, percentage_to_advance_group, percentage_to_retreat_group):
        army = self.mainAgent.army

        if len(army) == 0:
            # No army to use, don't bother trying to attack
            self.mainAgent.waypoint = self.mainAgent.game_info.map_center # Restart waypoint
            return

        # Move army to mainAgent's waypoint and attack things on the way
        percentage_units_at_waypoint = \
            await self.move_and_get_percent_units_at_waypoint(army, self.mainAgent.waypoint, True)

        # If all units are close to the waypoint, pick a closer one
        if percentage_units_at_waypoint > percentage_to_advance_group:
            target = self.mainAgent.select_target()
            self.mainAgent.waypoint = self.mainAgent.waypoint.towards(target, 20)
        elif percentage_units_at_waypoint < percentage_to_retreat_group:
            # Move waypoint back
            if (self.mainAgent.waypoint != self.mainAgent.start_location):
                self.mainAgent.waypoint = self.mainAgent.waypoint.towards(self.mainAgent.start_location, 1)


    async def move_and_get_percent_units_at_waypoint(self, units, waypoint, should_attack):
        # Keep units together
        num_units_at_waypoint = 0
        # All strike force members attack to the waypoint
        for unit in units:
            distance_from_waypoint = unit.position.to2.distance_to(waypoint)
            if distance_from_waypoint < 15:
                num_units_at_waypoint += 1

            if should_attack:
                await self.mainAgent.do(unit.attack(waypoint))
            else:
                await self.mainAgent.do(unit.move(waypoint))


        percentage_units_at_waypoint = num_units_at_waypoint / len(units)
        return percentage_units_at_waypoint

    '''
    Send all military units out to different areas
    Die for knowledge
    '''
    async def heavy_scouting(self, iteration):
        await self.scout_with_percentage_of_army(1, True, False)

    '''
    Send a good amount of military units out
    '''
    async def medium_scouting(self, iteration):
        await self.scout_with_percentage_of_army(.5, True, False)

    '''
    Send a couple of things out for scouting and pull back if damage is taken
    '''
    async def light_scouting(self, iteration):
        await self.scout_with_percentage_of_army(.5, True, True)

    async def scout_with_percentage_of_army(self, percentage, use_overlords, pull_back_if_damaged):
        map_width = self.mainAgent.map_width
        map_height = self.mainAgent.map_height

        army = self.army

        if use_overlords:
            army += self.mainAgent.units(OVERLORD)

        desired_strike_force_size = int(percentage * army.amount)
        if self.mainAgent.strike_force is None:
            self.mainAgent.strike_force = army.take(desired_strike_force_size)

        # If strike force should include more members (If a unit was built)
        # Do not add more units if the entire army is already in strike force
        if len(self.mainAgent.strike_force) < desired_strike_force_size and len(army) > len(self.mainAgent.strike_force):
            self.mainAgent.strike_force += (army - self.mainAgent.strike_force).take(desired_strike_force_size - len(self.mainAgent.strike_force))

        for unit_ref in self.mainAgent.strike_force:
            # Need to reacquire unit from self.mainAgent.units to see that a command has been queued
            id = unit_ref.tag
            unit = self.mainAgent.units.find_by_tag(id)

            if unit is None:
                # Unit died
                self.mainAgent.strike_force.remove(unit_ref)
                continue
            if pull_back_if_damaged and unit.health < unit.health_max:
                # If pull_back is true and unti is damaged, move to random hatchery
                if (len(self.mainAgent.bases) > 0):
                    await self.mainAgent.do(unit.move(self.mainAgent.bases[random.randrange(0, len(self.mainAgent.bases))].position))
            elif unit.noqueue:
                # Go to a new random position
                pos = lambda: None  # https://stackoverflow.com/questions/19476816/creating-an-empty-object-in-python
                pos.x = random.randrange(0, map_width)
                pos.y = random.randrange(0, map_height)
                position_to_search = Point2.from_proto(pos)
                await self.mainAgent.do(unit.move(position_to_search))

    '''
    Complete recall back to main base
    Build lots of static defenses
    Build lots of lurkers
    '''
    async def heavy_defense(self, iteration):
        # Build 5 spinecrawlers and sporecrawlers, and 10 lurkers
        await self.prepare_defenses(4, 4, 10)

    '''
    Recall and distribute between main base and explansions
    Build some defensive structures and units
    '''
    async def medium_defense(self, iteration):
        # Build 3 spinecrawlers and sporecrawlers, and 5 lurkers
        await self.prepare_defenses(3, 3, 5)

    '''
    Distribute forces between main base and expansions
    Build a few defensive structures and units
    '''
    async def light_defense(self, iteration):
        # Build 1 spinecrawlers and sporecrawlers, and 3 lurkers
        await self.prepare_defenses(1, 1, 3)


    async def prepare_defenses(self, num_spine_crawlers_to_build, num_sporecrawlers_to_build, num_lurkers_to_build):
        hatchery = self.mainAgent.bases.ready.random

        # TODO: have some units go to expansions
        # Return all units to base
        for unit in self.mainAgent.army + self.mainAgent.overlords:
            if unit.distance_to(hatchery.position) > 20:
                await self.mainAgent.do(unit.move(hatchery.position))


        # Build spine crawlers
        if self.mainAgent.units(SPAWNINGPOOL).ready.exists and self.mainAgent.num_spinecrawlers_built < num_spine_crawlers_to_build \
                and self.mainAgent.can_afford(SPINECRAWLER):
            self.mainAgent.num_spinecrawlers_built += 1
            p = hatchery.position.towards(self.mainAgent.game_info.map_center, 3)
            await self.mainAgent.build(SPINECRAWLER, near=p)

        # Build spore crawlers
        if self.mainAgent.units(EVOLUTIONCHAMBER).ready.exists and self.mainAgent.num_sporecrawlers_built < num_sporecrawlers_to_build \
                and self.mainAgent.can_afford(SPORECRAWLER):
            self.mainAgent.num_sporecrawlers_built += 1
            p = hatchery.position.towards(self.mainAgent.game_info.map_center, 3)
            await self.mainAgent.build(SPORECRAWLER, near=p)


        # Build lurkers
        if self.mainAgent.units(LURKERDENMP).ready.exists and self.mainAgent.num_lurkers_built < num_lurkers_to_build \
                and self.mainAgent.can_afford(MORPH_LURKER) and self.mainAgent.num_larva > 0 and self.mainAgent.units(HYDRALISK).amount > 0:
            self.mainAgent.num_lurkers_built += 1
            hydralisk = self.mainAgent.units(HYDRALISK).random
            err = await self.mainAgent.do(hydralisk(MORPH_LURKER))
            if err:
                self.mainAgent.num_lurkers_built -= 1

        # Burrow all lurkers so they can attack
        for lurker in self.mainAgent.units(LURKERMP):
            abilities = await self.mainAgent.get_available_abilities(lurker)
            if AbilityId.BURROWDOWN_LURKER in abilities:
                await self.mainAgent.do(lurker(BURROWDOWN_LURKER))


    '''
    Build swarms hosts and harass with them
    Build mutalisks and harass with them
    If harass units are attacked, move to the next base
    '''
    async def heavy_harass(self, iteration):
        await self.harass(0)  # Die for the harass

    '''
    TODO
    '''
    async def medium_harass(self, iteration):
        await self.harass(.5)  # Return if damaged to half health

    '''
    If attacked pull back for a set time
    Only use harass units if you have them
    '''
    async def light_harass(self, iteration):
        await self.harass(1)  # Return immediately if damaged

    async def harass(self, percent_health_to_return):


        if self.mainAgent.did_strategy_change:
            self.mainAgent.mutalisk_waypoint = self.mainAgent.map_corner

        if self.army.amount == 0:
            # Nothing to harass with
            return

        harass_target = self.get_harass_target()


        mutalisks = self.mainAgent.units(MUTALISK)

        # Mutalisk harass is different from other things
        if mutalisks.amount > 0:
            if self.mainAgent.mutalisk_waypoint == self.mainAgent.enemy_start_locations[0]:
                # Second phase of muta harass, when at the enemy base, begin attacking
                for muta in mutalisks:
                    if muta.position.to2.distance_to(self.mainAgent.mutalisk_waypoint):
                        # Begin attacking workers or anything nearby
                        await self.mainAgent.do(muta.attack(harass_target))
                    else:
                        # Move to whre the workers are without attacking
                        await self.mainAgent.do(muta.move(self.mainAgent.mutalisk_waypoint))
            else:
                # Phase 1: Gather the mutas
                # Move mutalisks to mutalisk waypoint, and do not attack anything else on the way
                percentage_mutas_at_waypoint = await \
                    self.move_and_get_percent_units_at_waypoint(mutalisks, self.mainAgent.mutalisk_waypoint, False)
                if percentage_mutas_at_waypoint > .75:
                    self.mainAgent.mutalisk_waypoint = self.mainAgent.enemy_start_locations[0]  # Send them off to the enemy base

        for unit in self.army - self.mainAgent.units(MUTALISK):
            if unit.health < unit.health_max * percent_health_to_return:
                # low on health so come back
                await self.mainAgent.do(unit.move(self.mainAgent.bases.random))
            else:
                # still full health so keep attacking
                await self.mainAgent.do(unit.attack(harass_target))

    # Finds a target to harass
    # Will first choose workers, and if there are no workers, then to go a known base, and in no known bases,
    # Go to enemy main base
    def get_harass_target(self):
        # If there are known enemy expansions, harass those
        enemy_workers = self.mainAgent.known_enemy_units.filter(lambda x: x.name == "Drone" or x.name == "SCV" or x.name == "Probe")

        # If workers are visible, attack them
        if len(enemy_workers) > 0:
            harass_target = enemy_workers.random.position
        else:
            # If no workers are visible, find a town hall to attack
            enemy_bases = self.get_known_enemy_bases()
            if len(enemy_bases) > 0:
                harass_target = enemy_bases[random.randint(0, len(enemy_bases) - 1)]
            else:
                # if no town halls are known, go to the enemy start
                harass_target = self.mainAgent.enemy_start_locations[0]

        return harass_target

    '''
    Removes dead units from strike force
    '''
    def clean_strike_force(self):
        if self.mainAgent.strike_force is None:
            # No defined strike force yet
            return
        for unit in self.mainAgent.strike_force:
            if self.mainAgent.units.find_by_tag(unit.tag) is None:
                self.mainAgent.strike_force.remove(unit)


    '''
    Utilities
    '''

    @property
    def army(self):
        if self.mainAgent.is_army_cached:
            return self.mainAgent.cached_army
        else:
            self.mainAgent.is_army_cached = True
            self.cached_army = self.mainAgent.units.filter(
                lambda x: x.name != "Drone" and x.name != "Overlord" and x.name != "Queen" and x.name != "CreepTumorQueen"\
                          and x.name != "Egg" and x.name != "Larva" and not x.is_structure and x.name != "CreepTumorBurrowed") \
                            - self.mainAgent.units(LURKERMPBURROWED) - self.mainAgent.units(LURKERMPEGG) \
                            - self.mainAgent.units(BANELINGCOCOON)
            return self.cached_army

    @property
    def overlords(self):
        return self.mainAgent.units(OVERLORD)

    @property
    def buildings(self):
        return self.mainAgent.units.filter(lambda x: x.is_structure) + self.mainAgent.units(SPINECRAWLER) + self.mainAgent.units(SPORECRAWLER)

    @property
    def bases(self):
        return self.mainAgent.units.filter(lambda x: x.name == "Hatchery" or x.name == "Lair" or x.name == "Hive")

    def get_random_worker(self):
        return self.mainAgent.units(DRONE).random

    @property
    def game_time(self):
        return self.mainAgent.state.game_loop * 0.725 * (1 / 16)

    def get_known_enemy_bases(self):
        # Get all enemy structures, then filter to only take townhall types
        enemy_structures = self.mainAgent.known_enemy_structures
        townhall_ids = [item for sublist in race_townhalls.values() for item in sublist]
        return enemy_structures.filter(lambda x: x.type_id in townhall_ids)

    '''
    From Dentosal's proxyrax build
    Targets a random known enemy building
    If no known buildings, go towards to a possible enemy start position
    '''
    def select_target(self):
        target = self.mainAgent.known_enemy_units
        if target.exists:
            return target.random.position

        target = self.mainAgent.known_enemy_units
        if target.exists:
            return target.random.position

        return self.mainAgent.enemy_start_locations[0]

        # Code to explore more than one enemy starting position not needed because all maps are only 2 people
        # Not tested

        # # Explore other starting positions
        # units_near_predicted_position = self.mainAgent.units.filter(lambda x: x.position.distance_to(
        #     self.enemy_start_locations[self.predicted_enemy_position]) < 5)
        # if len(units_near_predicted_position) > 0:
        #     # There is a unit near the predicted position, but no visible structures or enemies
        #     self.predicted_enemy_position = (self.predicted_enemy_position + 1)
        #     # loop over starting positions if needed
        #     if self.predicted_enemy_position >= self.num_enemy_positions:
        #         self.predicted_enemy_position = 0
        #
        # return self.enemy_start_locations[self.predicted_enemy_position]

    @property
    def num_larva(self):
        """Get the current amount of larva"""
        return self.mainAgent.units(LARVA).amount

    @property
    def random_larva(self):
        """Get a random larva"""
        return self.mainAgent.units(LARVA).random

    '''
    Prints to console if self.is_printing_to_console
    Writes to log file if self.is_logging
    '''
    def log(self, data):
        """Log the data to the logfile if this agent is set to log information and logfile is below 1 megabyte"""
        if self.mainAgent.is_logging and os.path.getsize(self.mainAgent.log_file_name) < 1000000:
            self.mainAgent.log_file.write(f"{data}\n")
        if self.mainAgent.is_printing_to_console:
            print(data)

    def log_error(self, data):
        data = f"ERROR: {data}"
        self.mainAgent.log_file.write(f"{data}\n")
        print(data)


def main():
    # Start game with LoserAgent as the Bot, and begin logging
    sc2.run_game(sc2.maps.get("Abyssal Reef LE"), [
        Bot(Race.Zerg, LoserAgent(True, True, True)),
        Computer(Race.Protoss, Difficulty.Medium)
    ], realtime=False)

if __name__ == '__main__':
    main()
