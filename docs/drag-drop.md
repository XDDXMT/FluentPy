# 文件与文件夹拖放

`FileDropWidget` 与 `FolderDropWidget` 继承 `DropArea`，使用 Qt 原生拖放事件和文件对话框。默认尺寸分别为300×144、246×144逻辑像素，可通过普通Qt布局或resize调整。

```python
from fluentpy import FileDropWidget, FolderDropWidget

files = FileDropWidget(extensions=[".jpg", ".png", ".gif"])
files.pathsSelected.connect(lambda paths: print(paths))
files.filesSelected.connect(lambda paths: print("文件", paths))
files.folderSelected.connect(lambda path: print("文件夹", path))
files.pathsRejected.connect(lambda rejected: print(rejected))

folders = FolderDropWidget()
folders.folderSelected.connect(lambda path: print(path))
```

文件组件默认允许多个文件及文件夹，提供两个浏览入口；文件夹组件默认只接收一个文件夹。目录直接返回规范路径，不递归扫描，业务应用决定后续操作。组件不移动、上传或读取文件内容。

只接收文件可使用`FileDropWidget(allow_folders=False)`。空后缀列表接受所有类型；`.png`、`png`、`*.PNG`均可，后缀大小写不敏感。

```python
files.set_file_extensions([".png", ".gif"])
files.set_multiple(False)
files.set_text("把图片拖到这里")
files.submit_paths(["C:/Pictures/example.png"])  # 后台校验
print(files.selected_paths())
files.clear()
```

浏览与拖放在后台检查路径，Qt原生文件信息提供规范路径和元数据，所选后端处理后缀、类型、去重和单多选策略。`accept_paths(paths)`为同步入口，适用于需要立即取得结果的应用调用；其返回本次接收的路径。`selected_paths()`返回最近一次有效选择的副本。

`selectionChanged`仅在有效选择改变时发出；`pathsSelected`每次接收有效选择都会发出；`filesSelected`与`folderSelected`按路径类型发出。信号均回到GUI线程。取消浏览或全部无效的选择保持原值，`clear()`清空并取消未完成请求。隐藏、禁用或销毁控件后，旧结果不会回显。

`pathsRejected`传递`[(path, reason), ...]`。原因包括：`extension`不支持的后缀、`type`路径类型不符、`missing`不存在、`duplicate`重复、`multiple`超过单选限制、`invalid`空或无效路径。部分项目无效时，其余有效项目正常提交；关闭多选时接收首个有效项目。`busyChanged`报告后台工作状态，`errorOccurred`报告校验异常。

C加速源码为`native/drop_accel.c`，Python兼容策略为`src/fluentpy/backends/_drop_python.py`。默认auto优先C，缺失或旧版扩展没有拖放接口时自动回退Python，文件浏览、拖入、过滤和后台校验均保留。`files.acceleration_backend()`读取实际后端；`FLUENTPY_BACKEND`统一控制文本、日期、拖放与快捷键，见[后端选择与回退](backends.md)。

独立运行：`python examples/drop.py`，或双击`examples/run_drop.bat`。工作台入口：`python examples/showcase.py --page drop`。

![浅色拖放示例](assets/drop-light.png)

![深色拖放示例](assets/drop-dark.png)
