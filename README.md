# svg_pixel_match

批量比较 `before/` 和 `after/` 两个目录中的同名 SVG。

当前已实现的 V1 核心链路：

- 只扫描 `.svg`
- 按同名文件配对
- 按 `id` 删除指定元素
- 使用 Playwright Chromium 渲染 SVG 为 PNG
- 使用 Pillow 严格比较两张 PNG
- 输出：
  - `outputs/different.txt`
  - `outputs/unmatched_svgs.txt`

## 环境要求

- Python 3.13
- Windows PowerShell

## 安装依赖

先安装 Python 依赖：

```powershell
pip install pytest playwright pillow
```

再安装 Playwright Chromium：

```powershell
python -m playwright install chromium
```

如果你的环境里 `pip` 不在 PATH，也可以用：

```powershell
python -m pip install pytest playwright pillow
python -m playwright install chromium
```

## 如何运行程序

这个项目当前使用 `src/` 布局，直接运行 CLI 时需要把 `src` 加到 `PYTHONPATH`。

示例：

```powershell
$env:PYTHONPATH="src"
python -m svg_compare.cli `
  --before-dir tests/fixtures/before `
  --after-dir tests/fixtures/after `
  --remove-id mycurrenttime
```

如果需要删除多个 `id`，重复传入 `--remove-id`：

```powershell
$env:PYTHONPATH="src"
python -m svg_compare.cli `
  --before-dir tests/fixtures/before `
  --after-dir tests/fixtures/after `
  --remove-id mycurrenttime `
  --remove-id dot-before-a
```

运行后会先清空 `outputs/`，然后生成：

- `outputs/different.txt`
- `outputs/unmatched_svgs.txt`

## Debug 渲染

如果你想单独把某个 SVG 渲染成 PNG 方便查看，可以打开 debug：

```powershell
$env:PYTHONPATH="src"
python -m svg_compare.cli `
  --before-dir tests/fixtures/before `
  --after-dir tests/fixtures/after `
  --remove-id mycurrenttime `
  --debug `
  --debug-svg-path tests/fixtures/before/sample_same_1.svg `
  --debug-output-group before
```

这会额外输出：

- `outputs/before/sample_same_1.png`

`--debug-output-group` 只允许：

- `before`
- `after`

## 如何跑测试

跑全部当前测试：

```powershell
python -m pytest tests
```

跑单个模块测试：

```powershell
python -m pytest tests/test_pairing.py
python -m pytest tests/test_preprocess.py
python -m pytest tests/test_render.py
python -m pytest tests/test_compare.py
python -m pytest tests/test_cli.py
```

跑集成测试：

```powershell
python -m pytest tests/test_cli.py -k expected_different_txt
```

## 当前输出说明

- `different.txt`
  - 一行一个渲染后不同的文件名
- `unmatched_svgs.txt`
  - 一行一个未配对的 `.svg` 文件名

## 当前限制

当前还没有完成：

- `error.txt`
- `summary.json`
- 更完整的错误分类和统计
