from src.core.constants import TennisConstantsBase


class CustomTournamentConstants(TennisConstantsBase):
    def __init__(self, **kwargs):
        # Dynamically override any constants via kwargs for flexibility
        for key, value in kwargs.items():
            setattr(self, key, value)
