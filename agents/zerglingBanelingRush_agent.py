from loser_agent import *

class ZerglingBanelingRushAgent(LoserAgent):
    def __init__(self, is_logging = False, is_printing_to_console = False, isMainAgent = False, fileName = ""):
        super().__init__()

        self.num_drones_built = 0
        self.num_overlords_built = 0
        self.num_zerglings_built = 0
        self.num_banelings_built = 0
        self.num_queens = 0
        self.zergling_speed = 0
        self.baneling_speed = 0
        self.extractor_started = False
        self.hatchery_started = False
        self.spawning_pool_started = False
        self.moved_workers_to_gas = False
        self.moved_workers_from_gas = False
        self.moved_worker_to_expand = False
        self.queen_started = False
        self.baneling_nest_started = False

        # For debugging
        self.is_logging = is_logging  # Setting this to true to write information to log files in the agents/logs directory
        self.is_printing_to_console = is_printing_to_console  # Setting this to true causes all logs to be printed to the console

        #ZerglingBanelingRushAgent.mainAgent = self

    async def on_step(self, iteration, strategy_num):
        # self.log("Step: %s Overlord: %s" % (str(iteration), str(self.units(OVERLORD).amount)))
        # self.log("Step: " + str(iteration))

        # TEMP: Until strategy is given by Q table
        #strategy_num = (int)(iteration / 75) % 8

        # Build lings, queen, overlords, drones, and meleeattack1
        await self.basic_build(iteration)

        # Perform actions based on given strategy
        if strategy_num == -1:
            # self.mainAgent.log("No given strategy")
            pass
        else:
            await self.perform_strategy(iteration, strategy_num)

    async def basic_build(self, iteration):

        firstbase = self.mainAgent.bases.ready.first
        larvae = self.mainAgent.units(LARVA)

        if iteration == 0:
            await self.mainAgent.do(larvae.random.train(DRONE))
            self.num_drones_built += 1
            # print("Drone " + str(self.drone_counter))

        for idle_worker in self.mainAgent.workers.idle:
            mf = self.mainAgent.state.mineral_field.closest_to(idle_worker)
            await self.mainAgent.do(idle_worker.gather(mf))

        if self.game_time > 75 and self.mainAgent.workers.exists:
            for extractor in self.mainAgent.units(EXTRACTOR):
                if extractor.assigned_harvesters < extractor.ideal_harvesters and self.mainAgent.workers.exists:
                    await self.mainAgent.do(self.mainAgent.workers.random.gather(extractor))

        if self.num_overlords_built == 0 and larvae.exists and self.mainAgent.can_afford(OVERLORD)\
                and not self.mainAgent.already_pending(OVERLORD):
            await self.mainAgent.do(larvae.random.train(OVERLORD))
            self.num_overlords_built += 1
            # print ("Overlord " + str(self.num_overlords_built))

        if self.num_overlords_built ==  1:
            if self.mainAgent.can_afford(DRONE) and larvae.exists and self.mainAgent.supply_left > 0:
                await self.mainAgent.do(larvae.random.train(DRONE))
                self.num_drones_built += 1
                # print("Drone " + str(self.drone_counter))
                # print("Game Time: " + str(self.game_time))

        if self.game_time > 100:
            if self.num_overlords_built <= 1 and larvae.exists and self.mainAgent.can_afford(OVERLORD):
                await self.mainAgent.do(larvae.random.train(OVERLORD))
                self.num_overlords_built += 1
                # print ("Overlord " + str(self.num_overlords_built))
            elif self.game_time > 110 and self.num_overlords_built == 2 and larvae.exists and self.mainAgent.can_afford(OVERLORD):
                await self.mainAgent.do(larvae.random.train(OVERLORD))
                self.num_overlords_built += 1
                # print ("Overlord " + str(self.num_overlords_built))
            elif self.mainAgent.supply_left <= 2 and larvae.exists and self.mainAgent.can_afford(OVERLORD):
                await self.mainAgent.do(larvae.random.train(OVERLORD))
                self.num_overlords_built += 1
                # print("Overlord " + str(self.num_overlords_built))
                # print("Game Time: " + str(self.game_time))

        if self.game_time > 50 and not self.moved_worker_to_expand:
            pos = await self.mainAgent.get_next_expansion()
            err = await self.mainAgent.do(self.mainAgent.workers.closest_to(pos).move(pos))
            if not err:
                self.moved_worker_to_expand = True
                # print("Worker moved to expansion point")
                # print("Game Time: " + str(self.game_time))

        if self.game_time > 60 and self.moved_worker_to_expand and not self.hatchery_started and self.mainAgent.can_afford(HATCHERY):
            pos = await self.mainAgent.get_next_expansion()
            drone = self.mainAgent.workers.closest_to(pos)
            err = await self.mainAgent.build(HATCHERY, near=pos, max_distance=20, unit=drone)
            if not err:
                self.hatchery_started = True
                # print("Hatchery Started")
                # print("Game Time: " + str(self.game_time))

        if not self.extractor_started:
            if self.mainAgent.can_afford(EXTRACTOR) and self.mainAgent.workers.exists:
                drone = self.mainAgent.workers.random
                target = self.mainAgent.state.vespene_geyser.closest_to(drone.position)
                err = await self.mainAgent.do(drone.build(EXTRACTOR, target))
                if not err:
                    self.extractor_started = True
                    # print("Extractor Started")
                    # print("Game Time: " + str(self.game_time))

        elif not self.spawning_pool_started:
            if self.mainAgent.can_afford(SPAWNINGPOOL):
                for d in range(4, 15):
                    pos = firstbase.position.to2.towards(self.mainAgent.game_info.map_center, d)
                    if await self.mainAgent.can_place(SPAWNINGPOOL, pos):
                        drone = self.mainAgent.workers.closest_to(pos)
                        err = await self.mainAgent.do(drone.build(SPAWNINGPOOL, pos))
                        if not err:
                            self.spawning_pool_started = True
                            # print("Spawning pool started")
                            break

        elif not self.queen_started and self.mainAgent.units(SPAWNINGPOOL).ready.exists:
            if self.mainAgent.can_afford(QUEEN):
                err = await self.mainAgent.do(firstbase.train(QUEEN))
                if not err:
                    self.queen_started = True
                    # print("Queen Started")
                    # print("Game Time: " + str(self.game_time))

        for queen in self.mainAgent.units(QUEEN).idle:
            abilities = await self.mainAgent.get_available_abilities(queen)
            if AbilityId.EFFECT_INJECTLARVA in abilities:
                await self.mainAgent.do(queen(EFFECT_INJECTLARVA, firstbase))
                # if not err:
                    # print("Larva Injected")
                    # print("Game Time: " + str(self.game_time))

        if self.mainAgent.can_afford(RESEARCH_ZERGLINGMETABOLICBOOST) and self.zergling_speed == 0:
            sp = self.mainAgent.units(SPAWNINGPOOL).ready
            if sp.exists and self.mainAgent.minerals >= 100:
                await self.mainAgent.do(sp.first(RESEARCH_ZERGLINGMETABOLICBOOST))
                self.zergling_speed = 1
                # print("Researched Metabolic Boost")
                # print("Game Time: " + str(self.game_time))

        if self.mainAgent.units(SPAWNINGPOOL).ready.exists:
            if larvae.exists and self.mainAgent.can_afford(ZERGLING) and self.mainAgent.supply_left >= 1:
                if self.queen_started:
                    await self.mainAgent.do(larvae.random.train(ZERGLING))
                    self.num_zerglings_built += 1

        if not self.baneling_nest_started:
            if self.mainAgent.can_afford(BANELINGNEST) and self.mainAgent.units(SPAWNINGPOOL).ready.exists:
                for d in range(4, 15):
                    pos = firstbase.position.to2.towards(self.mainAgent.game_info.map_center, d)
                    if await self.mainAgent.can_place(BANELINGNEST, pos):
                        drone = self.mainAgent.workers.closest_to(pos)
                        err = await self.mainAgent.do(drone.build(BANELINGNEST, pos))
                        if not err:
                            self.baneling_nest_started = True
                            # print("Baneling nest started")
                            break

        if self.mainAgent.units(BANELINGNEST).ready.exists:

            if self.mainAgent.can_afford(RESEARCH_CENTRIFUGALHOOKS) and self.baneling_speed == 0:
                bn = self.mainAgent.units(BANELINGNEST).ready
                if bn.exists and self.mainAgent.minerals >= 100:
                    await self.mainAgent.do(bn.first(RESEARCH_CENTRIFUGALHOOKS))
                    self.baneling_speed = 1
                    # print("Researched Centrifugal Hooks")
                    # print("Game Time: " + str(self.game_time))

            for zergling in self.mainAgent.units(ZERGLING).ready:
                if self.mainAgent.can_afford(MORPHZERGLINGTOBANELING_BANELING) and larvae.exists and self.num_banelings_built < self.num_zerglings_built / 2:
                    err = await self.mainAgent.do(zergling(MORPHZERGLINGTOBANELING_BANELING))
                    if not err:
                        self.num_banelings_built += 1
                        # print("Morphed baneling")
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
