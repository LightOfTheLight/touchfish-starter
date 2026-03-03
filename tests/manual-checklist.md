# Dino Runner — Manual Test Checklist

> **How to use:** Open `index.html` in a browser and verify each item by playing the game.
> Mark each item `[x]` when confirmed passing, or `[!]` when a defect is found (note the defect).
>
> Last run: _(tester fills in)_
> Browser / OS: _(tester fills in)_

---

## 1. Start Screen (REQ §2.7)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 1.1 | Open `index.html` — observe game without pressing anything | Dino visible, standing still; "DINO RUNNER" title and "Press Space / ↑ or Tap to start" prompt shown; game does NOT move | `[ ]` |
| 1.2 | Wait 5 seconds without any input | Game remains on start screen; score stays 0 | `[ ]` |
| 1.3 | Press Space | Game starts: dino begins running, obstacles appear, score increments | `[ ]` |
| 1.4 | Reload; press Up Arrow | Same as 1.3 | `[ ]` |
| 1.5 | Reload; tap the canvas on a touch device | Same as 1.3 | `[ ]` |

---

## 2. Dinosaur Character (REQ §2.1)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 2.1 | Start game — observe dino while running | Legs alternate (running animation visible) | `[ ]` |
| 2.2 | Press Space or Up Arrow while running | Dino jumps; animation changes to airborne pose | `[ ]` |
| 2.3 | Press Space again immediately while in the air | Dino does NOT jump a second time | `[ ]` |
| 2.4 | Hold Down Arrow while running | Dino crouches visibly (body height reduces ~50%) | `[ ]` |
| 2.5 | Release Down Arrow | Dino returns to full standing height | `[ ]` |
| 2.6 | Try pressing Down Arrow while in the air | Dino does NOT duck mid-air | `[ ]` |
| 2.7 | On touch device: tap | Dino jumps | `[ ]` |
| 2.8 | On touch device: swipe down | Dino ducks | `[ ]` |
| 2.9 | Jump animation vs. running animation | Jump pose is visually distinct from running legs | `[ ]` |
| 2.10 | Duck animation vs. running animation | Duck pose is visually distinct (lower, elongated) | `[ ]` |

---

## 3. Obstacles (REQ §2.2)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 3.1 | Play for 30 seconds — observe cacti | Both small and large cactus variants appear | `[ ]` |
| 3.2 | Play for 30 seconds — observe cactus groups | Groups of 1, 2, and 3 cacti appear | `[ ]` |
| 3.3 | Play past score 200 — observe obstacles | Flying pterodactyls appear | `[ ]` |
| 3.4 | Observe pterodactyls — watch their vertical position | Pterodactyls appear at 3 different heights (low, mid, high) | `[ ]` |
| 3.5 | Observe pterodactyls — watch their wings | Wing animation alternates (flapping effect) | `[ ]` |
| 3.6 | Observe obstacle timing | Obstacles do not all appear at fixed intervals — there is variation | `[ ]` |
| 3.7 | Walk into a cactus | Game over triggers immediately | `[ ]` |
| 3.8 | Walk into a pterodactyl | Game over triggers immediately | `[ ]` |
| 3.9 | Jump over a low pterodactyl while standing | Dino clears it successfully | `[ ]` |
| 3.10 | Duck under a low pterodactyl (score > 200) | Dino's duck hitbox avoids the pterodactyl | `[ ]` |

---

## 4. Scoring (REQ §2.3)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 4.1 | Start game — observe top-right score | Score increments continuously from 00000 | `[ ]` |
| 4.2 | Observe score format | 5-digit zero-padded (e.g., "00042") | `[ ]` |
| 4.3 | Observe HI score label | "HI XXXXX" appears to the left of the current score | `[ ]` |
| 4.4 | Achieve a new high score (run far, then die) | HI score updates to new value on same session | `[ ]` |
| 4.5 | Reload the page after achieving high score | HI score is preserved from previous session (localStorage) | `[ ]` |
| 4.6 | Restart after game over | Score resets to 00000; HI score unchanged | `[ ]` |

---

## 5. Difficulty Progression (REQ §2.4)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 5.1 | At game start — observe obstacle movement speed | Obstacles move at a modest pace | `[ ]` |
| 5.2 | After reaching score ~500+ — compare speed | Obstacles move noticeably faster than at start | `[ ]` |
| 5.3 | Play a very long game (score 3000+) | Speed increases but the game remains playable (does not become impossibly fast) | `[ ]` |
| 5.4 | Compare obstacle spawn rate at start vs. score 500+ | Obstacles spawn more frequently at higher scores | `[ ]` |

---

## 6. Day / Night Cycle (REQ §2.5)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 6.1 | Start game | Background is light (day mode) | `[ ]` |
| 6.2 | Reach score 700 | Background transitions to dark (night mode) | `[ ]` |
| 6.3 | Continue to score 1400 | Background transitions back to light (day mode) | `[ ]` |
| 6.4 | During night mode — observe all elements | Dino, obstacles, and ground are all visible in dark theme | `[ ]` |
| 6.5 | During day mode — observe all elements | Dino, obstacles, and ground are all visible in light theme | `[ ]` |
| 6.6 | Restart after night mode | Game starts back in day mode | `[ ]` |

---

## 7. Game Over & Restart (REQ §2.6)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 7.1 | Collide with an obstacle | Game pauses immediately | `[ ]` |
| 7.2 | Observe screen after collision | "GAME OVER" text displayed prominently | `[ ]` |
| 7.3 | Observe restart instructions | "Press Space / ↑ or Tap to restart" (or similar) displayed | `[ ]` |
| 7.4 | Dino appearance on game over | Dino shows X-eyes / dead pose | `[ ]` |
| 7.5 | Press Space after game over | Game restarts; score resets to 00000 | `[ ]` |
| 7.6 | Press Up Arrow after game over | Same as 7.5 | `[ ]` |
| 7.7 | Tap screen after game over (touch device) | Same as 7.5 | `[ ]` |
| 7.8 | Check HI score after restart | Previous high score still shown | `[ ]` |

---

## 8. Visual / Rendering Quality (REQ §4.1, §4.2, §4.3)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 8.1 | Open on 1920×1080 desktop | Game renders cleanly; no visual glitches | `[ ]` |
| 8.2 | Open on 375px-wide mobile viewport | Game scales down, remains playable | `[ ]` |
| 8.3 | Open on 320px-wide viewport | Game still visible and usable (REQ §4.2) | `[ ]` |
| 8.4 | Observe frame rate during gameplay | Motion appears smooth (~60 FPS), no stuttering | `[ ]` |
| 8.5 | Open DevTools → Performance tab → record 10s run | Frame rate stays near 60 FPS; no sustained drops | `[ ]` |
| 8.6 | Ground scrolling | Ground line and pebbles scroll smoothly left | `[ ]` |
| 8.7 | Clouds | Clouds drift slowly in the background | `[ ]` |

---

## 9. Browser Compatibility (REQ §3.3)

| Browser | Version | Start / Jump / Duck | Score / Hi Score | Day/Night | Mobile Touch | Overall |
|---------|---------|---------------------|-----------------|-----------|--------------|---------|
| Chrome (latest) | | `[ ]` | `[ ]` | `[ ]` | n/a | `[ ]` |
| Firefox (latest) | | `[ ]` | `[ ]` | `[ ]` | n/a | `[ ]` |
| Safari (latest) | | `[ ]` | `[ ]` | `[ ]` | n/a | `[ ]` |
| Edge (latest) | | `[ ]` | `[ ]` | `[ ]` | n/a | `[ ]` |
| iOS Safari | | `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| Android Chrome | | `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |

---

## 10. Accessibility / Usability (REQ §4.3)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 10.1 | First-time player — read start screen | Controls are self-evident from the on-screen prompt | `[ ]` |
| 10.2 | Page scroll during game | Down arrow / Space do NOT scroll the page (default prevented) | `[ ]` |
| 10.3 | Touch canvas to start | Canvas cursor style indicates it is interactive (pointer) | `[ ]` |

---

## 11. Known Issues (from automated test analysis)

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| BUG-001 | Medium | **Spawn timing not randomized**: The random spawn gap set after each obstacle spawn is immediately overwritten by the deterministic formula on the next frame. Obstacles spawn at fixed, predictable intervals for a given speed. See `test.html` § Known Issues. | Open |
| BUG-002 | Low | **Touch swipe-down also triggers a jump**: `touchstart` fires `_onJumpPress()` before `touchmove` fires the duck, so a swipe-down gesture causes the dino to briefly jump before ducking. May cause unintended jumps. | Open |

---

*Maintained by: TESTER Agent*
*Created: 2026-03-03*
