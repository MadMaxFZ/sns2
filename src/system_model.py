# system_model.py
import time

import psygnal
from starsys_data import *
from src.simbody_list import SimBodyList
from sysbody_model import SimBody
from astropy.coordinates import solar_system_ephemeris
from astropy.time import Time
from vispy.scene.cameras import BaseCamera, FlyCamera, TurntableCamera, ArcballCamera, PanZoomCamera


class SimSystem(SimBodyList):
    """
    """
    initialized = psygnal.Signal(list)
    has_updated = psygnal.Signal(Time)
    panel_data = psygnal.Signal(list, list)
    _body_count: int = 0

    def __init__(self, sys_data, epoch=None, body_names=None, multi=False):
        """
            Initialize a star system model to include SimBody objects indicated by a list of names.
            If no list of names is provided, the complete default star system will be loaded.
            The 'multi' argument indicates if the multiprocessing routines should be used or not.

        Parameters
        ----------
        epoch        : Time     #   Epoch of the system.
        body_names   : list     #   List of names of bodies to include in the model.
        multi        : bool     #   If True, use multiprocessing to speed up calculations.
        """
        super(SimSystem, self).__init__([])
        self._IS_POPULATED = False
        self._HAS_INIT = False
        self._IS_UPDATING = False
        self._USE_LOCAL_TIMER = False
        self._USE_MULTIPROC = multi
        self._USE_AUTO_UPDATE_STATE = False
        self._dist_unit = u.km
        self._sys_primary = None
        self._sys_rel_pos = None
        self._sys_rel_vel = None
        self._bod_tot_acc = None
        self._agg_fields  = None
        self._curr_cam_idx = 0
        self._curr_tab_idx = 0
        self._curr_bod_idx = 0
        self.sys_data      = sys_data
        self._valid_body_names = self.sys_data.body_names
        self._sys_epoch = Time(self.sys_data.default_epoch, format='jd', scale='tdb')
        if epoch:
            self._sys_epoch = epoch

        if body_names:
            self._current_body_names = [_ for _ in body_names if _ in self._valid_body_names]
        else:
            self._current_body_names = self._valid_body_names

        self.load_from_names(self._current_body_names)

    def load_from_names(self, _body_names):
        """
            This metho
        Parameters
        ----------
        _body_names :

        Returns
        -------

        """
        solar_system_ephemeris.set("jpl")
        if _body_names is None:
            self._current_body_names = self._valid_body_names
        else:
            self._current_body_names = [_ for _ in _body_names if _ in self._valid_body_names]

        # populate the list with SimBody objects
        self.data.clear()
        [self.data.append(SimBody(body_data=self.sys_data.body_data(body_name)))
         for body_name in self._current_body_names]
        self._body_count = len(self.data)
        self._sys_primary = [sb for sb in self.data if sb.body.parent is None][0]
        [self._set_parentage(sb) for sb in self.data if sb.body.parent]
        self._IS_POPULATED = True
        self._sys_rel_pos = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._sys_rel_vel = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._bod_tot_acc = np.zeros((self._body_count,),
                                     dtype=vec_type)
        self.update_state(epoch=self._sys_epoch)
        self._HAS_INIT = True

    def _set_parentage(self, sb):
        sb.plane = Planes.EARTH_ECLIPTIC
        this_parent = sb.body.parent
        if this_parent is None:
            sb.type = 'star'
            sb.sb_parent = None
            sb.is_primary = True
        else:
            if this_parent.name in self._current_body_names:
                sb.sb_parent = self.data[self._current_body_names.index(this_parent.name)]
                if sb.sb_parent.type == 'star':
                    sb.type = 'planet'
                elif sb.sb_parent.type == 'planet':
                    sb.type = 'moon'
                    if this_parent.name == "Earth":
                        sb.plane = Planes.EARTH_EQUATOR

    def update_state(self, epoch=None):
        if epoch:
            if type(epoch) == Time:
                self._sys_epoch = epoch
        else:
            epoch = self._sys_epoch

        for sb in self.data:
            sb.epoch = epoch
            sb.update_state(sb, epoch)

    # @pyqtSlot(list)
    @property
    def positions_dict(self):
        res = {}
        [res.update({sb.name: sb.r}) for sb in self.data]
        return res

    @property
    def agg_fields(self):
        return self._agg_fields

    @property
    def body_names(self):
        return self._current_body_names

    @property
    def system_primary(self):
        return self._sys_primary

    @property
    def tracks_dict(self):
        traj_dict = {}
        [traj_dict.update({sb.name: sb.track}) for sb in self.data]
        return traj_dict


if __name__ == "__main__":
    ref_time = time.time()
    model = SimSystem()
    init_time = time.time() - ref_time
    model.update_state()
    done_time = time.time() - ref_time
    print(f"Setup time: {(init_time / 1e+09):0.4f} seconds")
    print(f'Update time: {(done_time / 1e+09):0.4f} seconds')



    # @property
    # def current_cam(self):
    #     return self._curr_cam
    #
    # @current_cam.setter
    # def current_cam(self, cam):
    #     if isinstance(cam, BaseCamera):
    #         self._curr_cam = cam
    #         [sb.set_curr_camera(cam) for sb in self.data]
    #     else:
    #         raise TypeError("SimSystem.set_model_cam(): 'cam' must be a BaseCamera object, got %s",
    #                         type(cam))
