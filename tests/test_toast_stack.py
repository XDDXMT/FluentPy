import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"
import sys
import unittest

from fluentpy import ProgressToast, Toast
from fluentpy.qt import QT_API, QtCore, QtWidgets

if QT_API == "PySide6":
    pass
else:
    pass


class ToastStackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, error, tb: self.errors.append(error)
        self.owner = QtWidgets.QWidget()
        self.owner.resize(900, 720)
        self.owner.show()
        self.app.processEvents()

    def tearDown(self):
        self.owner.close()
        self.owner.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def settle(self, toasts):
        for toast in toasts:
            toast._reveal.setCurrentTime(toast._reveal.duration())
            toast._stack_motion.setCurrentTime(toast._stack_motion.duration())
        self.app.processEvents()

    def card(self, toast):
        return toast._card_rect().translated(toast.pos())

    def test_bottom_newest_stays_at_edge_and_older_cards_grow_upward(self):
        toasts = [
            ProgressToast.start(
                "下载任务 " + str(i),
                parent=self.owner,
                placement="bottom-right",
                severity="warning",
            )
            for i in range(5)
        ]
        self.settle(toasts)
        self.assertEqual(toasts[-1].geometry().bottom() + 1, self.owner.height() - 18)
        for left, right in zip(toasts, toasts[1:]):
            self.assertLess(self.card(left).bottom(), self.card(right).top())
            self.assertEqual(left.geometry().right(), right.geometry().right())
        self.assertTrue(all(not toast.isWindow() for toast in toasts))

    def test_top_newest_stays_at_edge_and_older_cards_grow_downward(self):
        toasts = [
            Toast.success(str(i), parent=self.owner, placement="top-left", timeout_ms=0)
            for i in range(4)
        ]
        self.settle(toasts)
        self.assertEqual(toasts[-1].y(), 18)
        for old, new in zip(toasts, toasts[1:]):
            self.assertGreater(self.card(old).top(), self.card(new).bottom())
            self.assertEqual(old.x(), new.x())

    def test_new_card_retargets_existing_positions_with_smooth_animation(self):
        old = Toast.success("第一条", parent=self.owner, placement="bottom-right", timeout_ms=0)
        self.settle([old])
        initial = old.pos()
        new = Toast.success("第二条", parent=self.owner, placement="bottom-right", timeout_ms=0)
        old._stack_motion.setCurrentTime(100)
        self.assertLess(old.y(), initial.y())
        self.assertGreater(old.y(), old._stack_target.y())
        self.settle([old, new])

    def test_close_middle_and_external_delete_reflow_without_gaps(self):
        toasts = [Toast.success(str(i), parent=self.owner, timeout_ms=0) for i in range(4)]
        self.settle(toasts)
        manager = toasts[-1]._stack
        before = toasts[0].y()
        toasts[1].close()
        toasts[1]._reveal.setCurrentTime(Toast.HIDE_DURATION)
        self.settle([toasts[0], toasts[2], toasts[3]])
        self.assertLess(toasts[0].y(), before)
        self.assertEqual(len(manager.members()), 3)
        toasts[2].deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.settle([toasts[0], toasts[3]])
        self.assertEqual(len(manager.members()), 2)

    def test_mixed_message_task_and_multiline_heights_do_not_overlap(self):
        plain = Toast.success("保存完成", parent=self.owner, placement="bottom-left", timeout_ms=0)
        long = ProgressToast.start(
            "下载任务",
            detail="有多行说明的任务状态。" * 12,
            parent=self.owner,
            placement="bottom-left",
        )
        short = ProgressToast.start("准备中", parent=self.owner, placement="bottom-left")
        self.settle([plain, long, short])
        self.assertIs(plain._stack, long._stack)
        self.assertLess(self.card(plain).bottom(), self.card(long).top())
        self.assertLess(self.card(long).bottom(), self.card(short).top())

    def test_resize_bounds_overflow_retires_oldest_and_corners_are_independent(self):
        toasts = [
            Toast.success(str(i), parent=self.owner, placement="bottom-right", timeout_ms=0)
            for i in range(10)
        ]
        last = toasts[-1]
        self.owner.resize(380, 240)
        self.app.processEvents()
        members = last._stack.members()
        self.assertLess(len(members), 10)
        self.assertIs(members[-1], last)
        self.assertTrue(last.isVisible())
        self.assertTrue(all(self.owner.rect().contains(toast.geometry()) for toast in members))
        left = Toast.success("另一角", parent=self.owner, placement="top-left", timeout_ms=0)
        self.assertIsNot(left._stack, last._stack)

    def test_targeted_toasts_keep_arrow_and_do_not_join_corner_stack(self):
        target = QtWidgets.QPushButton("按钮", self.owner)
        target.setGeometry(300, 400, 80, 32)
        target.show()
        anchored = Toast.success("目标提示", target=target, timeout_ms=0)
        corner = Toast.success("角落提示", parent=self.owner, timeout_ms=0)
        self.assertIsNone(anchored._stack)
        self.assertIsNotNone(anchored._arrow_edge)
        self.assertEqual(len(corner._stack.members()), 1)

    def test_hide_and_reuse_or_change_corner_does_not_duplicate_entries(self):
        toast = Toast("可复用", parent=self.owner)
        toast.show_at("top-right")
        self.settle([toast])
        manager = toast._stack
        toast.hide()
        self.assertEqual(manager.members(), [])
        toast.show_at("bottom-left")
        toast.show_at("bottom-left")
        self.settle([toast])
        self.assertEqual(len(toast._stack.members()), 1)
        self.assertEqual(toast.x(), 18)

    def test_warning_progress_and_its_single_segment_still_render(self):
        toast = ProgressToast.start(
            "正在下载文件中，请稍候…", parent=self.owner, severity="warning", indeterminate=True
        )
        self.settle([toast])
        self.assertEqual(toast._icon.severity, "warning")
        self.assertFalse(toast.grab().isNull())
        toast.finish("下载成功", timeout_ms=0)
        self.assertEqual(toast.state(), "success")
        with self.assertRaises(ValueError):
            ProgressToast("无效", parent=self.owner, severity="other")
