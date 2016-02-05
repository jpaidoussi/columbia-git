import os
from setuptools import setup, find_packages


def read(*paths):
    """Build a file path from *paths* and return the contents."""
    with open(os.path.join(*paths), 'r') as f:
        return f.read()

setup(
    name="columbia.git",
    version="0.1",
    description="Columbia Git Repository Abstraction",
    long_description=read('README.rst'),
    author="Jason Paidoussi",
    author_email="jason@paidoussi.net",
    license="CC0 1.0 Universal",
    packages=find_packages(exclude=["tests*"]),
    namespace_packages=["columbia"],
    zip_safe=False,
    install_requires=[
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: Public Domain",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.5",
    ],
)
