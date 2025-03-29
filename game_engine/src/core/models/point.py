class Points:
    def __init__(self):
        self.current_points: int = 0
        self.total_points: int = 0

    def add_point(self, value: int = 1) -> None:
        self.current_points += value
        self.total_points += value

    def reset(self) -> None:
        self.current_points = 0

    def get_curr_pts(self) -> int:
        return self.current_points

    def __str__(self) -> None:
        return (
            f"Current Points: {self.current_points}, Total Points: {self.total_points}"
        )
