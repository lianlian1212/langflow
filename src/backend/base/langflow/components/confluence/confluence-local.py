from langchain_community.document_loaders import ConfluenceLoader
from langchain_community.document_loaders.confluence import ContentFormat
from atlassian import Confluence 
from langflow.custom import Component
from langflow.io import BoolInput, DropdownInput, IntInput, Output, SecretStrInput, StrInput
from langflow.schema import Data
from langchain_core.documents import Document

class ConfluenceComponentModified(Component):
    display_name = "Confluence-Path"
    description = "Load documents from a Confluence Space, optionally filtering by a parent page ID."
    documentation = "https://python.langchain.com/v0.2/docs/integrations/document_loaders/confluence/"
    trace_type = "tool"
    icon = "Confluence"
    name = "ConfluenceModified" # Renamed to avoid conflict if original exists

    inputs = [
        StrInput(
            name="url",
            display_name="Site URL",
            required=True,
            info="The base URL of the Confluence instance. Example: https://<company>.atlassian.net/wiki.",
        ),
        SecretStrInput(
            name="api_token",
            display_name="API Token",
            required=True,
            info="Atlassian API Token (NOT password). Create at: https://id.atlassian.com/manage-profile/security/api-tokens",
        ),
        # StrInput(
        #     name="username", # Added username, often required with API Token
        #     display_name="Username",
        #     required=False,
        #     info="Atlassian User E-mail associated with the API Token. Example: email@example.com",
        #     # value="YOUR_CONFLUENCE_USERNAME" # Default/Example if needed
        # ),
        StrInput(
            name="space_key",
            display_name="Space Key",
            required=True,
            info="The key of the Confluence Space (e.g., 'DS'). Used if Parent Page ID is not provided, or within CQL.",
        ),
        IntInput( # Changed to IntInput for Page ID
            name="parent_page_id",
            display_name="Parent Page ID (Optional)",
            required=False,
            value=None, # Default to None
            info="If provided, load only pages under this specific page ID (find ID in page URL or via API). Overrides loading the entire space.",
            advanced=False, # Make it a primary option
        ),
        DropdownInput(
            name="content_format",
            display_name="Content Format",
            options=[
                ContentFormat.EDITOR.value,
                ContentFormat.EXPORT_VIEW.value,
                ContentFormat.ANONYMOUS_EXPORT_VIEW.value,
                ContentFormat.STORAGE.value, # Usually best for raw content
                ContentFormat.VIEW.value,
            ],
            value=ContentFormat.STORAGE.value,
            required=True,
            advanced=True,
            info="Specify content format, defaults to ContentFormat.STORAGE",
        ),
        IntInput(
            name="max_pages",
            display_name="Max Pages",
            required=False,
            value=100,
            advanced=True,
            info="Maximum number of pages to retrieve in total, defaults to 100. Set higher if needed.",
        ),
         BoolInput(
            name="include_attachments",
            display_name="Include Attachments",
            required=False,
            value=False,
            advanced=True,
            info="Include attachments in the loaded documents (each attachment becomes a separate document)."
        ),
        BoolInput(
            name="include_comments",
            display_name="Include Comments",
            required=False,
            value=False,
            advanced=True,
            info="Include comments in the loaded documents."
        ),
    ]

    outputs = [
        Output(name="data", display_name="Data", method="load_documents"),
    ]

    def build_confluence_loader(self) -> ConfluenceLoader:
        """Builds the ConfluenceLoader based on provided inputs."""
        content_format = ContentFormat(self.content_format)
        loader_args = {
            "url": self.url,
           # "username": self.username,
            "token": self.api_token, 
            "content_format": content_format,
            "max_pages": self.max_pages if self.max_pages > 0 else None,
            "include_attachments": self.include_attachments,
            "include_comments": self.include_comments,
            "keep_markdown_format":True,
        }
        # Conditional loading based on parent_page_id
        if self.parent_page_id is not None and self.parent_page_id > 0:
            # Use CQL to load descendants of the parent page within the specified space
            # Note: 'ancestor' includes the parent page itself plus all descendants.
            # If you only want descendants, you might need a more complex query or post-filtering.
            cql_query = f'space = "{self.space_key}" and ancestor = {self.parent_page_id}'
            loader_args["cql"] = cql_query
            self.status = f"Configured to load pages under Page ID {self.parent_page_id} in space {self.space_key} using CQL."
        else:
            # Load all pages from the space if no parent_page_id is given
            loader_args["space_key"] = self.space_key
            self.status = f"Configured to load all pages from space {self.space_key}."
        return ConfluenceLoader(**loader_args)

    def load_documents(self) -> list[Data]:
        """Loads documents from Confluence using the configured loader."""
        try:
            confluence_loader = self.build_confluence_loader()
            self.status = f"Loading documents from Confluence ({self.url})..."
            documents: list[Document] = confluence_loader.load() # Explicit type hint
            self.status = f"Loaded {len(documents)} documents."
            data = [Data.from_document(doc) for doc in documents]
            self.status = data 

        except Exception as e:
            self.status = f"Error loading documents: {str(e)}"
            print(f"Confluence Loader Error: {e}") 
            return []

        return data
