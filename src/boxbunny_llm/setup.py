"""Setup configuration for boxbunny_llm package."""

from setuptools import setup
import os
from glob import glob

PACKAGE_NAME = "boxbunny_llm"

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
    description="Local LLM-powered coaching feedback and interactive chat for boxing training.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "llm_talk_node = boxbunny_llm.llm_coach_node:main",
            "llm_chat_gui = boxbunny_llm.llm_chat_gui:main",
        ],
    },
)
