class Player:
    visible_fields = ['name']

    def __init__(self, name: str):
        self.name: str = name
        self.team = None  # Reference to a Team object

    def win_point(self) -> int | Exception:
        """Delegate point scoring to the team."""
        if self.team:
            self.team.points.add_point()
        else:
            raise Exception("Player is not part of a team!")
        return self.team.points.get_curr_pts()

    def __str__(self):
        return f"Player: {self.name}"
