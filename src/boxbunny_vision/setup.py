"""Setup configuration for boxbunny_vision package."""

from setuptools import setup
import os
from glob import glob

PACKAGE_NAME = "boxbunny_vision"

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
    description="Computer vision for glove tracking and action recognition using RealSense RGB-D.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "realsense_glove_tracker = boxbunny_vision.realsense_glove_tracker:main",
            "action_predictor = boxbunny_vision.action_predictor_node:main",
            "simple_camera_node = boxbunny_vision.simple_camera_node:main",
        ],
    },
)
