from src.core.models.team_index import TeamIndex


class Set:
    def __init__(self):
        self.sets = []  # List of (team1_points, team2_points)
        self.add_new_set()

    def get_set_points(self):
        return self.sets

    def add_new_set(self):
        """Initialize a new set with zero points for both teams."""
        self.sets.append((0, 0))

    def pop_last_set(self):
        if self.sets:
            self.sets.pop()

    def update_score(self, team_index: TeamIndex, points: int = 1):
        """Update the score for the given team in the current set."""
        if not self.sets:
            raise Exception("No set to update")
        t1, t2 = self.sets[-1]
        if team_index.value == 1:
            self.sets[-1] = (t1 + points, t2)
        elif team_index.value == 2:
            self.sets[-1] = (t1, t2 + points)
        else:
            raise ValueError("Invalid team index, must be 1 or 2")

    def get_current_set_points(self):
        """Return the current set points as a tuple."""
        if not self.sets:
            raise Exception("No set available")
        return self.sets[-1]

    def transform_set_data(self):
        """
        Transform set data from [(6,2), (4,6), (7,6)]
        to [(6, 4, 7), (2, 6, 6)].
        """
        team1_scores = [t1 for t1, _ in self.sets]
        team2_scores = [t2 for _, t2 in self.sets]
        return team1_scores, team2_scores

    def __str__(self):
        return f"Sets: {self.sets}"
