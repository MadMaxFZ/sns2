# -*- coding: utf-8 -*-
"""
    This module contains classes to allow using Qt to control Vispy
"""
import logging.config
from typing import List
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot
# from composite import Ui_frm_sns_controls
from gui_tiled import Ui_SNS_DataPanels
from starsys_data import log_config

logging.config.dictConfig(log_config)

QT_NATIVE = False


class Controls(QtWidgets.QWidget):
    data_request = pyqtSignal(list)

    def __init__(self, parent=None):
        super(Controls, self).__init__(parent)
        # self.ui = Ui_frm_sns_controls()
        self.ui = Ui_SNS_DataPanels()
        self.ui.setupUi(self)
        self.ui_obj_dict = self.ui.__dict__
        # logging.info([i for i in self.ui.__dict__.keys() if (i.startswith("lv") or "warp" in i)])
        self._pattern_names = ['attr_', 'elem_', 'cam_', 'elem_coe_', 'elem_pqw_', 'elem_rv_',
                               'tw_', 'twb_', 'axis_']
        self._tab_names = ['elem_', 'syst_', 'vizz_']
        self._widget_groups = self._scanUi_4panels(patterns=self._pattern_names)
        print(f'{len(self._widget_groups)} widget groups (panels) defined...\n\t-> CONTROLS initialized...')
        self.active_bod = 0
        self.active_pnl = 0
        self.active_cam = 0

    def with_prefix(self, prefix):
        return [widget for name, widget in self.ui.__dict__.items()
                if name.startswith(prefix)
                ]

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
            panels.update({p: self.with_prefix(p)})

        return panels

    @property
    def widget_group(self, prefix=None):
        if prefix is None:
            return self._widget_groups
        elif prefix in self._widget_groups.keys():
            return self._widget_groups[prefix]
        else:
            raise ValueError(f'>>>ERROR: {prefix} is not a valid widget group name.')
