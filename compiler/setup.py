from setuptools import setup, find_packages
import os
import sys

# Add a conditional dependency for older Python versions
install_requires = ["lark", "pandas", "matplotlib"]
if sys.version_info < (3, 9):
    install_requires.append("importlib_resources")

# Define optional dependencies for development and specific features
extras_require = {"dev": ["pytest"], "lsp": ["pygls>=1.0.0"]}  # Language Server Protocol support

setup(
    name="valuascript-compiler",
    version="1.1.0",
    packages=find_packages(where=".", exclude=["tests"]),
    install_requires=install_requires,
    extras_require=extras_require,
    entry_points={
        "console_scripts": [
            "vsc = vsc.cli:main",
        ],
    },
    include_package_data=True,
    package_data={},
    author="Alessio Marcuzzi",
    author_email="alemarcuzzi03@gmail.com",
    description="A compiler for the ValuaScript financial modeling language.",
    long_description=open("../README.md").read() if os.path.exists("../README.md") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/Alessio2704/monte-carlo-simulator",
)
