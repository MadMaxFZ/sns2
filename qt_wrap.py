# -*- coding: utf-8 -*-

"""
    This module contains classes to allow using Qt to control Vispy
"""

import gc
import logging
import logging.config
import autologging
import numpy as np
from PyQt5 import QtWidgets
from vispy.scene import SceneCanvas, visuals
from vispy.app import use_app
from sim_window import MainSimWindow
from sns2_gui import Ui_wid_BodyData
# from body_attribs import Ui_frm_BodyAttribs
# from orbit_classical import Ui_frm_COE
# from time_control import Ui_frm_TimeControl
from composite import Ui_Form
from starsys_data import log_config

logging.config.dictConfig(log_config)


class MainQtWindow(QtWidgets.QMainWindow):
    def __init__(self, names=None, *args, **kwargs):
        super(MainQtWindow, self).__init__(*args,
                                           **kwargs)
        self._controls = Controls()
        self._canvas_wrapper = CanvasWrapper(names)
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(self._controls)
        main_layout.addWidget(self._canvas_wrapper.canvas.native)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        self._canvas_wrapper.canvas.model.toggle_timer()
        self._connect_controls()

    def _connect_controls(self):
        # stuff = gc.get_objects()
        # print(stuff)
        # connect controls to appropriate functions
        pass


class Controls(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Controls, self).__init__(parent)
        self.ui = Ui_Form().setupUi(self)

        # define functions of Qt controls here
        # print(self.ui.__dir__)


class CanvasWrapper:
    def __init__(self, names):
        self.canvas = MainSimWindow(body_names=names)

    def set_skymap_grid(self, color=(1, 1, 1, 1)):
        self.canvas.view.skymap.mesh.meshdata.color = color
        pass


if __name__ == "__main__":
    _body_include_set = ['Sun',
                         'Mercury',
                         'Venus',
                         'Earth',
                         'Moon',  # all built-ins from poliastro
                         'Mars',
                         'Jupiter',
                         'Saturn',
                         'Uranus',
                         'Neptune',
                         'Pluto',
                         # 'Phobos',
                         # 'Deimos',
                         # 'Europa',
                         # 'Ganymede',
                         # 'Enceladus',
                         # 'Titan',
                         # 'Titania',
                         # 'Triton',
                         # 'Charon',
                         ]
    app = use_app("pyqt5")
    app.create()
    win = MainQtWindow(names=_body_include_set)
    win.show()
    app.run()
