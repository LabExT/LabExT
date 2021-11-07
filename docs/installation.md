# Installation Instructions

It is recommended to work with [Python virtual environments](https://docs.python.org/3.8/library/venv.html#module-venv)
or conda environments. In these installation examples, we assume that we are working on a Windows machine
and you have a working [Anaconda3](https://www.anaconda.com/products/individual/) installation available.

If you just want to use LabExT and are not interested in code development, follow the
[Installation for Usage](installation.md#installation-for-usage) instructions. If you plan to change code and do some
development for LabExT, follow the [Installation for Development](installation.md#installation-for-development)
instructions.

After the installation of LabExT, we suggest to configure the available instruments, see
[Configuration](./settings_configuration.md).

## Installation for Usage
We assume that you have Anaconda installed (or anything else that provide the conda environment manager). Open the 
"Anaconda Prompt" console, then the installation for usage is straight forward via conda and pip:
```
conda create -n LabExT_env python=3.8
conda activate LabExT_env
pip install LabExT-pkg
```

The installation also works into a native Python venv. In any case, we heavily recommend the usage of any type of
environment (conda, venv, ...) as LabExT installs quite a few dependencies.

### Starting LabExT

Once you installed LabExT and you wish to (re)start LabExT,
its sufficient to simply activate the conda environment again and then start LabExT.
So, open the "Anaconda Prompt" console via start menu, then type:
```
conda activate LabExT_env
``` 
Since LabExT is also a registered executable within this environment, the following is then sufficient to start it 
again:
```
LabExT
```

## Installation for Development
Follow these steps if you plan on developing LabExT or if you want to change code. Also, make sure to have a version
of [Git](https://git-scm.com) installed.

!!! note
    Note that if you only want to add  instrument drivers or measurement algorithms, the usage installation above is
    sufficient and you can use the addon system to load your additional classes. See the
    [Configuration page](./settings_configuration.md#specify-addon-directories).

### Download

Clone this GitHub repo onto your local machine using Git Bash:
```
git clone git@github.com:LabExT/LabExT.git
```

Take note where you cloned this repo to. Lets assume the repo is at `<labext-path>`.

### Create Conda Environment

Open the "Anaconda Prompt" console via the start menu and create a separate Python environment for LabExT and activate
it.
```
conda create -n LabExT_env python=3.8
conda activate LabExT_env
```
We name this environment `LabExT_env`, but you may also choose your own name.

!!! info
    LabExT is currently tested with Python 3.7 and 3.8. Make sure to specify one of those versions in your environment.

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
