# Mover APIs

LabExT's Mover offers several possibilities to extend functionalities by user-defined code.
This guide gives practical hints to extend the Mover.

## Stages

To support another Stage, a new Stage implementation must be created.
Currently, the [following stages]() are supported in LabExT-Core.
New stages can be included by an addon path or permanently supported in Core by creating a pull request.

Each new stage must inherit from the abstract interface Stage in order to be included by LabExT:

```py
from LabExT.Movement.Stage import Stage

class MyNewStage(Stage):
    pass
```

The [Stage]() interface defines all the methods and properties that each new implementation must define to work correctly.
Below we provide notes on the methods and properties to implement:

::: LabExT.Movement.Stage.Stage
    rendering:
        show_root_heading: true
        sort_members: source


## Stage Polygons
TODO


## Path Planning Algorithms
The Mover APIs offer the possibility to extend LabExT with user-defined path planning.
For this purpose, an interface PathPlanning was defined, from which a concrete new implementation must inherit:

```py
from LabExT.Movement.PathPlanning import PathPlanning

class MyPathPlanning(PathPlanning):
    pass
```

Below we provide notes on the methods and properties to implement:

::: LabExT.Movement.PathPlanning.PathPlanning
    rendering:
        show_root_heading: true
        sort_members: source