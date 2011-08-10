"""
     Installation script for DANSE calculator perspective for SansView
"""
import os

from distutils.core import setup
setup(
    version = "0.9",
    name="invariant",
    description = "Invariant perspective for SansView",
    package_dir = {"sans":os.path.join("src", "sans"),
                   "sans.perspectives":os.path.join("src", "sans",
                                                    "perspectives"),
                   "sans.perspectives.invariant":os.path.join("src",
                                                            "sans",
                                                            "perspectives",
                                                            "invariant"),
                   },
    package_data={'sans.perspectives.invariant': [os.path.join("media",
                                                               '*')]},
    packages = ["sans.perspectives",
                "sans",
                "sans.perspectives.invariant",],
    )
