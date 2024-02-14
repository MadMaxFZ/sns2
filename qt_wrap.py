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
from composite import Ui_frm_sns_controls
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

        self.ui = Ui_frm_sns_controls()
        self.ui.setupUi(self)
        self.ui_obj_dict = self.ui.__dict__()
        logging.info([i for i in self.ui_obj_dict.keys() if (i.startswith("lv") or "warp" in i)])
        self._panel_names = ['attr', 'coe', 'qkw', 'rv', 'axis', 'cam', 'twarp']
        self._panel_widgs = self._get_panel_items(names=self._panel_names)

        # define functions of Qt controls here

    def _get_panel_items(self, names):
        panels = {}
        for n in names:
            panels.update({n: [self.ui.i for i in self.ui if n in i.__dir__()]})

        return panels


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
