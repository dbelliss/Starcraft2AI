from loser_agent import *

class MutaliskAgent(LoserAgent):
    def __init__(self, is_logging = False, is_printing_to_console = False, isMainAgent = False, fileName = ""):
        super().__init__()

        self.drone_counter = 0
        self.overlord_counter = 0
        self.zergling_counter = 0
        self.num_lairs_built = 0
        self.num_hives_built = 0
        self.num_queens = 0
        self.flying_attack_level = 0
        self.hatchery_started = False
        self.lair_started = False
        self.hive_started = False
        self.extractor_started = False
        self.spawning_pool_started = False
        self.infestation_pit_started = False
        self.moved_workers_to_gas = False
        self.moved_workers_from_gas = False
        self.moved_worker_to_expand = False
        self.queen_started = False
        self.mboost_started = False

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

        firstbase = self.mainAgent.bases.ready.first
        larvae = self.mainAgent.units(LARVA)

        if iteration == 0:
            await self.mainAgent.do(larvae.random.train(DRONE))
            self.drone_counter += 1
            print("Drone " + str(self.drone_counter))

        for idle_worker in self.mainAgent.workers.idle:
            mf = self.mainAgent.state.mineral_field.closest_to(idle_worker)
            await self.mainAgent.do(idle_worker.gather(mf))

        if self.game_time > 75 and self.mainAgent.workers.exists and \
                self.mainAgent.units(EXTRACTOR).amount < 2 * self.mainAgent.bases.amount:
            for extractor in self.mainAgent.units(EXTRACTOR):
                if extractor.assigned_harvesters < extractor.ideal_harvesters and self.mainAgent.workers.exists:
                    await self.mainAgent.do(self.mainAgent.workers.random.gather(extractor))

        if self.mainAgent.supply_left <= 2 and larvae.exists and self.mainAgent.can_afford(OVERLORD) \
                and not self.mainAgent.already_pending(OVERLORD):
            err = await self.mainAgent.do(larvae.random.train(OVERLORD))
            if not err:
                self.overlord_counter += 1
                print ("Overlord " + str(self.overlord_counter))

        if self.mainAgent.workers.amount + self.mainAgent.already_pending(DRONE) < 24 * self.mainAgent.bases.amount:
            if larvae.exists and self.mainAgent.can_afford(DRONE) and self.mainAgent.supply_left >= 1:
                await self.mainAgent.do(larvae.random.train(DRONE))

        if self.mainAgent.units(EXTRACTOR).ready.amount < (self.mainAgent.bases.ready.amount) * 2:
            if self.mainAgent.can_afford(EXTRACTOR) and self.mainAgent.workers.exists:
                drone = self.mainAgent.workers.random
                target = self.mainAgent.state.vespene_geyser.closest_to(drone.position)
                err = await self.mainAgent.do(drone.build(EXTRACTOR, target))
                if not err:
                    self.extractor_started = True
                    print("Extractor Started")
                    print("Game Time: " + str(self.game_time))

        if not self.mainAgent.units(SPAWNINGPOOL).ready.exists and not self.mainAgent.already_pending(SPAWNINGPOOL):
            if self.mainAgent.can_afford(SPAWNINGPOOL):
                for d in range(4, 15):
                    pos = firstbase.position.to2.towards(self.mainAgent.game_info.map_center, d)
                    if await self.mainAgent.can_place(SPAWNINGPOOL, pos):
                        drone = self.mainAgent.workers.closest_to(pos)
                        err = await self.mainAgent.do(drone.build(SPAWNINGPOOL, pos))
                        if not err:
                            self.spawning_pool_started = True
                            print("Spawning pool started")
                            break

        if self.mainAgent.units(SPAWNINGPOOL).ready.exists and self.mainAgent.minerals > 300:
            if larvae.exists and self.mainAgent.can_afford(ZERGLING) and self.mainAgent.supply_left >= 2:
                if not self.mainAgent.units(MUTALISK).ready.exists or self.mainAgent.minerals > 500:
                    await self.mainAgent.do(larvae.random.train(ZERGLING))
                    self.zergling_counter += 1

        if self.num_lairs_built < 1 and not self.mainAgent.already_pending(LAIR) \
                and not self.lair_started and self.mainAgent.units(HATCHERY).amount > 0 and self.mainAgent.can_afford(UPGRADETOLAIR_LAIR) \
                and self.mainAgent.can_afford(LAIR) and self.mainAgent.units(SPAWNINGPOOL).ready.exists:
            hatchery = self.mainAgent.units(HATCHERY).first
            err = await self.mainAgent.do(hatchery(UPGRADETOLAIR_LAIR))
            if not err:
                self.mainAgent.num_lairs_built += 1
                self.lair_started = True
                print("Upgraded to lair " + str(self.mainAgent.num_lairs_built))
                print("Game Time: " + str(self.game_time))

        if self.num_hives_built < 1 and not self.mainAgent.already_pending(HIVE) \
                and not self.hive_started and self.mainAgent.units(LAIR).amount > 0 and self.mainAgent.can_afford(UPGRADETOHIVE_HIVE) \
                and self.mainAgent.can_afford(HIVE) and self.mainAgent.units(INFESTATIONPIT).ready.exists:
            lair = self.mainAgent.units(LAIR).first
            err = await self.mainAgent.do(lair(UPGRADETOHIVE_HIVE))
            if not err:
                self.mainAgent.num_hives_built += 1
                self.hive_started = True
                print("Upgraded to hive " + str(self.mainAgent.num_hives_built))
                print("Game Time: " + str(self.game_time))

        if self.game_time > 60 and not self.hatchery_started and self.mainAgent.can_afford(HATCHERY):
            pos = await self.mainAgent.get_next_expansion()
            drone = self.mainAgent.workers.closest_to(pos)
            err = await self.mainAgent.build(HATCHERY, near=pos, max_distance=20, unit=drone)
            if not err:
                self.hatchery_started = True
                print("Hatchery Started")
                print("Game Time: " + str(self.game_time))

        if self.hatchery_started and not self.mainAgent.units(SPIRE).ready.exists and not self.mainAgent.already_pending(SPIRE):
            if self.mainAgent.can_afford(SPIRE):
                pos = await self.mainAgent.get_next_expansion()
                drone = self.mainAgent.workers.closest_to(pos)
                err = await self.mainAgent.build(SPIRE, near=pos, max_distance=20, unit=drone)
                if not err:
                    self.spire_started = True
                    print("Spire started")
                    print("Game Time: " + str(self.game_time))

        if self.mainAgent.can_afford(AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL1) and self.flying_attack_level == 0:
            sp = self.mainAgent.units(SPIRE).ready
            if sp.exists:
                err = await self.mainAgent.do(sp.first(RESEARCH_ZERGFLYERATTACKLEVEL1))
                if not err:
                    self.flying_attack_level += 1
                    print("Researched Flying Attack Level 1")
                    print("Game Time: " + str(self.game_time))

        if self.mainAgent.can_afford(AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL2) and self.flying_attack_level == 1:
            sp = self.mainAgent.units(SPIRE).ready
            if sp.exists:
                err = await self.mainAgent.do(sp.first(RESEARCH_ZERGFLYERATTACKLEVEL2))
                if not err:
                    self.flying_attack_level += 1
                    print("Researched Flying Attack Level 2")
                    print("Game Time: " + str(self.game_time))

        if self.mainAgent.can_afford(AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL3) and self.flying_attack_level == 2:
            if self.mainAgent.units(HIVE).ready.exists:
                sp = self.mainAgent.units(SPIRE).ready
                if sp.exists:
                    err = await self.mainAgent.do(sp.first(RESEARCH_ZERGFLYERATTACKLEVEL3))
                    if not err:
                        self.flying_attack_level += 1
                        print("Researched Flying Attack Level 3")
                        print("Game Time: " + str(self.game_time))

        if self.mainAgent.units(LAIR).exists and self.flying_attack_level == 2 and not self.infestation_pit_started:
            if self.mainAgent.can_afford(INFESTATIONPIT):
                pos = await self.mainAgent.get_next_expansion()
                drone = self.mainAgent.workers.closest_to(pos)
                err = await self.mainAgent.build(INFESTATIONPIT, near=pos, max_distance=20, unit=drone)
                if not err:
                    self.infestation_pit_started = True
                    print("Infestation Pit started")
                    print("Game Time: " + str(self.game_time))

        if self.num_queens < 2 and \
                (self.mainAgent.units(SPIRE).ready.exists or self.mainAgent.units(GREATERSPIRE).ready.exists):
            if self.mainAgent.can_afford(QUEEN):
                err = await self.mainAgent.do(firstbase.train(QUEEN))
                if not err:
                    self.num_queens += 1
                    self.queen_started = True
                    print("Queen Started")
                    print("Game Time: " + str(self.game_time))

        if self.mainAgent.units(QUEEN).amount + self.mainAgent.already_pending(QUEEN) >= 2 and self.mainAgent.supply_left > 2 and \
            self.mainAgent.units(SPIRE).ready.exists and self.mainAgent.can_afford(MUTALISK) and larvae.exists:
            err = await self.mainAgent.do(larvae.random.train(MUTALISK))
            if not err:
                print("Training Mutalisk")
                print("Game Time: " + str(self.game_time))

        for queen in self.mainAgent.units(QUEEN).idle:
            abilities = await self.mainAgent.get_available_abilities(queen)
            if AbilityId.EFFECT_INJECTLARVA in abilities:
                err = await self.mainAgent.do(queen(EFFECT_INJECTLARVA, firstbase))
                if not err:
                    print("Larva Injected")
                    print("Game Time: " + str(self.game_time))

def main():
    # Start game with LoserAgent as the Bot, and begin logging
    sc2.run_game(sc2.maps.get("Abyssal Reef LE"), [
        Bot(Race.Zerg, MutaliskAgent(True)),
        Computer(Race.Protoss, Difficulty.Medium)
    ], realtime=False)

if __name__ == '__main__':
    main()
