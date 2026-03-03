# TESTER Agent History

## Session Log

---

### Session 1 — 2026-03-03

**Trigger:** Chain trigger from DEV agent after implementing the Google Dinosaur web game.

**Branch:** `agent/PO/20260303-091856`

**Objective:** Review the DEV implementation against REQUIREMENT.md and produce a comprehensive test suite.

---

#### Thinking Process

**Step 1: Read requirements and role definition**
- Read `REQUIREMENT.md` to understand all acceptance criteria (§2.1–§2.7, §3–§4).
- Read `TESTER.md` to confirm responsibilities and constraints.
- Noted the game is single-file (`index.html`), using vanilla HTML/CSS/JS + Canvas API.

**Step 2: Analyze the DEV implementation**

Reviewed `index.html` (663 lines) end-to-end. The implementation includes:

| Feature | Implementation |
|---------|---------------|
| Dino character | `Dino` class — jump, duck, gravity arc, leg animation, hitbox |
| Cacti obstacles | `CactusGroup` class — 2 variants, 1–3 per group, hitboxes |
| Pterodactyl | `Pterodactyl` class — 3 height levels, wing animation, hitbox |
| Scoring | `SCORE_RATE=0.1 pts/frame`, 5-digit zero-padded display |
| High score | `localStorage` persistence (`dinoHiScore`) |
| Speed progression | `SPEED_INC=0.001/frame`, cap at `MAX_SPEED=13` |
| Day/night cycle | Toggle every `CYCLE_THRESH=700` score points |
| Game states | `STATE.IDLE → RUNNING → GAMEOVER → RUNNING` lifecycle |
| Input | Keyboard (Space/Up/Down) + Touch (tap/swipe-down) |
| Ground / clouds | Scrolling ground strip with pebbles; drifting clouds |

**Step 3: Code analysis — bugs found**

After careful code review, two issues were identified:

**BUG-001 (Medium) — Spawn timing not effectively randomized**

In `_update()`:
```javascript
// Line 563-574 (approx)
this.spawnGap = Math.max(SPAWN_MIN,
  SPAWN_MAX - (this.speed - INIT_SPEED) * 110);   // ← deterministic, set EVERY frame

this.spawnTimer += dt;
if (this.spawnTimer >= this.spawnGap) {
  this.spawnTimer = 0;
  this.spawnGap = SPAWN_MIN +
    Math.random() * ...;   // ← random value set here...
  this._spawnObstacle();
}
// ...but on the VERY NEXT frame, line 1 overwrites with the deterministic value.
```
The random `spawnGap` is set correctly at the end of a spawn event, but the FIRST thing the next frame does is overwrite it with the deterministic speed-based value. The randomization is therefore no-op. Obstacles spawn at a fixed, predictable interval for any given speed — violating REQ §2.2 ("Obstacle spawn timing is randomized within a defined interval range").

**BUG-002 (Low) — Touch swipe-down also triggers a jump**

In `_bindEvents()`, the `touchstart` handler always calls `_onJumpPress()` (which calls `dino.jump()`), even when the player's intent is to swipe down to duck. The duck only activates when `touchmove` fires with `dy > 20`. This means every swipe-down gesture also causes a momentary jump, which may cause unintended deaths.

**Step 4: Assessment of requirements coverage**

| Requirement | Status | Notes |
|-------------|--------|-------|
| REQ 2.1 — Dino running animation | ✅ Pass | Frame alternates legs every 7 ticks |
| REQ 2.1 — Space/Up jump | ✅ Pass | Handled in keydown |
| REQ 2.1 — Down duck | ✅ Pass | keydown/keyup managed |
| REQ 2.1 — Touch jump | ✅ Pass | touchstart |
| REQ 2.1 — Touch duck (swipe down) | ⚠ Partial | Works, but also triggers jump (BUG-002) |
| REQ 2.1 — No double jump | ✅ Pass | `if (!this.jumping)` guard |
| REQ 2.1 — No duck while airborne | ✅ Pass | `if (!this.jumping)` guard |
| REQ 2.2 — Cacti 2 variants | ✅ Pass | variant 0 (small) and 1 (large) |
| REQ 2.2 — Cacti groups 1–3 | ✅ Pass | `Math.floor(Math.random()*3)+1` |
| REQ 2.2 — Pterodactyl | ✅ Pass | 3 height levels |
| REQ 2.2 — Randomized spawn timing | ❌ Fail | BUG-001 |
| REQ 2.2 — Obstacles move left | ✅ Pass | `this.x -= speed` |
| REQ 2.2 — Collision → game over | ✅ Pass | `_checkCollision()` |
| REQ 2.3 — Score increments | ✅ Pass | `this.score += SCORE_RATE` |
| REQ 2.3 — Score displayed | ✅ Pass | Top-right HUD |
| REQ 2.3 — Hi score displayed | ✅ Pass | "HI XXXXX" alongside score |
| REQ 2.3 — Hi score localStorage | ✅ Pass | `dinoHiScore` key |
| REQ 2.3 — Hi score updates live | ✅ Pass | Updated in `_update()` |
| REQ 2.4 — Initial speed 5 px/frame | ✅ Pass | `INIT_SPEED=5` |
| REQ 2.4 — Speed increases | ✅ Pass | `+0.001/frame` |
| REQ 2.4 — Speed capped | ✅ Pass | `Math.min(..., MAX_SPEED)` |
| REQ 2.4 — Spawn freq increases | ✅ Pass | `spawnGap` decreases with speed (though not randomized per BUG-001) |
| REQ 2.5 — Starts in day mode | ✅ Pass | `this.night=false` |
| REQ 2.5 — Transitions to night | ✅ Pass | At score 700 |
| REQ 2.5 — Alternates day/night | ✅ Pass | Every CYCLE_THRESH |
| REQ 2.5 — All elements visible both modes | ✅ Pass | Two palettes applied to all draws |
| REQ 2.6 — Game pauses on collision | ✅ Pass | `state=GAMEOVER` stops `_update` |
| REQ 2.6 — Game Over message | ✅ Pass | "GAME OVER" text in overlay |
| REQ 2.6 — Restart prompt | ✅ Pass | Shown in GAMEOVER state |
| REQ 2.6 — Restart on Space/Up/Tap | ✅ Pass | `_onJumpPress()` transitions GAMEOVER → RUNNING |
| REQ 2.6 — Score resets, hi preserved | ✅ Pass | `this.score=0`, `this.hiScore` untouched |
| REQ 2.7 — No auto-start | ✅ Pass | `STATE.IDLE` on load |
| REQ 2.7 — Prompt shown | ✅ Pass | "Press Space / ↑ or Tap to start" |
| REQ 2.7 — Starts on valid input | ✅ Pass | Space/Up/Tap handled |

**Overall:** 30/31 requirements pass. 1 fails (BUG-001). 1 is partial (BUG-002).

**Step 5: Test artifacts created**

- `tests/test.html` — 110+ automated unit/integration tests in 15 suites
  - Mini test framework (no external dependencies)
  - Mocked `requestAnimationFrame` and `localStorage`
  - Loads game via `fetch('../index.html')` + `eval()`
  - Includes a BUG-001 detecting test in § Known Issues suite
- `tests/manual-checklist.md` — 50+ manual test items across 11 categories

---

#### Test Coverage Summary

| Category | Auto Tests | Manual Items |
|----------|-----------|-------------|
| Constants / Config | 9 | — |
| Dino initialization | 6 | 2 |
| Dino jump mechanics | 7 | 5 |
| Dino duck mechanics | 5 | 4 |
| Dino hitbox | 4 | — |
| CactusGroup | 11 | 4 |
| Pterodactyl | 11 | 4 |
| Game initial state | 7 | — |
| Scoring | 7 | 6 |
| Speed / difficulty | 4 | 4 |
| Day/night cycle | 5 | 6 |
| Collision / game over | 8 | 8 |
| Start screen | 3 | 5 |
| Obstacle spawn rules | 4 | — |
| Known issues (BUG-001) | 1 | — |
| Visual / rendering | — | 7 |
| Browser compatibility | — | 24 |
| Accessibility | — | 3 |
| **Total** | **~110** | **~82** |

---

#### Bugs Reported

| ID | Severity | Title |
|----|----------|-------|
| BUG-001 | Medium | Spawn timing is not effectively randomized (spawnGap overwritten each frame) |
| BUG-002 | Low | Touch swipe-down also triggers a jump due to touchstart ordering |

GitHub Issues created for both bugs.

---

## Change Log

| Date | Session | Change |
|------|---------|--------|
| 2026-03-03 | Session 1 | Initial test suite created: `tests/test.html`, `tests/manual-checklist.md` |
| 2026-03-03 | Session 1 | Identified BUG-001 (spawn randomization) and BUG-002 (touch swipe jump) |

---

*Maintained by: TESTER Agent*
