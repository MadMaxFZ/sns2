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
from multiprocessing import Pipe, Process
from asyncio import Queue
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QCoreApplication
from vispy.scene import SceneCanvas, visuals
from vispy.app import use_app
from sim_canvas import MainSimCanvas
from starsys_model import StarSystemModel
from sns2_gui import Ui_wid_BodyData
from composite import Ui_frm_sns_controls
from starsys_data import log_config

logging.config.dictConfig(log_config)


class ModelProc(Process):
    def __init__(self, to_emitter: Pipe, from_model, daemon=True):
        self.model = super(ModelProc, self).__init__()
        self.daemon = daemon
        self.to_emitter = to_emitter
        self.data_from_model = from_model

    def run(self):
        while True:
            req = self.data_from_model.get()
            self.to_emitter.send(req)


class MainQtWindow(QtWidgets.QMainWindow):
    data_request = pyqtSignal(list)

    def __init__(self, ctr=None, ssm=None, msc=None,
                 req=None, emt=None,
                 *args, **kwargs
                 ):
        super(MainQtWindow, self).__init__(*args, **kwargs)
        self.setWindowTitle("SPACE NAVIGATION SIMULATOR, (c)2024 Max S. Whitten")
        self.controls = ctr
        self.model    = ssm
        self.canvas   = msc

        self.ui = self.controls.ui
        main_layout = QtWidgets.QHBoxLayout()
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.controls)
        splitter.addWidget(self.canvas.native)
        main_layout.addWidget(splitter)
        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.proc_q = req
        self.emitter = emt
        self.emitter.daemon = True
        self.emitter.start()
        self.connect_controls()
        self.init_controls()

    @pyqtSlot(list)
    def to_model(self, target):
        self.proc_q.put(target)

    @pyqtSlot(list, list)
    def updateUI(self, target, data):
        """ This slot method accepts a list

        Parameters
        ----------
        target  :   a list indicating the widget set affected (same as list in data_request signal)
        data    :   a list of the data to be placed into the indicated target widgets

        Returns
        -------

        """

    def init_controls(self):
        self.ui.bodyList.clear()
        self.ui.bodyList.addItems(self.model.simbodies.keys())
        self.ui.bodyBox.addItems(self.model.simbodies.keys())
        # add items to camera combobox
        self.ui.tabWidget_Body.setCurrentIndex(0)
        self.ui.bodyBox.setCurrentIndex(0)
        self.data_request.emit([self.controls.active_body,
                                self.controls.active_panel,
                                self.controls.active_cam,
                                ])
        pass

    def connect_controls(self):
        # TODO:: From here the scope should allow access sufficient to define all
        #       slots necessary to communicate with model thread
        self.ui.bodyBox.currentIndexChanged.connect(self.ui.bodyList.setCurrentRow)
        self.ui.bodyList.currentRowChanged.connect(self.ui.bodyBox.setCurrentIndex)
        self.data_request.connect(self.to_model)
        self.emitter.data_return.connect(self.updateUI)


class Controls(QtWidgets.QWidget):
    data_request = pyqtSignal(list)

    def __init__(self, parent=None):
        super(Controls, self).__init__(parent)

        self.ui = Ui_frm_sns_controls()
        self.ui.setupUi(self)
        self.ui_obj_dict = self.ui.__dict__
        logging.info([i for i in self.ui_obj_dict.keys() if (i.startswith("lv") or "warp" in i)])
        self._wgtgrp_names = ['attr_', 'elem_', 'elem_coe_', 'elem_pqw_', 'elem_rv_',
                              'cam_', 'tw_', 'twb_', 'axis_']
        self._control_groups = self._scanUi_4panels(patterns=self._wgtgrp_names)
        self.tab_names = ['tab_TIME', 'tab_ATTR', 'tab_ELEM', 'tab_CAMS']

        # create some hooks to notable widget values...
        self.active_body = self.ui.bodyBox.currentText()
        self.active_cam = self.ui.camBox.currentText()
        self.active_panel = self.tab_names[self.ui.tabWidget_Body.currentIndex()]
        pass

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
                self._control_groups['attr_'].values()[i].setCurrentText(data_set[i])

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
        return self.ui.tabWidget_Body.currentWidget()

    @property
    def curr_cam(self):
        return self.ui.camBox.currentText()


class Emitter(QThread):
    data_return = pyqtSignal(list, list)

    def __init__(self, from_model: Pipe):
        super(Emitter, self).__init__()
        self.data_from_model = from_model

    def run(self):
        while True:
            try:
                mod_data = self.data_from_model.recv()
            except EOFError:
                break
            else:
                self.data_return.emit(mod_data)


if __name__ == "__main__":
    # app = QCoreApplication(sys.argv)
    # app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app = use_app("pyqt5")
    app.create()

    in_pipe, out_pipe = Pipe()
    request_q = Queue()
    emitter = Emitter(in_pipe)

    ctrl = Controls()
    modl = ModelProc(out_pipe, request_q, daemon=True)
    model = modl.model
    canv = MainSimCanvas(system_model=model)
    simu = MainQtWindow(ctr=ctrl, ssm=model, msc=canv, req=request_q, emt=emitter)
    modl.start()
    simu.show()
    app.run()
    # app.exec_()

