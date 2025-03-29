class TennisConstantsBase:
    # Core game points
    MIN_POINTS_TO_WIN_GAME = 4  # Points to win a game
    MIN_POINTS_DIFFERENCE_TO_WIN_GAME = 2  # Difference required to win a game in deuce

    # Set rules
    MIN_SET_POINTS = 6  # Points required to win a set
    MIN_SET_DIFFERENCE = 2  # Difference required to win a set
    MAX_SET_POINTS = 7  # Max point required to win a set

    # Tie-break rules
    TIEBREAK_TRIGGER_SCORE = 6  # Score to trigger tie-break (6-6)
    MIN_TIEBREAK_POINTS = 7  # Points required to win a tie-break
    MIN_TIEBREAK_POINT_DIFFERENCE = 2  # Difference required to win a tie-break

    # Match rules
    SETS_TO_WIN_MATCH = 2  # Default for regular tournaments

    # Additional game constants
    NUMBER_OF_PLAYERS = 2  # Number of players in a tennis match
    MIN_POINTS_FOR_DEUCE = 3  # Points threshold for deuce
    ADVANTAGE_DIFFERENCE = 1  # Difference required for advantage
