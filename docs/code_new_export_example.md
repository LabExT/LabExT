# Example: New Export Format

For this example on how to get started, we'll be extending LabExT to export measurement data to a text (.txt) file.


We start by creating a subclass of the provided `ExportFormatStep` class.

`FORMAT_TITLE` is the string used as an option in the export dialog.
```python
from os import path
from pathlib import Path

from LabExT.Exporter.ExportStep import ExportFormatStep

class ExportTXT(ExportFormatStep):
    FORMAT_TITLE = "Text File (.txt)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
```
We need to define some custom behavior to export our data. the `_export` method is called in a seperate thread (as the UI displays a progress bar) and is responsible for writing the measurement data.
```python
  def _export(self, data):
        """ Implementation of export in Text format. """
        print("Exporting data to Text format ...")
```

By default, the `ExportFormatStep` asks the user for a directory path and makes the result avalible in `self.export_path.get()`. This behavior can be changed by overloading the `build(self, frame)` method.

```python
        directory_path = self.export_path.get()
```
We then write each measurement to a text file.
```python
        file_names = []
        for measurement in data:
            # get output directory and check for overwriting
            orig_file_name = Path(measurement['file_path_known']).stem
            output_name = path.join(directory_path, orig_file_name) + ".txt"

            if path.exists(output_name):
                self.wizard.logger.warning("Not exporting {:s} due to existing target file.".format(output_name))
                continue

            # write to file
            with open(output_name, 'w', newline='\n', encoding='utf-8') as file:
                file.write("My LabExT Export\n")
                for key, value in measurement["values"].items():
                    file.write(f"{key}: ")
                    file.write(", ".join(values))
                    file.write("\n")

            file_names.append(output_name)

        self.wizard.logger.info('Exported %s files as .txt: %s', len(file_names), file_names)
```
Calling `export_success` lets the wizard know it is ready to move onto the final step.
```python
        self.export_success()
```

Once the export is finished, wizard will then call `build_overview(self, frame)` to build an overview the the exported data. By default, this displays a treeview of the exported data.