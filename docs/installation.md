# Installation Instructions

It is recommended to work with [Python virtual environments](https://docs.python.org/3.9/library/venv.html#module-venv)
or conda environments. In these installation examples, we assume that we are working on a Windows machine
and you have a working [Anaconda3](https://www.anaconda.com/products/individual/) installation available.

If you just want to use LabExT and are not interested in code development, follow the
[Installation for Usage](installation.md#installation-for-usage) instructions. If you plan to change code and do some
development for LabExT, follow the [Installation for Development](setup_dev_env.md) instructions.

After the installation of LabExT, we suggest to configure the available instruments, see
[Configuration](./settings_configuration.md).

## Installation for Usage
We assume that you have Anaconda installed (or anything else that provides the conda environment manager). Open the 
"Anaconda Prompt" console, then the installation for usage is straight forward via conda and pip:
```
conda create -n LabExT_env python=3.9
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

!!! hint
    Since LabExT is now registered as a module, you can access modules of LabExT simply by
    doing `from LabExT.Instruments.XXX import XXX` from any script executed in your Python environment.
    This can be very helpful for custom scripts which use part of LabExT (e.g. instrument driver classes, or
    Piezo Stage drivers) but are not integrated into LabExT.
