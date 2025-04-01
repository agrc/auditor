import re
from collections.abc import MutableSequence
from dataclasses import dataclass, field
from pathlib import Path

from github import Auth, Github
from github.ContentFile import ContentFile
from markdown_it import MarkdownIt

#: The SGIDLayerMetadata class contains the metadata for a single SGID layer. It is composed of other classes that store the metadata in a structure matching the headings and subheadings in the MATT files.

#: The basic units are the MarkdownData class, which exposes the raw markdown string via the value property, and MarkdownList class, which provides a list-like interface for accessing individual elements of a markdown unordered list. Both classes have an as_html() method which uses markdown-it-py to render the markdown as html.

#: There are classes for the description, credits, updates, and schema sections of the metadata that hold their respective sub-headings/elements as individual MarkdownData/List objects or collections thereof as appropriate. These also have as_html() methods to render the markdown as html (they generally call the as_html() method of their constituent MarkdownData/List objects).

#: The MetadataRepoContents and MetadataFile classes interface with the MATT repository in github to extract the metadata files in a structured way. MetadataRepoContents traverses the repository and structures the files by their category as MetadataFile objects.

#: The MetadataFile class provide access to a single layer's content as pygithub ContentFile objects, associating a schema file if present in the same group. The content and schema properties return the raw markdown text of the file(s). The object's data can be converted to a SGIDLayerMetadata object using the parse_markdown_into_sgid_metadata() method.

#: TODO: The classes currently cannot combine the general and county-specific parcel and parcel LIR files into a single coherent representation for each county. This probably lives best in the MetadataFile class following the pattern of also storing the schema in this class. This may suggest a renaming of the class since it's not just a single file but can be composed of multiple files (a single layer, a layer with schema, or a parcel layer combined from multiple files with a schema).

#: See https://github.com/agrc/auditor/issues/92


class MarkdownData:
    """ "Basic unit of metadata stored as a single string of markdown text.

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
    def value(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError("value must be a string")
        if value.strip() == "":
            self._values = []
            return
        if r"\n" not in value:
            self._values = [value.strip()]
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
class MetadataSchema:
    fields: dict[str, MarkdownData] = field(default_factory=dict)

    def as_html(self) -> str:
        return "".join([f"<h3>{field}</h3>{definition.as_html()}" for field, definition in self.fields.items()])


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
            disclaimers and attribution rules. If the MarkdownData value is empty, adds our default disclaimer.
        license_: The license the data are released under. Will usually be CC BY 4.0, but could be different. If the
            MarkdownData value is empty, adds "CC BY 4.0".
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
    schema: MetadataSchema = field(default_factory=MetadataSchema)

    default_license = "CC BY 4.0"
    default_restrictions = """
        The data, including but not limited to geographic data, tabular data, and analytical data, are provided “as is” and “as available”, with no guarantees relating to the availability, completeness, or accuracy of data, and without any express or implied warranties.

        These data are provided as a public service for informational purposes only. You are solely responsible for obtaining the proper evaluation of a location and associated data by a qualified professional. UGRC reserves the right to change, revise, suspend or discontinue published data and services without notice at any time.

        Neither UGRC nor the State of Utah are responsible for any misuse or misrepresentation of the data. UGRC and the State of Utah are not obligated to provide you with any maintenance or support. The user assumes the entire risk as to the quality and performance of the data. You agree to hold the State of Utah harmless for any claims, liability, costs, and damages relating to your use of the data. You agree that your sole remedy for any dissatisfaction or claims is to discontinue use of the data."""

    def __post_init__(self):
        """Set defaults for the restrictions and license_ attributes if their values are empty."""

        #: Every layer in github should have "Restriction" and "License" sections, but they can be empty ("").
        #: If they are empty, set them to the default values.
        if not self.restrictions.value:
            self.restrictions = MarkdownData(self.default_restrictions)
        if not self.license_.value:
            self.license_ = MarkdownData(self.default_license)

    #: TODO: repr needs some work.

    def __repr__(self):
        out_string = ""
        for var in vars(self):
            if type(getattr(self, var)) in ([MarkdownData, MarkdownList]):
                out_string += f"{var}:\n\t{getattr(self, var).value}\n"
            else:
                out_string += f"{var}:\n\t{getattr(self, var)}\n"
        return out_string


class MetadataRepoContents:
    """Loads content of the metadata repo grouped by SGID category as MetadataFiles, which expose the pygithub ContentFile representations of each file."""

    def __init__(self, repo):
        #: Setup instance variables
        self.repo = repo
        self._all_metadata_content = []
        self._initial_categories = {}
        self.categories = {}

        #: Load metadata files from github, group by SGID category, and extract content from each file
        self._load_metadata_content_files()
        self._categorize_content_files()
        self._extract_metadata_info()

    def _load_metadata_content_files(self):
        """Load all metadata files from the repo as pygithub ContentFiles."""
        contents = self.repo.get_contents("metadata")
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(self.repo.get_contents(file_content.path))
            else:
                self._all_metadata_content.append(file_content)

    def _categorize_content_files(self):
        """Categorize the pygithub ContentFiles by their directory structure."""
        for file_content in self._all_metadata_content:
            if file_content.path.startswith("metadata/") and file_content.path.endswith(".md"):
                category = file_content.path.split("/")[1].lower()
                if category in ["_category", "schema"]:
                    continue
                if category not in self._initial_categories:
                    self._initial_categories[category] = []
                self._initial_categories[category].append(file_content)

    def _extract_metadata_info(self):
        """Create dictionary of MetadataFile objects for each category."""
        for category in self._initial_categories:
            if category not in self.categories:
                self.categories[category] = []
            for content_file in self._initial_categories[category]:
                if content_file.path.endswith("_schema.md"):
                    continue
                metadata_file = MetadataFile(content_file, self._initial_categories[category])
                self.categories[category].append(metadata_file)


class MetadataFile:
    """Contains a single layer's metadata ContentFile and associated schema ContentFile if present, exposing the raw markdown text of each via the content and schema properties. Provides a method for parsing the data into a SGIDLayerMetadata object."""

    def __init__(self, content_file: ContentFile, group_contents: list[ContentFile]):
        self.group = content_file.path.split("/")[1].lower()  #: element[0] is "metadata"
        self.name = content_file.path.split("/")[2].lower()
        self._content_file = content_file
        self._group_contents = {
            Path(content.path): content for content in group_contents
        }  #: There's probably a more efficient way to do this than calculating this list for every item, but :shrug:

        self.schema_file = None
        self._get_schema_file()

        self._split_content = {}
        self._split_schema = {}
        self._split_content_and_schema_to_sections()

        self.metadata = None

    def _get_schema_file(self):
        content_file_parent = Path(self._content_file.path).parent
        schema_file_path = content_file_parent / (self._content_file.name.replace(".md", "_schema.md"))

        if schema_file_path in self._group_contents:
            self.schema_file = self._group_contents[schema_file_path]

    @property
    def content(self):
        """Return the decoded content of the metadata file."""
        return self._content_file.decoded_content.decode("utf-8")

    @property
    def schema(self):
        """Return the decoded content of the schema file if it exists."""
        if self.schema_file:
            return self.schema_file.decoded_content.decode("utf-8")
        return None

    def __repr__(self):
        output = f"content={self._content_file.path}"
        if self.schema_file:
            output += f"\n\tschema_file={self.schema_file}"
        return output

    @staticmethod
    def _split_markdown_to_sections(content) -> dict[str, str]:
        """Splits the raw markdown content from github into a dictionary of section names and associated markdown text."""
        split_content = {}
        lines = [line for line in MetadataFile._remove_comments_from_markdown(content).split("\n") if line]
        lines.append(
            "# End"
        )  #: add something at the end so that it doesn't fall off the end without saving the last section
        section_content = []
        section = ""
        for line in lines:
            if line.startswith("#"):
                #: kind of a look-behind thing- if the current line is a new section, save the previous section's content
                if section:
                    split_content[section] = "\n".join(section_content)
                    section_content = []
                section = re.match(r"^(?:#+)\s+(.*)", line)[1]  #: gets the header's content/name
                continue

            if line.strip():
                section_content.append(line)

        return split_content

    def _split_content_and_schema_to_sections(self) -> None:
        """Splits the raw markdown content and schema content into dictionaries of section names and associated markdown text."""
        self._split_content = self._split_markdown_to_sections(self.content)
        if self.schema:
            self._split_schema = self._split_markdown_to_sections(self.schema)

    @staticmethod
    def _remove_comments_from_markdown(markdown) -> str:
        """Removes comments from the markdown content."""
        return re.sub(r"<!--.*?-->", "", markdown, flags=re.DOTALL)

    def parse_markdown_into_sgid_metadata(self) -> SGIDLayerMetadata:
        """Creates an SGIDLayerMetadata object from the split markdown content."""
        metadata = SGIDLayerMetadata(
            title=MarkdownData(self._split_content["Title"]),
            category=MarkdownData(self.group),
            secondary_category=MarkdownData(self._split_content["Secondary Category"]),
            sgid_id=MarkdownData(self._split_content["ID"]),
            brief_summary=MarkdownData(self._split_content["Brief Summary"]),
            summary=MarkdownData(self._split_content["Summary"]),
            description=MetadataDescription(
                what=MarkdownData(self._split_content["What is the dataset?"]),
                purpose=MarkdownData(self._split_content["What is the purpose of the dataset?"]),
                represents=MarkdownData(self._split_content["What does the dataset represent?"]),
                created_maintained=MarkdownData(self._split_content["How was the dataset created?"]),
                reliability=MarkdownData(self._split_content["How reliable and accurate is the dataset?"]),
            ),
            credits_=MetadataCredits(
                data_source=MarkdownList(self._split_content["Data Source"]),
                host=MarkdownData(self._split_content["Host"]),
            ),
            restrictions=MarkdownData(self._split_content["Restrictions"]),
            license_=MarkdownData(self._split_content["License"]),
            tags=MarkdownList(self._split_content["Tags"]),
            data_page_link=MarkdownData(self._split_content["Data Page Link"]),
            update=MetadataUpdates(
                schedule=MarkdownData(self._split_content["Update Schedule"]),
                history=MarkdownList(self._split_content["Previous Updates"]),
            ),
        )
        if self.schema_file:
            metadata.schema = self._parse_markdown_into_schema()

        return metadata

    def _parse_markdown_into_schema(self) -> None:
        """Creates a MetadataSchema from the split schema content."""
        schema = MetadataSchema(
            {
                header: MarkdownData(content)
                for header, content in self._split_schema.items()
                if header not in ["Title", "ID"]
            }
        )
        return schema


def example_repo_pull():
    #: The Github API doesn't support uname/pwd authentication against github.com accounts, so we have to use a personal access token. Generate it on github, save to file. Use a fine-grained PAT and select either the appropriate repo for read-only access or just do all public repo read-only access.
    #: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
    token_file_path = ""
    with open(token_file_path) as f:
        access_token = f.read()
    auth = Auth.Token(access_token)

    g = Github(
        seconds_between_requests=1.1, auth=auth
    )  #: Ensures we don't run into any rate limiting for too many requests/too much server load per minute
    repo = g.get_repo("agrc/metadata-asset-tracking-tool")

    #: Create the repo object, which loads all the metadata files as MetadataFile objects
    metadata_repo = MetadataRepoContents(repo)

    parsed = {}
    error_layers = []

    for category in metadata_repo.categories:
        for metadata_file in metadata_repo.categories[category]:
            try:
                metadata = metadata_file.parse_markdown_into_sgid_metadata()
                parsed[metadata.sgid_id.value] = metadata
            except KeyError as e:  #: if there are any sections missing/misnamed
                error_layers.append(f"{metadata_file.name}: {e}")
                continue

    print(g.rate_limiting)  #: Check rate limiting on github
    pass


if __name__ == "__main__":
    example_repo_pull()
    pass
