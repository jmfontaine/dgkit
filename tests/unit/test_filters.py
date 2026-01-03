import pytest

from dgkit.filters import UnsetFields, FilterChain, parse_filter
from dgkit.models import Artist


@pytest.fixture
def make_artist():
    """Factory for creating Artist instances with defaults."""

    def _make(
        id: int = 1,
        name: str | None = "Test",
        real_name: str | None = None,
        profile: str | None = None,
        data_quality=None,
        **kwargs,
    ) -> Artist:
        return Artist(
            id=id,
            data_quality=data_quality,
            name=name,
            profile=profile,
            real_name=real_name,
            **kwargs,
        )

    return _make


class TestExpressionFilter:
    def test_equality_match_drops_record(self, make_artist):
        f = parse_filter("id == 1")
        artist = make_artist(id=1)
        assert f(artist) is None

    def test_less_than(self, make_artist):
        f = parse_filter("id < 5")
        artist = make_artist(id=3)
        assert f(artist) is None

    def test_greater_or_equal(self, make_artist):
        f = parse_filter("id >= 5")
        artist1 = make_artist(id=5)
        artist2 = make_artist(id=6)
        artist3 = make_artist(id=4)
        assert f(artist1) is None  # 5 >= 5
        assert f(artist2) is None  # 6 >= 5
        assert f(artist3) == artist3  # 4 >= 5 is false

    def test_less_or_equal(self, make_artist):
        f = parse_filter("id <= 5")
        artist1 = make_artist(id=5)
        artist2 = make_artist(id=4)
        artist3 = make_artist(id=6)
        assert f(artist1) is None  # 5 <= 5
        assert f(artist2) is None  # 4 <= 5
        assert f(artist3) == artist3  # 6 <= 5 is false

    def test_null_not_equal_to_value(self, make_artist):
        """None != 5 should be true (drop record)."""
        f = parse_filter("profile != null")
        artist = make_artist(profile=None)
        assert f(artist) == artist  # None == null, so != is false, keep

    def test_value_not_equal_to_null(self, make_artist):
        """5 != null should be true (drop record)."""
        f = parse_filter("id != null")
        artist = make_artist(id=5)
        assert f(artist) is None  # 5 != null is true, drop

    def test_null_equal_null(self, make_artist):
        """null == null should be true."""
        f = parse_filter("profile == null")
        artist = make_artist(profile=None)
        assert f(artist) is None

    def test_type_coercion_string_comparison(self, make_artist):
        """Non-string field compared to string value should coerce."""
        f = parse_filter('id == "1"')
        artist = make_artist(id=1)
        assert f(artist) is None  # 1 coerced to "1"

    def test_single_quoted_string(self, make_artist):
        """Single-quoted strings should work."""
        f = parse_filter("name == 'Test'")
        artist = make_artist(name="Test")
        assert f(artist) is None

    def test_boolean_true(self, make_artist):
        """Boolean true value parsing."""
        # Use a dict-based record to test boolean
        f = parse_filter("active == true")
        record = {"active": True}
        # This tests the dict branch
        assert f(record) is None

    def test_boolean_false(self, make_artist):
        """Boolean false value parsing."""
        f = parse_filter("active == false")
        record = {"active": False}
        assert f(record) is None

    def test_dict_field_access(self):
        """Filter should work with dict records."""
        f = parse_filter("id == 1")
        record = {"id": 1, "name": "Test"}
        assert f(record) is None

    def test_dict_nested_field_missing(self):
        """Missing nested field in dict returns None."""
        f = parse_filter("nested.field == 1")
        record = {"id": 1}
        assert f(record) == record  # nested.field is None, != 1

    def test_incompatible_comparison_returns_false(self, make_artist):
        """Comparing incompatible types (that raise TypeError) returns False."""
        f = parse_filter("name > 5")
        artist = make_artist(name="Test")
        # "Test" > 5 raises TypeError, comparison returns False, record kept
        assert f(artist) == artist

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
    def test_unset_empty_list_returns_record(self, make_artist):
        """Empty fields list returns record unchanged."""
        f = UnsetFields([])
        artist = make_artist(name="Test", profile="Bio")
        result = f(artist)
        assert result == artist

    def test_unset_single_field(self, make_artist):
        f = UnsetFields(["name"])
        artist = make_artist(name="Test", profile="Bio")
        result = f(artist)
        assert isinstance(result, Artist)
        assert result.name is None
        assert result.profile == "Bio"

    def test_unset_multiple_fields(self, make_artist):
        f = UnsetFields(["name", "profile"])
        artist = make_artist(name="Test", profile="Bio")
        result = f(artist)
        assert isinstance(result, Artist)
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
