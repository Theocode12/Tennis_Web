from . import BasePlayerView


class MatchViewData:
    def __init__(self, player1_view: BasePlayerView, player2_view: BasePlayerView):
        self.player1_view = player1_view
        self.player2_view = player2_view

    def __eq__(self, other):
        if not isinstance(other, MatchViewData):
            return False
        return (
            self.player1_view == other.player1_view
            and self.player2_view == other.player2_view
        )
