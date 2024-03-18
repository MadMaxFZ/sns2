# -*- coding: utf-8 -*-

"""
    This module contains classes to allow using Qt to control Vispy
"""

import logging
import logging.config
from typing import List

import sys
import autologging
import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QCoreApplication
from vispy.scene import SceneCanvas, visuals
from vispy.app import use_app
from vispy.app.timer import Timer
from camera_set import CameraSet
from sim_canvas import MainSimCanvas
from src.system_model import SimSystem
from starsys_visual import StarSystemVisuals
from composite import Ui_frm_sns_controls
from starsys_data import log_config

logging.config.dictConfig(log_config)

QT_NATIVE = False


class Controls(QtWidgets.QWidget):
    data_request = pyqtSignal(list)

    def __init__(self, parent=None):
        super(Controls, self).__init__(parent)

        self.ui = Ui_frm_sns_controls()
        self.ui.setupUi(self)
        self.ui_obj_dict = self.ui.__dict__
        logging.info([i for i in self.ui.__dict__.keys() if (i.startswith("lv") or "warp" in i)])
        self._group_names = ['attr_', 'elem_', 'elem_coe_', 'elem_pqw_', 'elem_rv_',
                             'cam_', 'tw_', 'twb_', 'axis_']
        self._widget_groups = self._scanUi_4panels(patterns=self._group_names)
        self.tab_names = ['tab_TIME', 'tab_ATTR', 'tab_ELEM', 'tab_CAMS']
        pass

    @property
    def active_body(self):
        return self.ui.bodyBox.currentText()

    @property
    def active_cam(self):
        return self.ui.camBox.currentText()

    @property
    def active_panel(self):
        return self.tab_names[self.ui.tabWidget_Body.currentIndex()]

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
                               self.ui_obj_dict.items() if name.startswith(p)]})

        return panels

    @pyqtSlot(list, list)
    def refresh(self, target, data_set):
        if target[1] == "tab_ATTR":
            for i in range(len(data_set)):
                self._widget_groups['attr_'].values()[i].setCurrentText(data_set[i])

        pass

    @property
    def panels(self, name=None):
        if name is None:
            return self._widget_groups
        elif name in self._widget_groups.keys():
            return self._widget_groups[name]
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
        return self.ui.tabWidget_Body.currentWidget()

    @property
    def curr_cam(self):
        return self.ui.camBox.currentText()


class MainQtWindow(QtWidgets.QMainWindow):
    update_panel = pyqtSignal(list)
    newActiveBody = pyqtSignal(int)
    newActiveTab = pyqtSignal(int)
    newActiveCam = pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        super(MainQtWindow, self).__init__(*args,
                                           **kwargs)
        self.setWindowTitle("SPACE NAVIGATION SIMULATOR, (c)2024 Max S. Whitten")
        self.cameras  = CameraSet()
        self.model    = SimSystem()
        self.model.current_cam = self.cameras.curr_cam
        self.canvas   = CanvasWrapper()
        self.canvas.assign_camera(self.cameras.curr_cam)
        self.visuals  = StarSystemVisuals()
        self.visuals.generate_visuals(self.canvas.view, agg_data=self.model.agg_fields)
        self.controls = Controls()
        self.ui = self.controls.ui

        main_layout = QtWidgets.QHBoxLayout()
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.controls)
        splitter.addWidget(self.canvas.native)
        main_layout.addWidget(splitter)
        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.connect_controls()
        # self.thread = QThread()
        # self.model.moveToThread(self.thread)
        # self.thread.start()
        self.init_controls()

    def init_controls(self):
        self.ui.bodyList.clear()
        item_names = [self.model.data[n].name for n in range(len(self.model.data))]
        self.ui.bodyList.addItems(item_names)
        self.ui.bodyBox.addItems(item_names)
        # add items to camera combobox
        self.ui.tabWidget_Body.setCurrentIndex(0)
        self.ui.bodyBox.setCurrentIndex(0)
        self.ui.camBox.setCurrentIndex(0)
        self.update_panel.emit([self.controls.active_body,
                                self.controls.active_panel,
                                self.controls.active_cam,
                                ])
        pass

    def connect_controls(self):
        # TODO:: From here the scope should allow access sufficient to define all
        #       slots necessary to communicate with model thread
        self.ui.bodyBox.currentIndexChanged.connect(self.ui.bodyList.setCurrentRow)
        self.ui.bodyList.currentRowChanged.connect(self.ui.bodyBox.setCurrentIndex)
        self.ui.bodyBox.currentIndexChanged.connect(self.newActiveBody)
        self.ui.tabWidget_Body.currentChanged.connect(self.newActiveTab)
        self.ui.camBox.currentIndexChanged.connect(self.newActiveCam)
        self.update_panel.connect(self.model.send_panel)
        self.model.data_return.connect(self.controls.refresh)


class CanvasWrapper:
    """     This class simply encapsulates the simulation, which resides within
        the vispy SceneCanvas object.
    """
    #   TODO:: Be prepared to add some methods to this class
    def __init__(self):
        self._canvas = MainSimCanvas()
        self._scene = self._canvas.view.scene
        self._view = self._canvas.view

    def assign_camera(self, camera):
        self._canvas.view.camera = camera

    @property
    def native(self):
        return self._canvas.native

    @property
    def scene(self):
        return self._scene


if __name__ == "__main__":
    if QT_NATIVE:
        app = QCoreApplication(sys.argv)
        app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    else:
        app = use_app("pyqt5")
        app.create()

    sim = MainQtWindow()
    sim.show()

    if QT_NATIVE:
        sys.exit(app.exec_())
    else:
        app.run()
