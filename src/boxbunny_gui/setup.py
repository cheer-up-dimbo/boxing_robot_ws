"""Setup configuration for boxbunny_gui package."""

from setuptools import setup
import os
from glob import glob

PACKAGE_NAME = "boxbunny_gui"

setup(
    name=PACKAGE_NAME,
    version="1.0.0",
    packages=[PACKAGE_NAME],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{PACKAGE_NAME}"]),
        (f"share/{PACKAGE_NAME}", ["package.xml"]),
        (os.path.join("share", PACKAGE_NAME, "config"), glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="BoxBunny Team",
    maintainer_email="boxbunny@example.com",
    description="PySide6-based graphical interface for boxing drills and real-time telemetry.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "boxing_gui = boxbunny_gui.gui_main:main",
        ],
    },
)
