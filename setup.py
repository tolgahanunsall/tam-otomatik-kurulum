"""Setup script for Note Backup Tool."""

from setuptools import setup, find_packages

setup(
    name="note-backup-tool",
    version="1.0.0",
    description="Notion/Obsidian icin otomatik yedekleme araci",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Note Backup Tool",
    license="MIT",
    python_requires=">=3.8",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
        "PyYAML>=6.0",
        "dropbox>=11.36.0",
        "GitPython>=3.1.30",
        "python-dateutil>=2.8.2",
        "colorama>=0.4.6",
    ],
    entry_points={
        "console_scripts": [
            "note-backup=backup:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
