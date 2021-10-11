# Installation Instructions

It is recommended to work with [Python virtual environments](https://docs.python.org/3.7/library/venv.html#module-venv)
or conda environments. In this installation example, we assume that we are working on a Windows machine
and you have a working [Anaconda3](https://www.anaconda.com/products/individual/) installation available.
Also, make sure to have a version of [Git](https://git-scm.com) installed.

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
conda create -n LabExT_env python=3.7
conda activate LabExT_env
```
We name this environment `LabExT_env`, but you may also choose your own name.

!!! info
    Make sure to create the conda environment with Python version 3.7!

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


### Starting LabExT

Once you installed LabExT according to the instructions above and you wish to (re)start LabExT,
its sufficient to simply activate the anaconda environment again and then start LabExT.
So, open the "Anaconda Prompt" console via start menu, then type:
```
conda activate LabExT_env
``` 
Since LabExT is also a registered executable within this environment, the following is then sufficient to start it 
again:
```
LabExT
```

### Configuration

After the installation of LabExT, we suggest to configure the available instruments, see
[Configuration](./settings_configuration.md).
