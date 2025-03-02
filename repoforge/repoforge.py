import os
import textwrap
import tiktoken
from typing import Set, List, Dict, Optional, Union, Any

class RepoForge:
    """
    A class for generating formatted prompts from repository directories.
    """
    # Default configuration constants
    DEFAULT_IGNORED_DIRS = {'.git', '__pycache__', '.idea', '.vscode'}
    DEFAULT_IGNORED_EXTENSIONS = {'.pyc', '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.env'}
    DEFAULT_MAX_FILE_SIZE_BYTES = 1_000_000_000  # Skip summarizing files larger than this
    DEFAULT_TOKEN_LIMIT = 128_000  # Maximum tokens for the prompt
    
    def __init__(
        self,
        ignored_dirs: Optional[Set[str]] = None,
        ignored_extensions: Optional[Set[str]] = None,
        max_file_size_bytes: float = DEFAULT_MAX_FILE_SIZE_BYTES,
        max_chars: Optional[int] = 1_000_000_000,
        ignore_max_chars_for: Optional[List[str]] = None,
        model: str = "o1-pro",
        token_limit: Optional[int] = None
    ):
        """
        Initialize the RepoForge instance.
        
        Parameters:
            ignored_dirs: Additional directories to ignore (combined with defaults)
            ignored_extensions: Additional file extensions to ignore (combined with defaults)
            max_file_size_bytes: Maximum file size for summarizing
            max_chars: Maximum characters to include in the summary (None means no limit)
            ignore_max_chars_for: List of file patterns or directory paths that should ignore the max_chars limit
            model: The model to use for token counting
            token_limit: Maximum number of tokens for the prompt (defaults to DEFAULT_TOKEN_LIMIT if None)
        """
        self.ignored_dirs = self.DEFAULT_IGNORED_DIRS.copy()
        if ignored_dirs:
            self.ignored_dirs.update(ignored_dirs)
            
        self.ignored_extensions = self.DEFAULT_IGNORED_EXTENSIONS.copy()
        if ignored_extensions:
            self.ignored_extensions.update(ignored_extensions)
            
        self.max_file_size_bytes = max_file_size_bytes
        self.max_chars = max_chars
        self.ignore_max_chars_for = ignore_max_chars_for or []
        self.model = model
        self.token_limit = token_limit if token_limit is not None else self.DEFAULT_TOKEN_LIMIT

    def summarize_text_file(self, filepath: str, max_chars: Optional[int] = None) -> str:
        """
        Return a truncated summary of a text file.
        
        Parameters:
            filepath: Path to the file
            max_chars: Maximum characters to include (None means no limit)
            
        Returns:
            A string containing the file content, potentially truncated
        """
        # Check if this file should ignore the max_chars limit
        # This can be because the file matches a pattern or is in a directory that should be ignored
        normalized_path = os.path.normpath(filepath)
        file_dir = os.path.dirname(normalized_path)
        
        should_ignore_limit = False
        for pattern in self.ignore_max_chars_for:
            # Check if the pattern is in the filepath (file pattern match)
            if pattern in normalized_path:
                should_ignore_limit = True
                break
            
            # Check if the pattern is a directory and the file is in that directory
            pattern_path = os.path.normpath(pattern)
            if os.path.isdir(pattern_path) and file_dir.startswith(pattern_path):
                should_ignore_limit = True
                break
            
            # Also check if the pattern is a directory name that appears in the path
            if os.path.basename(pattern) in file_dir.split(os.sep):
                should_ignore_limit = True
                break
        
        if should_ignore_limit:
            max_chars = None
            
        summary_lines = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
                if max_chars is not None and len(content) > max_chars:
                    content = content[:max_chars] + "\n... [Truncated]"
                
                summary_lines = content.split('\n')
                
                # Special handling for CSV files (limit to fewer lines)
                if filepath.endswith('.csv') and max_chars is not None:
                    csv_max_chars = max_chars // 10
                    csv_content = '\n'.join(summary_lines)
                    if len(csv_content) > csv_max_chars:
                        csv_content = csv_content[:csv_max_chars] + "\n... [Truncated]"
                        summary_lines = csv_content.split('\n')
                        
        except Exception as e:
            summary_lines = [f"Error reading file: {e}"]
        
        return "\n".join(summary_lines)

    def create_directory_tree(self, root_dir: str) -> str:
        """
        Create a plain-text directory tree outline for quick reference.
        
        Parameters:
            root_dir: Path to the repository directory
            
        Returns:
            A string containing the directory tree
        """
        tree_lines = []

        def walk_directory(path, prefix=""):
            entries = sorted(os.listdir(path))
            entries = [e for e in entries if e not in self.ignored_dirs]
            
            for i, entry in enumerate(entries):
                full_path = os.path.join(path, entry)
                connector = "└── " if i == len(entries) - 1 else "├── "
                if os.path.isdir(full_path):
                    tree_lines.append(prefix + connector + entry + "/")
                    new_prefix = prefix + ("    " if i == len(entries) - 1 else "│   ")
                    walk_directory(full_path, new_prefix)
                else:
                    # We do not filter file extensions in the directory tree view.
                    tree_lines.append(prefix + connector + entry)
        
        # Start the tree with the root directory's basename
        root_basename = os.path.basename(os.path.normpath(root_dir)) or root_dir
        tree_lines.append(root_basename + "/")
        walk_directory(root_dir, prefix="")

        return "\n".join(tree_lines)

    def create_repo_summary(self, root_dir: str) -> List[Dict[str, Any]]:
        """
        Walk the repo, build a data structure with directory/file info and summaries.
        
        Parameters:
            root_dir: Path to the repository directory
            
        Returns:
            A list of entries: [{ 'directory': <relative_path>, 'files': [...] }, ...]
        """
        repo_summary = []

        for current_path, dirs, files in os.walk(root_dir):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs]

            rel_dir = os.path.relpath(current_path, root_dir)
            if rel_dir == '.':
                rel_dir = ''  # top-level

            file_summaries = []
            for filename in sorted(files):  # Sort files for consistent output
                _, ext = os.path.splitext(filename)
                if ext.lower() in self.ignored_extensions or filename.startswith('.'):
                    continue

                full_path = os.path.join(current_path, filename)
                size_bytes = os.path.getsize(full_path)

                if size_bytes > self.max_file_size_bytes:
                    file_summaries.append({
                        'name': filename,
                        'summary': f"File size ({size_bytes} bytes) exceeds limit; skipping content."
                    })
                    continue

                file_content_summary = self.summarize_text_file(full_path, max_chars=self.max_chars)
                file_summaries.append({
                    'name': filename,
                    'summary': file_content_summary
                })

            if file_summaries:
                repo_summary.append({
                    'directory': rel_dir,
                    'files': file_summaries
                })

        return repo_summary

    def format_prompt_xml(
        self, 
        repo_summary: List[Dict[str, Any]], 
        directory_tree: str, 
        system_message: str = "", 
        user_instructions: str = ""
    ) -> str:
        """
        Convert the repository summary and directory tree into a textual prompt with XML tags.
        
        Parameters:
            repo_summary: Repository summary from create_repo_summary
            directory_tree: Directory tree from create_directory_tree
            system_message: Optional system message
            user_instructions: Optional user instructions
            
        Returns:
            A formatted prompt string
        """
        prompt_parts = []

        # Embed system and user instructions in XML tags
        prompt_parts.append("<SYSTEM_MESSAGE>")
        prompt_parts.append(system_message.strip() if system_message else "No system message provided.")
        prompt_parts.append("</SYSTEM_MESSAGE>\n")

        prompt_parts.append("<USER_INSTRUCTIONS>")
        prompt_parts.append(user_instructions.strip() if user_instructions else "No user instructions provided.")
        prompt_parts.append("</USER_INSTRUCTIONS>\n")

        # Add the directory tree at the top
        prompt_parts.append("<DIRECTORY_TREE>")
        prompt_parts.append(directory_tree)
        prompt_parts.append("</DIRECTORY_TREE>\n")

        prompt_parts.append("<REPOSITORY_CONTENTS>")
        for entry in repo_summary:
            dir_path = entry['directory'] or "(top-level)"
            prompt_parts.append(f'  <directory name="{dir_path}">')
            for file_info in entry['files']:
                prompt_parts.append(f'    <file name="{file_info["name"]}">')
                prompt_parts.append("      <content>")
                for line in file_info["summary"].split("\n"):
                    prompt_parts.append("         " + line)
                prompt_parts.append("      </content>")
                prompt_parts.append("    </file>")
            prompt_parts.append("  </directory>")
        prompt_parts.append("</REPOSITORY_CONTENTS>")

        return "\n".join(prompt_parts)

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string.
        
        Parameters:
            text: The text to count tokens for
            
        Returns:
            The number of tokens
        """
        encoding = tiktoken.encoding_for_model(self.model)
        return len(encoding.encode(text))

    def generate_prompt(
        self,
        repo_dir: str,
        system_message: str = "",
        user_instructions: str = ""
    ) -> str:
        """
        Generate a formatted prompt from a repository directory.
        
        Parameters:
            repo_dir: Path to the repository directory
            system_message: Optional system message
            user_instructions: Optional user instructions
        
        Returns:
            The formatted prompt
        
        Raises:
            ValueError: If the provided directory does not exist
        """
        if not os.path.isdir(repo_dir):
            raise ValueError(f"Directory {repo_dir} does not exist.")
        
        directory_tree = self.create_directory_tree(repo_dir)
        repo_summary = self.create_repo_summary(repo_dir)
        formatted_prompt = self.format_prompt_xml(
            repo_summary=repo_summary,
            directory_tree=directory_tree,
            system_message=system_message,
            user_instructions=user_instructions
        )
        token_count = self.count_tokens(formatted_prompt)
        
        # Recursively reduce max_chars if token count exceeds the limit
        if token_count > self.token_limit and self.max_chars is not None:
            # Calculate reduction factor based on how much we need to reduce
            reduction_factor = self.token_limit / token_count
            # Apply with a safety margin
            new_max_chars = int(self.max_chars * reduction_factor * 0.9)
            print(f"Token count too high ({token_count}). Reducing max_chars from {self.max_chars} to {new_max_chars}.")
            
            # Create a new instance with reduced max_chars
            new_instance = RepoForge(
                ignored_dirs=self.ignored_dirs - self.DEFAULT_IGNORED_DIRS,
                ignored_extensions=self.ignored_extensions - self.DEFAULT_IGNORED_EXTENSIONS,
                max_file_size_bytes=self.max_file_size_bytes,
                max_chars=new_max_chars,
                ignore_max_chars_for=self.ignore_max_chars_for,
                model=self.model,
                token_limit=self.token_limit
            )
            
            return new_instance.generate_prompt(
                repo_dir,
                system_message=system_message,
                user_instructions=user_instructions
            )
            
        print(f"Final token count: {token_count}")
        return formatted_prompt

    def generate_prompt_with_metadata(
        self,
        repo_dir: str,
        system_message: str = "",
        user_instructions: str = ""
    ) -> Dict[str, Any]:
        """
        Generate a formatted prompt from a repository directory and return metadata.
        
        Parameters:
            repo_dir: Path to the repository directory
            system_message: Optional system message
            user_instructions: Optional user instructions
        
        Returns:
            Dictionary containing the formatted prompt and metadata:
            {
                'prompt': str,
                'token_count': int,
                'char_count': int,
                'file_count': int,
                'directory_count': int
            }
        
        Raises:
            ValueError: If the provided directory does not exist
        """
        prompt = self.generate_prompt(repo_dir, system_message, user_instructions)
        
        # Count files and directories in the repo summary
        repo_summary = self.create_repo_summary(repo_dir)
        directory_count = len(repo_summary)
        file_count = sum(len(entry['files']) for entry in repo_summary)
        
        return {
            'prompt': prompt,
            'token_count': self.count_tokens(prompt),
            'char_count': len(prompt),
            'file_count': file_count,
            'directory_count': directory_count
        }


# Optional: CLI entrypoint for manual testing
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate a formatted prompt from a repository directory")
    parser.add_argument("repo_dir", help="Path to the repository directory")
    parser.add_argument("--system-message", default="", help="Optional system message")
    parser.add_argument("--user-instructions", default="", help="Optional user instructions")
    parser.add_argument("--ignored-dirs", nargs="+", default=[], help="Additional directories to ignore")
    parser.add_argument("--ignored-extensions", nargs="+", default=[], help="Additional file extensions to ignore")
    parser.add_argument("--max-file-size", type=float, default=RepoForge.DEFAULT_MAX_FILE_SIZE_BYTES, 
                        help="Maximum file size for summarizing")
    parser.add_argument("--max-chars", type=int, default=None, 
                        help="Maximum characters to include in the summary (None means no limit)")
    parser.add_argument("--ignore-max-chars-for", nargs="+", default=[], 
                        help="List of file patterns or directory paths that should ignore the max_chars limit")
    parser.add_argument("--model", default="o1-pro", help="The model to use for token counting")
    parser.add_argument("--token-limit", type=int, default=None, 
                        help="Maximum number of tokens for the prompt (defaults to DEFAULT_TOKEN_LIMIT if None)")
    parser.add_argument("--with-metadata", action="store_true", 
                        help="Include metadata about the generated prompt")
    
    args = parser.parse_args()
    
    try:
        repo_forge = RepoForge(
            ignored_dirs=set(args.ignored_dirs),
            ignored_extensions=set(args.ignored_extensions),
            max_file_size_bytes=args.max_file_size,
            max_chars=args.max_chars,
            ignore_max_chars_for=args.ignore_max_chars_for,
            model=args.model,
            token_limit=args.token_limit
        )
        
        if args.with_metadata:
            result = repo_forge.generate_prompt_with_metadata(
                args.repo_dir,
                system_message=args.system_message,
                user_instructions=args.user_instructions
            )
            # Print metadata first
            print(f"--- METADATA ---")
            print(f"Token count: {result['token_count']}")
            print(f"Character count: {result['char_count']}")
            print(f"File count: {result['file_count']}")
            print(f"Directory count: {result['directory_count']}")
            print(f"--- PROMPT ---")
            print(result['prompt'])
        else:
            prompt = repo_forge.generate_prompt(
                args.repo_dir,
                system_message=args.system_message,
                user_instructions=args.user_instructions
            )
            print(prompt)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
