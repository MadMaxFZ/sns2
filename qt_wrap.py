# -*- coding: utf-8 -*-

"""
    This module contains classes to allow using Qt to control Vispy
"""

import numpy as np
from PyQt5 import QtWidgets
from vispy.scene import SceneCanvas, visuals
from vispy.app import use_app
from sim_window import MainSimWindow


class MainQtWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainQtWindow, self).__init__(*args, **kwargs)
        central_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QHBoxLayout()
        self._controls = Controls()
        main_layout.addWidget(self._controls)
        self._canvas_wrapper = CanvasWrapper()
        main_layout.addWidget(self._canvas_wrapper.canvas.native)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        self._connect_controls()

    def _connect_controls(self):
        # connect controls to appropriate functions
        pass


class Controls(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Controls, self).__init__(parent)
        layout = QtWidgets.QVBoxLayout()
        # define Qt controls here


class CanvasWrapper:
    def __init__(self):
        self.canvas = MainSimWindow()

    def set_skymap_grid(self, color=(1, 1, 1, 1)):
        pass


if __name__ == "__main__":
    app = use_app("pyqt5")
    app.create()
    win = MainQtWindow()
    win.show()
    app.run()
