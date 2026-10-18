"""Behavioral regressions for Qt models, native views and choice lifecycles."""
import os
import sys
import unittest
from pathlib import Path
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples'))
from fluentpy import (ComboBox, EditableComboBox, ModelComboBox, EditableModelComboBox,
    MultiSelectionComboBox, TreeComboBox, MultiSelectionTreeComboBox,
    TransparentComboBox, FontComboBox, theme)
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
from combo_boxes import ComboBoxExamples, tree_model, KINDS
if QT_API == 'PySide6':
    from PySide6.QtTest import QTest, QSignalSpy
else:
    from PyQt6.QtTest import QTest, QSignalSpy


class ComboBoxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, error, tb: self.errors.append(str(error))
        self.owner = QtWidgets.QWidget()
        self.owner.resize(800, 620)
        self.owner.show()

    def tearDown(self):
        self.owner.close()
        self.owner.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def combo(self, cls=ComboBox):
        combo = cls(self.owner)
        combo.setGeometry(28, 40, 310, 36)
        combo.show()
        return combo

    def open(self, combo):
        combo.show_popup()
        popup = combo._popup
        popup._reveal.setCurrentTime(popup.SHOW_DURATION)
        self.app.processEvents()
        return popup

    def click_row(self, popup, row, parent=QtCore.QModelIndex()):
        index = popup.proxy.index(row, 0, parent)
        popup.view.scrollTo(index)
        self.app.processEvents()
        QTest.mouseClick(popup.view.viewport(), QtCore.Qt.MouseButton.LeftButton,
                         pos=popup.view.visualRect(index).center())

    def test_placeholder_item_data_and_selection_signals(self):
        combo = self.combo()
        indexes, texts, activated = [], [], []
        combo.currentIndexChanged.connect(indexes.append)
        combo.currentTextChanged.connect(texts.append)
        combo.activated.connect(activated.append)
        combo.addItem('开发', {'id': 1})
        combo.addItem('发布', {'id': 2})
        self.assertEqual(combo.currentData(), {'id': 1})
        combo.setPlaceholderText('请选择')
        combo.setCurrentIndex(-1)
        self.assertEqual(combo.currentText(), '')
        self.assertEqual(combo.placeholderText(), '请选择')
        self.click_row(self.open(combo), 1)
        self.assertEqual(combo.currentData(), {'id': 2})
        self.assertEqual(indexes, [0, -1, 1])
        self.assertEqual(texts, ['开发', '', '发布'])
        self.assertEqual(activated, [1])
        self.assertFalse(combo._popup._opened)

    def test_mutations_preserve_identity_and_removed_current_is_repaired(self):
        combo = self.combo()
        combo.addItems(['A', 'B', 'C'])
        combo.setCurrentIndex(1)
        combo.insertItem(0, 'X')
        self.assertEqual((combo.currentIndex(), combo.currentText()), (2, 'B'))
        combo.setItemText(2, 'B2')
        self.assertEqual(combo.currentText(), 'B2')
        combo.removeItem(2)
        self.assertIn(combo.currentText(), ['X', 'A', 'C'])
        combo.clear()
        self.assertEqual((combo.count(), combo.currentIndex(), combo.currentText()), (0, -1, ''))

    def test_keyboard_skips_disabled_and_escape_does_not_commit(self):
        combo = self.combo()
        combo.addItems(['A', 'B', 'C'])
        combo.setItemEnabled(1, False)
        QTest.keyClick(combo, QtCore.Qt.Key.Key_Down)
        self.assertEqual(combo.currentIndex(), 2)
        combo.setCurrentIndex(1)
        self.assertEqual(combo.currentIndex(), 2)
        popup = self.open(combo)
        popup.view.setCurrentIndex(popup.proxy.index(0, 0))
        QTest.keyClick(popup.view, QtCore.Qt.Key.Key_Escape)
        QTest.qWait(150)
        self.assertEqual(combo.currentIndex(), 2)
        self.assertFalse(popup._opened)

    def test_live_external_model_sort_rename_reset_and_delete(self):
        model = QtGui.QStandardItemModel(self.owner)
        model.appendRow(QtGui.QStandardItem('B'))
        model.appendRow(QtGui.QStandardItem('A'))
        combo = self.combo(ModelComboBox)
        combo.setModel(model)
        popup = self.open(combo)
        model.sort(0)
        self.assertEqual((combo.currentIndex(), combo.currentText()), (1, 'B'))
        model.setData(model.index(1, 0), 'B2')
        self.assertEqual(combo.currentText(), 'B2')
        self.app.processEvents()  # Let the proxy finish sorting before a view refresh.
        self.assertIs(popup.proxy.sourceModel(), model)
        model.clear()
        self.assertEqual(combo.currentText(), '')
        model.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(combo.count(), 0)
        combo.addItem('新模型')
        self.assertEqual(combo.currentText(), '新模型')

    def test_editable_empty_enter_adds_once_and_shared_model_updates(self):
        combo = self.combo(EditableModelComboBox)
        model = QtGui.QStandardItemModel(self.owner)
        model.appendRow(QtGui.QStandardItem('Alpha'))
        combo.setModel(model)
        combo.lineEdit().clear()
        # User editing emits textEdited, as opposed to a programmatic clear().
        combo.lineEdit().setText('Beta')
        QTest.keyClick(combo.lineEdit(), QtCore.Qt.Key.Key_Return)
        self.assertEqual((combo.count(), combo.currentText()), (2, 'Beta'))
        QTest.keyClick(combo.lineEdit(), QtCore.Qt.Key.Key_Return)
        self.assertEqual(combo.count(), 2)
        model.setData(model.index(1, 0), 'Beta renamed')
        self.assertEqual(combo.lineEdit().text(), 'Beta renamed')
        combo.setEditText('')
        self.assertEqual((combo.currentIndex(), combo.currentText()), (-1, ''))
        completer = QtWidgets.QCompleter(['custom'], combo)
        combo.setCompleter(completer)
        self.assertIs(combo.completer(), completer)
        combo.setCompleter(None)
        QTest.keyClick(combo.lineEdit(), QtCore.Qt.Key.Key_F4)
        self.assertTrue(combo._popup._opened)

    def test_editing_draft_survives_unrelated_model_changes_and_completion_commits(self):
        combo = self.combo(EditableComboBox)
        combo.addItems(['Alpha', 'Beta'])
        combo.setEditText('draft')
        combo.setItemText(0, 'Alpha2')
        self.assertEqual(combo.currentText(), 'draft')
        combo.completer().activated[str].emit('Beta')
        self.assertEqual((combo.currentIndex(), combo.currentText(), combo.count()), (1, 'Beta', 2))
        combo.setEditText('draft')
        combo.setCurrentIndex(-1)
        self.assertEqual(combo.currentText(), '')

    def test_a_plain_qt_string_list_model_can_be_shared(self):
        model = QtCore.QStringListModel(['A', 'B'], self.owner)
        left, right = self.combo(ModelComboBox), self.combo(EditableModelComboBox)
        left.setModel(model)
        right.setModel(model)
        right.addItem('C')
        self.assertEqual(left.count(), 3)
        right.setCurrentIndex(2)
        model.setData(model.index(2, 0), 'C2')
        self.assertEqual(right.currentText(), 'C2')

    def test_arrow_opens_multiselect_without_changing_selection(self):
        combo = self.combo(MultiSelectionComboBox)
        combo.addItems(['A', 'B'])
        combo.setSelectedIndexes([0])
        QTest.keyClick(combo, QtCore.Qt.Key.Key_Down)
        self.assertEqual(combo.selectedTexts(), ['A'])
        self.assertTrue(combo._popup._opened)

    def test_multiple_tags_search_and_independent_model_state(self):
        combo = self.combo(MultiSelectionComboBox)
        combo.addItems(['Alpha', 'Beta', 'Gamma'])
        combo.setItemData(0, 123)
        popup = self.open(combo)
        self.click_row(popup, 0)
        self.click_row(popup, 2)
        self.assertTrue(popup._opened)
        self.assertEqual(combo.selectedTexts(), ['Alpha', 'Gamma'])
        self.assertEqual(combo.itemData(0, QtCore.Qt.ItemDataRole.CheckStateRole), None)
        popup.search.setText('Beta')
        self.assertEqual(popup.proxy.rowCount(), 1)
        self.click_row(popup, 0)
        self.assertEqual(combo.selectedData()[0], 123)
        combo.hide_popup()
        combo._tag_buttons[0].click()
        self.assertEqual(combo.selectedTexts(), ['Gamma', 'Beta'])
        combo.clearSelection()
        self.assertEqual(combo.selectedTexts(), [])
        self.assertEqual(combo.count(), 3)

    def test_multiple_removes_deleted_indexes_and_collapses_tags_within_bounds(self):
        combo = self.combo(MultiSelectionComboBox)
        combo.addItems(['long item '+str(i) for i in range(12)])
        combo.setSelectedIndexes(range(12))
        self.assertTrue(any(button.text().startswith('+') for button in combo._tag_buttons))
        self.assertTrue(all(combo.rect().contains(button.geometry()) for button in combo._tag_buttons))
        combo.removeItem(0)
        self.assertEqual(len(combo.selectedIndexes()), 11)
        previous = combo.selectedTexts()
        with self.assertRaises(ValueError):
            combo.setSelectedIndexes([0, 500])
        self.assertEqual(combo.selectedTexts(), previous)

    def test_tag_captions_fit_the_actual_button_font_padding_and_close_glyph(self):
        for cls in (MultiSelectionComboBox, MultiSelectionTreeComboBox):
            combo = self.combo(cls)
            combo.resize(560, 36)
            names = ['主窗口', '设置页面', '组件预览', '+项目']
            combo.addItems(names)
            combo.setSelectedIndexes(range(len(names)))
            self.assertEqual([button.text() for button in combo._tag_buttons],
                             [name+' ×' for name in names])
            for mode in ('light', 'dark'):
                theme.set_mode(mode)
                self.app.processEvents()
                for button in combo._tag_buttons:
                    required = button.fontMetrics().horizontalAdvance(button.text())+2*button._h_padding+1
                    self.assertLessEqual(required, button.width(), button.text())
            combo.resize(180, 36)
            self.assertTrue(any(button.text().startswith('+') for button in combo._tag_buttons))
            for button in combo._tag_buttons:
                self.assertTrue(combo.rect().contains(button.geometry()))
                self.assertLessEqual(button.fontMetrics().horizontalAdvance(button.text())+2*button._h_padding+1,
                                     button.width(), button.text())
            combo.hide()

    def test_long_tag_elides_its_name_without_clipping_the_close_glyph(self):
        combo = self.combo(MultiSelectionComboBox)
        combo.resize(560, 36)
        combo.addItems(['这是一个需要省略但仍然可以完整点击关闭的很长标签', '普通标签'])
        combo.setSelectedIndexes([0, 1])
        button = combo._tag_buttons[0]
        self.assertIn('…', button.text())
        self.assertTrue(button.text().endswith(' ×'))
        self.assertLessEqual(button.fontMetrics().horizontalAdvance(button.text())+2*button._h_padding+1,
                             button.width())
        button.click()
        self.assertEqual(combo.selectedTexts(), ['普通标签'])

    def test_tree_distinguishes_same_row_in_different_parents_and_filters(self):
        combo = self.combo(TreeComboBox)
        model = tree_model(self.owner)
        combo.setModel(model)
        changes = []
        combo.currentModelIndexChanged.connect(lambda index: changes.append(QtCore.QPersistentModelIndex(index)))
        first = model.index(0, 0, model.index(0, 0))
        other = model.index(0, 0, model.index(1, 0))
        combo.setCurrentModelIndex(first)
        combo.setCurrentModelIndex(other)
        self.assertEqual(combo.currentPath(), ['资源', '主题配色'])
        self.assertEqual(len(changes), 2)
        popup = self.open(combo)
        popup.search.setText('设置页面')
        self.assertEqual(popup.proxy.rowCount(), 1)
        parent = popup.proxy.index(0, 0)
        self.click_row(popup, 0, parent)
        self.assertEqual(combo.currentPath(), ['界面', '设置页面'])

    def test_tree_multiple_uses_leaf_indexes_without_mutating_parents(self):
        combo = self.combo(MultiSelectionTreeComboBox)
        model = tree_model(self.owner)
        combo.setModel(model)
        first = model.index(0, 0, model.index(0, 0))
        second = model.index(0, 0, model.index(1, 0))
        combo.setSelectedIndexes([first, second])
        self.assertEqual(combo.selectedTexts(), ['主窗口', '主题配色'])
        self.assertEqual(combo.selectedData(), ['界面/主窗口', '资源/主题配色'])
        with self.assertRaises(ValueError):
            combo.setSelectedIndexes([model.index(0, 0)])

    def test_long_list_scrolls_and_popup_stays_inside_owner(self):
        combo = self.combo()
        combo.move(480, 560)
        combo.addItems(['选项 '+str(i) for i in range(100)])
        combo.setCurrentIndex(95)
        popup = self.open(combo)
        self.assertIsInstance(popup.view, QtWidgets.QListView)
        self.assertFalse(popup.isWindow())
        self.assertTrue(self.owner.rect().contains(popup._surface.geometry()))
        self.assertGreater(popup.view.verticalScrollBar().maximum(), 0)
        self.click_row(popup, 97)
        self.assertEqual(combo.currentIndex(), 97)

    def test_hiding_disabling_reopening_and_outside_click_cleanup(self):
        combo = self.combo()
        combo.addItems(['A', 'B'])
        popup = self.open(combo)
        combo.hide()
        self.assertFalse(popup._opened)
        combo.show()
        self.assertIs(self.open(combo), popup)
        combo.setEnabled(False)
        self.assertFalse(popup._opened)
        combo.setEnabled(True)
        self.open(combo)
        QTest.mouseClick(popup, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(720, 550))
        QTest.qWait(150)
        self.assertFalse(popup._filter_installed)

    def test_font_and_transparent_components_and_theme_switch(self):
        transparent = self.combo(TransparentComboBox)
        transparent.addItems(['A', 'B'])
        transparent.setTextColor('#147d95')
        with self.assertRaises(ValueError):
            transparent.setTextColor('invalid')
        fonts = self.combo(FontComboBox)
        families = QtGui.QFontDatabase.families()
        self.assertEqual(fonts.count(), len(families))
        if families:
            values = []
            fonts.currentFontChanged.connect(values.append)
            fonts.setCurrentFont(QtGui.QFont(families[-1]))
            self.assertEqual(fonts.currentFont().family(), families[-1])
        theme.set_mode('dark')
        popup = self.open(transparent)
        self.assertTrue(popup._opened)
        theme.set_mode('light')
        self.assertIsNotNone(transparent.grab())

    def test_playground_switches_all_types_without_losing_shared_model(self):
        play = ComboBoxExamples(self.owner)
        play.setGeometry(10, 5, 760, 540)
        play.show()
        for number, (_, cls, _) in enumerate(KINDS):
            play.kind.setCurrentIndex(number)
            self.app.processEvents()
            self.assertIs(type(play.preview), cls)
            self.assertTrue(play.rect().contains(QtCore.QRect(play.preview.mapTo(play, QtCore.QPoint()), play.preview.size())))
        play.kind.setCurrentIndex(2)
        play.model_name.setText('新环境')
        play.preview.setCurrentIndex(0)
        self.assertEqual(play.preview.currentText(), '新环境')
        play.kind.setCurrentIndex(3)
        self.assertEqual(play.preview.itemText(0), '新环境')


if __name__ == '__main__':
    unittest.main()
