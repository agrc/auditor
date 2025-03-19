import re
from collections.abc import MutableSequence
from dataclasses import dataclass

from markdown_it import MarkdownIt

#: Normal values should be stored as markdown text and have a .as_html() method for returning HTML rendered version.
#: List values should be stored as individual elements to allow for easy inserts/deletes. Their default return should be as markdown text and have a .as_html() method for returning HTML rendered version.

class MarkdownData:
    """"Basic unit of metadata stored as a single string of markdown text.

    Properties:
        value: The markdown text as a single string. Can hold simple single line data or more complex multi-line data with markdown formatting.
    Methods:
        as_html: Returns the value as an HTML string using markdown-it-py, thus returning one or more <p> sections.
    """

    def __init__(self, value: str):
        self.value = value

    def __repr__(self):
        return self.value

    @property
    def value(self) -> str:
        """Return the markdown text."""
        return self._value

    @value.setter
    def value(self, new_value: str):
        """Set the markdown text."""
        if not isinstance(new_value, str):
            raise ValueError("MarkdownData value must be a string.")
        self._value = new_value

    def as_html(self) -> str:
        """Convert the markdown text to HTML using markdown-it-py."""
        md = MarkdownIt()
        return md.render(self.value.replace("\n\n", "\n"))  #: We seem to be getting double newlines for some reason?



class MarkdownList(MutableSequence, MarkdownData):
    """A markdown unordered list (`-`) stored as individual markdown strings.

    Properties:
        value: A single string of markdown unordered list items defined by `-` (preserving any formatting within each list item). The setter parses the string into a list of individual items, and the getter returns a single markdown unordered list string.
    Methods:
        as_html: Returns value as an HTML unordered list using markdown-it-py.
        List methods: Supports most list methods for access and manipulation of the individual list items, including indexing.
    """


    def __init__(self, value: str):
        self.value = value

    def __len__(self) -> int:
        return len(self._values)

    def __getitem__(self, index: int) -> str:
        return self._values[index]
    def __setitem__(self, index: int, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError("value must be a string")
        self._values[index] = value
    def __delitem__(self, index: int) -> None:
        del self._values[index]

    def insert(self, index: int, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError("value must be a string")
        self._values.insert(index, value)
    def append(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError("value must be a string")
        self._values.append(value)
    def clear(self) -> None:
        self._values.clear()
    def remove(self, value: str) -> None:
        self._values.remove(value)

    def __contains__(self, value):
        return self.values.__contains__(value)
    def __iter__(self):
        return iter(self._values)

    def __repr__(self):
        return self.value

    @property
    def value(self) -> str:
        #: return list as a markdown string of unordered list items
        return "\n".join([f"- {v}" for v in self._values])

    #: parse a markdown unordered list into a list of strings
    @value.setter
    def value(self, value:str) -> None:
        if not isinstance(value, str):
            raise ValueError("value must be a string")
        if value.strip() == "":
            self._values = []
            return
        values = re.findall(r"- (.+)", value)
        if not values:
            raise ValueError("value must be a markdown unordered list using '- ' as the item prefix")
        self._values = [v.strip() for v in values]


    def as_html(self) -> str:
        """Convert the list of strings to an HTML unordered list."""

        items = "".join([f"<li>{v}</li>" for v in self._values])
        return f"<ul>{items}</ul>"

@dataclass
class MetadataDescription:
    """A more in-depth explanation of the dataset, where it came from, and how it's created, stored as multiple MarkdownData objects for structured access.

    Attributes:
        what: More detailed summary
        purpose: Application and general uses, why the dataset exists
        represents: What does the model represent in real life?
        created_maintained: History, how the dataset is updated, what parties it needs to go through, etc. How we
            aggregate it, where we get the data from.
        reliability: Any notes about reliability, ie, "Utah's authoritative municipal boundaries" or "best effort", etc
    Methods:
        as_html: Returns the description as an HTML string that has at least one <p> section for each child element (does not include any headers or differentiators between child elements).
    """

    what: MarkdownData
    purpose: MarkdownData
    represents: MarkdownData
    created_maintained: MarkdownData
    reliability: MarkdownData

    def __repr__(self):

        out_string = ""
        for var in vars(self):
            if type(getattr(self, var)) in ([MarkdownData, MarkdownList]):
                out_string += f"{var}:\n\t{getattr(self, var).value}\n"
            else:
                out_string += f"{var}:\n\t{getattr(self, var)}\n"
        return out_string

    def as_html(self) -> str:
        return "".join([getattr(self, var).as_html() for var in vars(self)])

@dataclass
class MetadataCredits:
    """Differentiates between who created the data and who aggregates/hosts it.

    Attributes:
        data_source: There could be multiple sources, ie both counties and UGRC
        host: Who is aggregating and hosting the feature service, downloadable zip file, etc. For roads, this would be
            UGRC
    """

    data_source: MarkdownList
    host: MarkdownData

    def __repr__(self):

        out_string = ""
        for var in vars(self):
            if type(getattr(self, var)) in ([MarkdownData, MarkdownList]):
                out_string += f"{var}:\n\t{getattr(self, var).value}\n"
            else:
                out_string += f"{var}:\n\t{getattr(self, var)}\n"
        return out_string

@dataclass
class MetadataUpdates:
    """How often the dataset is updated and a history of previous updates.

    Attributes:
        schedule: How often the dataset is updated (weekly, quarterly, as needed, etc)
        history: A list of previous updates, matching the updateHistory from the data page
    """

    schedule: MarkdownData
    history: MarkdownList

    def __repr__(self):

        out_string = ""
        for var in vars(self):
            if type(getattr(self, var)) in ([MarkdownData, MarkdownList]):
                out_string += f"{var}:\n\t{getattr(self, var).value}\n"
            else:
                out_string += f"{var}:\n\t{getattr(self, var)}\n"
        return out_string

@dataclass
class SGIDLayerMetadata:
    """All the metadata about a layer in the SGID or entry in the SGID index. Text should be in markdown format with
        newlines (`\n`) as needed.

    Attributes:
        title: Should match the OpenSGID layer_name (ie, in snake_case: county_boundaries)
        category: Inferred from the MATT repo directory structure
        secondary_category : Another category the layer fits in, if applicable. Can be left blank.
        sgid_id: The GUID from the SGID Index sheet in the stewardship doc that acts as the
            primary id key for the layer to track metadata across all systems
        brief_summary: A super-short, one-liner description of the dataset. Corresponds to the pageDescription
            item in the data page's metadata
        summary: A brief (<2048 characters for AGOL) explanation of the dataset to give the user a high-level
            overview of what the layer is when skimming lists of datasets. Will be the first description people see in
            Hub open data and should match the Summary section of the layer's data page.
        description: A more in-depth explanation of the dataset, where it came from and how its
            created, so the user can decide if its what they need. See MetadataDescription's documentation for
            individual pieces.
        credits_: Information about who created or provides the data (credits_.data_sources) and who is aggregating and
            hosting the actual data content (feature service, downloadable zip file, etc- credits_.host). Note that
            `credits` is a reserved word in Python, so we use `credits_` instead.
        restrictions: Any usage limitations or constraints on where or how the dataset can be used, including
            disclaimers and attribution rules
        license_: The license the data are released under. Will usually be CC BY 4.0, but could be different.
        tags: Each data set's tags should include the stewarding agency (UGRC, DWR, etc), "SGID," and the
            layer's category. Add any other relevant tags, but don't include any words in the layer's title.
        data_page_link: Link to the layer's data page on gis.utah.gov
        update: Information about When the dataset is updated (weekly, quarterly, as needed, etc- update.schedule)
            and a list of previous updates, matching the updateHistory from the data page (update.history).
    """

    title: MarkdownData
    category: MarkdownData
    secondary_category: MarkdownData
    sgid_id: MarkdownData
    brief_summary: MarkdownData
    summary: MarkdownData
    description: MetadataDescription
    credits_: MetadataCredits  #: `credits` is a reserved word
    restrictions: MarkdownData
    license_: MarkdownData  #: so is `license`
    tags: MarkdownList
    data_page_link: MarkdownData
    update: MetadataUpdates

    #: TODO: repr needs some work.

    def __repr__(self):

        out_string = ""
        for var in vars(self):
            if type(getattr(self, var)) in ([MarkdownData, MarkdownList]):
                out_string += f"{var}:\n\t{getattr(self, var).value}\n"
            else:
                out_string += f"{var}:\n\t{getattr(self, var)}\n"
        return out_string

