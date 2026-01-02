"""XML element validation for detecting unhandled data."""

from typing import Iterator

from lxml import etree


class TrackingElement:
    """Wrapper that tracks which parts of an XML element are accessed.

    Use this to detect unhandled tags or attributes in XML elements,
    ensuring parsers extract all available data.
    """

    def __init__(self, elem: etree._Element, path: str = "") -> None:
        self._elem = elem
        self._path = path
        self._accessed_tags: set[str] = set()
        self._accessed_attrs: set[str] = set()
        self._accessed_text: bool = False
        self._children: dict[str, list["TrackingElement"]] = {}

    @property
    def tag(self) -> str:
        return self._elem.tag

    @property
    def text(self) -> str | None:
        self._accessed_text = True
        return self._elem.text

    def get(self, attr: str, default: str | None = None) -> str | None:
        """Get an attribute value."""
        self._accessed_attrs.add(attr)
        return self._elem.get(attr, default)

    def findtext(self, tag: str, default: str | None = None) -> str | None:
        """Find text content of a child element."""
        self._accessed_tags.add(tag)
        return self._elem.findtext(tag, default)

    def find(self, tag: str) -> "TrackingElement | None":
        """Find a child element."""
        self._accessed_tags.add(tag)
        child = self._elem.find(tag)
        if child is None:
            return None
        if tag not in self._children:
            self._children[tag] = [TrackingElement(child, f"{self._path}/{tag}")]
        return self._children[tag][0]

    def findall(self, tag: str) -> list["TrackingElement"]:
        """Find all matching child elements."""
        self._accessed_tags.add(tag)
        if tag not in self._children:
            self._children[tag] = [
                TrackingElement(child, f"{self._path}/{tag}")
                for child in self._elem.findall(tag)
            ]
        return self._children[tag]

    def get_unaccessed(self) -> set[str]:
        """Return paths of tags/attrs that exist but weren't accessed."""
        unaccessed: set[str] = set()

        # Check child tags
        actual_children = {child.tag for child in self._elem}
        for tag in actual_children - self._accessed_tags:
            unaccessed.add(tag)

        # Check attributes
        for attr in self._elem.attrib:
            if attr not in self._accessed_attrs:
                unaccessed.add(f"@{attr}")

        # Check text content (only if element has meaningful text and no children)
        if (
            not self._accessed_text
            and self._elem.text
            and self._elem.text.strip()
            and len(self._elem) == 0  # No children
        ):
            unaccessed.add("#text")

        # Recursively check accessed children
        for tag, wrappers in self._children.items():
            for wrapper in wrappers:
                for path in wrapper.get_unaccessed():
                    unaccessed.add(f"{tag}/{path}")

        return unaccessed

    def __iter__(self) -> Iterator["TrackingElement"]:
        """Iterate over child elements (wrapped)."""
        for child in self._elem:
            tag = child.tag
            self._accessed_tags.add(tag)
            if tag not in self._children:
                self._children[tag] = []
            wrapper = TrackingElement(child, f"{self._path}/{tag}")
            self._children[tag].append(wrapper)
            yield wrapper


class UnhandledElementError(Exception):
    """Raised when unhandled elements are detected in strict mode."""

    def __init__(self, element_id: str, tag: str, unaccessed: set[str]) -> None:
        self.element_id = element_id
        self.tag = tag
        self.unaccessed = unaccessed
        paths = ", ".join(sorted(unaccessed))
        super().__init__(f"Unhandled in {tag} id={element_id}: {paths}")
