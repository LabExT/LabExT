import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    requirements = fh.read().splitlines()

setuptools.setup(
    name="LabExT",
    version="2.1.0",
    author="Institute of Electromagnetic Fields (IEF) at ETH Zurich",
    author_email="ief@ief.ee.ethz.ch",
    description="LaboratoryExperimentTool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://git.ee.ethz.ch/labext/LabExT",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'LabExT = LabExT.Main:main',
        ],
    },
    package_data={
        '': ['*.ini', '*.config']
    }
)
