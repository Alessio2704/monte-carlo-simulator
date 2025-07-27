from setuptools import setup
import sys

# Add a conditional dependency for older Python versions
install_requires = ["lark"]
if sys.version_info < (3, 9):
    install_requires.append("importlib_resources")

setup(
    name="valuascript-compiler",
    version="1.0.0", 
    py_modules=["vsc"],
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            # It creates a command named 'vsc' that will execute the
            # 'main' function inside the 'vsc.py' module.
            "vsc = vsc:main",
        ],
    },
    include_package_data=True,
    author="Alessio Marcuzzi",
    author_email="alemarcuzzi03@gmail.com",
    description="A compiler for the ValuaScript financial modeling language.",
    long_description=open("README.md").read() if open("README.md", "r", encoding="utf-8") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/Alessio2704/monte-carlo-simulator",
)
