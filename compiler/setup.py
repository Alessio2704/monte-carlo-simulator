# compiler/setup.py

from setuptools import setup, find_packages
import os  # <-- Added os import for os.path.exists
import sys

# Add a conditional dependency for older Python versions
install_requires = ["lark", "pandas", "matplotlib"]
if sys.version_info < (3, 9):
    install_requires.append("importlib_resources")

setup(
    name="valuascript-compiler",
    version="1.1.0",
    packages=find_packages(where=".", exclude=["tests"]),
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "vsc = vsc.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        # This path needs to be relative to the package itself.
        # However, since valuascript.lark is outside the vsc package,
        # we need to ensure it's found via MANIFEST.in.
        # This setup is a bit tricky, let's simplify and rely on MANIFEST.in
    },
    author="Alessio Marcuzzi",
    author_email="alemarcuzzi03@gmail.com",
    description="A compiler for the ValuaScript financial modeling language.",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/Alessio2704/monte-carlo-simulator",
)
