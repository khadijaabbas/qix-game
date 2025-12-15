# qix-game

This is a simplified version of the classic Qix game built with Python and Pygame.
The player moves along the edges of a square field and pushes into the interior to claim area.
The goal is to capture a target percentage of the field while avoiding enemies such as the Qix and Sparx, which reduce the player’s life if they make contact during a push.

##setup instructions
1. install dependencies
  python3 -m pip install pygame
2. run the game
   python3 main.py
3. run in test mode (no graphics)
   python3 main.py --test
