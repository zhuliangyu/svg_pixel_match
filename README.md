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
  - `outputs/diff_details/`

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

推荐先进入项目目录再运行：

```powershell
Set-Location "D:\Code\svg_pixel_match"
$env:PYTHONPATH="src"
python -m svg_compare.cli `
  --before-dir tests/fixtures/before `
  --after-dir tests/fixtures/after `
  --concurrency 4 `
  --remove-id mycurrenttime
```

如果你不在项目目录下运行，就要把 `PYTHONPATH` 设成绝对路径：

```powershell
$env:PYTHONPATH="D:\Code\svg_pixel_match\src"
python -m svg_compare.cli `
  --before-dir "D:\Code\svg_pixel_match\tests\fixtures\before" `
  --after-dir "D:\Code\svg_pixel_match\tests\fixtures\after" `
  --concurrency 4 `
  --remove-id mycurrenttime
```

如果需要删除多个 `id`，重复传入 `--remove-id`：

```powershell
Set-Location "D:\Code\svg_pixel_match"
$env:PYTHONPATH="src"
python -m svg_compare.cli `
  --before-dir tests/fixtures/before `
  --after-dir tests/fixtures/after `
  --concurrency 4 `
  --remove-id mycurrenttime `
  --remove-id dot-before-a
```

`--concurrency` 默认值是 `4`。

运行后会先清空 `outputs/`，然后生成：

- `outputs/different.txt`
- `outputs/unmatched_svgs.txt`
- `outputs/diff_details/<filename-stem>/`

## Debug 渲染

如果你想单独把某个 SVG 渲染成 PNG 方便查看，可以打开 debug：

```powershell
Set-Location "D:\Code\svg_pixel_match"
$env:PYTHONPATH="src"
python -m svg_compare.cli `
  --before-dir tests/fixtures/before `
  --after-dir tests/fixtures/after `
  --concurrency 4 `
  --remove-id mycurrenttime `
  --debug `
  --debug-svg-path tests/fixtures/before/sample_same_1.svg `
  --debug-output-group before
```

这会额外输出：

- `outputs/debug/before/sample_same_1.png`

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
python -m pytest tests/test_cli.py -k integration
```

## Benchmark

可以用仓库里的脚本批量生成大 SVG 基准数据。

生成 `500` 对、单文件约 `1.5MB` 的测试数据：

```powershell
Set-Location "D:\Code\svg_pixel_match"
python tests/benchmarks/generate_large_svg_pairs.py `
  --output-root tests/benchmarks/large_500_pairs `
  --pairs 500 `
  --target-bytes 1500000
```

生成后目录是：

- `tests/benchmarks/large_500_pairs/before`
- `tests/benchmarks/large_500_pairs/after`

数据规则：

- 前一半文件对渲染结果相同
- 后一半文件对渲染结果不同

运行 benchmark：

```powershell
Set-Location "D:\Code\svg_pixel_match"
$env:PYTHONPATH="src"
python -m svg_compare.cli `
  --before-dir tests/benchmarks/large_500_pairs/before `
  --after-dir tests/benchmarks/large_500_pairs/after `
  --concurrency 4
```

一次实际测得的参考结果：

- 数据规模：`500` 对，`1000` 张 SVG
- 单文件大小：平均约 `1.5MB`
- 总耗时：约 `531.31` 秒
- 每 `100` 张图片平均耗时：约 `53.13` 秒
- 每 `100` 对平均耗时：约 `106.26` 秒

这个结果会受以下因素影响：

- CPU 性能
- 磁盘速度
- Playwright Chromium 启动开销
- SVG 的复杂度
- 并发数设置

## 当前输出说明

- `different.txt`
  - 一行一个渲染后不同的文件名
- `unmatched_svgs.txt`
  - 一行一个未配对的 `.svg` 文件名
- `diff_details/<filename-stem>/before.png`
  - 差异文件对应的 before 渲染图
- `diff_details/<filename-stem>/after.png`
  - 差异文件对应的 after 渲染图
- `diff_details/<filename-stem>/diff.png`
  - 相同像素透明，不同像素高亮为红色
- `debug/before/*.png`
  - 手动开启 `--debug --debug-output-group before` 时的单图渲染输出
- `debug/after/*.png`
  - 手动开启 `--debug --debug-output-group after` 时的单图渲染输出

## 当前限制

当前还没有完成：

- `error.txt`
- `summary.json`
- 更完整的错误分类和统计
