# Google Dinosaur Web Game

Create a Google Chrome dinosaur runner web game.

## Requirements

- A browser-based endless runner game inspired by the Chrome offline dinosaur game
- The player controls a dinosaur that runs automatically and must jump over obstacles (cacti, birds)
- The game should include:
  - A running dinosaur character with jump and duck animations
  - Randomly generated obstacles (cacti of different sizes, flying pterodactyls)
  - Score counter that increases over time
  - Game speed that gradually increases as the score goes up
  - Day/night cycle visual effect
  - High score tracking (stored in localStorage)
  - Game over screen with restart option
- Built with vanilla HTML, CSS, and JavaScript (no frameworks)
- Responsive design that works on both desktop and mobile
- Keyboard controls: Space/Up Arrow to jump, Down Arrow to duck
- Touch controls for mobile: tap to jump, swipe down to duck
- Sound effects for game events:
  - Jump sound when the dinosaur jumps
  - Point/milestone sound when reaching score milestones (e.g. every 100 points)
  - Collision/game over sound when hitting an obstacle
  - Sounds should be generated programmatically using the Web Audio API (no external audio files needed)
  - Include a mute/unmute toggle so players can disable sounds
