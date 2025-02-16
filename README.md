# repo-forge

RepoForge is a Python tool that scans a repository directory, summarizes its contents, and generates a formatted prompt with XML tags. This prompt includes a visual directory tree and summaries of text files, making it ideal for integrations with other tools or for creating structured inputs for language models.

## Features

- **Recursive Directory Scanning:** Walks through the directory tree while ignoring specified directories (e.g., `.git`, `__pycache__`, `.idea`, `.vscode`).
- **File Summarization:** Reads text files and includes a truncated summary (up to a configurable number of lines) unless the file exceeds a set size limit.
- **Ignored File Types:** Skips files with certain extensions (e.g., `.pyc`, images, PDFs, ZIPs) to focus on relevant content.
- **XML-Formatted Output:** Combines the directory tree and file summaries into a structured XML-like prompt.
- **Command-Line Interface (CLI):** Includes an optional CLI entrypoint for manual testing and quick usage.

## Installation

Repo Prompt Generator can be installed via [PyPI](https://pypi.org/) once published:

```bash
pip install repo-forge
```

Alternatively, clone the repository from GitHub and install it locally:

```bash
git clone https://github.com/ahearn15/repo-forge.git
cd repo-forge
pip install .
```

## Usage
### As a Command-Line Tool
The package provides a CLI that allows you to generate a prompt directly from the terminal.

```bash
python -m repo-forge <repo_directory> [<system_message>] [<user_instructions>]
```
For example:

```bash
python -m repo-forge /path/to/your/repo "System message goes here" "User instructions go here"
```

### As a Python Module
You can also import and use the functionality directly in your Python code:

```python
from repo-forge import generate_prompt

# Define the repository directory and optional messages
repo_dir = "/path/to/your/repo"
system_message = "System message goes here"
user_instructions = "User instructions go here"

# Generate the formatted prompt
prompt = generate_prompt(repo_dir, system_message, user_instructions)
print(prompt)
```

## Configuration
The behavior of Repo Prompt Generator can be modified by adjusting the following configuration constants in the code:

- `IGNORED_DIRS`: Set of directory names to skip (default: `{'.git', '__pycache__', '.idea', '.vscode'}`).
- `IGNORED_EXTENSIONS`: Set of file extensions to ignore (default: `{'.pyc', '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip'}`).
- `MAX_FILE_SIZE_BYTES`: Maximum file size in bytes to summarize (default: `100000 bytes`).
- `MAX_SUMMARY_LINES`: Maximum number of lines to include from a file’s content (default: `500`).

Feel free to modify these constants to fit the needs of your project.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.

## Contributing
Contributions, bug reports, and feature requests are welcome! Please open an issue or submit a pull request on GitHub.

## Acknowledgements
`repo-forge` leverages Python's standard libraries, such as os and textwrap, to provide a simple yet powerful solution for summarizing repository contents.

Happy coding!
