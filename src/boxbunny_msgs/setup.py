"""Setup configuration for boxbunny_msgs package."""

from setuptools import setup
import os
from glob import glob

PACKAGE_NAME = "boxbunny_msgs"

setup(
    name=PACKAGE_NAME,
    version="1.0.0",
    packages=[PACKAGE_NAME],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{PACKAGE_NAME}"]),
        (f"share/{PACKAGE_NAME}", ["package.xml"]),
        (os.path.join("share", PACKAGE_NAME, "msg"), glob("msg/*.msg")),
        (os.path.join("share", PACKAGE_NAME, "srv"), glob("srv/*.srv")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="BoxBunny Team",
    maintainer_email="boxbunny@example.com",
    description="Custom ROS 2 message and service definitions for BoxBunny.",
    license="MIT",
)
