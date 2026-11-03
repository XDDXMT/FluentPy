# FluentPy 展示主页

独立于文档的轻量介绍页。`dist/` 使用普通 HTML、CSS、JavaScript 和项目自己的 Qt 截图，不需要 Node.js 构建或服务器接口。

- `dist/index.html`：项目定位、真实界面预览、安装与作者介绍。
- `dist/home.css`、`dist/home.js`：响应式、明暗主题、预览切换与安装命令复制。
- `package_site.py`：把主页与现有文档组合成完整静态网站；主页在 `/`，文档在 `/docs/`。

从组件库根目录生成可预览目录：

```powershell
python sites/fluentpy-docs/build_content.py
python sites/fluentpy-home/package_site.py
python scripts/preview_site.py
```

手动部署包：

```powershell
python sites/fluentpy-home/package_site.py --output dist/site/FluentPy-site-complete.zip
```

输出包不会覆盖已有压缩包。把包内的完整目录上传到网站根目录，保留 `assets/` 和 `docs/`；服务器无需 Python、Qt 或 Node.js。旧的 `/#/...` 文档链接会跳转至 `/docs/#/...`。文档内容和生成工具仍在 `sites/fluentpy-docs`。

页面使用 FluentPy 自有标识与真实 Qt 截图，项目采用 MIT。截图内的 Microsoft 图标遵循随资源提供的 MIT 许可。

预览脚本使用绝对路径提供首页和 `/docs/`，避免在其他目录运行相对 `--directory` 时出现 404。也可以从任意目录运行：

```powershell
python "D:\文档\fluentpy\scripts\preview_site.py"
```

服务默认仅监听本机 127.0.0.1:8768；端口已被占用时会报告错误，不结束其他程序。
