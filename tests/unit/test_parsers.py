from io import BytesIO

from lxml import etree

from dgkit.models import Artist, ArtistAlias, Label
from dgkit.parsers import ArtistParser, LabelParser


class TestArtistParser:
    def test_parse_artist_with_all_fields(self):
        xml = """
        <artist>
            <id>1</id>
            <name>Test Artist</name>
            <realname>Real Name</realname>
            <profile>Test profile.</profile>
            <aliases>
                <name id="100">Alias One</name>
                <name id="200">Alias Two</name>
            </aliases>
            <urls>
                <url>https://example.com</url>
            </urls>
        </artist>
        """
        elem = etree.fromstring(xml)
        parser = ArtistParser()
        records = list(parser.parse(elem))

        # First record should be Artist
        artist = records[0]
        assert isinstance(artist, Artist)
        assert artist.id == 1
        assert artist.name == "Test Artist"
        assert artist.real_name == "Real Name"
        assert artist.profile == "Test profile."
        assert artist.urls == ["https://example.com"]

        # Following records should be ArtistAlias
        aliases = [r for r in records if isinstance(r, ArtistAlias)]
        assert len(aliases) == 2
        assert aliases[0] == ArtistAlias(artist_id=1, alias_id=100)
        assert aliases[1] == ArtistAlias(artist_id=1, alias_id=200)

    def test_parse_artist_with_empty_fields(self):
        xml = """
        <artist>
            <id>2</id>
            <name>Minimal Artist</name>
        </artist>
        """
        elem = etree.fromstring(xml)
        parser = ArtistParser()
        records = list(parser.parse(elem))

        assert len(records) == 1
        artist = records[0]
        assert artist.id == 2
        assert artist.name == "Minimal Artist"
        assert artist.real_name is None
        assert artist.profile is None
        assert artist.urls == []


class TestLabelParser:
    def test_parse_label(self):
        xml = """
        <label>
            <id>1</id>
            <name>Test Label</name>
        </label>
        """
        elem = etree.fromstring(xml)
        parser = LabelParser()
        records = list(parser.parse(elem))

        assert len(records) == 1
        label = records[0]
        assert isinstance(label, Label)
        assert label.id == 1
        assert label.name == "Test Label"
