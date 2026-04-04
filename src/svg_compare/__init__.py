# __init__.py 的核心作用是把目录声明成一个 Python 包。
                                                                                                                                                    
#   在你这个项目里，src/svg_compare/__init__.py 的意义主要有两点：                                                                                    
                                                                                                                                                    
#   - 让 svg_compare 被当成可导入包使用，这样测试里才能写 from svg_compare.cli import main                                                            
#   - 作为包级入口预留位置，后面如果你想在包层暴露公共 API，可以放到这个文件里                                                                        
                                                                                                                                                    
#   结合你当前结构：                                                                                                                                  
                                                                                                                                                    
#   - src/svg_compare__init__.py                                                                                                                      
#   - src/svg_compare/cli.py                                                                                                                          
                                                                                                                                                    
#   有了 __init__.py，src/svg_compare/ 就是一个明确的包目录。虽然在现代 Python 里有时可以靠“命名空间包”不写这个文件，但你这个项目是标准 src/ 布局，保 
#   留空的 __init__.py 更稳妥，也更符合测试和打包习惯。  