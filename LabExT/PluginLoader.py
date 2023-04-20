#
# This file contains code that was borrowed from mammo0 on GitHub.
#
# This is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License version 3 as published by the Free Software
# Foundation.
#
# This software is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# Copyright: see https://github.com/mammo0/py-simple-plugin-loader
#

import inspect
import logging
import os
import pkgutil
import sys
from importlib import import_module
from typing import Any, List, Tuple, Dict


def import_plugins_from_paths(
    base_class: Any,
    search_paths: list = []
) -> Tuple[dict, dict]:
    """
    Imports all plugins of a base class from a list of search paths.
    Later plugins do not replace found plugins with the same name.
    Paths at higher positions in the list have, therefore, more priority.

    Parameters
    ----------
    base_class: Any
        Base class of the plugins to be imported.
    search_paths: list = []
        List of search paths

    Returns
    -------
    imported_plugins: dict
        Dictionary from all imported classes, indexed by class name
    search_stats: dict
        Indexed by search path, the number of imported classes is given.
    """
    plugin_loader = PluginLoader()

    imported_plugins = {}
    search_stats = {}

    for path in search_paths:
        newly_imported_classes = plugin_loader.load_plugins(
            path, plugin_base_class=base_class, recursive=True)
        unique_classes = {
            k: v for k,
            v in newly_imported_classes.items() if k not in imported_plugins}

        search_stats[path] = len(unique_classes)
        imported_plugins.update(unique_classes)

    return imported_plugins, search_stats


class PluginAPI:
    """
    Simple registry and interface for Plugin classes.
    """

    def __init__(
        self,
        base_class: Any,
        core_search_path: str
    ) -> None:
        self._base_class = base_class
        self._core_search_path = core_search_path

        self._imported_classes: Dict[str, Any] = {}
        self._import_stats: Dict[str, int] = {}

    def import_classes(self, search_paths: list = []) -> None:
        """
        Imports all Mover API classes.

        Parameters:
        -----------
        search_paths: list = []
            List of search paths to import from.
        """
        self._imported_classes, self._import_stats = import_plugins_from_paths(
            base_class=self._base_class, search_paths=[self._core_search_path] + search_paths)

    @property
    def imported_classes(self) -> Dict[str, Any]:
        """
        Returns a duct of all imported classes.
        Read-only.
        """
        return self._imported_classes

    @property
    def import_stats(self) -> Dict[str, int]:
        return self._import_stats


    def get_class(
        self,
        class_name: str,
        default: Any = None
    ) -> Any:
        """
        Returns class for given class name.
        """
        return self.imported_classes.get(str(class_name), default)

class PluginLoader:
    def __init__(self):
        self.__available_plugins = {}

        self.logger = logging.getLogger()

    @property
    def plugins(self):
        """
        Get all already loaded plugins.
        """
        return self.__available_plugins

    def load_plugins(self, path: str,
                     plugin_base_class: type,
                     specific_plugins: List[str] = [],
                     recursive: bool = False) -> dict:
        """
        Load all classes in a directory specified by 'path' that match the 'plugin_base_class' class.
        Alternatively if the 'specific_plugins' list contains class names, only those will be loaded.
        They don't need to be subclasses of e.g. 'SamplePlugin'.
        All other classes or methods are ignored.
        """
        # normalize the path
        path = os.path.abspath(os.path.normpath(path))

        # if path does not exist, warn user
        if not os.path.exists(path):
            self.logger.warning(f'Path {path:s} does not exist. Skipping...')
            return {}

        # add the parent path to the system PATH if it doesn't already exists
        # this is needed for the import later
        sys_path_modified = False
        if os.path.dirname(path) not in sys.path:
            # insert the parent path at index zero, because the loader should
            # look at this location first
            sys.path.insert(0, os.path.dirname(path))
            sys_path_modified = True

        # do the actual import
        plugins = self.__load(path,
                              # the module main package is the last directory
                              # of the path
                              os.path.basename(path),
                              plugin_base_class,
                              specific_plugins,
                              recursive)

        # reset the modified path again
        if (sys_path_modified and
                os.path.dirname(path) in sys.path):
            sys.path.remove(os.path.dirname(path))

        self.__available_plugins.update(plugins)
        return plugins

    def __load(self, path: str,
               package_name: str,
               plugin_base_class: type,
               specific_plugins: List[str] = [],
               recursive: bool = False) -> dict:
        plugins = {}
        # iterate over the modules that are within the path
        for (_, name, ispkg) in pkgutil.iter_modules([path]):
            if ispkg:
                if recursive:
                    plugins.update(self.__load(os.path.join(path, name),
                                               ".".join([package_name, name]),
                                               plugin_base_class,
                                               specific_plugins,
                                               recursive))
                    continue
                else:
                    # do not try to import it, since it's not a module
                    continue

            # import the module
            try:
                imported_module = import_module(".".join([package_name, name]))
            except (ImportError, OSError, ModuleNotFoundError) as e:
                self.logger.error("Can't import module '%s'! (%s) -> Skipping it.",
                                  ".".join([package_name, name]), str(e))
                continue

            plugin_found = False
            # try to find a subclass of the plugin class
            for i in dir(imported_module):
                attribute = getattr(imported_module, i)

                # first check if it's a class
                if (inspect.isclass(attribute) and
                        # check if only specific plugins should be loaded
                        ((specific_plugins and
                          # they must match the name case sensitive
                          attribute.__name__ in specific_plugins) or
                         # otherwise check for plugin subclass
                         (not specific_plugins and
                          issubclass(attribute, plugin_base_class) and
                          # but do not match the plugin class itself
                          attribute != plugin_base_class))):
                    # the plugin name is the class name
                    pn = attribute.__name__

                    # save the file path to the module from where we got that
                    # class from
                    mod_path = os.path.join(path, name) + '.py'
                    if not hasattr(attribute, 'PluginLoader_module_path'):
                        attribute.PluginLoader_module_path = [mod_path]
                    else:
                        attribute.PluginLoader_module_path.append(mod_path)

                    plugins[pn] = attribute
                    plugin_found = True

                    self.logger.debug("Imported plugin %s", pn)

            # remove imported module again if no plugin class is found
            if not plugin_found:
                del imported_module

        return plugins
