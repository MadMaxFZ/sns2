# -*- coding: utf-8 -*-

"""
    This module contains classes to allow using Qt to control Vispy
"""

import logging
import logging.config
from typing import List

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from composite import Ui_frm_sns_controls
from src.starsys_data import log_config

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
        self._pattern_names = ['attr_', 'elem_', 'elem_coe_', 'elem_pqw_', 'elem_rv_',
                           'cam_', 'tw_', 'twb_', 'axis_']
        self._tab_names = ['tab_TIME', 'tab_ATTR', 'tab_ELEM', 'tab_CAMS']
        self._widget_groups = self._scanUi_4panels(patterns=self._pattern_names)
        print(f'{len(self._widget_groups)} groups defined...')

    @property
    def active_widgets(self):
        return dict.fromkeys([i for i in self.ui_obj_dict.items() if i[1].isActive()])

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


