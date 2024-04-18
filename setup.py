import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    requirements = fh.read().splitlines()

setuptools.setup(
    name="LabExT_pkg",
    version="2.3.0",
    author="Institute of Electromagnetic Fields (IEF) at ETH Zurich",
    author_email="ief@ief.ee.ethz.ch",
    maintainer="Marco Eppenberger",
    maintainer_email="mail@mebg.ch",
    description="LabExT is a software environment for performing laboratory experiments on silicon-photonic devices.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/labext/LabExT",
    project_urls={
        "Documentation": "https://labext.readthedocs.io",
    },
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'LabExT = LabExT.Main:main',
        ],
    },
    include_package_data=True
)
