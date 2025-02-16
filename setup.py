from setuptools import setup, find_packages

setup(
    name="repo-forge",       # Package name on PyPI
    version="0.1.0",
    author="Adam Hearn",
    author_email="ahearn15@gmail.com",
    description="Generate a formatted LLM prompt from a repository directory.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ahearn15/repoforge/",  # Project homepage
    packages=find_packages(),  # Finds all packages in the directory (include __init__.py)
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",  # or another license
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    entry_points={
        'console_scripts': [
            'repo-prompt=prompt_generator:generate_prompt',  
        ],
    },
)
