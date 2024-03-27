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
STOP_IT = True


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

        # Here we define sets of keys that will correspond to data fields in the model, visuals and cameras.
        # The first two are fields that exist for each SimBody (exceptr primary)
        self._model_fields2agg = ('rad', 'pos', 'rot')
        self._color_fields2agg = ('body_alpha', 'track_alpha', 'body_mark',
                                  'body_color', 'track_data', 'rel2cam')
        # This key set refers to fields that are common to the cameras (only FlyCameras right now)
        self._cams_fields2agg = ('center', 'rot1', 'rot2', 'scale', 'fov', 'zoom')

        self.body_agg_data = self._get_model_agg_fields(self._model_fields2agg)                     ###
        self.visuals = StarSystemVisuals(self.sys_data.body_names, _body_names)
        self.visuals.generate_visuals(self.canvas.view, agg_data=self.body_agg_data)
        self.body_agg_data.update(self._get_vizz_agg_fields(self._color_fields2agg))                ###
        # self.cam_agg_data = self._get_cam_agg_fields(self._cams_fields2agg)

        self._setup_layout()
        self.init_controls()
        # self.thread = QThread()
        # self.model.moveToThread(self.thread)
        # self.thread.start()
        self.blockSignals(True)
        self.connect_slots()
        self.blockSignals(False)

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
        """
            Connects slots to signals.
        """
        self.ui.bodyBox.currentIndexChanged.connect(self.ui.bodyList.setCurrentRow)
        self.ui.bodyList.currentRowChanged.connect(self.ui.bodyBox.setCurrentIndex)
        self.ui.bodyBox.currentIndexChanged.connect(self.newActiveBody)
        self.ui.tabWidget_Body.currentChanged.connect(self.newActiveTab)
        self.ui.camBox.currentIndexChanged.connect(self.newActiveCam)
        # self.update_panel.connect(self.send_panel_data)
        self.model.panel_data.connect(self.controls.refresh_panel)
        print("Slots Connected...")

        # TODO:: Review the data sent versus data expected, and fix if necessary
        # self.update_panel.emit([self.ui.bodyBox.currentIndex(),
        #                         self.ui.tabWidget_Body.currentIndex(),
        #                         self.ui.camBox.currentIndex(),
        #                         ], {})
        # print("Panel data sent...")
    def newActiveBody(self, idx):
        self.refresh_panel_data('attr_')

    def refresh_panel_data(self, target):
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
        model_agg_data = {}
        body_idx = target[0]
        panel_key = target[1]
        match panel_key:
            case "cam_":
                pass

            case "attr_":
                body_obj: Body = self.data[body_idx].body
                for i in range(len(body_obj._fields())):
                    model_agg_data.update({panel_key + str(i): body_obj[i]})

            case "elem_":
                model_agg_data = self._get_model_agg_fields()

        self.update_panel.emit(model_agg_data)
        pass

    def _get_model_agg_fields(self, field_ids):
        res = {'primary_name': self.model.system_primary.name}
        for f_id in field_ids:
            agg = {}
            [agg.update({sb.name: self._get_sbod_field(sb, f_id)})
             for sb in self.model.data.values()]
            res.update({f_id: agg})

        return res

    def _get_vizz_agg_fields(self, field_ids):
        res = {}
        for f_id in field_ids:
            agg = {}
            [agg.update({pl.name: self._get_vizz_field(pl, f_id)})
             for pl in self.visuals.planets]
            res.update({f_id: agg})

        return res

    def _get_cam_agg_fields(self, field_ids):
        res = {}
        for f_id in field_ids:
            agg = {}
            [agg.update({"def_cam": self._get_cams_field(cam, f_id)})
             for cam in self.cameras.cam_list]
            res.update({f_id: agg})

        return res

    def _get_sbod_field(self, _simbod, field_id):
        """
            This method is used to get the values of a particular field for a given SimBody object.
        Parameters
        ----------
        _simbod             : SimBody            The SimBody object for which the field value is to be retrieved.
        field_id            : str                The field for which the value is to be retrieved.

        Returns
        -------
        simbod.<field_id>   : float or list       The value of the field for the given SimBody object.
        """
        match field_id:
            case 'rad':
                return _simbod.radius[0]

            case 'pos':
                return _simbod.pos

            case 'rot':
                return _simbod.rot

            case 'track':
                return _simbod.track

            case 'axes':
                return _simbod.axes

            case 'track_data':
                return _simbod.track

    def _get_vizz_field(self, _planet, field_id):
        match field_id:
            case 'body_alpha':
                return _planet[self._color_fields2agg[0]]

            case 'track_alpha':
                return _planet[self._color_fields2agg[1]]

            case 'body_mark':
                return _planet[self._color_fields2agg[2]]

            case 'body_color':
                return _planet[self._color_fields2agg[3]]

    def _get_cams_field(self, _camera, field_id):
        _idx = 0
        match field_id:
            case 'center':
                _state = self.cameras.cam_states(self.cameras._cam_dict[_idx](self.ui.camBox.currentIndex()))

                res = {}
                for _idx, _widget in enumerate(self.controls.panel_widgets['cam_']):
                    res.update({_idx: [_widget, _state[_idx]]})

                return res

            case 'rot1':
                pass

            case 'rot2':
                pass

            case 'zoom':
                pass

            case 'fov':
                pass

            case 'scale':
                pass


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
