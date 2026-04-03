# SVG Batch Compare - High Level Design

目标规模：约 2000 对 SVG
每张 SVG 约 2 MB

## 1. Goal
    - 输入有两个目录：before/ 和 after/
    - 里面有同名 SVG，一一对应
    - 先按规则删除指定 element
    - 再渲染
    - 再做严格像素比较
    - 输出不同文件名和错误信息

## 2. V1 Scope
### In scope
    - 按 id 精确删除 element
    - 渲染 SVG 成 PNG
    - 严格 RGBA 比较
    - 只输出 different.txt、error.txt、summary.json
### Out of scope
    - 不处理非 .svg 文件
    - 不处理不配对的文件
    - 不输出 diff 图片
    - 不做模糊匹配
    - 不支持其他格式
    - 不支持 xpath
    - 不做视觉容差
    - 不做复杂 UI
    - 不做云端服务

## 3. Inputs and Outputs
- 输入
    - before_dir
    - after_dir
    - remove_ids
    - output_dir
    - concurrency
- 输出
    - different.txt
    - error.txt
    - summary.json

different.txt 一行一个文件名
error.txt 一行一个 filename + reason

## 4. End-to-end Workflow
1. 扫描两个目录 before and after
2. 只关注 .svg 文件, 忽视其他文件类型
3. 按文件名配对, 不配对的文件直接跳过
4. 从 before/xxx.svg 读入原始文本
5. 找到after文件夹中同名文件
6. Python 在内存里解析 SVG XML
7. SVG在内存中预处理, 删除用户指定的 id 的节点
8. 得到“处理后的 SVG 字符串”
9. 把这个字符串直接喂给浏览器页面
10. 浏览器渲染后直接拿 screenshot 的 bytes (渲染 PNG 不用写临时文件)
11. 对after文件夹中同名文件做同样处理
12. Pillow 从 bytes 读图
13. Pillow在内存中做比较
14. 只输出结果文件名

假设处理一对文件：

before/a.svg
after/a.svg

顺序是这样：

cli.py
  -> pairing.py                  # 找到 a.svg 是 matched pair
  -> preprocess.py              # 处理 before/a.svg
  -> preprocess.py              # 处理 after/a.svg
  -> render.py                  # 渲染 before 处理后的 SVG
  -> render.py                  # 渲染 after 处理后的 SVG
  -> compare.py                 # 比较两张图
  -> report.py                  # 记录结果

## 5. Module Design
### pairing
### preprocess
### render
### compare
### report
### cli

## 6. Key Design Decisions

## 7. Error Handling
    - 定义这些错误类型：
        - missing_in_before
        - missing_in_after
        - invalid_svg
        - preprocess_error
        - render_error
        - different_size
    - 并说明：
        - 出错时是否继续处理其他文件
        - 错误记录到哪里
        - summary 怎么统计

## 8. Testing Strategy
- TDD
- 单元测试覆盖
    - pairing
    - preprocess
    - compare
    - report
- 集成测试覆盖
    - render
    - CLI orchestrator
    - 最小 end-to-end
- 不测什么
    - 不在单测里启动真实浏览器
    - 浏览器只留少量集成测试
## 9. Performance Assumptions
    - 目标规模：约 2000 对 SVG
    - 每张 SVG 约 2 MB
    - 每张渲染不超过 1 秒
    - 默认并发目标：4
    - 输出只保留结果文件，不保留 diff 图
## 10. Future Extensions