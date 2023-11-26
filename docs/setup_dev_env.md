# Development Environment Setup Instructions

This page shows you how to setup your development environment for developing LabExT, we show how to locally 
run the tests and how to render the documentation. If you are only interested in using LabExT, see [the 
installation instructions for users](installation.md).

## Installation of LabExT via Git
Follow these steps if you plan on developing LabExT or if you want to change code. Make sure to have a version
of [Git](https://git-scm.com) installed. Also, we use conda environments for separating Python installations.

!!! note
    Note that if you only want to add  instrument drivers or measurement algorithms, the
    [user installation](installation.md) is sufficient and you can use the addon system to load your additional
    classes. See the [configuration page](./settings_configuration.md#specify-addon-directories).

### Download

Clone the GitHub repo of LabExT onto your local machine using Git Bash:
```
git clone git@github.com:LabExT/LabExT.git
```

Take note where you cloned this repo to. Lets assume the repo is at `<labext-path>`.

!!! hint
    Please fork the project on GitHub and clone your fork if you plan on contributing. You will need to replace above's
    repo URL with your own.

### Create Conda Environment

Open the "Anaconda Prompt" console via the start menu and create a separate Python environment for LabExT and activate
it.
```
conda create -n LabExT_env python=3.9
conda activate LabExT_env
```
We name this environment `LabExT_env`, but you may also choose your own name. LabExT is currently tested with
Python 3.9 and 3.10. Make sure to specify one of those versions in your environment.

### Install LabExT

Within this environment, we install all requirements of LabExT. This step needs to be repeated every time a dependency
is updated. Make sure you change to the root folder of the cloned repo, otherwise pip will not find the file.
```
cd <labext-path>
pip install -r ./requirements.txt
```

!!! info
    Make sure to use the requirements**.txt** file, and not the requirements**.in** file!

The next step is to register LabExT as a module in your Python environment. We install it as editable (`-e`) so you can
easily change Python code without having to re-install every time. Type the following commands:
```
pip install -e <labext-path>
```

Finally, run LabExT by typing:
```
LabExT
```
A highly recommended alternative to start LabExT is by using your favourite Python IDE.

!!! hint
    Since LabExT is now registered as a module, you can access modules of LabExT simply by
    doing `from LabExT.Instruments.XXX import XXX` from any script executed in your Python environment.
    This can be very helpful for custom scripts which use part of LabExT (e.g. instrument driver classes, or
    Piezo Stage drivers) but are not integrated into LabExT.

## Running Tests

To run the unittests locally, follow these instructions. You will need to work in your conda environment where you
installed LabExT for development.

Install `pytest` and `tox`:
```
pip install pytest tox --upgrade
```


### Running Testsuits
Test cases in LabExT are divided into lab tests and normal tests. Lab tests require lab equipment and are therefore skipped when the test suite is running in CI.

- To run the complete CI test suite with Python version 3.9 and 3.10 use:
```
cd <labext-path>
tox
```

- To run the CI test suite with your current Python version, use:
```
cd <labext-path>
python -m LabExT.Tests.runtests
```

- To run the CI test suite **and** the laboratory tests use the `--laboratory_tests` flag:
```
cd <labext-path>
python -m LabExT.Tests.runtests --laboratory_tests
```

On every push and every pull request to the LabExT repo, tox is run. A pull request needs to pass all tests to be
considered for merging.

### Run GitHub Actions Locally

GitHub actions are used to automate testing in the LabExT Git repo. You can use [act](https://github.com/nektos/act) to
simulate Github Actions on your local machine and to debug them. Make sure that docker is installed.

To run either of the CI workflows we have, use:
```
act push
```
or 
```
act pull_request
```

## Render Documentation Locally

We use mkdocs to generate the public documentation on https://labext.readthedocs.io. The online documentation always 
shows documentation of the latest commit in the main branch and is automatically updated. To locally display the 
documentation, e.g. to see how your changes would look like, use the following commands.
You will need to work in your conda environment where you installed LabExT for development.
```
cd <labext-path>
mkdocs serve
```
Then open any browser on your machine and point it to http://127.0.0.1:8000/ or wherever mkdocs tells you. You should
now see the locally rendered documentation.
