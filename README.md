# Starcraft2AI
A Starcraft 2 AI

## Setup
### Install pysc2
Install pysc2 from: 

### Install python-sc2 with Starcraft 2 Viewer
Install python-sc2 with starcraft viewer (We found that this works the best when you clone the repo to the following path: `~/StarCraftII/`: 

```
git clone https://github.com/dbelliss/python-sc2
cd python-sc2
sudo  python3.6 setup.py install
```
##### IMPORTANT SIDE NOTE
If you have already installed the Dentosal python-sc2 repository, go into the installed location and do the following before the above:

`sudo rm -rf sc2/`

### Testing
`python3.6 examples/cannon_rush.py`

### Current issues:
* After a game ends, the pygame window does not close. You can close it by hitting `ctl+c` in the terminal window that the game was started in (Note: Do not press more than once)
* Agents do not seem to be able to access properties like mineral_content

## Notes
* All agents derive from the base LoserAgent class
* The agent the swaps between other agents is AgentSelector

