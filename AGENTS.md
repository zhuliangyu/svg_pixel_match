## Design source of truth
- Read `docs/high-level-design.md` before changing pipeline structure.
- The V1 scope is defined there and should not be expanded unless explicitly requested.

项目目标：批量比较 before/ 和 after/ 的 SVG
V1 范围：按 id 删除、渲染、严格像素比较、只输出不同文件名
TDD 规则：先测试，后实现，最后重构
模块顺序：pairing → preprocess → compare → render → report → cli
命令：如何跑测试、如何跑单测、如何跑集成测试
约束：不要一次性生成整套系统；每次只做一个小任务；默认不扩 scope

在渲染SVG前，Python 先改 SVG 文本，再送给浏览器, 先在内存里把这些 id 对应的节点删除，再把处理后的 SVG 送去渲染。

TDD 规则：先测试，后实现，最后重构

模块顺序：pairing → preprocess → compare → render → report → cli

Core Workflow:
