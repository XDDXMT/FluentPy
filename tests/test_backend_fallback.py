"""Differential policies and fresh-process UI checks with no usable C binary."""
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

from fluentpy.backends import date, drop, shortcut, text
from fluentpy.backends import _date_python, _drop_python, _shortcut_python

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src/fluentpy'


def outcome(call):
    try:
        return ('value', call())
    except Exception as error:
        return ('error', type(error))


class BackendFallbackTests(unittest.TestCase):
    def test_all_components_fall_back_in_auto_and_keep_native_mode_explicit(self):
        for backend, operation in ((date, lambda: date.days_in_month(2024, 2)),
                (drop, lambda: drop.normalize_extensions(['PNG'])),
                (shortcut, lambda: shortcut.normalize(65, 0x04000000)),
                (text, lambda: text.json_spans('true'))):
            with self.subTest(backend=backend.__name__), patch.object(backend, '_extension', None):
                for mode in ('auto', 'python'):
                    with patch.dict(os.environ, {'FLUENTPY_BACKEND': mode}):
                        self.assertEqual(backend.backend_name(), 'python')
                        self.assertFalse(backend.native_available())
                        operation()
                with patch.dict(os.environ, {'FLUENTPY_BACKEND': 'native'}):
                    with self.assertRaisesRegex(RuntimeError, 'FLUENTPY_BACKEND=native.*compiled'):
                        operation()

    def test_invalid_mode_is_rejected_consistently(self):
        with patch.dict(os.environ, {'FLUENTPY_BACKEND': 'not-a-backend'}):
            for backend in (date, drop, shortcut, text):
                with self.subTest(backend=backend.__name__), self.assertRaisesRegex(ValueError, 'FLUENTPY_BACKEND'):
                    backend.backend_name()

    def test_python_mode_never_calls_an_available_native_function(self):
        fake = unittest.mock.Mock()
        with patch.dict(os.environ, {'FLUENTPY_BACKEND': ' python '}):
            for backend in (date, drop, shortcut, text):
                with patch.object(backend, '_extension', fake):
                    self.assertEqual(backend.backend_name(), 'python')
                    if backend is date:
                        self.assertEqual(date.days_in_month(2024, 2), 29)
                    elif backend is drop:
                        self.assertEqual(drop.normalize_extensions(['PNG']), ('.png',))
                    elif backend is shortcut:
                        self.assertEqual(shortcut.normalize(97, 0), (65, 0))
                    else:
                        self.assertEqual(text.json_spans('true'), [(0, 4, 3)])
        self.assertEqual(fake.mock_calls, [])

    def test_older_extension_falls_back_per_feature_without_disabling_valid_features(self):
        namespace = '_fluentpy_older_extension'
        package, backends = types.ModuleType(namespace), types.ModuleType(namespace+'.backends')
        package.__path__, backends.__path__ = [], [str(SRC / 'backends')]
        fake = types.SimpleNamespace(json_spans=lambda value: [(0, len(value), 3)],
                                     date_days_in_month=lambda *a: 99)
        with patch.dict(sys.modules, {namespace: package, backends.__name__: backends}), \
                patch.dict(os.environ, {'FLUENTPY_BACKEND':'auto'}), \
                patch('importlib.import_module', return_value=fake):
            for name in ('date', 'drop', 'shortcut', 'text'):
                spec = importlib.util.spec_from_file_location(f'{namespace}.backends.{name}', SRC / 'backends' / f'{name}.py')
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if name == 'text':
                    self.assertTrue(module.native_available())
                    self.assertEqual(module.backend_name(), 'native')
                else:
                    self.assertFalse(module.native_available())
                    self.assertEqual(module.backend_name(), 'python')
                    self.assertIsNotNone(module.native_error())

    def test_compatibility_normalizes_integer_subclasses_before_arithmetic(self):
        class Integer(int):
            def __mod__(self, _other):
                raise AssertionError('subclass arithmetic hook')
            __and__ = __add__ = __lt__ = __mod__
        self.assertEqual(_date_python.step_date(Integer(2024), Integer(2), Integer(29), Integer(1), Integer(1)), (2024,3,29))
        self.assertEqual(_shortcut_python.normalize(Integer(97), Integer(0x04000000)), (65,0x04000000))
        self.assertEqual(_drop_python.filter_paths([('a.png',Integer(1))],['png']), ([('a.png',1)],[]))


@unittest.skipUnless(date.native_available() and drop.native_available() and shortcut.native_available(), 'C comparison requires the current optional extension')
class DifferentialFallbackTests(unittest.TestCase):
    def test_calendar_matches_c_for_random_ranges_and_extreme_steps(self):
        from datetime import date as Date
        randomizer = random.Random(20261017)
        for _ in range(180):
            minimum, maximum = sorted(Date.fromordinal(randomizer.randint(1,Date.max.toordinal())).timetuple()[:3] for _ in range(2))
            value = (randomizer.randint(1,9999), randomizer.randint(1,12), randomizer.randint(-30,90))
            self.assertEqual(_date_python.clamp_date(*value,minimum,maximum), date._extension.date_clamp_date(*value,minimum,maximum))
            for column in range(3):
                step = randomizer.choice((10**500,-10**500,randomizer.randint(-100000,100000)))
                radius = randomizer.choice((0,4,100))
                args = (*value,column,step,minimum,maximum)
                self.assertEqual(_date_python.step_date(*args),date._extension.date_step_date(*args))
                args = (*value,column,radius,minimum,maximum)
                self.assertEqual(_date_python.column_values(*args),date._extension.date_column_values(*args))

    def test_calendar_invalid_inputs_have_matching_exception_classes(self):
        cases = [('days_in_month',(True,2),{}), ('days_in_month',(10**100,2),{}),
                 ('clamp_date',(2024,2,None),{}), ('clamp_date',(2024,2,31),{'minimum':None}),
                 ('clamp_date',(2024,2,31),{'minimum':(2024,2,30)}),
                 ('clamp_date',(2024,2,31),{'minimum':(2025,1,1),'maximum':(2024,1,1)}),
                 ('column_values',(2024,2,29,0,101),{}), ('step_date',(2024,2,29,0,False),{})]
        for name,args,kwargs in cases:
            with self.subTest(name=name,args=args):
                self.assertEqual(outcome(lambda:getattr(_date_python,name)(*args,**kwargs)),
                                 outcome(lambda:getattr(date._extension,'date_'+name)(*args,**kwargs)))

    def test_drop_filter_matches_c_for_unicode_flags_and_rejection_order(self):
        paths = [('图片 😀.PNG',1),('Straße.JPG',1),('STRASSE.jpg',1),('x.tar.GZ',1),
                 ('a.json',1),('a.json',1),('目录',2),('',1),('x\0.png',1),('gone.png',0),('pipe',3)]
        for extensions in ([],['png'],['*.JPG','tar.gz'],['*','json']):
            for flags in range(16):
                args = (paths,extensions,*(bool(flags & 1<<bit) for bit in range(4)))
                with self.subTest(extensions=extensions,flags=flags):
                    self.assertEqual(_drop_python.filter_paths(*args),drop._extension.drop_filter_paths(*args))

    def test_drop_validation_matches_c_and_does_not_skip_after_wildcards(self):
        for suffixes in ('png',None,[True],['*',''],['*','p/ng'],['.'],['*.PNG',' JPG ','.tar.gz'],['.a\u2003b']):
            self.assertEqual(outcome(lambda:_drop_python.normalize_extensions(suffixes)),
                             outcome(lambda:drop._extension.drop_normalize_extensions(suffixes)))
        for items in (None,'a',[(1,1)],[('a',True)],[('a',10**100)],[('a',4)],[('a',1),('b',)]):
            self.assertEqual(outcome(lambda:_drop_python.filter_paths(items,[])),
                             outcome(lambda:drop._extension.drop_filter_paths(items,[],True,True,True,True)))

    def test_shortcut_keys_modifiers_and_invalid_reserved_tail_match_c(self):
        for key in (0,1,32,97,0xd800,0x1f600,0x01000004,0x01000020,10**100,False):
            for modifiers in (0,0x04000000,0x06000000,1,-1,10**100):
                with self.subTest(key=key,modifiers=modifiers):
                    self.assertEqual(outcome(lambda:_shortcut_python.normalize(key,modifiers)),
                                     outcome(lambda:shortcut._extension.shortcut_normalize(key,modifiers)))
        for reserved in ([('a',1)],[(65,0x04000000),(False,0)],[(65,0x04000000)],[],['bad'],None):
            self.assertEqual(outcome(lambda:_shortcut_python.conflicts(65,0x04000000,reserved)),
                             outcome(lambda:shortcut._extension.shortcut_conflicts(65,0x04000000,reserved)))


_UI_PROBE = r'''
import importlib.abc,json,sys,tempfile,types
from pathlib import Path
root=Path(sys.argv[1]); kind=sys.argv[2]
source=Path(sys.argv[3]) if len(sys.argv)>3 else root/'src'
sys.path[:0]=[str(source),str(root/'examples')]
if kind=='old':
    old=types.ModuleType('fluentpy._native')
    old.json_spans=lambda value: []
    sys.modules['fluentpy._native']=old
else:
    class NoNative(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname=='fluentpy._native':
                if kind=='incompatible': raise OSError('simulated incompatible native ABI')
                raise ImportError('simulated missing native binary')
    sys.meta_path.insert(0,NoNative())
from fluentpy import DatePicker,FileDropWidget,ShortcutPicker,TimePicker,CalendarPicker,DateRangePicker,DateTimePicker
import fluentpy
assert Path(fluentpy.__file__).is_relative_to(source)
from fluentpy.qt import QtCore,QtWidgets,QT_API
if QT_API=='PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest
from fluentpy.backends import date,drop,shortcut,time as clock,calendar
errors=[]
def report_error(typ,error,tb):
    errors.append(str(error)); sys.__excepthook__(typ,error,tb)
sys.excepthook=report_error
app=QtWidgets.QApplication([]); app.setQuitOnLastWindowClosed(False)
host=QtWidgets.QWidget(); host.resize(720,600)
picker=DatePicker(host); picker.set_date(QtCore.QDate(2024,2,29))
picker.set_date_range(QtCore.QDate(2024,2,10),QtCore.QDate(2025,3,12))
host.show(); app.processEvents()
picker.show_popup(); app.processEvents()
assert picker._popup is not None and picker._popup.isVisible()
picker._popup.wheel.set_value((2024,2,29),(2024,2,10),(2025,3,12))
QTest.keyClick(picker._popup.wheel,QtCore.Qt.Key.Key_Down)
QTest.keyClick(picker._popup.wheel,QtCore.Qt.Key.Key_Return)
assert picker.date().isValid()
files=FileDropWidget(host); files.set_file_extensions(['png'])
with tempfile.TemporaryDirectory() as folder:
    good=Path(folder)/'图片 😀.PNG'; good.write_bytes(b'test')
    bad=Path(folder)/'reject.txt'; bad.write_text('test')
    files.accept_paths([str(bad),str(good)])
    assert len(files.selected_paths())==1
    files.submit_paths([str(good)])
    for _ in range(300):
        if not files.is_busy(): break
        QTest.qWait(5)
    assert not files.is_busy() and len(files.selected_paths())==1
keys=ShortcutPicker('Ctrl+Shift+A',host)
keys.set_reserved_sequences(['Ctrl+S'])
keys.show(); keys.open_editor(); QTest.qWait(200)
editor=keys._editor
QTest.keyClick(editor.recorder,QtCore.Qt.Key.Key_L,QtCore.Qt.KeyboardModifier.AltModifier)
editor.yes_button.click(); QTest.qWait(150)
assert keys.key_sequence().toString()=='Alt+L'
time_picker=TimePicker(host,use_12_hour=True)
time_picker.setGeometry(300,260,300,38)
time_picker.setTime(QtCore.QTime(23,59)); time_picker.show(); time_picker.show_popup()
time_picker._popup.wheel.step(1,1)
QTest.keyClick(time_picker._popup.wheel,QtCore.Qt.Key.Key_Return)
QTest.qWait(160)
assert time_picker.time()==QtCore.QTime(23,0)
single=CalendarPicker(host); single.setGeometry(20,20,250,36); single.set_date(QtCore.QDate(2024,2,28)); single.show(); single.show_popup(); QTest.qWait(240)
single._popup.calendar.choose((2024,2,29)); QTest.qWait(160)
assert single.date()==QtCore.QDate(2024,2,29)
interval=DateRangePicker(host); interval.setGeometry(20,60,300,36); interval.show(); interval.show_popup(); QTest.qWait(240)
interval._popup.calendar.choose((2024,3,21)); interval._popup.calendar.choose((2024,3,13)); QTest.qWait(160)
assert interval.start_date()==QtCore.QDate(2024,3,13)
scheduled=DateTimePicker(host); scheduled.setGeometry(20,100,300,36); scheduled.set_date_time(QtCore.QDateTime(QtCore.QDate(2026,2,10),QtCore.QTime(20,0,0)))
scheduled.show(); scheduled.show_popup(); QTest.qWait(240); scheduled._popup.seconds.step(2,5); scheduled._popup.confirm_button.click(); QTest.qWait(160)
assert scheduled.date_time().time()==QtCore.QTime(20,0,5)
for widget in (picker,files,keys,time_picker,single,interval,scheduled): assert widget.acceleration_backend()=='python'
from showcase import Showcase
workbench=Showcase(page='inputs', startup=False); workbench.show(); QTest.qWait(350)
assert workbench.date_picker is not None
assert hasattr(workbench,'drop_examples') and hasattr(workbench,'shortcut_examples')
assert all(backend.backend_name()=='python' for backend in (date,drop,shortcut,clock,calendar))
if kind!='old': assert workbench.backend_badge.text()=='Python 兼容模式'
else: assert workbench.backend_badge.text()=='混合后端'
workbench.set_page('drop',animated=False)
workbench.set_page('calendar',animated=False)
workbench.set_page('feedback',animated=False)
workbench.close(); host.close()
workbench.deleteLater(); host.deleteLater()
app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
assert not errors,errors
print(json.dumps({'scenario':kind,'date':True,'time':True,'calendar_range_datetime':True,'drop_sync_async':True,'shortcut_record_save':True,'workbench':True}))
'''


class MissingNativeIntegrationTests(unittest.TestCase):
    def test_fresh_processes_missing_incompatible_and_old_binary_keep_widgets_operable(self):
        env=os.environ.copy()
        env.update(QT_QPA_PLATFORM='offscreen',FLUENTPY_BACKEND='auto')
        for kind in ('missing','incompatible','old'):
            with self.subTest(kind=kind):
                result=subprocess.run([sys.executable,'-I','-B','-X','utf8','-c',_UI_PROBE,str(ROOT),kind],
                    cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=30)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertTrue(json.loads(result.stdout)['workbench'])


if __name__=='__main__':
    unittest.main()
