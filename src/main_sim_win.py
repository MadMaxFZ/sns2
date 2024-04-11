# -*- coding: utf-8 -*-

# import logging
# from typing import List
# import autologging
# import numpy as np
# from vispy.scene import SceneCanvas, visuals
# from vispy.app.timer import Timer
# from composite import Ui_frm_sns_controls

import sys
import numpy as np
import logging.config
from vispy.app import use_app
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QCoreApplication
from poliastro.bodies import Body
from astropy.units.quantity import Quantity
from decimal import Decimal
from camera_dict import CameraSet
from starsys_model import SimSystem
from sim_canvas import CanvasWrapper
from sim_controls import Controls
from starsys_visual import StarSystemVisuals
from starsys_data import log_config, SystemDataStore

logging.config.dictConfig(log_config)
QT_NATIVE = False
STOP_IT = True


def round_off(val):
    n_digits = 3
    factor = pow(10, n_digits)
    try:
        data_unit = val / val.value
        res = (int(val.value * factor) / factor) * data_unit

    except:
        res = val

    return res


def show_it(value):
    print(f'VAL: {value}, TYPE(VAL): {type(value)}')


def to_bold_font(value):
    if value:
        ante = "<html><head/><body><p><span style=\" font-weight:600;\">"
        post = "</span></p></body></html>"

        return ante + str(value) + post


def pad_plus(value):
    if value:
        res = value
        if not value.startswith('+'):
            res = "+" + value

        return res

    else:
        return ''


def to_vector_str(vec):
    if vec is not None:
        print(f'{type(vec)}')
        vec_str = str("X: " + pad_plus(f'{vec[0]:.4}') +
                      "\nY: " + pad_plus(f'{vec[1]:.4}') +
                      "\nZ: " + pad_plus(f'{vec[2]:.4}'))

        return vec_str


def to_quat_str(quat):
    if quat is not None:
        print(f'{type(quat)}')
        quat_str = str("X: " + f'{quat.x:.4}' +
                       "\nY: " + f'{quat.y:.4}' +
                       "\nZ: " + f'{quat.z:.4}' +
                       "\nW: " + f'{quat.w:.4}')

        return quat_str


class MainQtWindow(QtWidgets.QMainWindow):
    """     This module contains MainQtWindow class, the entry point into the application and
        where access to all simulation components can be utilized to provide control of the sim.
    """
    # Signals for communication between simulation components:
    main_window_ready = pyqtSignal(str)
    # newActiveBody = pyqtSignal(int)
    # newActiveTab = pyqtSignal(int)
    # newActiveCam = pyqtSignal(int)

    """     A dictionary of labels to act as keys to reference the data stored in the SimSystem model:
        The first four data elements must be computed every cycle regardless, while the remaining elements will
        only require updating if they are modified by the user at runtime. (Maybe separate the two sets?)
    """

    def __init__(self, _body_names=None, *args, **kwargs):
        super(MainQtWindow, self).__init__(*args,
                                           **kwargs)
        self.setWindowTitle("SPACE NAVIGATION SIMULATOR, (c)2024 Max S. Whitten")
        self.model = SimSystem()
        self.model.load_from_names()
        [sb.set_field_dict() for sb in self.model.data.values() if not sb.is_primary]
        self.cameras = CameraSet()
        self.canvas = CanvasWrapper(self.cameras)
        self.controls = Controls()
        self.ui = self.controls.ui
        self.central_widget = QtWidgets.QWidget()
        self._vizz_fields2agg = ('pos', 'radius', 'body_alpha', 'track_alpha', 'body_mark',
                                 'body_color', 'track_data', 'tex_data', 'is_primary',
                                 'axes', 'rot',
                                 )
        self.vizz_agg_data = self.model.get_agg_fields(self._vizz_fields2agg)
        self.visuals = StarSystemVisuals(self.model.body_names)
        self.visuals.generate_visuals(self.canvas.view,
                                      self.vizz_agg_data)
        self._setup_layout()
        self.controls.init_controls(self.model.body_names, self.cameras.cam_ids)
        # self.thread = QThread()
        # self.model.moveToThread(self.thread)
        # self.thread.start()
        self._connect_slots()
        self.main_window_ready.emit('Earth')

    def _setup_layout(self):
        # TODO:     Learn more about the QSplitter object
        main_layout = QtWidgets.QHBoxLayout()
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.controls)
        splitter.addWidget(self.canvas.native)
        main_layout.addWidget(splitter)
        self.central_widget.setLayout(main_layout)
        self.setCentralWidget(self.central_widget)

    def _connect_slots(self):
        """
            Connects slots to signals.
        """
        self.blockSignals(True)
        self.ui.bodyBox.currentIndexChanged.connect(self.ui.bodyList.setCurrentRow)
        self.ui.bodyList.currentRowChanged.connect(self.ui.bodyBox.setCurrentIndex)
        self.ui.bodyBox.currentTextChanged.connect(self.setActiveBody)
        self.ui.camBox.currentTextChanged.connect(self.setActiveCam)
        self.controls.new_active_body.connect(self.setActiveBody)
        # self.controls.new_active_camera.connect(self.newActiveCam)
        self.main_window_ready.connect(self.setActiveBody)
        self.main_window_ready.connect(self.setActiveCam)
        self.main_window_ready.connect(self.refresh_canvas)
        self.blockSignals(False)
        # self.update_panel.connect(self.send_panel_data)
        # self.model.panel_data.connect(self.controls.refresh_panel)
        print("Slots Connected...")

        # TODO:: Review the data sent versus data expected, and fix if necessary
        # self.update_panel.emit([self.ui.bodyBox.currentIndex(),
        #                         self.ui.tabWidget_Body.currentIndex(),
        #                         self.ui.camBox.currentIndex(),
        #                         ], {})
        # print("Panel data sent...")

    @pyqtSlot(str)
    def setActiveBody(self, new_body_name):
        if new_body_name in self.model.body_names:
            self.controls.set_active_body(new_body_name)

        self.refresh_panel('attr_')
        self.refresh_panel('elem_coe_')
        self.refresh_panel('elem_rv_')
        self.refresh_panel('elem_pqw_')
        self.refresh_panel('cam_')

    @pyqtSlot(int)
    def updatePanels(self, new_bod_idx):
        self.refresh_panel('elem_coe_')
        self.refresh_panel('elem_rv_')
        self.refresh_panel('elem_pqw_')
        self.refresh_panel('cam_')

    @pyqtSlot(str)
    def setActiveCam(self, new_cam_id):
        if new_cam_id in self.cameras.cam_ids:
            self.canvas.view.camera = self.cameras.set_curr2key(new_cam_id)
            self.controls.set_active_cam(new_cam_id)
            self.canvas.view.camera = self.cameras.curr_cam
        self.refresh_panel('cam_')

    @pyqtSlot(str)
    def refresh_canvas(self, body_name):
        self.visuals.update_vizz()

    def refresh_panel(self, panel_key):
        """
            This method will return the data block for the selected target given
        Parameters
        ----------
        panel_key : str

        Returns
        -------
            Has no return value, but emits the data_set via signal
        """
        widg_grp    = self.controls.widget_group(panel_key)
        show_it(widg_grp)
        curr_simbod = self.model.data[self.controls.ui.bodyBox.currentText()]
        curr_cam_id = self.controls.ui.camBox.currentText()

        match panel_key:

            case 'elem_coe_':
                if curr_simbod.is_primary:
                    for w in widg_grp:
                        w.setText('')
                else:
                    data_set = self.model.data_group(sb_name=curr_simbod.name, tgt_key=panel_key)
                    print(f'widg_grp: {len(widg_grp)}, data_set: {len(data_set)}')
                    for i, w in enumerate(widg_grp):
                        print(f'widget #{i}: {w.objectName()} -> {data_set[i]}')
                        w.setText(str(data_set[i].round(4)))

            case 'elem_rv_':
                [w.setText("") for w in widg_grp]
                self.controls.ui.elem_rv_0.setText(to_vector_str(curr_simbod.r))
                self.controls.ui.elem_rv_1.setText(to_vector_str(curr_simbod.v))

            case 'elem_pqw_':
                if curr_simbod.is_primary:
                    for w in widg_grp:
                        w.setText('')
                else:
                    data_set = self.model.data_group(sb_name=curr_simbod.name, tgt_key=panel_key)
                    print(f'widg_grp: {len(widg_grp)}, data_set: {len(data_set)}')
                    for i, w in enumerate(widg_grp):
                        print(f'widget #{i}: {w.objectName()} -> {data_set[i]}')
                        w.setText(str(to_vector_str(data_set[i].value)))

            case 'attr_':
                data_set = curr_simbod.body
                print(f'{data_set}')
                print(f'panel_key: {panel_key}, widg_grp: {len(widg_grp)}, data_set: {len(data_set)}')
                for i, data in enumerate(data_set):
                    if type(data) == Body:
                        res = data.name
                    elif type(data) == Quantity:
                        res = f'{data:.4e}'
                    elif type(data) == str:
                        res = f'{data}'
                    else:
                        res = data

                    print(f'widget #{i}: {widg_grp[i].objectName()} -> {str(res)}')
                    widg_grp[i].setText(str(res))

            case 'cam_':
                # TODO: output the get_state() dict, whatever it is, in (key, value) pairs of labels.
                i = 0
                cam_state = self.cameras.curr_cam.get_state()
                key_widgs = self.controls.widget_group('key_')
                [print(f'{k} has type {type(v)} with value {v}') for k, v in cam_state.items()]
                for k, v in cam_state.items():
                    key_widgs[i].setText(str(k))
                    match str(type(v)):

                        case "<class \'float\'>":
                            res = f'{v:.4}'

                        case "<class \'tuple\'>":
                            res = to_vector_str(v)

                        case "<class \'vispy.util.quaternion.Quaternion\'>":
                            res = to_quat_str(v)

                        case _:
                            res = ''

                    widg_grp[i].setText(res)
                    i += 1

        pass
        # self.update_panel.emit(model_agg_data)

    @property
    def curr_body_name(self):
        return self.ui.bodyBox.currentText()


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
