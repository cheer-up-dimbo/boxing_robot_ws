"""Setup configuration for boxbunny_drills package."""

from setuptools import setup
import os
from glob import glob

PACKAGE_NAME = "boxbunny_drills"

setup(
    name=PACKAGE_NAME,
    version="1.0.0",
    packages=[PACKAGE_NAME],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{PACKAGE_NAME}"]),
        (f"share/{PACKAGE_NAME}", ["package.xml"]),
        (os.path.join("share", PACKAGE_NAME, "config"), glob("config/*.yaml")),
        (os.path.join("share", PACKAGE_NAME, "launch"), glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="BoxBunny Team",
    maintainer_email="boxbunny@example.com",
    description="Boxing training drill managers including reaction drills and shadow sparring.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "reaction_drill_manager = boxbunny_drills.reaction_drill_manager:main",
            "shadow_sparring_drill = boxbunny_drills.shadow_sparring_drill:main",
            "defence_drill = boxbunny_drills.defence_drill:main",
        ],
    },
)
