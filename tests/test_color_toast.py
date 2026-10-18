import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys
import unittest
from fluentpy import Button,ColorToast,ProgressToast,Toast,theme
from fluentpy.qt import QtCore,QtGui,QtWidgets,QT_API
if QT_API=='PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class ColorToastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def setUp(self):
        self.errors=[];self.old_hook=sys.excepthook
        sys.excepthook=lambda kind,error,tb:self.errors.append(error)
        self.original_theme=theme.mode
        self.owner=QtWidgets.QWidget();self.owner.resize(900,720);self.owner.show();self.app.processEvents()
    def tearDown(self):
        self.owner.close();self.owner.deleteLater();self.app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.original_theme);self.app.processEvents();sys.excepthook=self.old_hook
        self.assertEqual(self.errors,[])
    def settle(self,toast):
        toast._reveal.setCurrentTime(toast.SHOW_DURATION);toast._stack_motion.setCurrentTime(240)
        self.app.processEvents()

    def test_native_surface_and_top_strip_match_the_requested_custom_color(self):
        before=set(self.app.topLevelWidgets())
        toast=ColorToast('Lesson 4','一段可换行的消息。',self.owner,color='#e02616')
        toast.show_at('top-right');self.settle(toast)
        self.assertIsInstance(toast,Toast);self.assertFalse(toast.isWindow());self.assertIsNone(toast.windowHandle())
        self.assertEqual(set(self.app.topLevelWidgets()),before);self.assertTrue(toast._icon.isHidden())
        image=toast.grab().toImage();rect=toast._card_rect();x=round(rect.center().x());y=round(rect.top()+1)
        self.assertEqual(image.pixelColor(x,y).name(),'#e02616')
        self.assertEqual(toast._title.parentWidget(),toast._content)
        self.assertEqual(toast._detail.text(),'一段可换行的消息。')

    def test_color_validation_is_atomic_defensive_and_animated(self):
        toast=ColorToast('标题',parent=self.owner,color='#009faa');toast.show_at();self.settle(toast)
        saved=toast.color();copy=toast.color();copy.setRed(255);self.assertEqual(toast.color(),saved)
        with self.assertRaises(ValueError):toast.set_color('not-a-color')
        self.assertEqual(toast.color(),saved)
        toast.set_color('#ff0000');toast._color_motion.setCurrentTime(80)
        self.assertNotEqual(toast._bar_display,saved);self.assertNotEqual(toast._bar_display,toast.color())
        toast._color_motion.setCurrentTime(160);self.assertEqual(toast._bar_display,toast.color())

    def test_action_is_existing_button_emits_once_and_dismisses(self):
        calls=[];toast=ColorToast('Title','消息',self.owner,action_text='Action',action_callback=lambda:calls.append('callback'))
        toast.actionTriggered.connect(lambda:calls.append('signal'));toast.show_at();self.settle(toast)
        self.assertIsInstance(toast.action_button,Button)
        self.assertFalse(toast._action_row.isHidden());toast.action_button.click()
        self.assertEqual(calls,['callback','signal']);self.assertTrue(toast._closing)
        toast._reveal.setCurrentTime(toast.HIDE_DURATION);self.assertFalse(toast.isVisible())

    def test_action_replacement_and_persistent_action_do_not_call_old_callback(self):
        calls=[];toast=ColorToast('Title',parent=self.owner,action_text='Action',action_callback=lambda:calls.append('old'))
        toast.set_action('重试',lambda:calls.append('new'),close_on_action=False)
        toast.show_at();self.settle(toast);toast.action_button.click()
        self.assertEqual(calls,['new']);self.assertTrue(toast.isVisible());self.assertFalse(toast._closing)
        toast.set_action('');self.assertTrue(toast._action_row.isHidden())

    def test_action_callback_can_delete_the_toast(self):
        toast=ColorToast('Title',parent=self.owner,action_text='删除')
        def remove():
            toast.deleteLater();self.app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
        toast.set_action('删除',remove);toast.show_at();self.settle(toast);toast.action_button.click()

    def test_text_width_wrap_and_optional_action_fit_owner(self):
        toast=ColorToast('很长的标题'*12,'很长的消息内容。'*25,self.owner,card_width=300,action_text='操作按钮')
        toast.show_at('bottom-center');self.settle(toast)
        self.assertEqual(round(toast._card_rect().width()),300)
        self.assertGreater(toast.height(),150)
        self.assertTrue(self.owner.rect().contains(toast.geometry()))
        self.owner.resize(220,180);self.app.processEvents();self.assertTrue(self.owner.rect().contains(toast.geometry()))
        toast.set_title('标题');toast.set_detail('');toast.set_action('');toast.set_card_width(None)
        self.assertTrue(toast._detail_row.isHidden());self.assertTrue(toast._action_row.isHidden())

    def assert_content_fits(self,toast,widget):
        bounds=QtCore.QRectF(widget.mapTo(toast,QtCore.QPoint()),widget.size())
        self.assertTrue(toast._card_rect().contains(bounds),f'{widget}: {bounds} outside {toast._card_rect()}')
        if isinstance(widget,QtWidgets.QLabel) and widget.wordWrap():
            self.assertGreaterEqual(widget.height(),widget.heightForWidth(widget.width()))

    def test_wrap_boundaries_never_clip_body_or_action(self):
        toast=ColorToast('操作提示','可以自定义顶部颜色，并在通知中提供操作按钮。',self.owner,action_text='查看详情')
        toast.show_at();self.settle(toast)
        # Adjacent widths catch the former one-pixel discrepancy between the
        # estimated line width and the actual Qt layout, including CJK fonts.
        for width in range(220,421):
            toast.set_card_width(width);self.app.processEvents()
            for widget in (toast._title,toast._detail,toast.action_button):
                self.assert_content_fits(toast,widget)
            self.assertEqual(toast.action_button.height(),toast.action_button.sizeHint().height())

    def test_action_label_can_be_long_and_is_constrained_to_the_card(self):
        toast=ColorToast('标题',parent=self.owner,card_width=240,action_text='This is a longer developer supplied action label')
        toast.show_at();self.settle(toast);self.assert_content_fits(toast,toast.action_button)
        toast.set_card_width(None);self.app.processEvents()
        self.assert_content_fits(toast,toast.action_button)

    def test_public_content_layout_sizes_nested_widgets_and_updates_the_stack(self):
        toast=ColorToast('自定义内容',parent=self.owner,card_width=300)
        self.assertIs(toast.content_widget.layout(),toast.content_layout)
        field=QtWidgets.QLineEdit(toast.content_widget)
        row=QtWidgets.QHBoxLayout();row.setSpacing(8)
        first=Button('保存',toast.content_widget);second=Button('取消',toast.content_widget)
        row.addWidget(first);row.addWidget(second);row.addStretch()
        toast.content_layout.addWidget(field);toast.content_layout.addLayout(row)
        toast.show_at('bottom-right');self.settle(toast)
        original_height=toast.height()
        for widget in (field,first,second):self.assert_content_fits(toast,widget)
        other=ColorToast('另一条通知',parent=self.owner);other.show_at('bottom-right');self.settle(other);self.settle(toast)
        extra=QtWidgets.QLabel('Custom content that wraps over several lines. '*4,toast.content_widget)
        extra.setWordWrap(True);toast.content_layout.addWidget(extra)
        self.app.processEvents();self.app.processEvents();self.settle(toast)
        self.assertGreater(toast.height(),original_height);self.assert_content_fits(toast,extra)
        self.assertLess(toast.geometry().bottom(),other.geometry().top()+14)
        expanded=toast.height();extra.hide();self.app.processEvents();self.app.processEvents()
        self.assertLess(toast.height(),expanded)
        field.setFixedHeight(58);self.app.processEvents();self.app.processEvents()
        self.assertEqual(field.height(),58);self.assert_content_fits(toast,field)
        self.assertFalse(field.isWindow());self.assertFalse(first.isWindow())
        self.assertEqual(extra.parentWidget(),toast.content_widget)

    def test_custom_content_added_after_show_and_removed_is_measured(self):
        toast=ColorToast('标题',parent=self.owner,card_width=300);toast.show_at();self.settle(toast)
        original_height=toast.height()
        button=Button('用户定义的按钮',toast.content_widget)
        toast.content_layout.addWidget(button);self.app.processEvents();self.app.processEvents()
        self.assertGreater(toast.height(),original_height);self.assert_content_fits(toast,button)
        button.deleteLater();self.app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents();self.app.processEvents();self.assertEqual(toast.height(),original_height)

    def test_center_positions_stack_in_both_directions_with_mixed_types(self):
        for placement in ('top-center','bottom-center'):
            first=ColorToast.notify('第一条',detail='正文',parent=self.owner,placement=placement,timeout_ms=0)
            second=ProgressToast.start('任务提示',parent=self.owner,placement=placement)
            self.settle(second);self.settle(first)
            self.assertIs(first._stack,second._stack)
            for toast in (first,second):self.assertLessEqual(abs(toast.x()*2+toast.width()-self.owner.width()),1)
            self.assertLess(first.y(),second.y()) if placement.startswith('bottom') else self.assertGreater(first.y(),second.y())
            first.hide();second.hide()

    def test_factories_and_theme_colors_support_custom_override(self):
        for method,tone in ((ColorToast.success,'success'),(ColorToast.warning,'warning'),(ColorToast.error,'error'),(ColorToast.info,'info')):
            toast=method('状态消息',parent=self.owner,timeout_ms=0);self.assertEqual(toast.tone(),tone);toast.hide()
        toast=ColorToast('主题色',parent=self.owner,color='#123456');theme.toggle()
        self.assertEqual(toast.color().name(),'#123456');toast.set_color(None)
        self.assertEqual(toast.color().name(),theme.tokens.accent.lower())
        toast.set_tone('warning');self.assertNotEqual(toast.color().name(),theme.tokens.accent.lower())

    def test_timeout_waits_for_entry_and_pauses_for_action_hover(self):
        toast=ColorToast.notify('Title',detail='带操作按钮',parent=self.owner,timeout_ms=80,action_text='Action')
        self.assertFalse(toast._timeout.isActive());self.settle(toast);self.assertTrue(toast._timeout.isActive())
        self.app.sendEvent(toast,QtGui.QEnterEvent(QtCore.QPointF(1,1),QtCore.QPointF(1,1),QtCore.QPointF(1,1)))
        QTest.qWait(100);self.assertTrue(toast.isVisible());self.assertFalse(toast._timeout.isActive())
        self.app.sendEvent(toast,QtCore.QEvent(QtCore.QEvent.Type.Leave));QTest.qWait(80+toast.HIDE_DURATION+40)
        self.app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)

    def test_resize_reflow_hide_reuse_and_owner_destruction(self):
        toast=ColorToast('Title','Body',self.owner,action_text='Action');toast.show_at('top-center');self.settle(toast)
        old_height=toast.height();toast.set_action('');self.assertLess(toast.height(),old_height)
        toast.hide();self.assertIsNone(toast._stack);toast.show_at('bottom-left');self.settle(toast)
        self.assertEqual(toast.x(),18);self.owner.hide();self.assertFalse(toast.isVisible())

    def test_invalid_factory_arguments_never_expose_a_window(self):
        before=set(self.app.topLevelWidgets())
        for kwargs in ({'placement':'elsewhere'},{'tone':'elsewhere'},{'color':'invalid'},{'card_width':2},{'timeout_ms':-1},{'action_callback':42}):
            with self.subTest(kwargs=kwargs),self.assertRaises((ValueError,TypeError)):
                ColorToast.notify('Title',parent=self.owner,**kwargs)
        self.assertEqual({w for w in self.app.topLevelWidgets() if w.isVisible()},{self.owner})

    def test_construction_and_show_never_expose_orphan_label_windows(self):
        class Monitor(QtCore.QObject):
            def eventFilter(self,obj,event):
                if event.type()==QtCore.QEvent.Type.Show and isinstance(obj,QtWidgets.QLabel) and obj.isWindow():shown.append(obj.text())
                return False
        shown=[];monitor=Monitor();self.app.installEventFilter(monitor)
        try:
            toast=ColorToast('Title','Body',self.owner,action_text='Action');toast.show_at();self.settle(toast)
            self.assertEqual(shown,[])
        finally:self.app.removeEventFilter(monitor)

    def test_demo_is_idle_reuses_native_controls_and_cleans_its_notifications(self):
        from pathlib import Path
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
        try:
            from color_toast import ColorToastExamples
            from fluentpy import ColorPickerButton,ComboBox
            demo=ColorToastExamples(self.owner);demo.resize(520,420);demo.show();self.app.processEvents()
            self.assertEqual(demo._messages,{})
            self.assertIsInstance(demo.position,ComboBox);self.assertIsInstance(demo.color_picker,ColorPickerButton)
            demo.auto_close.setChecked(False);demo.position.setCurrentIndex(4);demo.action_check.setChecked(True)
            demo.action_text_input.setText('立即重试')
            toast=demo.show_message();self.settle(toast)
            self.assertEqual(toast._placement,'bottom-center');self.assertFalse(toast._action_row.isHidden())
            self.assertEqual(toast.action_button.text(),'立即重试')
            demo.color_picker.set_color('#9b50cc');self.assertEqual(toast.color().name(),'#9b50cc')
            toast.action_button.click();self.assertEqual(demo.result.text(),'已触发“立即重试”操作。')
            demo.hide();toast._reveal.setCurrentTime(toast.HIDE_DURATION)
            self.app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete);self.assertEqual(demo._messages,{})
        finally:sys.path.pop(0)

    def test_demo_custom_content_uses_native_input_and_buttons(self):
        from pathlib import Path
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
        try:
            from color_toast import ColorToastExamples
            from fluentpy import LineEdit
            demo=ColorToastExamples(self.owner);demo.show();self.app.processEvents()
            toast=demo.show_content();self.settle(toast)
            field=toast.content_widget.findChild(LineEdit);field.setText('开发者内容')
            apply=next(b for b in toast.content_widget.findChildren(Button) if b.text()=='应用')
            self.assert_content_fits(toast,field);self.assert_content_fits(toast,apply)
            apply.click();self.assertEqual(demo.result.text(),'已应用备注：开发者内容');self.assertTrue(toast._closing)
        finally:sys.path.pop(0)
