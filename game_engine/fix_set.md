You're spot-on in identifying a key design principle here: **separation of concerns** and ensuring **logical ownership of data** are critical to building a clean and maintainable system. Let's analyze both approaches and determine the best path forward:

---

### **Option 1: Set as a Team-Specific Object**
- **Design**: Each `Team` has its own `Set` object, which maintains its team's set points. For example:
  ```python
  Team 1: Set [6, 4, 2]
  Team 2: Set [4, 6, 6]
  ```
  - Each team's `Set` object tracks the points it scored in each set.

- **Advantages**:
  1. **Separation of Concerns**: Each `Team` is responsible only for its own data.
  2. **Simplicity**: `Set` objects are independent, requiring no shared state.
  3. **Flexibility**: This design easily supports cases like doubles matches where teams might have their own context for tracking points.

- **Disadvantages**:
  1. The logic for determining set winners, comparing points, or deciding tie-breaks must live elsewhere, like in the game engine or a referee object. This might seem less intuitive since a `Set` doesn't encapsulate the full context of the set.

---

### **Option 2: Set as a Shared Object**
- **Design**: A single `Set` object tracks points for both teams:
  ```python
  Set 1: (6, 4)
  Set 2: (4, 6)
  Set 3: (2, 6)
  ```
  - The `Set` object becomes a more global concept, owned or managed by the game engine, and records both teams' scores.

- **Advantages**:
  1. **Centralized Context**: The `Set` has a full view of the state of the game, making it easier to handle rules like tie-breaks or determining set winners without needing additional coordination between teams.
  2. **Encapsulation**: The logic for set-related operations (e.g., comparing points) can live within the `Set` class itself, reducing duplication and promoting reuse.

- **Disadvantages**:
  1. **Coupling**: The `Set` object becomes tightly coupled to the game engine since it must understand and track both teams.
  2. **Ownership Complexity**: The game engine must manage and update the `Set` object, which might feel less natural than having teams manage their own set points.

---

### **Natural, Logical, and Best Practice Recommendation**

#### **Hybrid Approach: Use a Shared `Set` but Separate Team Responsibilities**
The best solution often combines the strengths of both approaches. Here's how:

1. **Shared `Set` Object**:
   - The `Set` tracks points for both teams as `(team1_points, team2_points)`.
   - The `Set` is managed by the **game engine**, not by the teams, since the concept of a set inherently involves both teams.

2. **Team-Specific Abstractions**:
   - Each team still manages its own logic for gameplay (e.g., calling `win_point`, resetting game points).
   - Teams rely on the engine or a "referee" class to handle comparisons and rules that depend on the shared `Set`.

3. **Game Engine as Mediator**:
   - The game engine maintains and updates the `Set` object, ensuring clear separation of concerns:
     - Teams focus on gameplay (scoring, resetting points).
     - The engine tracks match progression (current set points, set winners, tie-break logic).

---

### **Implementation**

#### Refactor `Set` for Shared Use
```python
class Set:
    def __init__(self):
        self.sets = []  # List of (team1_points, team2_points)

    def add_new_set(self):
        """Initialize a new set with zero points for both teams."""
        self.sets.append((0, 0))

    def update_score(self, team_index: int, points: int = 1):
        """Update the score for the given team in the current set."""
        if not self.sets:
            raise Exception("No set to update")
        t1, t2 = self.sets[-1]
        if team_index == 1:
            self.sets[-1] = (t1 + points, t2)
        elif team_index == 2:
            self.sets[-1] = (t1, t2 + points)
        else:
            raise ValueError("Invalid team index, must be 1 or 2")

    def get_current_set_points(self):
        """Return the current set points as a tuple."""
        if not self.sets:
            raise Exception("No set available")
        return self.sets[-1]

    def get_winner(self, rules) -> Optional[int]:
        """Determine the winner of the current set based on rules."""
        t1, t2 = self.get_current_set_points()
        if t1 >= rules.MIN_SET_POINTS and t1 - t2 >= rules.MIN_SET_DIFFERENCE:
            return 1
        if t2 >= rules.MIN_SET_POINTS and t2 - t1 >= rules.MIN_SET_DIFFERENCE:
            return 2
        return None

    def __str__(self):
        return f"Sets: {self.sets}"
```

---

#### Game Engine Integration
The game engine uses the `Set` to handle match progression:
```python
class GameEngine:
    def __init__(self, team1: Team, team2: Team, rules):
        self.team1 = team1
        self.team2 = team2
        self.rules = rules
        self.sets = Set()  # Shared Set object

    def start_new_set(self):
        """Add a new set and reset game points."""
        self.sets.add_new_set()
        self.team1.reset_game_points()
        self.team2.reset_game_points()

    def team_scores_point(self, team_index: int):
        """Record a point for a team and check for set progression."""
        if team_index == 1:
            self.team1.points.add_point()
        elif team_index == 2:
            self.team2.points.add_point()
        else:
            raise ValueError("Invalid team index, must be 1 or 2")
        
        # Update the shared Set object
        self.sets.update_score(team_index)

        # Check for set winner
        winner = self.sets.get_winner(self.rules)
        if winner:
            print(f"Team {winner} wins the set!")
            self.start_new_set()
```

---

### Why This Works
- **Encapsulation**: The `Set` handles all logic related to scores and winner determination.
- **Separation of Concerns**: Teams manage their gameplay independently, while the game engine manages match progression.
- **Scalability**: The shared `Set` easily adapts to different rules, formats, or match structures.

Would you like further help implementing or testing this design?