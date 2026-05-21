import pytest

from live_stats_planner import parse_planner_indices, salvage_json_object
from live_stats_stitch import stitch_bundle_answers, StitchedPart


class TestPlannerParse:
    def test_valid_indices(self):
        assert parse_planner_indices('{"indices":[0,7]}', 61, 4) == [0, 7]

    def test_fence(self):
        raw = '```json\n{"indices":[23]}\n```'
        assert parse_planner_indices(raw, 61, 4) == [23]

    def test_invalid_fallback(self):
        assert parse_planner_indices("nope", 61, 4, metrics_like=True) == [0]

    def test_out_of_range(self):
        assert parse_planner_indices('{"indices":[0,99]}', 61, 4) == [0]


class TestStitch:
    def test_one_part(self):
        out = stitch_bundle_answers([StitchedPart(0, "entity.users", "42 users", False)])
        assert "42 users" in out

    def test_failed(self):
        out = stitch_bundle_answers([StitchedPart(7, "entity.friendRequests", "", True)])
        assert "unavailable" in out

    def test_salvage_json(self):
        assert '"indices"' in salvage_json_object('prefix {"indices":[1]} suffix')
