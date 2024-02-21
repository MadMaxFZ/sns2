# -*- coding: utf-8 -*-

"""
    This module contains classes to allow using Qt to control Vispy
"""

import logging
import logging.config
from typing import List

import autologging
import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread
from vispy.scene import SceneCanvas, visuals
from vispy.app import use_app
from sim_canvas import MainSimCanvas
from sns2_gui import Ui_wid_BodyData
# from body_attribs import Ui_frm_BodyAttribs
# from orbit_classical import Ui_frm_COE
# from time_control import Ui_frm_TimeControl
from composite import Ui_frm_sns_controls
from starsys_data import log_config
from camera_set import CameraSet


logging.config.dictConfig(log_config)


class MainQtWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainQtWindow, self).__init__(*args,
                                           **kwargs)
        self._controls = Controls()
        self._canvas = CanvasWrapper()
        self._canvas.assign_cam(cams=self._canvas.cameras)
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(self._controls)
        # main_layout.addStretch()
        main_layout.addWidget(self._canvas.native)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        self._connect_controls()
        self.thread = QThread()
        # self._canvas.model.moveToThread(self.thread)

    def _connect_controls(self):

        # connect control slots to appropriate functions in response to signals

        pass


class Controls(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Controls, self).__init__(parent)

        self.ui = Ui_frm_sns_controls()
        self.ui.setupUi(self)
        self.ui_obj_dict = self.ui.__dict__
        logging.info([i for i in self.ui_obj_dict.keys() if (i.startswith("lv") or "warp" in i)])
        self._panel_names = ['attr', 'coe', 'pqw', 'rv', 'axis', 'cam', 'twarp']
        self._control_groups = self._scanUi_4panels(patterns=self._panel_names)

        # define functions of Qt controls here

    def _scanUi_4panels(self, patterns: List[str]) -> dict:
        """ This method identifies objects that contain one of the strings in the patterns list.
            The objects containing each pattern are collected into a dict with the pattern
            as the key with the value being a list of objects containing that pattern.

        Parameters
        ----------
            patterns :  a list of strings that the object names are matched to

        Returns
        -------
            dict     : a dict with the pattern string as a key and the value is a list of
                       the objects whose name contains that string.
        """
        panels = {}
        for p in patterns:
            panels.update({p: [(name, widget) for name, widget in
                           self.ui_obj_dict.items() if p in name]})

        return panels

    @property
    def panels(self, name=None):
        if name is None:
            return self._control_groups
        elif name in self._control_groups.keys():
            return self._control_groups[name]
        else:
            return None


class CanvasWrapper(MainSimCanvas):
    """     This class simply encapsulates the simulation, which resides within
        the vispy SceneCanvas object. This SceneCanvas has three main properties:
        - model :   contains and manages the properties of the model
        - view  :   contains the rendering of the simulation scene
        - vizz  :   contains the vispy visual nodes rendered in the view
    """
    def __init__(self):
        super(CanvasWrapper, self).__init__()
        self.assign_cam(CameraSet())

    @property
    def cameras(self):
        return self.cameras

    def set_skymap_grid(self, color=(1, 1, 1, 1)):
        self.view.skymap.mesh.meshdata.color = color
        pass


def load_simulation():
    res = MainQtWindow()

    return res


if __name__ == "__main__":
    app = use_app("pyqt5")
    app.create()
    sim = load_simulation()
    sim.show()
    app.run()
