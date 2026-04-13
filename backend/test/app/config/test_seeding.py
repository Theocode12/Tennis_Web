import pytest

from app.config.seeding import apply_seeding, seed_positions


class TestSeedPositions:
    def test_single_position(self) -> None:
        assert seed_positions(1) == [0]

    def test_two_positions(self) -> None:
        assert seed_positions(2) == [0, 1]

    def test_four_positions(self) -> None:
        assert seed_positions(4) == [0, 3, 1, 2]

    def test_eight_positions(self) -> None:
        assert seed_positions(8) == [0, 7, 3, 4, 1, 6, 2, 5]

    def test_sixteen_positions(self) -> None:
        pos = seed_positions(16)
        assert pos[0] == 0  # seed 1 at top
        assert pos[1] == 15  # seed 2 at bottom
        assert len(pos) == 16
        assert sorted(pos) == list(range(16))

    def test_thirty_two_positions(self) -> None:
        pos = seed_positions(32)
        assert pos[0] == 0  # seed 1
        assert pos[1] == 31  # seed 2
        assert len(pos) == 32
        assert sorted(pos) == list(range(32))

    def test_all_positions_unique(self) -> None:
        for size in [4, 8, 16, 32]:
            pos = seed_positions(size)
            assert len(set(pos)) == size, f"Duplicate positions for size {size}"

    def test_seeds_one_and_two_opposite_halves(self) -> None:
        """Seeds 1 and 2 should be in opposite halves of the bracket."""
        for size in [4, 8, 16, 32]:
            pos = seed_positions(size)
            half = size // 2
            assert pos[0] < half, f"Seed 1 not in top half for size {size}"
            assert pos[1] >= half, f"Seed 2 not in bottom half for size {size}"

    def test_seeds_three_four_opposite_quarters(self) -> None:
        """Seeds 3 and 4 should be in opposite quarters."""
        for size in [8, 16, 32]:
            pos = seed_positions(size)
            quarter = size // 4
            s3_quarter = pos[2] // quarter
            s4_quarter = pos[3] // quarter
            assert s3_quarter != s4_quarter, f"Seeds 3/4 in same quarter for size {size}"


class TestApplySeeding:
    @pytest.fixture
    def players(self):
        return [
            {"name": "Alcaraz", "world_ranking": 1},
            {"name": "Sinner", "world_ranking": 2},
            {"name": "Zverev", "world_ranking": 3},
            {"name": "Djokovic", "world_ranking": 4},
            {"name": "Medvedev", "world_ranking": 5},
            {"name": "Rublev", "world_ranking": 6},
            {"name": "Ruud", "world_ranking": 7},
            {"name": "De Minaur", "world_ranking": 8},
        ]

    def test_seeds_top_n_players(self, players) -> None:
        bracket = apply_seeding(players, 4)
        names = [p["name"] for p in bracket]
        # Only top 4 by ranking should be included
        assert "Alcaraz" in names
        assert "Sinner" in names
        assert "Zverev" in names
        assert "Djokovic" in names
        assert "De Minaur" not in names

    def test_seed_one_at_position_zero(self, players) -> None:
        bracket = apply_seeding(players, 8)
        assert bracket[0]["name"] == "Alcaraz"

    def test_seed_two_at_opposite_end(self, players) -> None:
        bracket = apply_seeding(players, 8)
        assert bracket[7]["name"] == "Sinner"

    def test_first_round_separation(self, players) -> None:
        """Top 4 seeds should not meet in the first round."""
        bracket = apply_seeding(players, 8)
        top_four_names = {"Alcaraz", "Sinner", "Zverev", "Djokovic"}
        for i in range(0, 8, 2):
            pair = {bracket[i]["name"], bracket[i + 1]["name"]}
            overlap = pair & top_four_names
            assert len(overlap) <= 1, f"Top-4 seeds paired together: {pair}"

    def test_unsorted_players_get_sorted(self) -> None:
        """Players provided in random order should still be seeded correctly."""
        unsorted = [
            {"name": "Rublev", "world_ranking": 6},
            {"name": "Alcaraz", "world_ranking": 1},
            {"name": "Sinner", "world_ranking": 2},
            {"name": "Djokovic", "world_ranking": 4},
        ]
        bracket = apply_seeding(unsorted, 4)
        assert bracket[0]["name"] == "Alcaraz"
        assert bracket[3]["name"] == "Sinner"
