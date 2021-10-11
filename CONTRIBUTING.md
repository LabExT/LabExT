# LabExT Contribution Guide
This file describes how developers may contribute to the project and get their own code incorporated into the
LabExt codebase.

### Reporting Bugs
#### Due diligence
Before submitting a bug, please do the following:

* Perform basic troubleshooting steps:
  * Make sure you’re on the latest version. Upgrading to the newest version on the master branch is always the best 
    first step as your problem may have been solved already!
  * Try upgrading dependency versions. (`pip install -r requirements.txt` inside your conda environment)
  * Maybe also try older versions: Roll back a few minor versions and see if the problem goes away. This will help the
    devs narrow down when the problem first arose.
* Search the [bug/issue tracker](https://github.com/LabExT/LabExT/issues) to make sure it’s not a known issue.

#### What to put into your bug report
Make sure your report gets the attention it deserves: bug reports with missing information may be ignored or punted back
to you, delaying a fix. The below constitutes a bare minimum; more info is almost always better:

* What operating system are you on? Windows? (7? 10? 32-bit? 64-bit?) Mac OS X? (10.7.4? 10.9.0?) Linux? (Which 
  distro? Which version of that distro? 32 or 64 bits?) Again, more detail is better.
* Which version resp. which Git commit of LabExT are you using? Ideally, you followed the advice above and have ruled
  out (or verified that the problem exists in) a few different versions.
* How can the developers recreate the bug on their end? Include a step-by-step list of what you did. If possible,
  include a copy of your code, the command you used to invoke it, and the full output of your run.
  * Include a description of what actually happened and what you expected to happen.
    
### Contributing Changes
#### Licensing of contributed material
Keep in mind as you contribute, that code, docs and other material submitted to LabExT are considered licensed under the
[GNU General Public Licence v3](https://www.gnu.org/licenses/gpl-3.0.en.html).

#### Before you start
We recommend getting in touch with the current developers and maintainers before you start implementing a feature. We 
can also point you to the right points in the codebase to start implementing.

* the [existing issues](https://github.com/LabExT/LabExT/issues)
* the bi-weekly LabExT online meeting to which the invitations are sent around in
* the developers mailing list < link coming soon >

#### Git branching and merge requests

* Always work in your own fork of LabExT and make a new branch for your work, no matter how small. This makes it easy
for others to take just that one set of changes from your repository, in case you have multiple unrelated changes
floating around.
  * A corollary: don’t submit unrelated changes in the same branch/pull request! The maintainer shouldn’t have to reject
    your awesome bugfix because the feature you put in with it needs more review.
* Base your new branch off the `dev` branch on the main repository.
  * Note that depending on how long it takes for the dev team to merge your patch, the copy of `dev` you worked off of 
    may get out of date! If you find yourself ‘bumping’ a pull request that’s been sidelined for a while, make sure you
    rebase or merge to latest `dev` to ensure a speedier resolution.
* Once you are done implementing a feature, open a
  [pull request here](https://github.com/LabExT/LabExT/pulls) to the `dev` branch. Use the provided 
  template to describe your changes. Then assign one of the project maintainers such that
  code-review can begin. And please be patient - the maintainers will get to you when they can.

#### Code formatting

* Follow the [PEP-8](https://www.python.org/dev/peps/pep-0008/) guidelines. Most Python IDEs should have some form or
  the other of checking, if your code conforms to these.
                
#### Documentation isn't optional
It’s not! Patches without documentation will be returned to sender. By "documentation" we mean:

* Docstrings must be created or updated for public API functions/methods/etc. (This step is optional for some bugfixes.)
* New features should include updates to prose documentation, including useful example code snippets.
* If you write a subclass of `Measurement`, you MUST include a docstring in 
  [Markdown format](https://www.markdownguide.org/basic-syntax) listing
    1. purpose, example application and scientific use of the measurement
    1. an example laboratory setup
    1. a detailed description of all parameters
    1. links to further documentation, if applicable
* If you write a subclass of `Instrument`, you MUST include a docstring in 
  [Markdown format](https://www.markdownguide.org/basic-syntax) listing
    1. purpose, example application and scientific use of the instrument
    1. a full list of all known compatible instrument model numbers
    1. peculiarities of the driver class resp. instrument

If you are unsure about how to write documentation, see the already existing files for reference, and
discuss your suggestions and thoughts with other active developers or the project maintainers.
