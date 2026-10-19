"""Slider, ToolTipSlider and RangeSlider using one live preview."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from component_playground import Playground, PlaygroundWindow

from fluentpy import (
    CheckBox,
    ComboBox,
    ExpandableCardWidget,
    RangeSlider,
    Slider,
    SpinBox,
    ToolTipSlider,
    theme,
)
from fluentpy.qt import QtCore, QtWidgets


class SliderExamples(Playground):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.preview = None
        self._syncing = False
        self.class_label = QtWidgets.QLabel("Slider")
        self.preview_layout.addWidget(self.class_label)
        self.preview_layout.addStretch()
        self.slot = QtWidgets.QVBoxLayout()
        self.slot.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.preview_layout.addLayout(self.slot, 1)
        self.preview_layout.addStretch()
        self.readout = QtWidgets.QLabel()
        self.readout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.preview_layout.addWidget(self.readout)
        self.hint = QtWidgets.QLabel("点击轨道或拖动滑块；也可使用方向键、Home / End。")
        self.hint.setWordWrap(True)
        self.preview_layout.addWidget(self.hint)
        self.kind = ComboBox()
        self.kind.addItems(["标准滑块", "数值提示", "区间选择"])
        self.field("组件类型", self.kind)
        self.orientation = ComboBox()
        self.orientation.addItems(["水平", "垂直"])
        self.field("方向", self.orientation)
        self.value_input = SpinBox()
        self.value_input.setRange(0, 100)
        self.value_input.setValue(35)
        self.value_caption = self.field("当前值", self.value_input)
        self.upper_input = SpinBox()
        self.upper_input.setRange(0, 100)
        self.upper_input.setValue(80)
        self.upper_caption = self.field("上界", self.upper_input)
        self.enabled = CheckBox("允许交互")
        self.enabled.setChecked(True)
        self.form.addWidget(self.enabled)
        self.advanced = ExpandableCardWidget("更多设置")
        self.minimum_input, self.maximum_input, self.step_input = SpinBox(), SpinBox(), SpinBox()
        self.minimum_input.setRange(-10000, 10000)
        self.maximum_input.setRange(-10000, 10000)
        self.maximum_input.setValue(100)
        self.step_input.setRange(1, 100)
        self.step_input.setValue(1)
        for caption, widget in [
            ("最小值", self.minimum_input),
            ("最大值", self.maximum_input),
            ("键盘步长", self.step_input),
        ]:
            self.advanced.body_layout.addWidget(QtWidgets.QLabel(caption))
            self.advanced.body_layout.addWidget(widget)
        self.tracking = CheckBox("拖动时实时更新")
        self.tracking.setChecked(True)
        self.inverted = CheckBox("反转显示方向")
        self.gradient = CheckBox("渐变轨道")
        for widget in (self.tracking, self.inverted, self.gradient):
            self.advanced.body_layout.addWidget(widget)
        self.form.addWidget(self.advanced)
        self.form.addStretch()
        for field in (self.kind, self.orientation):
            field.currentIndexChanged.connect(self.rebuild)
        for field in (self.minimum_input, self.maximum_input, self.step_input):
            field.valueChanged.connect(self.rebuild)
        for field in (self.enabled, self.tracking, self.inverted, self.gradient):
            field.toggled.connect(self.rebuild)
        self.value_input.valueChanged.connect(self.apply_values)
        self.upper_input.valueChanged.connect(self.apply_values)
        self.rebuild()

    def rebuild(self, *args):
        if self._syncing:
            return
        self._syncing = True
        if self.preview is not None:
            self.slot.removeWidget(self.preview)
            self.preview.hide()
            self.preview.deleteLater()
        lo, hi = self.minimum_input.value(), self.maximum_input.value()
        if hi < lo:
            hi = lo
            self.maximum_input.setValue(hi)
        for field in (self.value_input, self.upper_input):
            field.setRange(lo, hi)
        if self.upper_input.value() < self.value_input.value():
            self.upper_input.setValue(self.value_input.value())
        cls = (Slider, ToolTipSlider, RangeSlider)[self.kind.currentIndex()]
        orientation = (
            QtCore.Qt.Orientation.Horizontal
            if self.orientation.currentIndex() == 0
            else QtCore.Qt.Orientation.Vertical
        )
        widget = cls(orientation, self.canvas)
        self.preview = widget
        widget.setRange(lo, hi)
        widget.setSingleStep(self.step_input.value())
        widget.setPageStep(max(1, self.step_input.value() * 10))
        widget.setTracking(self.tracking.isChecked())
        widget.setInvertedAppearance(self.inverted.isChecked())
        widget.setEnabled(self.enabled.isChecked())
        if orientation == QtCore.Qt.Orientation.Horizontal:
            widget.setMinimumWidth(160)
            widget.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
            )
        else:
            widget.setFixedSize(38, 210)
        self.slot.addWidget(widget)
        if isinstance(widget, RangeSlider):
            widget.setValues(self.value_input.value(), self.upper_input.value())
            widget.valuesChanged.connect(self.sync_values)
            self.hint.setText("拖动两端选择区间；Space 切换当前端点，方向键调整。")
        else:
            widget.setValue(self.value_input.value())
            widget.valueChanged.connect(self.sync_values)
            self.hint.setText("点击轨道或拖动滑块；也可使用方向键、Home / End。")
        if self.gradient.isChecked():
            widget.set_track_gradient([(0, "#16418c"), (1, "#00bbbd")], thickness=8)
        is_range = isinstance(widget, RangeSlider)
        self.upper_input.setVisible(is_range)
        self.upper_caption.setVisible(is_range)
        self.value_caption.setText("下界" if is_range else "当前值")
        self.class_label.setText(cls.__name__)
        widget.show()
        self._syncing = False
        self.sync_values()

    def apply_values(self, *args):
        if self._syncing:
            return
        if isinstance(self.preview, RangeSlider):
            lower = min(self.value_input.value(), self.upper_input.value())
            upper = max(self.value_input.value(), self.upper_input.value())
            self.preview.setValues(lower, upper)
            self.sync_values()
        else:
            self.preview.setValue(self.value_input.value())

    def sync_values(self, *args):
        if self._syncing:
            return
        self._syncing = True
        if isinstance(self.preview, RangeSlider):
            lower, upper = self.preview.values()
            self.value_input.setValue(lower)
            self.upper_input.setValue(upper)
            text = f"{lower} – {upper}"
        else:
            self.value_input.setValue(self.preview.value())
            text = str(self.preview.value())
        self.readout.setText(text)
        self.readout.setStyleSheet(f"color:{theme.tokens.accent};font-size:28px;font-weight:600;")
        self.result.setText(
            "当前选择："
            + text
            + (" · 松开后提交" if not self.preview.hasTracking() else " · 拖动时实时更新")
        )
        self._syncing = False

    def _apply_theme(self):
        super()._apply_theme()
        if hasattr(self, "readout"):
            self.readout.setStyleSheet(
                f"color:{theme.tokens.accent};font-size:28px;font-weight:600;"
            )


class SliderDemo(PlaygroundWindow):
    def __init__(self, dark=False):
        super().__init__("滑块", SliderExamples, dark=dark)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dark", action="store_true")
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    demo = SliderDemo(args.dark)
    demo.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
