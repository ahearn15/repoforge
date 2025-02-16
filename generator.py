import os
import textwrap

# Configuration constants
IGNORED_DIRS = {'.git', '__pycache__', '.idea', '.vscode'}
IGNORED_EXTENSIONS = {'.pyc', '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip'}
MAX_FILE_SIZE_BYTES = 100_000  # Skip summarizing files larger than this
MAX_SUMMARY_LINES = 500         # Maximum lines of content to include

def summarize_text_file(filepath, max_lines=MAX_SUMMARY_LINES):
    """
    Return a truncated summary (the first few lines) of a text file.
    """
    summary_lines = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    summary_lines.append("... [Truncated]")
                    break
                summary_lines.append(line.rstrip('\n'))
    except Exception as e:
        summary_lines = [f"Error reading file: {e}"]
    
    return "\n".join(summary_lines)

def create_directory_tree(root_dir):
    """
    Create a plain-text directory tree outline for quick reference.
    """
    tree_lines = []

    def walk_directory(path, prefix=""):
        entries = sorted(os.listdir(path))
        entries = [e for e in entries if e not in IGNORED_DIRS]
        
        for i, entry in enumerate(entries):
            full_path = os.path.join(path, entry)
            connector = "└── " if i == len(entries) - 1 else "├── "
            if os.path.isdir(full_path):
                tree_lines.append(prefix + connector + entry + "/")
                new_prefix = prefix + ("    " if i == len(entries) - 1 else "│   ")
                walk_directory(full_path, new_prefix)
            else:
                # Skip files with ignored extensions
                _, ext = os.path.splitext(entry)
                if ext.lower() in IGNORED_EXTENSIONS:
                    continue
                tree_lines.append(prefix + connector + entry)
    
    # Start the tree with the root directory's basename
    root_basename = os.path.basename(os.path.normpath(root_dir)) or root_dir
    tree_lines.append(root_basename + "/")
    walk_directory(root_dir, prefix="")

    return "\n".join(tree_lines)

def create_repo_summary(root_dir):
    """
    Walk the repo, build a data structure with directory/file info and summaries.
    Returns a list of entries: [{ 'directory': <relative_path>, 'files': [...] }, ...].
    """
    repo_summary = []

    for current_path, dirs, files in os.walk(root_dir):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        rel_dir = os.path.relpath(current_path, root_dir)
        if rel_dir == '.':
            rel_dir = ''  # top-level

        file_summaries = []
        for filename in files:
            _, ext = os.path.splitext(filename)
            if ext.lower() in IGNORED_EXTENSIONS:
                continue

            full_path = os.path.join(current_path, filename)
            size_bytes = os.path.getsize(full_path)

            if size_bytes > MAX_FILE_SIZE_BYTES:
                file_summaries.append({
                    'name': filename,
                    'summary': f"File size ({size_bytes} bytes) exceeds limit; skipping content."
                })
                continue

            file_content_summary = summarize_text_file(full_path, max_lines=MAX_SUMMARY_LINES)
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

def format_prompt_xml(repo_summary, directory_tree, system_message="", user_instructions=""):
    """
    Convert the repository summary and directory tree into a textual prompt with XML tags.
    """
    prompt_parts = []
    
    # Add the directory tree at the top
    prompt_parts.append("DIRECTORY TREE:")
    prompt_parts.append(directory_tree)
    prompt_parts.append("")

    # Embed system and user instructions in XML tags
    prompt_parts.append("<SYSTEM_MESSAGE>")
    prompt_parts.append(system_message.strip() if system_message else "No system message provided.")
    prompt_parts.append("</SYSTEM_MESSAGE>\n")

    prompt_parts.append("<USER_INSTRUCTIONS>")
    prompt_parts.append(user_instructions.strip() if user_instructions else "No user instructions provided.")
    prompt_parts.append("</USER_INSTRUCTIONS>\n")

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

def generate_prompt(repo_dir, system_message="", user_instructions=""):
    """
    Generate a formatted prompt from a repository directory.
    
    Parameters:
      repo_dir (str): Path to the repository directory.
      system_message (str): Optional system message.
      user_instructions (str): Optional user instructions.
    
    Returns:
      str: The formatted prompt.
    
    Raises:
      ValueError: If the provided directory does not exist.
    """
    if not os.path.isdir(repo_dir):
        raise ValueError(f"Directory {repo_dir} does not exist.")
    
    directory_tree = create_directory_tree(repo_dir)
    repo_summary = create_repo_summary(repo_dir)
    return format_prompt_xml(
        repo_summary=repo_summary,
        directory_tree=directory_tree,
        system_message=system_message,
        user_instructions=user_instructions
    )

# Optional: CLI entrypoint for manual testing
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <repo_directory> [<system_message>] [<user_instructions>]")
        sys.exit(1)

    repo_dir = sys.argv[1]
    system_message = sys.argv[2] if len(sys.argv) > 2 else ""
    user_instructions = sys.argv[3] if len(sys.argv) > 3 else ""

    try:
        prompt = generate_prompt(repo_dir, system_message, user_instructions)
        print(prompt)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
