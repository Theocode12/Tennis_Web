
---

# 🎾 Tennis Simulation Streaming System — Architectural Guide

---

## 🧩 System Overview

This system allows users to **watch simulated tennis matches** via WebSocket in a controlled, real-time-like environment. The simulations are already completed and stored on disk, but streamed to users with timed control to simulate live gameplay.

There are three types of users:
- **Player** (PvP or PvAI)
- **Spectator**
- (Internally: Scheduler components stream the match data.)

---

## 📚 Core Concepts

### 🎛 1. **Scheduler Manager**
**Role**: Central registry and lifecycle manager for all active `Schedulers`.

**Responsibilities**:
- Keep track of all active schedulers.
- Route incoming WebSocket requests to the correct `Scheduler` instance.
- Ensure new schedulers are created only when necessary.
- Destroy unused schedulers when no clients are attached.
- Deduplicate schedulers for shared experiences (e.g., spectators watching same match).

**Receives**:
- WebSocket events that need to attach to a stream.
- Signals to destroy or cleanup schedulers.

**Produces**:
- A `Scheduler` instance (existing or newly created) per client request.

---

### 📦 2. **Scheduler**
**Role**: Time-based stream engine for reading a game simulation file line-by-line and emitting data to all connected clients in the correct order and timing.

**Types**:
- `PvPSharedScheduler`: Shared between both players, synchronized controls.
- `PvAIScheduler`: Controlled by a single player independently.
- `SpectatorScheduler`: Shared between many users, no control allowed.

**Responsibilities**:
- Open and manage the simulation file (or Redis stream).
- Read game data incrementally using configured delay.
- Maintain current playback state (e.g., paused, current line, delay).
- Broadcast each chunk (e.g., rally, point, score) to connected clients.
- Respond to control messages (pause, play, speed up) based on user type.

**Receives**:
- Control commands from `ClientManager`.
- Requests to attach/detach clients.

**Produces**:
- Streamed game data via pub/sub system to `ClientManager`.

---

### 🧑‍💻 3. **Client Manager**
**Role**: Manages individual WebSocket connections and their relationship with schedulers.

**Responsibilities**:
- Authenticate and track connected clients.
- Parse WebSocket messages and determine user intent (join game, pause, etc).
- Attach clients to appropriate schedulers via `SchedulerManager`.
- Listen to data emitted from schedulers and send it to respective clients.
- Forward control actions to the scheduler (if user is a player).
- Handle disconnects and cleanup.
  
**Receives**:
- WebSocket messages (from frontend).
- Scheduler events (via queues or callbacks).

**Produces**:
- Scheduler control commands.
- WebSocket responses to client.

---

### 📂 4. **Game Storage (File or Redis)**
**Role**: Persistent storage of completed simulations, used for streaming playback.

**Responsibilities**:
- Store simulation output from game engine (line-based or chunk-based).
- Allow incremental reads during playback (support seeking, partial reads).
- Optionally support appending for live games.

**Receives**:
- Simulation results from game engine.

**Produces**:
- Match data during stream (e.g., rally-by-rally events).

---

### 🔔 5. **Control Protocol**
**Role**: Defines structured commands between client and server over WebSocket.

**Actions**:
- `start` – begin watching a match (with optional delay/speed).
- `pause` – halt playback (if permitted).
- `resume` – continue playback (if permitted).
- `speed` – update playback speed.
- `scrub` – seek to a specific point (players only).
- `stop` – detach from stream.

**Flow**:
Frontend ➡ Client Manager ➡ Scheduler ➡ Broadcast

---

## 🔄 Interaction Flow (Lifecycle)

### Example: Player starts a PvAI match
1. **Frontend** sends `{ "action": "start", "game_id": "123", "delay": 1.0 }` via WebSocket.
2. **Client Manager** parses the message, identifies user type = "player".
3. **Client Manager** asks **Scheduler Manager** for a scheduler for `game_id=123` with `mode=pvai`, `user_id=XYZ`.
4. **Scheduler Manager** creates a new `PvAIScheduler` and returns it.
5. **Scheduler** starts reading the file, chunk by chunk, every 1.0s.
6. **Scheduler** sends data to the client via an internal queue.
7. **Client Manager** reads from the queue and pushes updates to the WebSocket.

---

### Example: Spectator joins a match
1. WebSocket connects and sends `{ "action": "start", "game_id": "123" }`.
2. **Client Manager** routes to **Scheduler Manager**.
3. Scheduler Manager finds or creates a shared **SpectatorScheduler**.
4. Client is subscribed to the scheduler’s output queue.
5. Control messages like `pause`, `speed`, or `scrub` are ignored.

---

### Example: Player A in PvP pauses the game
1. Sends `{ "action": "pause" }` via WebSocket.
2. **Client Manager** sends `pause()` to the shared `PvPScheduler`.
3. `PvPScheduler` pauses stream for all attached clients (including Player B).
4. Scheduler stops reading file until `resume()` is received.

---

## 🧹 Cleanup Strategy

- When a **WebSocket disconnects**, `ClientManager` removes it from the scheduler.
- When a **Scheduler has no clients**, `SchedulerManager` kills it and releases resources.
- Spectator schedulers can have TTL (e.g. destroy after 5 minutes of inactivity).
- You can add periodic heartbeat checks to kill zombie schedulers.

---

## 🧱 Summary of Entity Responsibilities

| Entity | Key Responsibilities | Knows About |
|--------|----------------------|-------------|
| **SchedulerManager** | Track/create/kill schedulers | Scheduler registry |
| **Scheduler (various types)** | Stream data incrementally | File handle, playback state, client list |
| **ClientManager** | Manage WebSocket connections | SchedulerManager, WebSocket API |
| **Game Storage** | Store and provide match data | Match files or Redis streams |
| **Control Protocol** | Standard message schema | ClientManager, Scheduler |

---


## 🌍 Optional Feature Extensions

These features aren't core to the streaming engine but add **significant value, immersion, and engagement** to the platform. They can be rolled out incrementally or explored as the system scales.

---

### 🗨️ Communication & Social

- **Volatile Live Chat**: In-game chatroom for players and spectators, not stored permanently.
- **AI Commentary Feed**: Text-based live match commentary generated by AI and streamed to clients.
- **Emoji Reactions**: Real-time reactions (like Twitch emotes) spectators and players can send.
- **Video Conferencing for PvP**: Optional live camera feed between players during matches.
- **Spectator Mode**: Join ongoing matches without control rights — PvP, PvAI, or AIvAI.

---

### 🎵 Media & Atmosphere

- **Background Music Streaming**: Curated monthly playlists streamed to users during matches.
- **Dynamic Sound Effects**: Contextual match sounds (e.g., crowd cheers, ball hit sounds).
- **AI Voice Commentary** *(future)*: Text-to-speech engine generating dynamic match commentary.

---

### 🧠 Gameplay Features

- **Pause/Resume/Speed Control**: Players (in PvAI/PvP) can control playback flow.
- **Multi-speed Streaming**: 0.5x, 1x, 2x playback options.
- **Dynamic Court Types**: Grass, clay, hardcourt — affects gameplay realism.

---

### 🧩 Game Ecosystem

- **2D Visual**: Live 2d visual of live games
- **Possible Sign ups**: Users can sign up for their game records to be saved
- **Tournament Mode**: Auto-generated brackets (e.g., US Open, Roland Garros) for large-scale competitions.
- **Seasonal Events**: Special time-bound challenges with themed content.
- **Match Highlights(after 2D rollout)**: AI-generated post-match highlight reels for players and spectators.
- **Replay Archive(after 2D rollout)**: Users can rewatch past matches or famous simulated moments.

---

### 📈 Stats & Meta

- **Live Stats Feed**: Real-time data like ace count, rally length, shot accuracy.
- **Match History(after Sign ups Rollout)**: Store and view user performance across games.
- **XP and Rewards System(after Sign ups Rollout)**: Leveling up, achievements, and unlockables tied to gameplay.
- **Leaderboards(after Sign ups Rollout)**: Global or seasonal rankings for players and tournaments.

---

### 🕹️ Cross-Game Scalability

- **Multi-Game Support**: Platform extensible beyond tennis (e.g., basketball, soccer, racing).
- **Modular Game Engines**: Plug-and-play architecture for new sports simulations.
- **Unified User Profile(after Sign ups Rollout)**: Track cross-sport performance and stats.


---

### 🛡️ Infrastructure & Deployment

- **Distributed WebSocket System**: Horizontally scalable socket handling for many users.
- **Redis Pub/Sub or Kafka Streams**: For decoupled, high-performance data streams.
- **CDN-backed Media Delivery**: Low-latency music and video feed distribution.

---
