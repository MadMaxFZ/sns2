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

    @pyqtSlot(str)
    def refresh_panel(self, tgt_group, tgt_bname):
        """
            This method is called when the simulation panel needs to be refreshed.
        Parameters
        ----------
        tgt_group      :   key for a widget_group in the _widget_groups dict,
                        also it is a key for a set of values from the model.
        tgt_bname      :   the name of the SimBody to be used in the refresh.

        Returns
        -------
        nothing     :   applies a tuple of values from the model based upon the target key
                        to the currentText field of the widgets identified by the key.
        """
        match tgt_group:
            case 'attr_':   # , 'elem_', 'syst_']:
                new_data = self.model.data_group(sb_name=tgt_bname,
                                                 tgt_group=tgt_group)
                for i, w in enumerate(self.panel_widgets[tgt_group]):
                    print(f'widget#{i:>2}: {w}\n\tdata: {new_data[i]}')
                    try:
                        w.setCurrentText(new_data[i])
                    except:
                        print(f'>>>ERROR: Did not like widget {i}: {w} set to {new_data[i]}')

            case 'cams_':
                pass

    @property
    def panel_widgets(self, name=None):
        if name is None:
            return self._widget_groups
        elif name in self._widget_groups.keys():
            return self._widget_groups[name]
        else:
            return None


