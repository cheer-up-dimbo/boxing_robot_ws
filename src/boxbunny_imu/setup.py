"""Setup configuration for boxbunny_imu package."""

from setuptools import setup
import os
from glob import glob

PACKAGE_NAME = "boxbunny_imu"

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
    description="IMU sensor integration for punch detection and classification using MPU6050.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "mpu6050_node = boxbunny_imu.mpu6050_node:main",
            "imu_punch_classifier = boxbunny_imu.imu_punch_classifier:main",
            "imu_punch_gui = boxbunny_imu.imu_punch_gui:main",
            "imu_input_selector = boxbunny_imu.imu_input_selector:main",
        ],
    },
)
