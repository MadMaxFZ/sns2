# -*- coding: utf-8 -*-

"""
    This module contains classes to allow using Qt to control Vispy
"""

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
    def __init__(self, *args, **kwargs):
        super(MainQtWindow, self).__init__(*args,
                                           **kwargs)
        self._controls = Controls()
        self._canvas_wrapper = CanvasWrapper()
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(self._controls)
        # main_layout.addStretch()
        main_layout.addWidget(self._canvas_wrapper.canvas.native)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        self._connect_controls()

    def _connect_controls(self):
        # connect controls to appropriate functions
        pass


class Controls(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Controls, self).__init__(parent)
        # self.time_ctl = Ui_frm_TimeControl().setupUi(self)
        # self.bod_attrbs = Ui_frm_BodyAttribs().setupUi(self)
        # self.orb_states = Ui_frm_COE().setupUi(self)
        # vlo_main = QtWidgets.QVBoxLayout(self)
        # vlo_main.addWidget(self.bod_attrbs)
        # vlo_main.addWidget(self.orb_states)
        # vlo_main.addWidget(self.time_ctl)
        self.ui = Ui_Form().setupUi(self)

        # define functions of Qt controls here
        # print(self.ui.__dir__)


class CanvasWrapper:
    def __init__(self):
        self.canvas = MainSimWindow()

    def set_skymap_grid(self, color=(1, 1, 1, 1)):
        self.canvas.view.skymap.mesh.meshdata.color = color
        pass


if __name__ == "__main__":
    app = use_app("pyqt5")
    app.create()
    win = MainQtWindow()
    win.show()
    app.run()
