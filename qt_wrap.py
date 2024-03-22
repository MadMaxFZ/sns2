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
from poliastro.bodies import Body
from vispy.scene import SceneCanvas, visuals
from vispy.app import use_app
from vispy.app.timer import Timer
from camera_set import CameraSet
from sim_canvas import MainSimCanvas
from src.system_model import SimSystem
from starsys_visual import StarSystemVisuals
from composite import Ui_frm_sns_controls
from starsys_data import log_config, SystemDataStore

logging.config.dictConfig(log_config)

QT_NATIVE = False


class MainQtWindow(QtWidgets.QMainWindow):
    update_panel = pyqtSignal(list, dict)
    newActiveBody = pyqtSignal(int)
    newActiveTab = pyqtSignal(int)
    newActiveCam = pyqtSignal(int)
    fields2agg = ('rad', 'rel2cam', 'pos', 'rot', 'b_alpha', 't_alpha', 'symb', 'color', 'track',)

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

        self._agg_data = self._load_agg_fields(self.fields2agg)
        self.visuals = StarSystemVisuals(self.sys_data.body_names, _body_names)
        self.visuals.generate_visuals(self.canvas.view, agg_data=self._agg_data)
        self._setup_layout()
        self.connect_controls()
        # self.thread = QThread()
        # self.model.moveToThread(self.thread)
        # self.thread.start()
        self.init_controls()

    def _setup_layout(self):
        main_layout = QtWidgets.QHBoxLayout()
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.controls)
        splitter.addWidget(self.canvas.native)
        main_layout.addWidget(splitter)
        self.central_widget.setLayout(main_layout)
        self.setCentralWidget(self.central_widget)
        self._agg_data = self._load_agg_fields(self.fields2agg)

    def connect_controls(self):
        # TODO:: From here the scope should allow access sufficient to define all
        #       slots necessary to communicate with model thread
        self.ui.bodyBox.currentIndexChanged.connect(self.ui.bodyList.setCurrentRow)
        self.ui.bodyList.currentRowChanged.connect(self.ui.bodyBox.setCurrentIndex)
        self.ui.bodyBox.currentIndexChanged.connect(self.newActiveBody)
        self.ui.tabWidget_Body.currentChanged.connect(self.newActiveTab)
        self.ui.camBox.currentIndexChanged.connect(self.newActiveCam)
        self.update_panel.connect(self.send_panel_data)
        self.model.panel_data.connect(self.controls.refresh_panel)

    def init_controls(self):
        self.ui.bodyList.clear()
        self.ui.bodyBox.clear()
        self.ui.bodyList.addItems(self.model.body_names)
        self.ui.bodyBox.addItems(self.model.body_names)
        self.ui.camBox.addItems(self.cameras.cam_ids)
        self.ui.bodyBox.setCurrentIndex(0)
        self.ui.tabWidget_Body.setCurrentIndex(0)
        self.ui.camBox.setCurrentIndex(0)

        # TODO:: Review the data sent versus data expected, and fix if necessary
        self.update_panel.emit([self.controls.active_body,
                                self.controls.active_panel,
                                self.controls.active_cam,
                                ])
        print("Controls initialized...")

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


class Controls(QtWidgets.QWidget):
    data_request = pyqtSignal(list)

    def __init__(self, parent=None):
        super(Controls, self).__init__(parent)

        self.ui = Ui_frm_sns_controls()
        self.ui.setupUi(self)
        self.ui_obj_dict = self.ui.__dict__
        logging.info([i for i in self.ui.__dict__.keys() if (i.startswith("lv") or "warp" in i)])
        self._grp_names = ['attr_', 'elem_', 'elem_coe_', 'elem_pqw_', 'elem_rv_',
                             'cam_', 'tw_', 'twb_', 'axis_']
        self._tab_names = ['tab_TIME', 'tab_ATTR', 'tab_ELEM', 'tab_CAMS']
        self._widget_groups = self._scanUi_4panels(patterns=self._grp_names)
        print(f'{len(self._widget_groups)} groups defined...')

    @property
    def active_body(self):
        return self.ui.bodyBox.currentIndex()

    @property
    def active_cam(self):
        return self.ui.camBox.currentIndex()

    @property
    def active_panel(self):
        return self._tab_names[self.ui.tabWidget_Body.currentIndex()]

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
    def refresh_panel(self, target, data_set):
        if target[1] == "tab_ATTR":
            for i in range(len(data_set)):
                self._widget_groups['attr_'].values()[i].setCurrentText(data_set[i])

        pass

    @property
    def panel_widgets(self, name=None):
        if name is None:
            return self._widget_groups
        elif name in self._widget_groups.keys():
            return self._widget_groups[name]
        else:
            return None


class CanvasWrapper:
    """     This class simply encapsulates the simulation, which resides within
        the vispy SceneCanvas object.
    """
    #   TODO:: Be prepared to add some methods to this class
    def __init__(self, _camera_set):
        self._canvas = MainSimCanvas(camera_set=_camera_set)
        self._scene = self._canvas.view.scene
        self._view = self._canvas.view

    @property
    def native(self):
        return self._canvas.native

    @property
    def view(self):
        return self._canvas.view

    @property
    def scene(self):
        return self._scene


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
