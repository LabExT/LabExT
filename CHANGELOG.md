## Version 2.1.1
Released 2021-11-07

* feature: LabExt is now pip installable. Documentation is updated to reflect this.
* community: added GitHub issue and PR templates
* under-the-hood: LabExt is now Python 3.7 and 3.8 compatible. Suggested version is 3.8.

## Version 2.1.0
Released 2021-09-06

* feature: A new live viewer GUI is released. It allows to control multiple lasers and power meter channels at the same time and is easily extensible for live-controlling other instruments.
* feature: New, faster search-for-peak with logged power meter and continuous piezo-stage movement. (Only possible with N7744A power meters.)
* bugfix: Piezo stage speeds were wrongly loaded from old save files. The stage API has all units in microns, and not any more nano-meters. A warning to the user is displayed if speed control is off (i.e. speed 0).
* bugfix: LabExT now starts properly on Linux.

## Version 2.0.2
Released 2021-05-03

* feature: A faster, swept search-for-peak (SfP) algorithm is available. The SfP method can be chosen in the Search-for-Peak window as parameter.
* bugfix: Instrument connections were not closed properly after reading instrument properties provoking some more Error 9s.

## Version 2.0.1
Released 2021-02-22

* usability: A comprehensive browser-based help is now accessible via the F1 key inside LabExT or via the Help menu. Try it out!
* usability: A small tool-tip now explains every measurement in more detail, whenever you need to select a measurement.
* usability: Improved during-runtime performance by caching ad-hoc classes at program startup.
* bugfix: Search for peak can now again be enabled in multi-device scans.
* under-the-hood: Updated dependencies to latest versions.
* under-the-hood: Templates for issues and feature requests are now available on the issue tracker.
* under-the-hood: Added author list and contributing guide as part of new help.

## Version 2.0.0
Released 2021-01-15

* under-the-hood: A long awaited feature has finally made into a release: After long trials, it is now possible to run measurements in standalone scripts w/o GUI. This required a change of how Measurements are interfacing with LabExT and required breaking changes, hence the major version upgrade.
  * All previously coded measurements were translated to the new API and are ready to use.
  * Measurement parameter types are more tightly controlled: you can specify int and float for number types.
* usability: Every measurement now has a documentation string associated which details parameters and recommended lab setup.
