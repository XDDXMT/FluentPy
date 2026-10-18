# 发布到 PyPI

项目安装名为 **fluentpy-qt**，导入名保留 **fluentpy**。PyPI 上的 `fluentpy` 已由其他项目使用。
不要把两个项目安装到同一个环境。当前源码及 PyPI 发布版本为 **0.7.1**。
发布助手按当前项目版本检查 `dist/pypi/0.7.1/`；发布文件已经上传，重复运行仅核对或跳过相同文件。

**0.7.1 已发布**：[PyPI 项目页](https://pypi.org/project/fluentpy-qt/0.7.1/)。三个文件均已核对公开 SHA-256；原生 wheel 已从 PyPI 实际下载安装，并通过八组后端、107 个图标及主要控件的安装验证。

此前的 [0.7.0](https://pypi.org/project/fluentpy-qt/0.7.0/) 与 [0.6.9](https://pypi.org/project/fluentpy-qt/0.6.9/) 发布文件保留原样。

## 账号准备

在 [PyPI 账号设置](https://pypi.org/manage/account/) 中完成邮箱验证和双重验证。
生成 API token 时，首次创建项目尚无法选择项目范围，可暂用整个账号范围。
第一次发布完成后，改用仅限 `fluentpy-qt` 的 token，并撤销首次使用的账号级 token。

API token 只在本机上传窗口的隐藏输入提示中填写，不发到聊天、不写入仓库或命令行参数。
本项目的上传助手不保存 token，也不修改用户的 `.pypirc` 或系统凭据。

## 0.7.1 的已发布文件

`dist/pypi/0.7.1/` 中只上传以下三种文件，`release.json` 是本地校验清单，不上传：

- `fluentpy_qt-0.7.1-py3-none-any.whl`：通用 Python 回退包，基本运行无需编译器。
- `fluentpy_qt-0.7.1-cp313-cp313-win_amd64.whl`：Windows x64／普通 CPython 3.13，含 C 扩展。
- `fluentpy_qt-0.7.1.tar.gz`：源码，含 C 文件、构建入口、测试和示例。

当前解释器兼容时，pip 优先选择原生 wheel；其他环境选择通用 wheel。
通用 wheel 运行兼容后端。其他平台要启用 C，可从源码构建，或以后补充对应平台的原生 wheel。

## 本机上传

检查文件而不上传：

```powershell
.\build\pypi-tools\Scripts\python.exe -X utf8 -B scripts/publish_pypi.py
```

准备好账号后，双击仓库根目录的 **上传到PyPI.bat**。
窗口会先列出项目名、版本和文件，复核 SHA-256、元数据及 PyPI 描述，然后进入官方 Twine 上传。
在 token／password 提示中粘贴完整 `pypi-...` 令牌，输入时不显示字符，按 Enter 提交。
不要填写 PyPI 登录密码。只有带 `--upload` 才会执行上传。

成功后助手再次查询 PyPI 的公开文件哈希。若网络中断，可重新运行：已存在且哈希相同的文件不重复上传；
同名文件内容不同则终止，不能覆盖已有发布文件。不要使用根目录 `dist/*`，那里还有旧构建和网站压缩包。

PyPI 公开索引可能稍晚于上传成功响应，本地助手会在约 27 秒内分次重试；若仍未同步，可只核验、不上传也不输入令牌：

```powershell
.\build\pypi-tools\Scripts\python.exe -X utf8 -B scripts/publish_pypi.py --verify-published
```

`This environment is not supported for trusted publishing` 提示指当前没有 CI 身份认证环境；本机使用 API token 上传仍可正常完成。

上传后可在新环境验证：

```powershell
python -m venv .venv-test
.\.venv-test\Scripts\python.exe -m pip install --index-url https://pypi.org/simple fluentpy-qt==0.7.1
.\.venv-test\Scripts\python.exe -c "import fluentpy; print(fluentpy.__version__)"
```

## 以后重新构建

发布工具使用 Python 3.12+（本机为 3.13），包括安全的源码解包过滤器；组件库本身仍支持 Python 3.10+。

```powershell
python -m venv build/pypi-tools
.\build\pypi-tools\Scripts\python.exe -m pip install --index-url https://pypi.org/simple build twine wheel "setuptools>=77"
.\build\pypi-tools\Scripts\python.exe -X utf8 -B scripts/prepare_release.py --native --zig .toolchains/zig-x86_64-windows-0.14.1/zig.exe
```

脚本从同一份 sdist 的两个独立目录构建原生及通用 wheel，避免旧 `.pyd` 混入通用包。
已有发布目录不会覆盖；修改代码后应先同步 `pyproject.toml` 和 `src/fluentpy/__init__.py` 的版本，再构建新版本。
只构建通用 wheel 时省略 `--native --zig ...`。准备脚本不上传。

官方参考：[打包教程](https://packaging.python.org/en/latest/tutorials/packaging-projects/)、
[PyPI token](https://pypi.org/help/#apitoken)、[Twine](https://twine.readthedocs.io/en/stable/)。
