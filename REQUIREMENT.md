# Project Requirements

## 1. Overview

**Project Name:** Google Dinosaur Web Game
**Project Type:** Browser-based endless runner game
**Target Users:** General web users; casual gamers on desktop and mobile

### 1.1 Vision

A faithful recreation of the Google Chrome offline dinosaur runner game, playable entirely in the browser. The game gives users an entertaining experience that works without any external dependencies, frameworks, or internet connection.

### 1.2 Core Principles

- **Simplicity:** Pure vanilla HTML, CSS, and JavaScript — no build tools or frameworks
- **Accessibility:** Fully playable on both desktop (keyboard) and mobile (touch)
- **Progressiveness:** Difficulty scales naturally so players are always challenged

---

## 2. Functional Requirements

### 2.1 Dinosaur Character

**Description:** The player controls a dinosaur that runs automatically from left to right. The dinosaur can jump to avoid ground obstacles and duck to avoid aerial obstacles.

**Acceptance Criteria:**
- [ ] Dinosaur is rendered on a ground baseline and runs with an animated loop (alternating legs)
- [ ] Pressing Space or Up Arrow causes the dinosaur to jump (single jump only — no double jump)
- [ ] Pressing Down Arrow causes the dinosaur to duck (reduced hitbox height)
- [ ] Jump and duck animations are visually distinct from the running animation
- [ ] Jumping while ducking is not possible; input is ignored or resolved gracefully

### 2.2 Obstacle Generation

**Description:** Obstacles are procedurally generated and scroll from right to left. There are two categories: ground obstacles (cacti) and aerial obstacles (pterodactyls).

**Acceptance Criteria:**
- [ ] At least 3 visually distinct cactus variants (small, medium, large / clustered)
- [ ] Pterodactyl (flying bird) obstacle that appears at varied heights (low, mid, high)
- [ ] Obstacles are randomly selected and spaced with a minimum safe gap between them
- [ ] Obstacle spawn rate increases as the score rises
- [ ] No obstacle placement causes an impossible (unwinnable) situation

### 2.3 Score System

**Description:** The game tracks a continuously increasing score based on distance/time survived.

**Acceptance Criteria:**
- [ ] Score counter is visible on screen during gameplay (top-right area)
- [ ] Score increments automatically over time while the game is running
- [ ] High score is displayed alongside the current score
- [ ] High score is persisted in `localStorage` and survives page refresh
- [ ] A visual or audio milestone is triggered every 100 points (e.g., flash/blink effect)

### 2.4 Game Speed Progression

**Description:** Game difficulty increases over time by speeding up the scroll rate.

**Acceptance Criteria:**
- [ ] Game starts at a fixed initial speed
- [ ] Speed increases gradually as the score increases (not in sudden jumps)
- [ ] Speed is capped at a maximum value to keep the game playable
- [ ] Obstacle gap minimum adjusts proportionally to speed to maintain fairness

### 2.5 Day/Night Cycle

**Description:** The background alternates between a day-time and night-time visual theme to add variety.

**Acceptance Criteria:**
- [ ] Visual transition occurs at defined score intervals (e.g., every 200 points)
- [ ] Night mode inverts or darkens the colour palette (dark background, light ground/sprites)
- [ ] Transition is smooth (short fade or immediate toggle — either is acceptable)
- [ ] Stars or moon can appear during night mode (optional enhancement)

### 2.6 Game Over and Restart

**Description:** A collision with any obstacle ends the game and presents a restart option.

**Acceptance Criteria:**
- [ ] Collision detection is pixel-accurate enough that fair hits feel fair (allow minor tolerance)
- [ ] Game over screen is displayed immediately on collision showing "GAME OVER" text
- [ ] Current score and high score are shown on the game over screen
- [ ] Pressing Space, Up Arrow, or tapping the screen restarts the game from the beginning
- [ ] High score is updated if the current run exceeds the previous best

### 2.7 Mobile Touch Controls

**Description:** The game must be fully playable on touchscreen devices without a keyboard.

**Acceptance Criteria:**
- [ ] Tapping anywhere on the game canvas causes the dinosaur to jump
- [ ] Swiping down on the game canvas causes the dinosaur to duck
- [ ] Touch controls activate the same code path as keyboard controls (no duplication of logic)
- [ ] Controls remain responsive at 60 fps on modern mobile browsers

---

## 3. Technical Requirements

### 3.1 Technology Stack

| Component | Technology |
|-----------|------------|
| Markup | HTML5 (single file or minimal files) |
| Styling | CSS3 (inline or `<style>` block) |
| Logic | Vanilla JavaScript (ES6+) |
| Rendering | HTML5 Canvas API |
| Storage | Web Storage API (`localStorage`) |
| Framework | None |

### 3.2 Constraints

- No external libraries, CDN links, or npm packages
- Game must run by opening a single `index.html` file in any modern browser
- No server-side component required
- Assets must be drawn programmatically (canvas shapes/paths) or embedded as inline data URIs — no external image files required
- Code should be contained in as few files as practical (ideally a single `index.html`)

---

## 4. Non-Functional Requirements

### 4.1 Performance
- Game loop targets 60 fps on a modern desktop browser
- No memory leaks — objects are recycled or properly removed when off-screen
- Game remains smooth as score and speed increase

### 4.2 Responsiveness
- Canvas scales to fill the viewport width on mobile devices
- Game is playable on screens as narrow as 320 px (minimum mobile width)
- Landscape and portrait orientations are both supported

### 4.3 Compatibility
- Works in the latest stable versions of Chrome, Firefox, Safari, and Edge
- Graceful degradation if `localStorage` is unavailable (no crash, score just resets)

---

## 5. Acceptance Criteria

### 5.1 MVP (Minimum Viable Product)

- [ ] Single `index.html` file opens and renders the game without errors
- [ ] Dinosaur runs, jumps, and ducks correctly via keyboard
- [ ] At least one cactus obstacle type scrolls and triggers game over on collision
- [ ] Score increments and is displayed on screen
- [ ] Game over screen appears on collision with a restart option
- [ ] High score is saved to `localStorage`

### 5.2 Full Feature Set

- [ ] All obstacle types (3+ cactus variants, pterodactyl at varied heights)
- [ ] Jump and duck animations
- [ ] Speed progression tied to score
- [ ] Day/night cycle
- [ ] Touch controls for mobile
- [ ] Responsive canvas scaling

### 5.3 Future Enhancements (Out of Scope for v1)

- Sound effects and background music
- Achievements or unlockable characters
- Online leaderboard
- Configurable key bindings
- Accessibility mode (reduced motion)

---

*Document maintained by: PO Agent*
*Last updated: 2026-03-01*
