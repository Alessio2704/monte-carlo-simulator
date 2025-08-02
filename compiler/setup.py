# compiler/setup.py
from setuptools import setup, find_packages
import os

this_directory = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "A compiler for the ValuaScript financial modeling language."

setup(
    author="Alessio Marcuzzi",
    author_email="alemarcuzzi03@gmail.com",
    description="A compiler for the ValuaScript financial modeling language.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Alessio2704/monte-carlo-simulator",
    packages=find_packages(),
    install_requires=["lark", "pandas", "matplotlib", "pygls>=1.0.0"],
    package_data={"vsc": ["*.lark"]},
    entry_points={"console_scripts": ["vsc = vsc.cli:main"]},
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
)
