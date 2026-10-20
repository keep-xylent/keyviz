from setuptools import setup, find_packages

setup(
    name="keyviz",
    version="0.2.1",
    description="Real-time modern keyboard visualizer and overlay built with Python and PyQt6",
    author="Ikbal Habibi (keep-xylent)",
    author_email="ikbalhabibi8@gmail.com",
    url="https://github.com/keep-xylent/keyviz",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "keyviz": ["*.json", "*.png"],
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
