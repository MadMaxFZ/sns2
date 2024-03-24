# -*- coding: utf-8 -*-

# import logging
# from typing import List
# import autologging
# import numpy as np
# from vispy.scene import SceneCanvas, visuals
# from vispy.app.timer import Timer
# from composite import Ui_frm_sns_controls

import sys
import logging.config
from vispy.app import use_app
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QCoreApplication
from poliastro.bodies import Body

from camera_set import CameraSet
from src.system_model import SimSystem
from sim_canvas import CanvasWrapper
from controls import Controls
from starsys_visual import StarSystemVisuals
from starsys_data import log_config, SystemDataStore

logging.config.dictConfig(log_config)
QT_NATIVE = False


class MainQtWindow(QtWidgets.QMainWindow):
    """     This module contains MainQtWindow class, the entry point into the application and
        where access to all simulation components can be utilized to provide control of the sim.
    """
    # Signals for communication between simulation components:
    update_panel = pyqtSignal(list, dict)
    newActiveBody = pyqtSignal(int)
    newActiveTab = pyqtSignal(int)
    newActiveCam = pyqtSignal(int)

    """     A dictionary of labels to act as keys to reference the data stored in the SimSystem model:
        The first four data elements must be computed every cycle regardless, while the remaining elements will
        only require updating if they are modified by the user at runtime. (Maybe separate the two sets?)
    """
    model_fields2agg = ('rad', 'rel2cam', 'pos', 'rot',)
    color_fields2agg = ('b_alpha', 't_alpha', 'symb', 'color', 'track',)

    def __init__(self, _body_names=None, *args, **kwargs):
        super(MainQtWindow, self).__init__(*args,
                                           **kwargs)
        self.setWindowTitle("SPACE NAVIGATION SIMULATOR, (c)2024 Max S. Whitten")
        self.sys_data = SystemDataStore()
        self.model    = SimSystem(self.sys_data)
        self.cameras  = CameraSet()
        self.canvas   = CanvasWrapper(self.cameras)
        self.controls = Controls()
        self.ui = self.controls.ui
        self.central_widget = QtWidgets.QWidget()

        self._agg_data = self._load_agg_fields(self.model_fields2agg)
        self.visuals = StarSystemVisuals(self.sys_data.body_names, _body_names)
        self.visuals.generate_visuals(self.canvas.view, agg_data=self._agg_data)
        self._setup_layout()
        self.init_controls()
        # self.thread = QThread()
        # self.model.moveToThread(self.thread)
        # self.thread.start()
        self.connect_slots()

    def _setup_layout(self):
        main_layout = QtWidgets.QHBoxLayout()
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.controls)
        splitter.addWidget(self.canvas.native)
        main_layout.addWidget(splitter)
        self.central_widget.setLayout(main_layout)
        self.setCentralWidget(self.central_widget)

    def init_controls(self):
        self.ui.bodyList.clear()
        self.ui.bodyBox.clear()
        self.ui.bodyList.addItems(self.model.body_names)
        self.ui.bodyBox.addItems(self.model.body_names)
        self.ui.camBox.addItems(self.cameras.cam_ids)
        self.ui.bodyBox.setCurrentIndex(0)
        self.ui.tabWidget_Body.setCurrentIndex(0)
        self.ui.camBox.setCurrentIndex(0)
        print("Controls initialized...")

    def connect_slots(self):
        # TODO:: From here the scope should allow access sufficient to define all
        #       slots necessary to communicate with model thread
        self.ui.bodyBox.currentIndexChanged.connect(self.ui.bodyList.setCurrentRow)
        self.ui.bodyList.currentRowChanged.connect(self.ui.bodyBox.setCurrentIndex)
        self.ui.bodyBox.currentIndexChanged.connect(self.newActiveBody)
        self.ui.tabWidget_Body.currentChanged.connect(self.newActiveTab)
        self.ui.camBox.currentIndexChanged.connect(self.newActiveCam)
        # self.update_panel.connect(self.send_panel_data)
        self.model.panel_data.connect(self.controls.refresh_panel)

        # TODO:: Review the data sent versus data expected, and fix if necessary
        self.update_panel.emit([self.controls.active_body,
                                self.controls.active_panel,
                                self.controls.active_cam,
                                ], {})

    # TODO::    Incorporate the following methods into the MainQtWindow class
    def send_panel_data(self, target):
        """
            This method will return the data block for the selected target given
        Parameters
        ----------
        target

        Returns
        -------
            Has no return value, but emits the data_set via signal
        """
        #
        data_set = [0, 0]
        body_idx = target[0]
        panel_key = target[1]
        if panel_key == "CAMS":
            pass
        elif panel_key == "tab_ATTR":
            body_obj: Body = self.data[body_idx].body
            data_set = []
            for i in range(len(body_obj._fields())):
                data_set.append(body_obj[i])

        self.update_panel.emit(target, data_set)
        pass

    def _load_agg_fields(self, field_ids):
        res = {'primary_name': self.model.system_primary.name}
        for f_id in field_ids:
            agg = {}
            [agg.update({sb.name: self._get_field(sb, f_id)}) for sb in self.model.data]
            res.update({f_id: agg})

        return res

    def _get_field(self, simbod, field_id):
        """
            This method is used to get the values of a particular field for a given SimBody object.
        Parameters
        ----------
        simbod      : SimBody            The SimBody object for which the field value is to be retrieved.
        field_id    : str                The field for which the value is to be retrieved.

        Returns
        -------
        res     : float or list       The value of the field for the given SimBody object.
        """
        match field_id:
            case 'rad':
                return simbod.radius[0]
            # case 'rel2cam':
            #     return self.rel2cam(simbod)
            case 'pos':
                return simbod.pos
            case 'rot':
                return simbod.rot
            case 'track':
                return simbod.track
            case 'axes':
                return simbod.axes
            case 'b_alpha':
                return self.sys_data.vizz_data(simbod.name)['body_alpha']
            case 't_alpha':
                return self.sys_data.vizz_data(simbod.name)['track_alpha']
            case 'symb':
                return self.sys_data.vizz_data(simbod.name)['body_mark']
            case 'color':
                return self.sys_data.vizz_data(simbod.name)['body_color']


'''==============================================================================================================='''
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
