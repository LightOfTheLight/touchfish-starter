# Project Requirements

## 1. Overview

**Project Name:** Google Dinosaur Web Game
**Project Type:** Browser-based Web Game
**Target Users:** General web users on desktop and mobile browsers

### 1.1 Vision

A faithful recreation of the Google Chrome offline dinosaur runner game, playable in any modern browser. The game provides an engaging endless runner experience with increasing difficulty, visual variety through a day/night cycle, and persistent high score tracking.

### 1.2 Core Principles

- **Simplicity:** Vanilla HTML/CSS/JS only — no external frameworks or libraries
- **Accessibility:** Works on both desktop (keyboard) and mobile (touch) devices
- **Fidelity:** Core gameplay mechanics mirror the Chrome dinosaur game experience

---

## 2. Functional Requirements

### 2.1 Dinosaur Character

**Description:** The player controls a dinosaur that runs automatically from left to right. The player can make it jump or duck to avoid obstacles.

**Acceptance Criteria:**
- [ ] Dinosaur runs continuously with a running animation (alternating legs)
- [ ] Pressing Space or Up Arrow causes the dinosaur to jump
- [ ] Pressing Down Arrow causes the dinosaur to duck (crouch lower)
- [ ] Tapping the screen causes the dinosaur to jump (mobile)
- [ ] Swiping down on the screen causes the dinosaur to duck (mobile)
- [ ] Jump and duck animations are visually distinct from the running animation
- [ ] Dinosaur cannot jump again while already in the air

### 2.2 Obstacles

**Description:** Randomly generated obstacles appear from the right side of the screen and move left. The player must avoid them.

**Acceptance Criteria:**
- [ ] Cacti obstacles appear in at least 2 different sizes/variants
- [ ] Cacti can appear in groups (e.g., 1–3 cacti side by side)
- [ ] Flying pterodactyl (bird) obstacles appear at varying heights
- [ ] Obstacle spawn timing is randomized within a defined interval range
- [ ] Obstacles move from right to left at the current game speed
- [ ] Collision with any obstacle triggers game over

### 2.3 Scoring

**Description:** The player's score increases as they survive longer. The score and high score are displayed on screen.

**Acceptance Criteria:**
- [ ] Score increments continuously while the game is running
- [ ] Current score is displayed prominently on screen
- [ ] High score is displayed alongside the current score
- [ ] High score persists across browser sessions via localStorage
- [ ] High score is updated immediately when the current score exceeds it

### 2.4 Difficulty Progression

**Description:** The game becomes harder over time by increasing the speed of the dinosaur and obstacles.

**Acceptance Criteria:**
- [ ] Game speed starts at a defined initial value
- [ ] Game speed gradually increases as the score increases
- [ ] Speed increase is capped at a maximum value to keep the game playable
- [ ] Obstacle spawn frequency may also increase with speed

### 2.5 Day/Night Cycle

**Description:** The game's visual theme alternates between a light (day) mode and a dark (night) mode at regular intervals.

**Acceptance Criteria:**
- [ ] Game starts in day mode (light background)
- [ ] Game transitions to night mode (dark background) after a defined score threshold
- [ ] Transitions alternate between day and night periodically
- [ ] All game elements (dinosaur, obstacles, ground) remain visible in both modes

### 2.6 Game Over & Restart

**Description:** When the dinosaur collides with an obstacle, the game ends and the player is offered the option to restart.

**Acceptance Criteria:**
- [ ] Game pauses immediately upon collision
- [ ] A "Game Over" message is displayed
- [ ] A restart prompt (e.g., press Space or tap screen) is shown
- [ ] Pressing Space, Up Arrow, or tapping the screen restarts the game
- [ ] Score resets to 0 on restart; high score is preserved

### 2.7 Start Screen

**Description:** Before the first game begins, the game is in a waiting state until the player initiates it.

**Acceptance Criteria:**
- [ ] Game does not start automatically on page load
- [ ] A prompt instructs the player how to start (e.g., "Press Space to Start")
- [ ] Game begins on the first valid input (Space, Up Arrow, or tap)

---

## 3. Technical Requirements

### 3.1 Technology Stack

| Component | Technology |
|-----------|------------|
| Markup | HTML5 |
| Styling | CSS3 |
| Logic | Vanilla JavaScript (ES6+) |
| Storage | Browser localStorage |
| Rendering | Canvas API or DOM elements |

### 3.2 Constraints

- No external JavaScript frameworks (e.g., no React, Vue, jQuery)
- No external CSS frameworks (e.g., no Bootstrap, Tailwind)
- Must run entirely in the browser with no server-side component
- Single-file or minimal file structure preferred for simplicity

### 3.3 Browser Compatibility

- Must support modern browsers: Chrome, Firefox, Safari, Edge (latest versions)
- Mobile browsers: iOS Safari, Android Chrome

---

## 4. Non-Functional Requirements

### 4.1 Performance
- Game loop must run at a stable 60 FPS on modern hardware
- No significant frame drops during normal gameplay

### 4.2 Responsiveness
- Game canvas/viewport scales appropriately for common screen sizes
- Playable on screens as small as 320px width

### 4.3 Usability
- Controls must be intuitive with no learning curve for anyone familiar with the Chrome dino game
- Touch targets must be large enough for mobile use

---

## 5. Acceptance Criteria

### 5.1 MVP
- [ ] Dinosaur character visible and animating on screen
- [ ] Player can jump over obstacles using keyboard
- [ ] Cactus obstacles spawn and move across the screen
- [ ] Collision detection works correctly
- [ ] Score increments during gameplay
- [ ] Game over screen appears on collision
- [ ] Player can restart the game
- [ ] High score saved to localStorage

### 5.2 Full Feature Set
- [ ] All MVP criteria met
- [ ] Duck mechanic implemented
- [ ] Pterodactyl (bird) obstacles implemented
- [ ] Day/night cycle implemented
- [ ] Touch controls for mobile implemented
- [ ] Responsive layout for mobile screens

### 5.3 Future Enhancements
- Sound effects (jump, collision, milestone score)
- Achievement system
- Multiple difficulty settings
- Leaderboard (requires backend)

---

## 6. Implementation Guide

### 6.1 Game Configuration Constants

These values serve as recommended starting points. DEV may adjust based on playtesting, but must not deviate substantially without documenting the rationale.

| Constant | Recommended Value | Notes |
|----------|------------------|-------|
| Canvas width | 800px | Scales on smaller screens |
| Canvas height | 300px | Fixed height |
| Initial game speed | 5 px/frame | Pixels moved per frame at 60 FPS |
| Max game speed | 15 px/frame | Speed cap to keep game playable |
| Speed increment | +0.001 per frame | Gradual increase |
| Gravity | 0.6 px/frame² | Applied to dinosaur vertical velocity |
| Jump velocity | -12 px/frame | Upward impulse on jump |
| Ground level | 220px (from top) | Y coordinate of ground surface |
| Obstacle spawn interval (min) | 60 frames | ~1 second at 60 FPS |
| Obstacle spawn interval (max) | 150 frames | ~2.5 seconds at 60 FPS |
| Day/night toggle score | Every 500 points | Cycle threshold |
| Score increment rate | +1 per 6 frames | Score ticks at ~10 per second |

### 6.2 Suggested File Structure

```
/
├── index.html          # Single entry point (HTML + embedded CSS + JS preferred)
├── README.md           # User requirements (do not modify)
└── REQUIREMENT.md      # This file (PO-owned)
```

Alternatively, if DEV chooses a multi-file structure:

```
/
├── index.html
├── style.css
├── game.js
├── README.md
└── REQUIREMENT.md
```

### 6.3 Implementation Phases

The DEV agent should implement in the following order to deliver working increments:

**Phase 1 — MVP Core (matches 5.1)**
1. Set up canvas and game loop (requestAnimationFrame at 60 FPS)
2. Draw and animate the dinosaur (running animation, ground placement)
3. Implement jump mechanic with gravity (Space/Up Arrow)
4. Spawn and animate cactus obstacles (at least 2 variants)
5. Collision detection (dinosaur vs obstacle bounding box)
6. Score counter (incrementing display)
7. Game Over state (pause, display message, restart prompt)
8. Restart mechanic (reset state, reset score)
9. localStorage high score persistence

**Phase 2 — Full Feature Set (matches 5.2)**
1. Duck mechanic (Down Arrow, reduced hitbox)
2. Pterodactyl obstacle (3 height variants: low, mid, high)
3. Day/night cycle (background color transition at score threshold)
4. Touch controls (tap to jump, swipe-down to duck)
5. Responsive scaling (canvas fits viewport down to 320px width)

**Phase 3 — Polish (optional, pre-full-feature)**
1. Start screen idle state (no auto-start)
2. Score milestone visual flash (every 100 points)
3. Smooth day/night transition (fade vs hard switch)

### 6.4 Collision Detection Guidance

Use axis-aligned bounding box (AABB) collision. Apply a small inset (~5px) on all sides of each entity's hitbox to avoid pixel-perfect frustration:

```
entity hitbox = { x + 5, y + 5, width - 10, height - 10 }
```

Collision occurs when hitboxes overlap on both X and Y axes.

### 6.5 Rendering Approach Decision

Canvas API is recommended over DOM for this game due to:
- Better performance for per-frame redraws
- Simpler coordinate system for physics
- Easier pixel-level control

DEV may use CSS pixel art sprites or drawn shapes (no external image assets required for a functional implementation).

---

*Document maintained by: PO Agent*
*Last updated: 2026-03-01*
