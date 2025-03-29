from src.core.rules import (
    TennisRules,
    GrandSlamRules,
    RegularTournamentRules,
    CustomTennisRules,
)

from src.core.constants import CustomTournamentConstants


class RulesFactory:
    @staticmethod
    def create_rules(
        tournament_type="regular",
        constants: CustomTournamentConstants = None,
    ) -> TennisRules:
        if tournament_type == "grand_slam":
            return GrandSlamRules()
        elif tournament_type == "regular":
            return RegularTournamentRules()
        elif tournament_type == "custom":
            if not constants:
                raise ValueError("No constants object is set")
            return CustomTennisRules(constants)
        else:
            raise ValueError("Invalid Rule Type")
