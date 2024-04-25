import ast


def show_info(functionNode):
    if len(functionNode.args.args) > 1:
        print("\n\tFunction name:", functionNode.name)
        for arg in functionNode.args.args:
            # import pdb; pdb.set_trace()
            print("\t\tParameter:\t", arg.arg)
    else:
        print("\n\tProperty name:", functionNode.name)


def scan_fname(filename=None):
    with open(filename) as file:
        node = ast.parse(file.read())

    functions = [n for n in node.body if isinstance(n, ast.FunctionDef)]
    classes = [n for n in node.body if isinstance(n, ast.ClassDef)]

    for function in functions:
        show_info(function)

    for class_ in classes:
        print("--------------------------------------")
        print("Class name:", class_.name)
        methods = [n for n in class_.body if isinstance(n, ast.FunctionDef)]
        for method in methods:
            show_info(method)


path_name = "C:\\_Projects\\sns2\\src\\"
trgt_dict = dict(g="starsys_data.py",
                 # i="viz_functs.py",
                 # f="qt_wrap.py",
                 f="sim_controls.py",
                 i="main_sim_win.py",
                 e="sim_canvas.py",
                 a="starsys_model.py",
                 b="simbody_model.py",
                 c="starsys_visual.py",
                 d="simbody_visual.py",
                 h="skymap_visual.py",
                 j="camera_dict.py",
                 k="gui_composite.py",
                 )
for i in sorted(trgt_dict.keys()):
    filename = path_name + trgt_dict[i]
    print("======================================")
    print(filename)
    print("======================================")
    scan_fname(filename=filename)
    print("**************************************")

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