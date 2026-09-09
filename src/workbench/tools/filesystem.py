"""
Filesystem Tools Interface.

Owned by: Developer 5 (Tool/Sandbox Engineer)
Subsystem: tools
"""


class FilesystemTools:
    """
    Interface for controlled local read_file and write_file operations.
    """

    def read_file(self, path: str) -> str:
        """
        Reads text content from a controlled path.
        """
        raise NotImplementedError("FilesystemTools.read_file will be implemented by Developer 5.")

    def write_file(self, path: str, content: str) -> str:
        """
        Writes content to a controlled path.
        """
        raise NotImplementedError("FilesystemTools.write_file will be implemented by Developer 5.")
