from loser_agent import *

class ZerglingBanelingRushAgent(LoserAgent):
    def __init__(self, is_logging = False, is_printing_to_console = False, isMainAgent = False, fileName = ""):
        super().__init__()

        self.drone_counter = 0
        self.overlord_counter = 0
        self.zergling_counter = 0
        self.baneling_counter = 0
        self.extractor_started = False
        self.hatchery_started = False
        self.spawning_pool_started = False
        self.moved_workers_to_gas = False
        self.moved_workers_from_gas = False
        self.moved_worker_to_expand = False
        self.queen_started = False
        self.mboost_started = False
        self.baneling_nest_started = False
        self.chooks_started = False

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

        self.strike_force = None

        # Previous strategy so you now when the strategy changes
        self.prev_strategy = None

        # True if strategy just changed in this iteration
        self.did_strategy_change = False

        # Way point for units to move to
        self.waypoint = None

        # Predict enemy will be in the first possible position
        self.predicted_enemy_position_num = -1

        # Position to search for enemy untis
        self.num_enemy_positions = -1

        # Position the bot begins
        self.start_location = None

        # Easier way to access map information, must be loaded in after game loads
        self.map_height = None
        self.map_width = None
        #ZerglingBanelingRushAgent.mainAgent = self

    async def on_step(self, iteration, strategy_num=2):
        # self.log("Step: %s Overlord: %s" % (str(iteration), str(self.units(OVERLORD).amount)))
        # self.log("Step: " + str(iteration))

        # TEMP: Until strategy is given by Q table
        # strategy_num = (int)(iteration / 75) % 8

        # Build lings, queen, overlords, drones, and meleeattack1
        await self.basic_build(iteration)

        # Perform actions based on given strategy
        if strategy_num == -1:
            # self.mainAgent.log("No given strategy")
            pass
        else:
            await self.perform_strategy(iteration, strategy_num)

    async def basic_build(self, iteration):

        hatchery = self.mainAgent.units(HATCHERY).ready.first
        larvae = self.mainAgent.units(LARVA)

        if iteration == 0:
            await self.mainAgent.do(larvae.random.train(DRONE))
            self.drone_counter += 1
            print("Drone " + str(self.drone_counter))

        for idle_worker in self.mainAgent.workers.idle:
            mf = self.mainAgent.state.mineral_field.closest_to(idle_worker)
            await self.mainAgent.do(idle_worker.gather(mf))

        if self.game_time > 75 and self.mainAgent.workers.exists:
            for extractor in self.mainAgent.units(EXTRACTOR):
                if extractor.assigned_harvesters < extractor.ideal_harvesters and self.mainAgent.workers.exists:
                    await self.mainAgent.do(self.mainAgent.workers.random.gather(extractor))

        if self.overlord_counter == 0 and larvae.exists and self.mainAgent.can_afford(OVERLORD)\
                and not self.mainAgent.already_pending(OVERLORD):
            await self.mainAgent.do(larvae.random.train(OVERLORD))
            self.overlord_counter += 1
            print ("Overlord " + str(self.overlord_counter))

        if self.overlord_counter ==  1:
            if self.mainAgent.can_afford(DRONE) and larvae.exists and self.mainAgent.supply_left > 0:
                await self.mainAgent.do(larvae.random.train(DRONE))
                self.drone_counter += 1
                print("Drone " + str(self.drone_counter))
                print("Game Time: " + str(self.game_time))

        if self.game_time > 100:
            if self.overlord_counter <= 1 and larvae.exists and self.mainAgent.can_afford(OVERLORD):
                await self.mainAgent.do(larvae.random.train(OVERLORD))
                self.overlord_counter += 1
                print ("Overlord " + str(self.overlord_counter))
            elif self.game_time > 110 and self.overlord_counter == 2 and larvae.exists and self.mainAgent.can_afford(OVERLORD):
                await self.mainAgent.do(larvae.random.train(OVERLORD))
                self.overlord_counter += 1
                print ("Overlord " + str(self.overlord_counter))
            elif self.mainAgent.supply_left <= 2 and larvae.exists and self.mainAgent.can_afford(OVERLORD):
                await self.mainAgent.do(larvae.random.train(OVERLORD))
                self.overlord_counter += 1
                print("Overlord " + str(self.overlord_counter))
                print("Game Time: " + str(self.game_time))

        if self.game_time > 50 and not self.moved_worker_to_expand:
            pos = await self.mainAgent.get_next_expansion()
            err = await self.mainAgent.do(self.mainAgent.workers.closest_to(pos).move(pos))
            if not err:
                self.moved_worker_to_expand = True
                print("Worker moved to expansion point")
                print("Game Time: " + str(self.game_time))

        if self.game_time > 60 and self.moved_worker_to_expand and not self.hatchery_started and self.mainAgent.can_afford(HATCHERY):
            pos = await self.mainAgent.get_next_expansion()
            drone = self.mainAgent.workers.closest_to(pos)
            err = await self.mainAgent.build(HATCHERY, near=pos, max_distance=20, unit=drone)
            if not err:
                self.hatchery_started = True
                print("Hatchery Started")
                print("Game Time: " + str(self.game_time))

        if not self.extractor_started:
            if self.mainAgent.can_afford(EXTRACTOR) and self.mainAgent.workers.exists:
                drone = self.mainAgent.workers.random
                target = self.mainAgent.state.vespene_geyser.closest_to(drone.position)
                err = await self.mainAgent.do(drone.build(EXTRACTOR, target))
                if not err:
                    self.extractor_started = True
                    print("Extractor Started")
                    print("Game Time: " + str(self.game_time))

        elif not self.spawning_pool_started:
            if self.mainAgent.can_afford(SPAWNINGPOOL):
                for d in range(4, 15):
                    pos = hatchery.position.to2.towards(self.mainAgent.game_info.map_center, d)
                    if await self.mainAgent.can_place(SPAWNINGPOOL, pos):
                        drone = self.mainAgent.workers.closest_to(pos)
                        err = await self.mainAgent.do(drone.build(SPAWNINGPOOL, pos))
                        if not err:
                            self.spawning_pool_started = True
                            print("Spawning pool started")
                            break

        elif not self.queen_started and self.mainAgent.units(SPAWNINGPOOL).ready.exists:
            if self.mainAgent.can_afford(QUEEN):
                err = await self.mainAgent.do(hatchery.train(QUEEN))
                if not err:
                    self.queen_started = True
                    print("Queen Started")
                    print("Game Time: " + str(self.game_time))

        for queen in self.mainAgent.units(QUEEN).idle:
            abilities = await self.mainAgent.get_available_abilities(queen)
            if AbilityId.EFFECT_INJECTLARVA in abilities:
                err = await self.mainAgent.do(queen(EFFECT_INJECTLARVA, hatchery))
                if not err:
                    print("Larva Injected")
                    print("Game Time: " + str(self.game_time))

        if self.mainAgent.can_afford(RESEARCH_ZERGLINGMETABOLICBOOST) and not self.mboost_started:
            sp = self.mainAgent.units(SPAWNINGPOOL).ready
            if sp.exists and self.mainAgent.minerals >= 100:
                await self.mainAgent.do(sp.first(RESEARCH_ZERGLINGMETABOLICBOOST))
                self.mboost_started = True
                print("Researched Metabolic Boost")
                print("Game Time: " + str(self.game_time))

        if self.mainAgent.units(SPAWNINGPOOL).ready.exists:
            if larvae.exists and self.mainAgent.can_afford(ZERGLING) and self.mainAgent.supply_left >= 1:
                if self.queen_started:
                    await self.mainAgent.do(larvae.random.train(ZERGLING))
                    self.zergling_counter += 1

        # if self.zergling_counter >= 10:
        #     if not self.attacking:
        #         self.attacking = True
        #         self.countdown = self.game_time
        #
        #     for unit in self.units(ZERGLING) | self.units(BANELING):
        #         await self.do(unit.attack(target.to2.towards(self.game_info.map_center, self.attack_distance)))
        #
        #     #if self.baneling_counter != 0:
        #     #    for worker in self.workers:
        #     #        await self.do(worker.attack(target.to2.towards(self.game_info.map_center, 30)))

        # if self.attacking:
        #     self.attack_distance = 80 - (self.game_time - self.countdown)

        if not self.baneling_nest_started:
            if self.mainAgent.can_afford(BANELINGNEST) and self.mainAgent.units(SPAWNINGPOOL).ready.exists:
                for d in range(4, 15):
                    pos = hatchery.position.to2.towards(self.mainAgent.game_info.map_center, d)
                    if await self.mainAgent.can_place(BANELINGNEST, pos):
                        drone = self.mainAgent.workers.closest_to(pos)
                        err = await self.mainAgent.do(drone.build(BANELINGNEST, pos))
                        if not err:
                            self.baneling_nest_started = True
                            print("Baneling nest started")
                            break

        if self.mainAgent.units(BANELINGNEST).ready.exists:

            if self.mainAgent.can_afford(RESEARCH_CENTRIFUGALHOOKS) and not self.chooks_started:
                bn = self.mainAgent.units(BANELINGNEST).ready
                if bn.exists and self.mainAgent.minerals >= 100:
                    await self.mainAgent.do(bn.first(RESEARCH_CENTRIFUGALHOOKS))
                    self.chooks_started = True
                    print("Researched Centrifugal Hooks")
                    print("Game Time: " + str(self.game_time))

            for zergling in self.mainAgent.units(ZERGLING).ready:
                if self.mainAgent.can_afford(MORPHZERGLINGTOBANELING_BANELING) and larvae.exists and self.baneling_counter < self.zergling_counter / 2:
                    err = await self.mainAgent.do(zergling(MORPHZERGLINGTOBANELING_BANELING))
                    if not err:
                        self.baneling_counter += 1
                        print("Morphed baneling")
                else:
                    break


def main():
    # Start game with LoserAgent as the Bot, and begin logging
    sc2.run_game(sc2.maps.get("Abyssal Reef LE"), [
        Bot(Race.Zerg, ZerglingBanelingRushAgent(True)),
        Computer(Race.Protoss, Difficulty.Medium)
    ], realtime=False)

if __name__ == '__main__':
    main()
