from setuptools import find_packages, setup

setup(
    name="monitoring",
    version="0.0.1",
    packages=find_packages(exclude=["tests"]),
    install_requires=[
        "aiohttp >= 3.9.5",
        "pydantic >= 2.7.0",
        "prettytable >= 3.10.0",
        "click >= 8.1.7",
        "asyncpg >= 0.29.0",
    ],
    scripts=["cli/monitor"],
    python_requires=">=3.7",
)
