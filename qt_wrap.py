# -*- coding: utf-8 -*-

"""
    This module contains classes to allow using Qt to control Vispy
"""

import logging
import logging.config
from typing import List

import autologging
import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from vispy.scene import SceneCanvas, visuals
from vispy.app import use_app
from sim_canvas import MainSimCanvas
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
        self.setWindowTitle("SPACE NAVIGATION SIMULATOR, (c)2024 Max S. Whitten")
        self.controls = Controls()
        self.ui       = self.controls.ui
        self.canvas   = CanvasWrapper()
        self.model    = self.canvas.model

        main_layout = QtWidgets.QHBoxLayout()
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.controls)
        splitter.addWidget(self.canvas.native)
        main_layout.addWidget(splitter)
        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.controls.connect_controls()
        self.thread = QThread()
        self.model.moveToThread(self.thread)
        self.thread.start()
        self.init_controls()

    def init_controls(self):
        self.ui.bodyList.clear()
        self.ui.bodyList.addItems(self.model.simbodies.keys())
        self.ui.bodyBox.addItems(self.model.simbodies.keys())
        # add items to camera combobox
        self.ui.tabWidget_Body.setCurrentIndex(0)
        self.ui.bodyBox.setCurrentIndex(0)
        self.controls.gimmedat.emit([self.controls.active_body,
                                     self.controls.active_panel,
                                     self.controls.active_cam,
                                     ])
        pass


class Controls(QtWidgets.QWidget):
    gimmedat = pyqtSignal(list)

    def __init__(self, parent=None):
        super(Controls, self).__init__(parent)

        self.ui = Ui_frm_sns_controls()
        self.ui.setupUi(self)
        self.ui_obj_dict = self.ui.__dict__
        logging.info([i for i in self.ui_obj_dict.keys() if (i.startswith("lv") or "warp" in i)])
        self._wgtgrp_names = ['attr', 'elem', 'elem_coe', 'elem_pqw', 'elem_rv', 'cam', 'tw', 'twb', 'axis']
        self._control_groups = self._scanUi_4panels(patterns=self._wgtgrp_names)
        self.tab_names = ['tab_TIME', 'tab_ATTR', 'tab_ELEM', 'tab_CAMS']

        # self._body_list = self.ui.bodyList
        # self._curr_body = self.ui.bodyBox
        # self._body_tabs = self.ui.tabWidget_Body
        # self._curr_cam = self.ui.camBox
        # self._time_warp = self.ui.twarp_val
        # self._tw_base = self.ui.tw_mant
        # self._tw_exp = self.ui.twarp_exp

        self.active_body = self.ui.bodyBox.currentText()
        self.active_cam = self.ui.camBox.currentText()
        self.active_panel = self.tab_names[self.ui.tabWidget_Body.currentIndex()]
        # define functions of Qt controls here

    def connect_controls(self):
        # TODO:: Must figure out how to implement signal/slot from Controls to Model and back
        #        Controls send three strings to Model indicating which data sets requested
        #        Models needs a slot which will signal back with the indicated data sets,
        #        then Controls needs a slot which updates its widgets...
        # connect control slots to appropriate functions in response to signals
        self.ui.bodyBox.currentIndexChanged.connect(self.ui.bodyList.setCurrentRow)
        # self.ui.bodyBox.currentIndexChanged.connect(self._refresh)
        self.ui.bodyList.currentRowChanged.connect(self.ui.bodyBox.setCurrentIndex)

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

    def _refresh(self):
        self.gimmedat.emit([self.ui.bodyBox.currentText(),
                            self.tab_names[self.ui.tabWidget_Body.currentIndex()],
                            self.ui.camBox.currentText()],
                           )
        pass

    @property
    def panels(self, name=None):
        if name is None:
            return self._control_groups
        elif name in self._control_groups.keys():
            return self._control_groups[name]
        else:
            return None

    @property
    def body_list(self):
        return self.ui.bodyList.items()

    @property
    def curr_body(self):
        return self.ui.bodyBox.currentText()

    @property
    def curr_tab(self):
        return self.ui.tabWidget_Body.rrentWidget()

    @property
    def curr_cam(self):
        return self.ui.camBox.currentText()


class CanvasWrapper:
    """     This class simply encapsulates the simulation, which resides within
        the vispy SceneCanvas object. This SceneCanvas has three main properties:
        - model :   contains and manages the properties of the model
        - view  :   contains the rendering of the simulation scene
        - vizz  :   contains the vispy visual nodes rendered in the view
    """

    def __init__(self):
        self._canvas = MainSimCanvas()

    def set_skymap_grid(self, color=(0, 0, 1, .3)):
        self._canvas.view.skymap.mesh.meshdata.color = color
        pass

    @property
    def native(self):
        return self._canvas.native

    @property
    def model(self):
        return self._canvas.model


def load_simulation():
    res = MainQtWindow()

    return res


if __name__ == "__main__":
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app = use_app("pyqt5")
    app.create()
    sim = load_simulation()
    sim.show()
    app.run()
