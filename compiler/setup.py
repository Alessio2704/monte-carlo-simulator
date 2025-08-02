# compiler/setup.py
from setuptools import setup, find_packages
import os
import sys

# Read the contents of your README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

install_requires = ["lark", "pandas", "matplotlib", "pygls>=1.0.0"]
if sys.version_info < (3, 9):
    install_requires.append("importlib_resources")

setup(
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    name="valuascript-compiler",
    version="1.0.0",
    author="Alessio Marcuzzi",
    author_email="alemarcuzzi03@gmail.com",
    description="A compiler for the ValuaScript financial modeling language.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Alessio2704/monte-carlo-simulator",
    packages=find_packages(),
    install_requires=install_requires,
    package_data={
        "vsc": ["*.lark"],
    },
    entry_points={
        "console_scripts": [
            "vsc = vsc.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    python_requires=">=3.7",
)
