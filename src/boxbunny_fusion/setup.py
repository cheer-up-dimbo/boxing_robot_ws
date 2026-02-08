"""Setup configuration for boxbunny_fusion package."""

from setuptools import setup
import os
from glob import glob

PACKAGE_NAME = "boxbunny_fusion"

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
    description="Sensor fusion for combining vision and IMU punch detection data.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "punch_fusion_node = boxbunny_fusion.punch_fusion_node:main",
        ],
    },
)
