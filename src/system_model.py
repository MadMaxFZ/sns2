# starsystem.py

from starsys_data import *
from simbody_list import SimBodyList
from sysbody_model import SimBody
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject
from astropy.coordinates import solar_system_ephemeris


class SimSystem(SimBodyList, QObject):
    """
    """
    initialized = pyqtSignal(list)
    updating    = pyqtSignal(Time)
    ready       = pyqtSignal(float)
    data_return = pyqtSignal(list, list)

    def __init__(self, body_names=None, multi=False):
        """

        Parameters
        ----------
        body_names :
        """
        super(SimSystem, self).__init__(iterable=body_names)
        self._IS_POPULATED    = False
        self._HAS_INIT        = False
        self._IS_UPDATING     = False
        self._USE_LOCAL_TIMER = False
        self._USE_MULTIPROC   = multi
        self._USE_AUTO_UPDATE_STATE = False
        solar_system_ephemeris.set("jpl")
        self._sys_epoch = Time(sys_data.default_epoch, format='jd', scale='tdb')
        self._body_names = None
        self._body_count = None
        self.load_from_names(body_names)

    def load_from_names(self, body_names):
        """

        Parameters
        ----------
        body_names :

        Returns
        -------

        """
        _body_names = sys_data.body_names
        if body_names is None:
            body_names = _body_names

        # populate the list with SimBody objects
        [self.append(SimBody(body_data=sys_data.body_data(body_name)))
         for body_name in body_names if body_name in _body_names]
        self._body_names = tuple([sb.name for sb in self])
        [for sb in self]
        self._IS_POPULATED = True

