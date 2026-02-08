"""Setup configuration for boxbunny_analytics package."""

from setuptools import setup
import os
from glob import glob

PACKAGE_NAME = "boxbunny_analytics"

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
    description="Real-time punch statistics aggregation and analysis for boxing training.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "punch_stats_node = boxbunny_analytics.punch_stats_node:main",
        ],
    },
)
