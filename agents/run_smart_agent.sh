#!/usr/bin/env bash
## Run on map Simple64 using SmartAgent (with Q table) as Terran. Do not render graphics, and end the program after 5000 steps
#python -m pysc2.bin.agent --map Simple64 --agent smart_agent.SmartAgent --agent_race T --norender --max_agent_steps 5000
# Run on map Simple64 using SmartAgent (with Q table) as Terran, and end the program after 10000 steps
python -m pysc2.bin.agent --map Simple64 --agent smart_agent.SmartAgent --agent_race Z --max_agent_steps 0
$SHELL