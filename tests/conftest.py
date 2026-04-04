from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# tests/conftest.py 是 pytest 的本地配置与共享夹具文件。它的意义不是“普通测试文件”，而是给整个 tests/ 目录提供公共测试环境。

#   在你这个项目里，它当前只做了一件事：
                                                                                                                                                    
#   - 把 src/ 加进 sys.path                                                                                                                           
#   - 这样 pytest 跑测试时，tests/test_cli.py 才能导入 svg_compare                                                                                    
                                                                                                                                                    
#   也就是它解决了你现在这个问题：                                                                                                                    
                                                                                                                                                    
#   - 项目采用 src/ 布局                                                                                                                              
#   - 直接跑 python -m pytest tests\test_cli.py 时，Python 默认找不到 src/svg_compare                                                                 
#   - 所以在 tests/conftest.py 里统一补上导入路径                                                                                                     
                                                                                                                                                    
#   它后面还常用于这些用途：                                                                                                                          
                                                                                                                                                    
#   - 放共享 fixture                                                                                                                                  
#   - 放测试前置/后置逻辑                                                                                                                             
#   - 放全局测试钩子                                                                                                                                  
#   - 放公共 mock/测试数据构造                                                                                                                        
                                                                                                                                                    
#   所以对你当前项目来说，它的存在意义就是：让测试环境知道源码包在哪，并作为以后测试公共配置的集中入口。      
