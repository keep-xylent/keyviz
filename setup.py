from setuptools import setup, find_packages

setup(
    name="keyviz",
    version="0.1.1",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "keyviz": ["*.json"],
    },
    entry_points={
        "console_scripts": [
            "keyviz=keyviz.main:main",
        ],
    },
    install_requires=[
        "PyQt6",
        "keyboard",
    ],
)
