from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="mech-toolkit",
    version="1.0.0",
    description="A Python toolkit for common mechanical engineering hand calculations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Haneet",
    packages=find_packages(exclude=["tests", "examples"]),
    install_requires=[
        "numpy>=1.24",
        "matplotlib>=3.7",
    ],
    extras_require={
        "dev": ["pytest>=7.0"],
    },
    python_requires=">=3.9",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering",
    ],
)
