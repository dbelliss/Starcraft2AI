from loser_agent import *

class SpawnPoolRavagerAgent(LoserAgent):
    def __init__(self, is_logging = False):
        super().__init__()

        # For debugging
        self.is_logging = is_logging
        if self.is_logging:

            # Make logs directory if it doesn't exist
            if not os.path.exists("./logs"):
                os.mkdir("./logs")
            self.log_file_name = "./logs/" + strftime("%Y-%m-%d %H:%M:%S", localtime()) + ".log"
            self.log_file = open(self.log_file_name, "w+")  # Create log file based on the time

    async def on_step(self, iteration):
        self.log("Step: %s Idle Workers: %s Overlord: %s" % (str(iteration), str(self.get_idle_workers), str(self.units(OVERLORD).amount)))
        #self.log(str(self.researched))
        self.log(str(self.get_minerals)) # no attribute "mineral_content" but "get_minerals()" is recognized
def main():
    # Start game with LoserAgent as the Bot, and begin logging
    sc2.run_game(sc2.maps.get("Abyssal Reef LE"), [
        Bot(Race.Zerg, SpawnPoolRavagerAgent(True)),
        Computer(Race.Protoss, Difficulty.Medium)
    ], realtime=False)

if __name__ == '__main__':
    main()
