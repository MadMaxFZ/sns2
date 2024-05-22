# -*- coding: utf-8 -*-

import cProfile
import logging.config
import psygnal
from vispy.app import use_app
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication
from starsys_model import SimSystem
from sim_canvas import CanvasWrapper
from sim_controls import Controls
from starsys_visual import StarSystemVisuals
from starsys_data import *

logging.config.dictConfig(log_config)
QT_NATIVE = False
STOP_IT = True
DO_PROFILE = False


class MainQtWindow(QtWidgets.QMainWindow):
    """     This module contains MainQtWindow class, the entry point into the application and
        where access to all simulation components can be utilized to provide control of the sim.
    """
    # Signals for communication between simulation components:
    main_window_ready = pyqtSignal(str)
    panel_refreshed = pyqtSignal(str)
    on_draw_sig    = psygnal.Signal(str)
    vispy_keypress = psygnal.Signal(str)

    """     A dictionary of labels to act as keys to reference the data stored in the SimSystem model:
        The first four data elements must be computed every cycle regardless, while the remaining elements will
        only require updating if they are modified by the user at runtime. (Maybe separate the two sets?)
    """

    def __init__(self, _body_names=None, *args, **kwargs):
        """
            Here we initialize the primary QMainWindow that will interface to the Simulation.

        Parameters
        ----------
        _body_names :
        args        :
        kwargs      :
        """
        super(MainQtWindow, self).__init__(*args, **kwargs)
        self.setWindowTitle("SPACE NAVIGATION SIMULATOR, (c)2024 Max S. Whitten")
        self.timer_paused = True
        self.interval = 10
        self.tw_hold = 0
        self.model = SimSystem()
        self.model.load_from_names()
        self.body_names = self.model.body_names

        #       TODO:   Encapsulate the creation of the CameraSet instance inside the
        #               CanvasWrapper class, which will expose methods to manipulate the cameras.
        #       CONSIDER:   Encapsulating the CanvasWrapper instance inside the
        #                   StarSystemVisuals class, which would assume the role of CanvasWrapper
        self.canvas = CanvasWrapper(self.on_draw_sig, self.vispy_keypress)
        self.cameras = self.canvas.cam_set
        self.controls = Controls()
        self.ui = self.controls.ui
        self.central_widget = QtWidgets.QWidget(self)
        self.timer = QtCore.QTimer()
        self.timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)

        #       TODO:   Encapsulate the vizz_fields2agg inside StartSystemVisuals class
        self._vizz_fields2agg = ('pos', 'radius', 'body_alpha', 'track_alpha', 'body_mark',
                                 'body_color', 'track_data', 'tex_data', 'is_primary',
                                 'axes', 'rot', 'parent_name'
                                 )
        self.visuals = StarSystemVisuals(self.body_names)
        self.visuals.generate_visuals(self.canvas.view,
                                      self.model.get_agg_fields(self._vizz_fields2agg))

        self._setup_layout()
        self.controls.init_controls(self.body_names, self.cameras.cam_ids)
        # self.thread = QThread()
        # self.model.moveToThread(self.thread)
        # self.thread.start()
        self._connect_slots()
        self.cameras.curr_cam.set_range(self.visuals.vizz_bounds,
                                        self.visuals.vizz_bounds,
                                        self.visuals.vizz_bounds,)
        # set the initial camera position in the ecliptic looking towards the primary
        self.cameras.curr_cam.set_state(DEF_CAM_STATE)
        self.curr_simbod = self.model['Earth']
        self.reset_rotation()
        self.main_window_ready.emit('Earth')
        self._last_elapsed = 0.0

    def _key_handler(self, key_chr):
        match key_chr:

            case "[":
                # lower time warp
                pass

            case "]":
                # increase time warp
                pass

            case "[":
                pass

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
        # Handling signals when GUI created
        self.main_window_ready.connect(self.setActiveBody)
        self.main_window_ready.connect(self.setActiveCam)
        self.main_window_ready.connect(self.refresh_canvas)
        self.canvas.key_sig.connect(self._key_handler)

        # Handling changes in the GUI
        self.ui.bodyBox.currentIndexChanged.connect(self.ui.bodyList.setCurrentRow)
        self.ui.bodyList.currentRowChanged.connect(self.ui.bodyBox.setCurrentIndex)
        self.ui.bodyBox.currentTextChanged.connect(self.setActiveBody)
        self.ui.camBox.currentTextChanged.connect(self.setActiveCam)

        #   Handling epoch timer widget signals
        self.ui.time_wexp.valueChanged.connect(self.controls.tw_exp_updated)
        self.ui.time_slider.valueChanged.connect(self.controls.tw_slider_updated)
        self.ui.time_elapsed.textChanged.connect(self.controls.tw_elapsed_updated)
        self.ui.time_sys_epoch.textChanged.connect(self.update_model_epoch)
        self.ui.time_sys_epoch.textChanged.connect(self.updatePanels)
        # self.model.has_updated.connect(self.canvas.update_canvas)
        self.model.has_updated.connect(self.refresh_canvas)

        self.timer.setInterval(self.interval)
        self.timer.timeout.connect(self.update_elapsed)

        # Handling buttons in epoch timer
        self.ui.btn_play_pause.pressed.connect(self.toggle_play_pause)
        self.ui.btn_real_twarp.pressed.connect(self.controls.toggle_twarp2norm)
        self.ui.btn_reverse.pressed.connect(self.controls.toggle_twarp_sign)
        self.ui.btn_stop_reset.pressed.connect(self.controls.reset_epoch_timer)
        self.ui.btn_set_rot.pressed.connect(self.reset_rotation)
        self.blockSignals(False)
        print("Signals / Slots Connected...")

    def reset_rotation(self):
        self.cameras.curr_cam.set_default_state()
        self.cameras.curr_cam.reset()
        self.updatePanels('')

    def update_elapsed(self):
        self.ui.time_elapsed.setText(f'{(float(self.ui.time_elapsed.text()) + self.interval / 86400):.4f}')

    @property
    def curr_body_name(self):
        return self.ui.bodyBox.currentText()

    @pyqtSlot(str)
    def setActiveBody(self, new_body_name):
        if new_body_name in self.model.body_names:
            self.controls.set_active_body(new_body_name)
            self.curr_simbod = self.model[new_body_name]
            if self.ui.cam2selected.isChecked():
                if self.ui.camBox.currentText() == "tt_cam":
                    self.cameras.curr_cam.set_state({'distance':
                                                     self.curr_simbod.radius[0].to(self.curr_simbod.dist_unit).value * 2})

        self.refresh_panel('attr_')
        # self.updatePanels('')

    @pyqtSlot(str)
    def updatePanels(self, new_bod_idx):
        self.refresh_panel('elem_coe_')
        self.refresh_panel('elem_rv_')
        self.refresh_panel('elem_pqw_')
        self.refresh_panel('cam_')

    @pyqtSlot(str)
    def setActiveCam(self, new_cam_id):
        if new_cam_id in self.cameras.cam_ids:
            self.canvas.view.camera = self.cameras.set_curr2key(new_cam_id)
            self.canvas.view.camera = self.cameras.curr_cam

        # self.refresh_panel('cam_')

    @pyqtSlot()
    def refresh_canvas(self):
        self.visuals.update_vizz(self.model.get_agg_fields(self._vizz_fields2agg))
        self.canvas.update_canvas()
        # self.updatePanels('')

    @pyqtSlot()
    def update_model_epoch(self):
        self.model.epoch = Time(self.ui.time_sys_epoch.text(), format='jd')
        if not self.model.USE_AUTO_UPDATE_STATE:
            self.model.update_state(self.model.epoch)

    @pyqtSlot()
    def toggle_play_pause(self):
        if self.timer_paused:
            self.ui.time_warp.setText(f'{self.tw_hold}')
            self.timer_paused = False
            self.timer.start()
            # self.ui.time_elapsed.setText(f'{(float(self.ui.time_elapsed.text()) + DEFAULT_DT):.4f}')
        else:
            self.tw_hold = float(self.ui.time_warp.text())
            self.timer_paused = True
            self.timer.stop()

    @pyqtSlot(str)
    def refresh_panel(self, panel_key):
        """
            This method will return the data block for the selected target given
        Parameters
        ----------
        panel_key : str     A tag to serve as a key to indicate which panels(s) to update

        Returns
        -------
            Has no return value, but emits the panel_key via the signal
        """
        widg_grp    = self.controls.widget_group(panel_key)
        # show_it(widg_grp)
        curr_cam_id = self.ui.camBox.currentText()
        if self.ui.cam2selected.isChecked():
            self.cameras.curr_cam.set_state({'center': tuple(self.curr_simbod.pos.value)})

        match panel_key:

            case 'elem_coe_':
                # print("COE!!")
                if self.curr_simbod.is_primary:
                    for w in widg_grp:
                        w.setText('')
                else:
                    for i, w in enumerate(widg_grp):
                        # print(f'widget #{i}: {w.objectName()} -> {data_set[i]}')
                        w.setText(str(self.model[self.curr_simbod.name].elem_coe[i].round(4)))

            case 'elem_rv_':
                # print("RV!!")
                if self.curr_simbod.is_primary:
                    [w.setText("") for w in widg_grp]
                else:
                    self.ui.elem_rv_0.setText(to_vector_str(self.curr_simbod.r.value))
                    self.ui.elem_rv_1.setText(to_vector_str(self.curr_simbod.v.value))
                    self.ui.elem_rv_3.setText(to_vector_str(self.curr_simbod.rot,
                                                      ('RA: ', '\nDEC:', '\nW:  '))
                                              )

            case 'elem_pqw_':
                # print("PQW!!")
                if self.curr_simbod.is_primary:
                    for w in widg_grp:
                        w.setText('')
                else:
                    for i, w in enumerate(widg_grp):
                        # print(f'widget #{i}: {w.objectName()} -> {data_set[i]}')
                        w.setText(str(to_vector_str(self.model[self.curr_simbod.name].elem_pqw[i])))

            case 'attr_':
                # print("ATTR!!")
                data_set = self.curr_simbod.body
                # print(f'{data_set}')
                # print(f'panel_key: {panel_key}, widg_grp: {len(widg_grp)}, data_set: {len(data_set)}')
                for i, data in enumerate(data_set):
                    if type(data) == Body:
                        res = data.name
                    elif type(data) == Quantity:
                        res = f'{data:.4e}'
                    elif type(data) == str:
                        res = f'{data}'
                    else:
                        res = data

                    # print(f'widget #{i}: {widg_grp[i].objectName()} -> {str(res)}')
                    widg_grp[i].setText(str(res))

            case 'cam_':
                # TODO: output the get_state() dict, whatever it is, in (key, value) pairs of labels.
                i = 0
                cam_state = self.cameras.curr_cam.get_state()
                state_size = len(cam_state.keys())
                key_widgs = self.controls.widget_group('key_')
                widg_count = len(key_widgs)
                # print("CAM!!!")
                # [print(f'{k} has type {type(v)} with value {v}') for k, v in cam_state.items()]
                # print(f'Number of items in camera state: {state_size}\n' +
                #       f'Number of widgets available: {widg_count}')

                for k, v in cam_state.items():
                    if i < widg_count:
                        key_widgs[i].setText(str(k))
                        match str(type(v)):

                            case "<class \'float\'>":
                                res = f'{v:.4}'

                            case "<class \'tuple\'>":
                                res = to_vector_str(v)

                            case "<class \'vispy.util.quaternion.Quaternion\'>":
                                res = to_quat_str(v)
                                widg_grp[i].setText(res)
                                key_widgs[-1].setText('Attitude:')
                                widg_grp[-1].setText(to_rpy_str(v))
                                break

                            case _:
                                res = ''

                        widg_grp[i].setText(res)
                        i += 1

        self.panel_refreshed.emit(panel_key)


def main():
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


'''==============================================================================================================='''
if __name__ == "__main__":

    if DO_PROFILE:
        cProfile.run('main()', sort='tottime')
    else:
        main()
