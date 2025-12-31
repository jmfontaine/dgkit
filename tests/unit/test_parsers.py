from lxml import etree

from dgkit.models import (
    Artist,
    ArtistRef,
    Company,
    CreditArtist,
    DataQuality,
    ExtraArtist,
    Format,
    Identifier,
    IdentifierType,
    Label,
    LabelRef,
    MasterRelease,
    Release,
    ReleaseLabel,
    ReleaseStatus,
    Series,
    Track,
    Video,
)
from dgkit.parsers import ArtistParser, LabelParser, MasterReleaseParser, ReleaseParser


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
        assert artist.data_quality == DataQuality.NEEDS_VOTE
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
        records = list(parser.parse(elem))

        assert len(records) == 1
        label = records[0]
        assert isinstance(label, Label)
        assert label.id == 1
        assert label.name == "Test Label"
        assert label.contact_info == "123 Main St"
        assert label.profile == "A great label."
        assert label.data_quality == DataQuality.CORRECT
        assert label.urls == ["https://example.com"]
        assert label.sub_labels == [LabelRef(100, "Sub Label One"), LabelRef(200, "Sub Label Two")]
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
        records = list(parser.parse(elem))

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
        records = list(parser.parse(elem))

        assert len(records) == 1
        master = records[0]
        assert isinstance(master, MasterRelease)
        assert master.id == 123
        assert master.title == "Test Album"
        assert master.main_release == 456
        assert master.year == 1999
        assert master.notes is None
        assert master.data_quality == DataQuality.CORRECT
        assert master.artists == [
            CreditArtist(1, "Artist One", "", ","),
            CreditArtist(2, "Artist Two", "", ""),
        ]
        assert master.genres == ["Electronic", "Rock"]
        assert master.styles == ["Ambient", "Techno"]
        assert master.videos == [
            Video("https://youtube.com/watch?v=abc", 300, True, "Music Video", "Official video")
        ]

    def test_parse_master_with_empty_fields(self):
        xml = """
        <master id="789">
            <title>Minimal Album</title>
        </master>
        """
        elem = etree.fromstring(xml)
        parser = MasterReleaseParser()
        records = list(parser.parse(elem))

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
        records = list(parser.parse(elem))

        assert len(records) == 1
        release = records[0]
        assert isinstance(release, Release)
        assert release.id == 1
        assert release.status == ReleaseStatus.ACCEPTED
        assert release.title == "Stockholm"
        assert release.country == "Sweden"
        assert release.released == "1999-03-00"
        assert release.notes == "Test notes."
        assert release.data_quality == DataQuality.NEEDS_VOTE
        assert release.master_id == 1660109
        assert release.is_main_release is True
        assert release.artists == [CreditArtist(1, "The Persuader", "", "")]
        assert release.labels == [ReleaseLabel(5, "Svek", "SK032")]
        assert release.extra_artists == [ExtraArtist(239, "Jesper Dahlbäck", "", "Written-By", "")]
        assert release.formats == [Format("Vinyl", 2, "", ['12"'])]
        assert release.genres == ["Electronic"]
        assert release.styles == ["Deep House"]
        assert release.tracklist == [Track("A", "Östermalm", "4:45", [], [], [])]
        assert release.identifiers == [Identifier(IdentifierType.MATRIX_RUNOUT, "A-side", "SK 032 A1")]
        assert release.videos == [Video("https://youtube.com/watch?v=abc", 325, True, "Test Video", "Description")]
        assert release.companies == [Company(271046, "The Globe Studios", "", 23, "Recorded At")]
        assert release.series == [Series(12345, "Test Series", "Vol. 1")]

    def test_parse_release_with_empty_fields(self):
        xml = """
        <release id="999" status="Draft">
            <title>Minimal Release</title>
        </release>
        """
        elem = etree.fromstring(xml)
        parser = ReleaseParser()
        records = list(parser.parse(elem))

        assert len(records) == 1
        release = records[0]
        assert release.id == 999
        assert release.status == ReleaseStatus.DRAFT
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
        records = list(parser.parse(elem))

        assert len(records) == 1
        release = records[0]
        assert len(release.tracklist) == 1
        track = release.tracklist[0]
        assert track.position == "1"
        assert track.title == "Track One"
        assert track.duration == "5:00"
        assert track.artists == [CreditArtist(100, "Track Artist", "T.A.", "")]
        assert track.extra_artists == [ExtraArtist(200, "Remixer", "", "Remix", "")]
        assert track.sub_tracks == []
