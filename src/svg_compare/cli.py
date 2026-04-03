# 负责命令行入口。
# 用户运行命令时，由它来调用前面这些模块，把整条流程串起来。
# cli.py
#   -> pairing.py
#   -> preprocess.py
#   -> render.py
#   -> compare.py
#   -> report.py
# cli.py 负责总调度
# pairing.py 先把文件配对出来
# 对每一对文件：
# preprocess.py 处理 before/after 的 SVG
# render.py 把它们渲染成图片
# compare.py 比较两张图片
# 最后 report.py 统一写结果

# 假设处理一对文件：

# before/a.svg
# after/a.svg

# 顺序是这样：

# cli.py
#   -> pairing.py                  # 找到 a.svg 是 matched pair
#   -> preprocess.py              # 处理 before/a.svg
#   -> preprocess.py              # 处理 after/a.svg
#   -> render.py                  # 渲染 before 处理后的 SVG
#   -> render.py                  # 渲染 after 处理后的 SVG
#   -> compare.py                 # 比较两张图
#   -> report.py                  # 记录结果