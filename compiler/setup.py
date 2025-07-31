from setuptools import setup, find_packages
import os
import sys

# Add pygls to the core requirements. It is not optional.
install_requires = ["lark", "pandas", "matplotlib", "pygls>=1.0.0"]
if sys.version_info < (3, 9):
    install_requires.append("importlib_resources")

# Optional dependencies for development
extras_require = {
    "dev": ["pytest"],
}

setup(
    name="valuascript-compiler",
    version="1.1.0",
    packages=find_packages(),
    install_requires=install_requires,
    extras_require=extras_require,
    package_data={
        "vsc": ["*.lark"],
    },
    entry_points={
        "console_scripts": [
            "vsc = vsc.cli:main",
        ],
    },
    author="Alessio Marcuzzi",
    author_email="alemarcuzzi03@gmail.com",
    description="A compiler for the ValuaScript financial modeling language.",
    long_description=open(os.path.join(os.path.dirname(__file__), "..", "README.md")).read() if os.path.exists(os.path.join(os.path.dirname(__file__), "..", "README.md")) else "",
    long_description_content_type="text/markdown",
    url="https://github.com/Alessio2704/monte-carlo-simulator",
)
