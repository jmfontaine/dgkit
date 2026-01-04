from pathlib import Path
from typing import cast

import pytest
from lxml import etree

from dgkit.models import (
    Artist,
    ArtistRef,
    Company,
    CreditArtist,
    ExtraArtist,
    Format,
    Identifier,
    Label,
    LabelRef,
    MasterRelease,
    Release,
    ReleaseLabel,
    Series,
    SubTrack,
    Track,
    Video,
)
from dgkit.parsers import (
    ArtistParser,
    LabelParser,
    MasterReleaseParser,
    ReleaseParser,
    get_parser,
)
from dgkit.types import Element


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
        records = list(parser.parse(cast(Element, elem)))

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
        assert artist.aliases == [
            ArtistRef(100, "Alias One"),
            ArtistRef(200, "Alias Two"),
        ]
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
        records = list(parser.parse(cast(Element, elem)))

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
    def test_parse_label_with_all_fields(self):
        xml = """
        <label>
            <id>1</id>
            <name>Test Label</name>
            <contactinfo>123 Main St</contactinfo>
            <profile>A great label.</profile>
            <data_quality>Correct</data_quality>
            <urls>
                <url>https://example.com</url>
            </urls>
            <sublabels>
                <label id="100">Sub Label One</label>
                <label id="200">Sub Label Two</label>
            </sublabels>
            <parentLabel id="50">Parent Label</parentLabel>
        </label>
        """
        elem = etree.fromstring(xml)
        parser = LabelParser()
        records = list(parser.parse(cast(Element, elem)))

        assert len(records) == 1
        label = records[0]
        assert isinstance(label, Label)
        assert label.id == 1
        assert label.name == "Test Label"
        assert label.contact_info == "123 Main St"
        assert label.profile == "A great label."
        assert label.data_quality == "Correct"
        assert label.urls == ["https://example.com"]
        assert label.sub_labels == [
            LabelRef(100, "Sub Label One"),
            LabelRef(200, "Sub Label Two"),
        ]
        assert label.parent_label == LabelRef(50, "Parent Label")

    def test_parse_label_with_empty_fields(self):
        xml = """
        <label>
            <id>2</id>
            <name>Minimal Label</name>
        </label>
        """
        elem = etree.fromstring(xml)
        parser = LabelParser()
        records = list(parser.parse(cast(Element, elem)))

        assert len(records) == 1
        label = records[0]
        assert label.id == 2
        assert label.name == "Minimal Label"
        assert label.contact_info is None
        assert label.profile is None
        assert label.data_quality is None
        assert label.urls == []
        assert label.sub_labels == []
        assert label.parent_label is None


class TestMasterReleaseParser:
    def test_parse_master_with_all_fields(self):
        xml = """
        <master id="123">
            <main_release>456</main_release>
            <artists>
                <artist>
                    <id>1</id>
                    <name>Artist One</name>
                    <anv/>
                    <join>,</join>
                </artist>
                <artist>
                    <id>2</id>
                    <name>Artist Two</name>
                    <anv/>
                    <join/>
                </artist>
            </artists>
            <genres>
                <genre>Electronic</genre>
                <genre>Rock</genre>
            </genres>
            <styles>
                <style>Ambient</style>
                <style>Techno</style>
            </styles>
            <year>1999</year>
            <title>Test Album</title>
            <data_quality>Correct</data_quality>
            <videos>
                <video src="https://youtube.com/watch?v=abc" duration="300" embed="true">
                    <title>Music Video</title>
                    <description>Official video</description>
                </video>
            </videos>
        </master>
        """
        elem = etree.fromstring(xml)
        parser = MasterReleaseParser()
        records = list(parser.parse(cast(Element, elem)))

        assert len(records) == 1
        master = records[0]
        assert isinstance(master, MasterRelease)
        assert master.id == 123
        assert master.title == "Test Album"
        assert master.main_release == 456
        assert master.year == 1999
        assert master.notes is None
        assert master.data_quality == "Correct"
        assert master.artists == [
            CreditArtist(id=1, artist_name_variation=None, join=",", name="Artist One"),
            CreditArtist(
                id=2, artist_name_variation=None, join=None, name="Artist Two"
            ),
        ]
        assert master.genres == ["Electronic", "Rock"]
        assert master.styles == ["Ambient", "Techno"]
        assert master.videos == [
            Video(
                description="Official video",
                duration=300,
                embed=True,
                src="https://youtube.com/watch?v=abc",
                title="Music Video",
            )
        ]

    def test_parse_master_with_empty_fields(self):
        xml = """
        <master id="789">
            <title>Minimal Album</title>
        </master>
        """
        elem = etree.fromstring(xml)
        parser = MasterReleaseParser()
        records = list(parser.parse(cast(Element, elem)))

        assert len(records) == 1
        master = records[0]
        assert master.id == 789
        assert master.title == "Minimal Album"
        assert master.main_release is None
        assert master.year is None
        assert master.notes is None
        assert master.data_quality is None
        assert master.artists == []
        assert master.genres == []
        assert master.styles == []
        assert master.videos == []


class TestReleaseParser:
    def test_parse_release_with_all_fields(self):
        xml = """
        <release id="1" status="Accepted">
            <artists>
                <artist>
                    <id>1</id>
                    <name>The Persuader</name>
                    <anv/>
                    <join/>
                </artist>
            </artists>
            <title>Stockholm</title>
            <labels>
                <label name="Svek" catno="SK032" id="5" />
            </labels>
            <extraartists>
                <artist>
                    <id>239</id>
                    <name>Jesper Dahlbäck</name>
                    <anv/>
                    <role>Written-By</role>
                    <tracks/>
                </artist>
            </extraartists>
            <formats>
                <format name="Vinyl" qty="2" text="">
                    <descriptions>
                        <description>12"</description>
                    </descriptions>
                </format>
            </formats>
            <genres>
                <genre>Electronic</genre>
            </genres>
            <styles>
                <style>Deep House</style>
            </styles>
            <country>Sweden</country>
            <released>1999-03-00</released>
            <notes>Test notes.</notes>
            <data_quality>Needs Vote</data_quality>
            <master_id is_main_release="true">1660109</master_id>
            <tracklist>
                <track>
                    <position>A</position>
                    <title>Östermalm</title>
                    <duration>4:45</duration>
                </track>
            </tracklist>
            <identifiers>
                <identifier type="Matrix / Runout" description="A-side" value="SK 032 A1" />
            </identifiers>
            <videos>
                <video src="https://youtube.com/watch?v=abc" duration="325" embed="true">
                    <title>Test Video</title>
                    <description>Description</description>
                </video>
            </videos>
            <companies>
                <company>
                    <id>271046</id>
                    <name>The Globe Studios</name>
                    <catno/>
                    <entity_type>23</entity_type>
                    <entity_type_name>Recorded At</entity_type_name>
                    <resource_url>https://api.discogs.com/labels/271046</resource_url>
                </company>
            </companies>
            <series>
                <series name="Test Series" catno="Vol. 1" id="12345" />
            </series>
        </release>
        """
        elem = etree.fromstring(xml)
        parser = ReleaseParser()
        records = list(parser.parse(cast(Element, elem)))

        assert len(records) == 1
        release = records[0]
        assert isinstance(release, Release)
        assert release.id == 1
        assert release.status == "Accepted"
        assert release.title == "Stockholm"
        assert release.country == "Sweden"
        assert release.released == "1999-03-00"
        assert release.notes == "Test notes."
        assert release.data_quality == "Needs Vote"
        assert release.master_id == 1660109
        assert release.is_main_release is True
        assert release.artists == [
            CreditArtist(
                id=1, artist_name_variation=None, join=None, name="The Persuader"
            )
        ]
        assert release.labels == [
            ReleaseLabel(id=5, catalog_number="SK032", name="Svek")
        ]
        assert release.extra_artists == [
            ExtraArtist(
                id=239,
                artist_name_variation=None,
                name="Jesper Dahlbäck",
                role="Written-By",
                tracks=None,
            )
        ]
        assert release.formats == [
            Format(name="Vinyl", quantity="2", text="", descriptions=['12"'])
        ]
        assert release.genres == ["Electronic"]
        assert release.styles == ["Deep House"]
        assert release.tracklist == [
            Track(
                duration="4:45",
                position="A",
                title="Östermalm",
                artists=[],
                extra_artists=[],
                sub_tracks=[],
            )
        ]
        assert release.identifiers == [
            Identifier(
                description="A-side",
                type="Matrix / Runout",
                value="SK 032 A1",
            )
        ]
        assert release.videos == [
            Video(
                description="Description",
                duration=325,
                embed=True,
                src="https://youtube.com/watch?v=abc",
                title="Test Video",
            )
        ]
        assert release.companies == [
            Company(
                id=271046,
                catalog_number=None,
                entity_type=23,
                entity_type_name="Recorded At",
                name="The Globe Studios",
            )
        ]
        assert release.series == [
            Series(id=12345, catalog_number="Vol. 1", name="Test Series")
        ]

    def test_parse_release_with_empty_fields(self):
        xml = """
        <release id="999" status="Draft">
            <title>Minimal Release</title>
        </release>
        """
        elem = etree.fromstring(xml)
        parser = ReleaseParser()
        records = list(parser.parse(cast(Element, elem)))

        assert len(records) == 1
        release = records[0]
        assert release.id == 999
        assert release.status == "Draft"
        assert release.title == "Minimal Release"
        assert release.country is None
        assert release.released is None
        assert release.notes is None
        assert release.data_quality is None
        assert release.master_id is None
        assert release.is_main_release is None
        assert release.artists == []
        assert release.labels == []
        assert release.extra_artists == []
        assert release.formats == []
        assert release.genres == []
        assert release.styles == []
        assert release.tracklist == []
        assert release.identifiers == []
        assert release.videos == []
        assert release.companies == []
        assert release.series == []

    def test_parse_release_with_track_artists(self):
        xml = """
        <release id="3" status="Accepted">
            <title>Compilation</title>
            <tracklist>
                <track>
                    <position>1</position>
                    <title>Track One</title>
                    <duration>5:00</duration>
                    <artists>
                        <artist>
                            <id>100</id>
                            <name>Track Artist</name>
                            <anv>T.A.</anv>
                            <join/>
                        </artist>
                    </artists>
                    <extraartists>
                        <artist>
                            <id>200</id>
                            <name>Remixer</name>
                            <anv/>
                            <role>Remix</role>
                            <tracks/>
                        </artist>
                    </extraartists>
                </track>
            </tracklist>
        </release>
        """
        elem = etree.fromstring(xml)
        parser = ReleaseParser()
        records = list(parser.parse(cast(Element, elem)))

        assert len(records) == 1
        release = records[0]
        assert len(release.tracklist) == 1
        track = release.tracklist[0]
        assert track.position == "1"
        assert track.title == "Track One"
        assert track.duration == "5:00"
        assert track.artists == [
            CreditArtist(
                id=100, artist_name_variation="T.A.", join=None, name="Track Artist"
            )
        ]
        assert track.extra_artists == [
            ExtraArtist(
                id=200,
                artist_name_variation=None,
                name="Remixer",
                role="Remix",
                tracks=None,
            )
        ]
        assert track.sub_tracks == []

    def test_parse_release_with_sub_tracks(self):
        """Test parsing tracks with sub_tracks (index tracks)."""
        xml = """
        <release id="4" status="Accepted">
            <title>Album with Index</title>
            <tracklist>
                <track>
                    <position>1</position>
                    <title>Main Track</title>
                    <duration>10:00</duration>
                    <sub_tracks>
                        <track>
                            <position>1a</position>
                            <title>Sub Track A</title>
                            <duration>5:00</duration>
                            <artists>
                                <artist>
                                    <id>100</id>
                                    <name>Sub Artist</name>
                                </artist>
                            </artists>
                            <extraartists>
                                <artist>
                                    <id>200</id>
                                    <name>Producer</name>
                                    <role>Producer</role>
                                </artist>
                            </extraartists>
                        </track>
                        <track>
                            <position>1b</position>
                            <title>Sub Track B</title>
                            <duration>5:00</duration>
                        </track>
                    </sub_tracks>
                </track>
            </tracklist>
        </release>
        """
        elem = etree.fromstring(xml)
        parser = ReleaseParser()
        records = list(parser.parse(cast(Element, elem)))

        assert len(records) == 1
        release = records[0]
        assert len(release.tracklist) == 1
        track = release.tracklist[0]
        assert track.title == "Main Track"
        assert len(track.sub_tracks) == 2
        assert track.sub_tracks[0] == SubTrack(
            duration="5:00",
            position="1a",
            title="Sub Track A",
            artists=[
                CreditArtist(
                    id=100, artist_name_variation=None, join=None, name="Sub Artist"
                )
            ],
            extra_artists=[
                ExtraArtist(
                    id=200,
                    artist_name_variation=None,
                    name="Producer",
                    role="Producer",
                    tracks=None,
                )
            ],
        )
        assert track.sub_tracks[1].position == "1b"
        assert track.sub_tracks[1].title == "Sub Track B"


class TestArtistParserMissingId:
    def test_parse_artist_missing_id_raises(self):
        """Artist without id should raise ValueError."""
        xml = """
        <artist>
            <name>No ID Artist</name>
        </artist>
        """
        elem = etree.fromstring(xml)
        parser = ArtistParser()
        with pytest.raises(ValueError, match="Required field 'id' is missing"):
            list(parser.parse(cast(Element, elem)))

    def test_parse_artist_empty_id_raises(self):
        """Artist with empty id should raise ValueError."""
        xml = """
        <artist>
            <id></id>
            <name>Empty ID Artist</name>
        </artist>
        """
        elem = etree.fromstring(xml)
        parser = ArtistParser()
        with pytest.raises(ValueError, match="Required field 'id' is missing"):
            list(parser.parse(cast(Element, elem)))


class TestGetParser:
    def test_get_parser_from_filename(self):
        """Parser detected from filename pattern."""
        parser = get_parser(Path("discogs_20250101_artists.xml.gz"))
        assert isinstance(parser, ArtistParser)

    def test_get_parser_explicit_entity_type(self):
        """Explicit entity type overrides filename."""
        parser = get_parser(Path("unknown_file.xml.gz"), entity_type="labels")
        assert isinstance(parser, LabelParser)

    def test_get_parser_unknown_filename_raises(self):
        """Unknown filename without entity type raises ValueError."""
        with pytest.raises(ValueError, match="Cannot detect entity type"):
            get_parser(Path("unknown_file.xml.gz"))

    def test_get_parser_unsupported_entity_raises(self):
        """Unsupported entity type raises NotImplementedError."""
        with pytest.raises(
            NotImplementedError, match="Parser for unknown not implemented"
        ):
            get_parser(Path("file.xml.gz"), entity_type="unknown")


class TestLabelParserEdgeCases:
    def test_parse_label_with_id_attribute(self):
        """Label id can be in attribute (older format)."""
        xml = """
        <label id="123">
            <name>Attr ID Label</name>
        </label>
        """
        elem = etree.fromstring(xml)
        parser = LabelParser()
        records = list(parser.parse(cast(Element, elem)))
        assert records[0].id == 123

    def test_parse_label_with_text_name(self):
        """Label name can be text content of element."""
        xml = """
        <label id="456">Test Label Name</label>
        """
        elem = etree.fromstring(xml)
        parser = LabelParser()
        records = list(parser.parse(cast(Element, elem)))
        assert records[0].name == "Test Label Name"


class TestParserSkipsNonMatchingTags:
    def test_credit_artists_skips_non_artist_tags(self):
        """Non-artist tags inside artists element should be skipped."""
        xml = """
        <release id="5" status="Accepted">
            <title>Test</title>
            <artists>
                <comment>This is not an artist</comment>
                <artist>
                    <id>1</id>
                    <name>Real Artist</name>
                </artist>
                <notes>Another non-artist</notes>
            </artists>
        </release>
        """
        elem = etree.fromstring(xml)
        parser = ReleaseParser()
        records = list(parser.parse(cast(Element, elem)))
        assert len(records[0].artists) == 1
        assert records[0].artists[0].name == "Real Artist"

    def test_extra_artists_skips_non_artist_tags(self):
        """Non-artist tags inside extraartists should be skipped."""
        xml = """
        <release id="6" status="Accepted">
            <title>Test</title>
            <extraartists>
                <info>Not an artist</info>
                <artist>
                    <name>Producer</name>
                    <role>Producer</role>
                </artist>
            </extraartists>
        </release>
        """
        elem = etree.fromstring(xml)
        parser = ReleaseParser()
        records = list(parser.parse(cast(Element, elem)))
        assert len(records[0].extra_artists) == 1
        assert records[0].extra_artists[0].name == "Producer"

    def test_tracks_skips_non_track_tags(self):
        """Non-track tags inside tracklist should be skipped."""
        xml = """
        <release id="7" status="Accepted">
            <title>Test</title>
            <tracklist>
                <info>Not a track</info>
                <track>
                    <position>1</position>
                    <title>Real Track</title>
                </track>
            </tracklist>
        </release>
        """
        elem = etree.fromstring(xml)
        parser = ReleaseParser()
        records = list(parser.parse(cast(Element, elem)))
        assert len(records[0].tracklist) == 1
        assert records[0].tracklist[0].title == "Real Track"

    def test_companies_skips_non_company_tags(self):
        """Non-company tags inside companies should be skipped."""
        xml = """
        <release id="8" status="Accepted">
            <title>Test</title>
            <companies>
                <note>Not a company</note>
                <company>
                    <id>1</id>
                    <name>Real Company</name>
                </company>
            </companies>
        </release>
        """
        elem = etree.fromstring(xml)
        parser = ReleaseParser()
        records = list(parser.parse(cast(Element, elem)))
        assert len(records[0].companies) == 1
        assert records[0].companies[0].name == "Real Company"

    def test_videos_skips_non_video_tags(self):
        """Non-video tags inside videos should be skipped."""
        xml = """
        <master id="9">
            <title>Test</title>
            <videos>
                <info>Not a video</info>
                <video src="http://example.com" duration="100" embed="false">
                    <title>Real Video</title>
                </video>
            </videos>
        </master>
        """
        elem = etree.fromstring(xml)
        parser = MasterReleaseParser()
        records = list(parser.parse(cast(Element, elem)))
        assert len(records[0].videos) == 1
        assert records[0].videos[0].title == "Real Video"
