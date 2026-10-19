"""C Gregorian date coverage, with independent standard-library oracles.

The isolated package loads the real bindings and extension without importing
the Qt widgets. Calendar algorithms below are test oracles only.
"""

import calendar
import importlib.util
import os
import random
import sys
import types
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

_SOURCE = Path(__file__).resolve().parents[1] / "src" / "fluentpy"
_NAMESPACE = "_fluentpy_date_test_package"
_package = types.ModuleType(_NAMESPACE)
_package.__path__ = [str(_SOURCE)]
_subpackage = types.ModuleType(f"{_NAMESPACE}.backends")
_subpackage.__path__ = [str(_SOURCE / "backends")]
sys.modules[_NAMESPACE] = _package
sys.modules[_subpackage.__name__] = _subpackage
_spec = importlib.util.spec_from_file_location(
    f"{_NAMESPACE}.backends.date",
    _SOURCE / "backends" / "date.py",
)
backend = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = backend
_spec.loader.exec_module(backend)


def _as_tuple(value):
    return value.year, value.month, value.day


def _clamp_oracle(year, month, day, minimum, maximum):
    current = date(year, month, max(1, min(day, calendar.monthrange(year, month)[1])))
    return max(date(*minimum), min(date(*maximum), current))


def _interval_oracle(current, column, minimum, maximum):
    lower, upper = date(*minimum), date(*maximum)
    if column == 0:
        return lower.year, upper.year
    if column == 1:
        return (
            lower.month if current.year == lower.year else 1,
            upper.month if current.year == upper.year else 12,
        )
    return (
        lower.day if (current.year, current.month) == (lower.year, lower.month) else 1,
        upper.day
        if (current.year, current.month) == (upper.year, upper.month)
        else calendar.monthrange(current.year, current.month)[1],
    )


def _step_oracle(year, month, day, column, steps, minimum, maximum):
    current = _clamp_oracle(year, month, day, minimum, maximum)
    lower, upper = _interval_oracle(current, column, minimum, maximum)
    if column == 0:
        year, month, day = max(lower, min(upper, current.year + steps)), current.month, current.day
    elif column == 1:
        year, month, day = (
            current.year,
            lower + (current.month - lower + steps) % (upper - lower + 1),
            current.day,
        )
    else:
        year, month, day = (
            current.year,
            current.month,
            lower + (current.day - lower + steps) % (upper - lower + 1),
        )
    return _as_tuple(_clamp_oracle(year, month, day, minimum, maximum))


class DateBackendAvailabilityTests(unittest.TestCase):
    def test_missing_binary_falls_back_except_when_native_is_explicitly_required(self):
        with (
            patch.object(backend, "_extension", None),
            patch.object(backend, "_native_import_error", "test missing binary"),
        ):
            self.assertFalse(backend.native_available())
            self.assertEqual(backend.native_error(), "test missing binary")
            calls = (
                lambda: backend.days_in_month(2024, 2),
                lambda: backend.clamp_date(2024, 2, 31),
                lambda: backend.step_date(2024, 2, 29, 0, 1),
                lambda: backend.column_values(2024, 2, 29, 0),
                backend.backend_name,
            )
            for mode in ("auto", "python"):
                with patch.dict(os.environ, {"FLUENTPY_BACKEND": mode}):
                    self.assertEqual(backend.backend_name(), "python")
                    self.assertEqual(backend.days_in_month(2024, 2), 29)
                    self.assertEqual(backend.clamp_date(2024, 2, 31), (2024, 2, 29))
                    self.assertEqual(backend.step_date(2024, 2, 29, 0, 1), (2025, 2, 28))
                    self.assertEqual(backend.column_values(2024, 2, 29, 0)[4], 2024)
            with patch.dict(os.environ, {"FLUENTPY_BACKEND": "native"}):
                for call in calls:
                    with self.assertRaisesRegex(RuntimeError, "Rebuild.*build_native.py"):
                        call()

    def test_real_import_handles_a_missing_and_a_text_only_extension(self):
        for name, extension in (
            ("missing", None),
            ("old", types.SimpleNamespace(json_spans=lambda text: [])),
        ):
            namespace = f"_fluentpy_date_{name}_test"
            package = types.ModuleType(namespace)
            package.__path__ = []
            subpackage = types.ModuleType(f"{namespace}.backends")
            subpackage.__path__ = [str(_SOURCE / "backends")]
            with patch.dict(sys.modules, {namespace: package, subpackage.__name__: subpackage}):
                spec = importlib.util.spec_from_file_location(
                    f"{namespace}.backends.date",
                    _SOURCE / "backends" / "date.py",
                )
                module = importlib.util.module_from_spec(spec)
                if extension is None:
                    spec.loader.exec_module(module)
                else:
                    with patch("importlib.import_module", return_value=extension):
                        spec.loader.exec_module(module)
                self.assertFalse(module.native_available())
                self.assertIn("_native", module.native_error())
                with patch.dict(os.environ, {"FLUENTPY_BACKEND": "auto"}):
                    self.assertEqual(module.days_in_month(2024, 2), 29)
                with patch.dict(os.environ, {"FLUENTPY_BACKEND": "native"}):
                    with self.assertRaisesRegex(RuntimeError, "compiled fluentpy._native"):
                        module.days_in_month(2024, 2)


class NativeDateTests(unittest.TestCase):
    def test_backend_selection_is_consistent_with_global_mode(self):
        for mode in ("auto", "python", "native"):
            with patch.dict(os.environ, {"FLUENTPY_BACKEND": mode}):
                if mode == "native" and not backend.native_available():
                    with self.assertRaises(RuntimeError):
                        backend.backend_name()
                    continue
                self.assertEqual(
                    backend.backend_name(),
                    "python" if mode == "python" or not backend.native_available() else "native",
                )
                self.assertEqual(backend.days_in_month(2024, 2), 29)

    def test_gregorian_leap_centuries_and_month_lengths(self):
        for year in (1, 4, 100, 400, 1600, 1700, 1900, 1996, 2000, 2023, 2024, 2100, 2400, 9999):
            for month in range(1, 13):
                with self.subTest(year=year, month=month):
                    self.assertEqual(
                        backend.days_in_month(year, month), calendar.monthrange(year, month)[1]
                    )
        self.assertEqual(backend.days_in_month(year=2000, month=2), 29)

    def test_clamps_days_and_complete_date_bounds(self):
        self.assertEqual(backend.clamp_date(2024, 2, 31), (2024, 2, 29))
        self.assertEqual(backend.clamp_date(2023, 2, 29), (2023, 2, 28))
        self.assertEqual(backend.clamp_date(2024, 4, 31), (2024, 4, 30))
        self.assertEqual(backend.clamp_date(2024, 1, -(10**200)), (2024, 1, 1))
        self.assertEqual(backend.clamp_date(2024, 1, 10**200), (2024, 1, 31))
        limits = {"minimum": (2024, 2, 14), "maximum": (2025, 4, 8)}
        self.assertEqual(backend.clamp_date(year=2024, month=1, day=31, **limits), (2024, 2, 14))
        self.assertEqual(backend.clamp_date(2025, 4, 30, **limits), (2025, 4, 8))
        self.assertEqual(backend.clamp_date(2024, 2, 29, **limits), (2024, 2, 29))

    def test_year_month_day_columns_are_independent(self):
        self.assertEqual(backend.step_date(2024, 2, 29, 0, 1), (2025, 2, 28))
        self.assertEqual(backend.step_date(2024, 1, 31, 1, 1), (2024, 2, 29))
        self.assertEqual(backend.step_date(2023, 1, 31, 1, 1), (2023, 2, 28))
        self.assertEqual(backend.step_date(2024, 12, 31, 1, 1), (2024, 1, 31))
        self.assertEqual(backend.step_date(2024, 1, 31, 1, -1), (2024, 12, 31))
        self.assertEqual(backend.step_date(2024, 2, 29, 2, 1), (2024, 2, 1))
        self.assertEqual(backend.step_date(2024, 3, 1, 2, -1), (2024, 3, 31))
        self.assertEqual(backend.step_date(1, 1, 1, 0, -1), (1, 1, 1))
        self.assertEqual(backend.step_date(9999, 12, 31, 0, 1), (9999, 12, 31))

    def test_partial_year_and_month_ranges(self):
        limits = {"minimum": (2024, 5, 14), "maximum": (2025, 4, 8)}
        cases = [
            ((2025, 3, 31, 0, -1), (2024, 5, 14)),
            ((2024, 12, 31, 0, 1), (2025, 4, 8)),
            ((2024, 5, 14, 1, -1), (2024, 12, 14)),
            ((2025, 4, 8, 1, 1), (2025, 1, 8)),
            ((2024, 5, 14, 2, -1), (2024, 5, 31)),
            ((2025, 4, 8, 2, 1), (2025, 4, 1)),
        ]
        for arguments, expected in cases:
            self.assertEqual(backend.step_date(*arguments, **limits), expected)
        single_month = {"minimum": (2024, 2, 14), "maximum": (2024, 2, 18)}
        self.assertEqual(backend.step_date(2024, 2, 14, 2, -1, **single_month), (2024, 2, 18))
        self.assertEqual(backend.step_date(2024, 2, 18, 1, 100, **single_month), (2024, 2, 18))

    def test_extreme_signed_steps_and_integer_subclasses(self):
        class IntSubclass(int):
            def __mod__(self, other):
                raise AssertionError("calendar must not invoke Python modulo overrides")

        steps_values = (0, 2**31 - 1, -(2**31), 2**63 - 1, -(2**63), 10**500, -(10**500))
        minimum, maximum = (1900, 3, 11), (2400, 10, 21)
        for column in range(3):
            for steps in steps_values:
                for value in (steps, IntSubclass(steps)):
                    with self.subTest(column=column, steps=str(steps)[:30]):
                        self.assertEqual(
                            backend.step_date(2024, 2, 29, column, value, minimum, maximum),
                            _step_oracle(2024, 2, 29, column, steps, minimum, maximum),
                        )

    def test_centered_rows_wrap_and_empty_year_boundaries(self):
        self.assertEqual(backend.column_values(1, 1, 1, 0), (None, None, None, None, 1, 2, 3, 4, 5))
        self.assertEqual(
            backend.column_values(9999, 12, 31, 0, radius=2), (9997, 9998, 9999, None, None)
        )
        self.assertEqual(backend.column_values(2024, 1, 31, 1, radius=2), (11, 12, 1, 2, 3))
        self.assertEqual(backend.column_values(2024, 2, 1, 2, radius=2), (28, 29, 1, 2, 3))
        self.assertEqual(backend.column_values(2024, 2, 29, 2, radius=0), (29,))
        rows = backend.column_values(year=2024, month=2, day=29, column=2, radius=5)
        self.assertEqual(len(rows), 11)
        self.assertEqual(rows[5], 29)
        self.assertEqual(len(backend.column_values(2024, 2, 1, 2, radius=100)), 201)

    def test_single_value_columns_only_populate_the_center(self):
        limits = {"minimum": (2024, 2, 14), "maximum": (2024, 2, 18)}
        expected = (None, None, 2024, None, None)
        self.assertEqual(backend.column_values(2024, 2, 15, 0, radius=2, **limits), expected)
        self.assertEqual(
            backend.column_values(2024, 2, 15, 1, radius=2, **limits), (None, None, 2, None, None)
        )
        self.assertEqual(
            backend.column_values(2024, 2, 14, 2, radius=2, **limits), (17, 18, 14, 15, 16)
        )
        for column, value in enumerate((2024, 2, 15)):
            limits = {"minimum": (2024, 2, 15), "maximum": (2024, 2, 15)}
            self.assertEqual(
                backend.column_values(2024, 2, 15, column, radius=1, **limits), (None, value, None)
            )
            self.assertEqual(
                backend.step_date(2024, 2, 15, column, 10**300, **limits), (2024, 2, 15)
            )

    def test_random_dates_steps_and_rows_match_standard_library(self):
        randomizer = random.Random(0xDA7E2024)
        for _ in range(800):
            minimum, maximum = sorted(
                _as_tuple(date.fromordinal(randomizer.randint(1, date.max.toordinal())))
                for _ in range(2)
            )
            year, month, day = (
                randomizer.randint(1, 9999),
                randomizer.randint(1, 12),
                randomizer.randint(-10, 70),
            )
            current = _clamp_oracle(year, month, day, minimum, maximum)
            self.assertEqual(
                backend.days_in_month(year, month), calendar.monthrange(year, month)[1]
            )
            self.assertEqual(
                backend.clamp_date(year, month, day, minimum, maximum), _as_tuple(current)
            )
            for column in range(3):
                steps = randomizer.choice((randomizer.randint(-10000, 10000), 10**100, -(10**100)))
                self.assertEqual(
                    backend.step_date(year, month, day, column, steps, minimum, maximum),
                    _step_oracle(year, month, day, column, steps, minimum, maximum),
                )
                radius = randomizer.randint(0, 7)
                lower, upper = _interval_oracle(current, column, minimum, maximum)
                center = _as_tuple(current)[column]
                expected = tuple(
                    None
                    if (column == 0 and not lower <= center + offset <= upper)
                    or (lower == upper and offset != 0)
                    else center + offset
                    if column == 0
                    else lower + (center - lower + offset) % (upper - lower + 1)
                    for offset in range(-radius, radius + 1)
                )
                self.assertEqual(
                    backend.column_values(year, month, day, column, radius, minimum, maximum),
                    expected,
                )

    def test_rejects_booleans_and_non_integer_date_fields(self):
        for value in (True, False, None, 2024.0, "2024", b"2024", [], {}):
            for call in (
                lambda: backend.days_in_month(value, 2),
                lambda: backend.days_in_month(2024, value),
                lambda: backend.clamp_date(2024, 2, value),
                lambda: backend.step_date(2024, 2, 29, value, 1),
                lambda: backend.step_date(2024, 2, 29, 0, value),
                lambda: backend.column_values(2024, 2, 29, 0, value),
            ):
                with self.subTest(value=value), self.assertRaises(TypeError):
                    call()

    def test_rejects_out_of_range_fields_and_invalid_bounds(self):
        for year in (0, -1, 10000, 10**100, -(10**100)):
            with self.assertRaises(ValueError):
                backend.days_in_month(year, 2)
            with self.assertRaises(ValueError):
                backend.clamp_date(year, 2, 1)
        for month in (0, -1, 13, 10**100):
            with self.assertRaises(ValueError):
                backend.clamp_date(2024, month, 1)
        for column in (-1, 3, 10**100):
            with self.assertRaises(ValueError):
                backend.step_date(2024, 2, 29, column, 1)
            with self.assertRaises(ValueError):
                backend.column_values(2024, 2, 29, column)
        for radius in (-1, 101, 10**100):
            with self.assertRaises(ValueError):
                backend.column_values(2024, 2, 29, 0, radius)
        invalid_bounds = (
            (0, 1, 1),
            (10000, 1, 1),
            (2024, 0, 1),
            (2024, 13, 1),
            (2024, 2, 0),
            (2024, 2, 30),
            (2023, 2, 29),
            (),
            (2024, 2),
            (2024, 2, 1, 0),
        )
        for bound in invalid_bounds:
            for keyword in ("minimum", "maximum"):
                with self.subTest(keyword=keyword, bound=bound), self.assertRaises(ValueError):
                    backend.clamp_date(2024, 2, 29, **{keyword: bound})
        for bound in (None, True, 2024, (True, 2, 1), (2024, False, 1), (2024, 2, True)):
            with self.assertRaises(TypeError):
                backend.clamp_date(2024, 2, 29, minimum=bound)
        for call in (
            backend.clamp_date,
            lambda *a, **kw: backend.step_date(*a, 0, 1, **kw),
            lambda *a, **kw: backend.column_values(*a, 0, **kw),
        ):
            with self.assertRaisesRegex(ValueError, "minimum"):
                call(2024, 2, 1, minimum=(2025, 1, 1), maximum=(2024, 1, 1))


if __name__ == "__main__":
    unittest.main()
