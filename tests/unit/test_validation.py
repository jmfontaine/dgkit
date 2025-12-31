from lxml import etree

from dgkit.validation import TrackingElement, UnhandledElementError


class TestTrackingElement:
    def test_findtext_marks_tag_as_accessed(self):
        xml = "<artist><id>1</id><name>Test</name></artist>"
        elem = etree.fromstring(xml)
        wrapper = TrackingElement(elem)

        wrapper.findtext("id")
        wrapper.findtext("name")

        assert wrapper.get_unaccessed() == set()

    def test_unaccessed_child_detected(self):
        xml = "<artist><id>1</id><name>Test</name><extra>data</extra></artist>"
        elem = etree.fromstring(xml)
        wrapper = TrackingElement(elem)

        wrapper.findtext("id")
        wrapper.findtext("name")

        assert wrapper.get_unaccessed() == {"extra"}

    def test_unaccessed_attribute_detected(self):
        xml = '<artist id="1"><name>Test</name></artist>'
        elem = etree.fromstring(xml)
        wrapper = TrackingElement(elem)

        wrapper.findtext("name")

        assert wrapper.get_unaccessed() == {"@id"}

    def test_get_marks_attribute_as_accessed(self):
        xml = '<artist id="1"><name>Test</name></artist>'
        elem = etree.fromstring(xml)
        wrapper = TrackingElement(elem)

        wrapper.get("id")
        wrapper.findtext("name")

        assert wrapper.get_unaccessed() == set()

    def test_find_returns_wrapped_child(self):
        xml = "<artist><aliases><name id='100'>Alias</name></aliases></artist>"
        elem = etree.fromstring(xml)
        wrapper = TrackingElement(elem)

        aliases = wrapper.find("aliases")
        assert aliases is not None
        assert isinstance(aliases, TrackingElement)

    def test_nested_unaccessed_detected(self):
        xml = "<artist><id>1</id><aliases><name id='100'>Alias</name><extra>data</extra></aliases></artist>"
        elem = etree.fromstring(xml)
        wrapper = TrackingElement(elem)

        wrapper.findtext("id")
        aliases = wrapper.find("aliases")
        for name in aliases.findall("name"):
            name.get("id")
            _ = name.text

        assert wrapper.get_unaccessed() == {"aliases/extra"}

    def test_findall_returns_wrapped_children(self):
        xml = "<artist><urls><url>http://a.com</url><url>http://b.com</url></urls></artist>"
        elem = etree.fromstring(xml)
        wrapper = TrackingElement(elem)

        urls = wrapper.find("urls")
        url_list = urls.findall("url")

        assert len(url_list) == 2
        assert all(isinstance(u, TrackingElement) for u in url_list)

    def test_text_property_marks_as_accessed(self):
        xml = "<name>Test Artist</name>"
        elem = etree.fromstring(xml)
        wrapper = TrackingElement(elem)

        _ = wrapper.text

        assert wrapper.get_unaccessed() == set()

    def test_iteration_wraps_children(self):
        xml = "<artist><id>1</id><name>Test</name></artist>"
        elem = etree.fromstring(xml)
        wrapper = TrackingElement(elem)

        # Iterate and access text in same loop
        children = []
        for child in wrapper:
            children.append(child)
            _ = child.text

        assert len(children) == 2
        assert all(isinstance(c, TrackingElement) for c in children)
        assert wrapper.get_unaccessed() == set()


class TestUnhandledElementError:
    def test_error_message(self):
        error = UnhandledElementError("123", "artist", {"extra", "@unknown"})
        assert "artist" in str(error)
        assert "123" in str(error)
        assert "@unknown" in str(error)
        assert "extra" in str(error)
