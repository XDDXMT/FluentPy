"""Public and historical component imports resolve to the same Qt classes."""

import importlib
import unittest

import fluentpy
from fluentpy import widgets


class ModuleCompatibilityTests(unittest.TestCase):
    def test_previous_button_module_retains_every_export(self):
        previous = importlib.import_module("fluentpy.widgets.advanced_button")
        modules = {
            "button": ("AccentIconButton", "TransparentIconButton"),
            "toggle_button": ("ToggleButton", "ToggleIconButton", "PillToggleButton"),
            "menu_button": ("DropDownButton", "AccentDropDownButton"),
            "split_button": ("SplitButton", "AccentSplitButton"),
            "loading_button": ("LoadingButton",),
        }
        for module_name, names in modules.items():
            current = importlib.import_module("fluentpy.widgets." + module_name)
            for name in names:
                with self.subTest(component=name):
                    component = getattr(current, name)
                    self.assertIs(getattr(previous, name), component)
                    self.assertIs(getattr(fluentpy, name), component)
                    self.assertIs(getattr(widgets, name), component)

    def test_tray_menu_remains_available_from_action_menu_module(self):
        previous = importlib.import_module("fluentpy.widgets.action_menu")
        current = importlib.import_module("fluentpy.widgets.system_tray_menu")
        self.assertIs(previous.SystemTrayMenu, current.SystemTrayMenu)
        self.assertIs(fluentpy.SystemTrayMenu, current.SystemTrayMenu)
