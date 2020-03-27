#!/usr/bin/env python
from setuptools import find_packages, setup

setup(
    name="weblate_omp",
    version="0.4.1",
    author="Aleksandr Loktionov",
    author_email="a.loktionov@omprussia.ru",
    description="Package with Open Mobile Platform weblate specific extensions.",
    license="GNU GPLv3",
    keywords="omp weblate",
    packages=find_packages(),
    install_requires=["Weblate"],
)
