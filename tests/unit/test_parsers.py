from lxml import etree

from dgkit.models import Artist, ArtistRef, Label
from dgkit.parsers import ArtistParser, LabelParser


class TestArtistParser:
    def test_parse_artist_with_all_fields(self):
        xml = """
        <artist>
            <id>1</id>
            <name>Test Artist</name>
            <realname>Real Name</realname>
            <profile>Test profile.</profile>
            <data_quality>Needs Vote</data_quality>
            <urls>
                <url>https://example.com</url>
            </urls>
            <namevariations>
                <name>Test</name>
                <name>T. Artist</name>
            </namevariations>
            <aliases>
                <name id="100">Alias One</name>
                <name id="200">Alias Two</name>
            </aliases>
            <members>
                <name id="10">Member One</name>
            </members>
            <groups>
                <name id="50">Group One</name>
            </groups>
        </artist>
        """
        elem = etree.fromstring(xml)
        parser = ArtistParser()
        records = list(parser.parse(elem))

        assert len(records) == 1
        artist = records[0]
        assert isinstance(artist, Artist)
        assert artist.id == 1
        assert artist.name == "Test Artist"
        assert artist.real_name == "Real Name"
        assert artist.profile == "Test profile."
        assert artist.data_quality == "Needs Vote"
        assert artist.urls == ["https://example.com"]
        assert artist.name_variations == ["Test", "T. Artist"]
        assert artist.aliases == [ArtistRef(100, "Alias One"), ArtistRef(200, "Alias Two")]
        assert artist.members == [ArtistRef(10, "Member One")]
        assert artist.groups == [ArtistRef(50, "Group One")]

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
        assert artist.data_quality is None
        assert artist.urls == []
        assert artist.name_variations == []
        assert artist.aliases == []
        assert artist.members == []
        assert artist.groups == []


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
