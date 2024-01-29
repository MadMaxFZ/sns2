import ast


def show_info(functionNode):
    print("\nFunction name:", functionNode.name)
    print("Args:")
    for arg in functionNode.args.args:
        #import pdb; pdb.set_trace()
        print("\tParameter name:", arg.arg)


def scan_fname(filename=None):
    with open(filename) as file:
        node = ast.parse(file.read())

    functions = [n for n in node.body if isinstance(n, ast.FunctionDef)]
    classes = [n for n in node.body if isinstance(n, ast.ClassDef)]

    for function in functions:
        show_info(function)

    for class_ in classes:
        print("Class name:", class_.name)
        methods = [n for n in class_.body if isinstance(n, ast.FunctionDef)]
        for method in methods:
            show_info(method)

path_name = "C:\\_Projects\\sns2\\"
name_list = ['starsys_data.py',
             # 'viz_functs.py',
             'sim_window.py',
             'starsys_model.py',
             'sysbody_model.py',
             'starsys_visual.py',
             'sysbody_visual.py',
             'sys_skymap.py',
             ]
for name in name_list:
    filename = path_name + name
    print("--------------------------------------\n", filename,
          "\n--------------------------------------\n")
    scan_fname(filename=filename)
    print("======================================\n")

"""
import ast

from pathlib import Path

parsed_ast = ast.parse(Path(__file__).read_text())

functions = [
    node
    for node in ast.walk(parsed_ast)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
]

for function in functions:
    print(f"Function name: {function.name}")
    print(f"Args: {', '.join([arg.arg for arg in function.args.args])}")
"""