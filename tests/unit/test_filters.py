import pytest

from dgkit.filters import ExpressionFilter, UnsetFields, FilterChain, parse_filter
from dgkit.models import Artist


@pytest.fixture
def make_artist():
    """Factory for creating Artist instances with defaults."""

    def _make(**kwargs):
        defaults = {
            "id": 1,
            "name": "Test",
            "real_name": None,
            "profile": None,
            "data_quality": None,
        }
        defaults.update(kwargs)
        return Artist(**defaults)

    return _make


class TestExpressionFilter:
    def test_equality_match_drops_record(self, make_artist):
        f = parse_filter("id == 1")
        artist = make_artist(id=1)
        assert f(artist) is None

    def test_equality_no_match_keeps_record(self, make_artist):
        f = parse_filter("id == 99")
        artist = make_artist(id=1)
        assert f(artist) == artist

    def test_not_equal(self, make_artist):
        f = parse_filter("id != 1")
        artist1 = make_artist(id=1)
        artist2 = make_artist(id=2)
        assert f(artist1) == artist1  # id == 1, so != is false, keep
        assert f(artist2) is None  # id != 1, drop

    def test_greater_than(self, make_artist):
        f = parse_filter("id > 5")
        artist = make_artist(id=10)
        assert f(artist) is None

    def test_string_equality(self, make_artist):
        f = parse_filter('name == "Test"')
        artist = make_artist(name="Test")
        assert f(artist) is None

    def test_null_comparison(self, make_artist):
        f = parse_filter("profile == null")
        artist = make_artist(profile=None)
        assert f(artist) is None

    def test_and_expression(self, make_artist):
        f = parse_filter("id > 0 and id < 10")
        artist = make_artist(id=5)
        assert f(artist) is None

    def test_or_expression(self, make_artist):
        f = parse_filter("id == 1 or id == 2")
        artist1 = make_artist(id=1)
        artist2 = make_artist(id=2)
        artist3 = make_artist(id=3)
        assert f(artist1) is None
        assert f(artist2) is None
        assert f(artist3) == artist3


class TestUnsetFields:
    def test_unset_single_field(self, make_artist):
        f = UnsetFields(["name"])
        artist = make_artist(name="Test", profile="Bio")
        result = f(artist)
        assert result.name is None
        assert result.profile == "Bio"

    def test_unset_multiple_fields(self, make_artist):
        f = UnsetFields(["name", "profile"])
        artist = make_artist(name="Test", profile="Bio")
        result = f(artist)
        assert result.name is None
        assert result.profile is None

    def test_unset_nonexistent_field(self, make_artist):
        f = UnsetFields(["nonexistent"])
        artist = make_artist()
        result = f(artist)
        assert result == artist


class TestFilterChain:
    def test_chain_applies_filters_in_order(self, make_artist):
        f1 = UnsetFields(["profile"])
        f2 = parse_filter("name == null")
        chain = FilterChain([f1, f2])

        artist = make_artist(name=None, profile="Bio")
        result = chain(artist)
        assert result is None  # Dropped by f2

    def test_chain_stops_on_drop(self, make_artist):
        f1 = parse_filter("id == 1")
        f2 = UnsetFields(["name"])
        chain = FilterChain([f1, f2])

        artist = make_artist(id=1, name="Test")
        result = chain(artist)
        assert result is None  # Dropped by f1, f2 never runs
