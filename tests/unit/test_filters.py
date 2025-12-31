from dgkit.filters import ExpressionFilter, UnsetFields, FilterChain, parse_filter
from dgkit.models import Artist


class TestExpressionFilter:
    def test_equality_match_drops_record(self):
        f = parse_filter('id == 1')
        artist = Artist(id=1, name="Test", profile=None, real_name=None)
        assert f(artist) is None

    def test_equality_no_match_keeps_record(self):
        f = parse_filter('id == 99')
        artist = Artist(id=1, name="Test", profile=None, real_name=None)
        assert f(artist) == artist

    def test_not_equal(self):
        f = parse_filter('id != 1')
        artist1 = Artist(id=1, name="Test", profile=None, real_name=None)
        artist2 = Artist(id=2, name="Test", profile=None, real_name=None)
        assert f(artist1) == artist1  # id == 1, so != is false, keep
        assert f(artist2) is None  # id != 1, drop

    def test_greater_than(self):
        f = parse_filter('id > 5')
        artist = Artist(id=10, name="Test", profile=None, real_name=None)
        assert f(artist) is None

    def test_string_equality(self):
        f = parse_filter('name == "Test"')
        artist = Artist(id=1, name="Test", profile=None, real_name=None)
        assert f(artist) is None

    def test_null_comparison(self):
        f = parse_filter('profile == null')
        artist = Artist(id=1, name="Test", profile=None, real_name=None)
        assert f(artist) is None

    def test_and_expression(self):
        f = parse_filter('id > 0 and id < 10')
        artist = Artist(id=5, name="Test", profile=None, real_name=None)
        assert f(artist) is None

    def test_or_expression(self):
        f = parse_filter('id == 1 or id == 2')
        artist1 = Artist(id=1, name="Test", profile=None, real_name=None)
        artist2 = Artist(id=2, name="Test", profile=None, real_name=None)
        artist3 = Artist(id=3, name="Test", profile=None, real_name=None)
        assert f(artist1) is None
        assert f(artist2) is None
        assert f(artist3) == artist3


class TestUnsetFields:
    def test_unset_single_field(self):
        f = UnsetFields(["name"])
        artist = Artist(id=1, name="Test", profile="Bio", real_name=None)
        result = f(artist)
        assert result.name is None
        assert result.profile == "Bio"

    def test_unset_multiple_fields(self):
        f = UnsetFields(["name", "profile"])
        artist = Artist(id=1, name="Test", profile="Bio", real_name=None)
        result = f(artist)
        assert result.name is None
        assert result.profile is None

    def test_unset_nonexistent_field(self):
        f = UnsetFields(["nonexistent"])
        artist = Artist(id=1, name="Test", profile=None, real_name=None)
        result = f(artist)
        assert result == artist


class TestFilterChain:
    def test_chain_applies_filters_in_order(self):
        f1 = UnsetFields(["profile"])
        f2 = parse_filter('name == null')
        chain = FilterChain([f1, f2])

        artist = Artist(id=1, name=None, profile="Bio", real_name=None)
        result = chain(artist)
        assert result is None  # Dropped by f2

    def test_chain_stops_on_drop(self):
        f1 = parse_filter('id == 1')
        f2 = UnsetFields(["name"])
        chain = FilterChain([f1, f2])

        artist = Artist(id=1, name="Test", profile=None, real_name=None)
        result = chain(artist)
        assert result is None  # Dropped by f1, f2 never runs
