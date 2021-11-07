# LabExT - Laboratory Experiment Tool

LabExT, short for Laboratory Experiment Tool, is a software environment for performing laboratory
experiments on silicon-photonic devices and chips. The tool is free, written in Python 3.8 and uses the I/O API VISA
through [pyvisa](https://github.com/pyvisa/pyvisa).

## Highlights
* Execute pre-defined measurement routines using laboratory instruments at any VISA address.
  * Measurement code and instrument driver code easily extensible via their API. 
* Immediately investigate and plot the resulting data.
  * A large set of meta-data is also recorded.
  * Commenting on resulting data is immediately possible after measurement.
* Chip-scale automation with motorized stages.
  * Supports coordinate files of on-chip devices and moves stages to correct locations (e.g. for coupling fibers to on-chip grating couplers).
  * Local optical coupling optimization including Gaussian mode profile fitting.
* High Usability
  * No Python coding knowledge necessary to execute lab experiments!
  * Keyboard shortcuts!

## Video
Before losing too many words, check out the following video which demonstrates how we use LabExT in our daily work:

< coming soon >

## Links
Here are the three most important pieces of documentation you will need:

* Full documentation incl. detailed installation instructions and getting started guide: [labext.readthedocs.io](https://labext.readthedocs.io/en/latest/).
* Press F1 in the main window to open the addon documentation.
* For guidelines on how to contribute to the LabExT codebase, see [the contribution guide](./CONTRIBUTING.md).

## Installation
Assuming you use conda as environment manager, installation is straight forward:
```
conda create -n LabExT_env python=3.8
conda activate LabExT_env
pip install LabExT-pkg
```

## Acknowledgements & Reference
LabExT is written in part by tireless folks at the
[Institute of Electromagnetic Fields, ETH Zurich, Switzerland](https://ief.ee.ethz.ch) as part of their daily grind in
an RF and optics laboratory.

Another big part is written by [Polariton Technologies AG](https://www.polariton.ch/) whose support and experience in
integrated optics design and the testing thereof we gratefully acknowledge.

If you use LabExT and believe that it helps you in your research as much as it helped us, consider citing us as follows:
```
M. Eppenberger, A. Messner, P. Wintermeyer, B. Baeuerle and J. Leuthold, "LabExT - Laboratory Experiment Tool," available on github.com/LabExT/LabExT, 2021.
```
