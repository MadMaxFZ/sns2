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
    fields2agg = ('rad', 'rel2cam', 'pos', 'rot', 'b_alpha', 't_alpha', 'symb', 'color', 'track',)
    _body_count: int = 0

    def __init__(self, cam=FlyCamera(fov=60), epoch=None, body_names=None, multi=False):
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
        self.IS_POPULATED = False
        self.HAS_INIT = False
        self._IS_UPDATING = False
        self.USE_LOCAL_TIMER = False
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
        self._current_body_names = sys_data.body_names
        self._sys_epoch = Time(sys_data.default_epoch, format='jd', scale='tdb')
        if epoch:
            self._sys_epoch = epoch
        if body_names:
            self._current_body_names = [n for n in body_names if n in sys_data.body_names]
        self.load_from_names(self._current_body_names)

    @property
    def current_cam(self):
        return self._curr_cam

    @current_cam.setter
    def current_cam(self, cam):
        if isinstance(cam, BaseCamera):
            self._curr_cam = cam
            [sb.set_curr_camera(cam) for sb in self.data]
        else:
            raise TypeError("SimSystem.set_model_cam(): 'cam' must be a BaseCamera object, got %s",
                            type(cam))

    def load_from_names(self, _body_names):
        """

        Parameters
        ----------
        _body_names :

        Returns
        -------

        """
        solar_system_ephemeris.set("jpl")
        _valid_names = sys_data.body_names
        if _body_names is None:
            _body_names = self._current_body_names

        # populate the list with SimBody objects
        [self.data.append(SimBody(body_data=sys_data.body_data(body_name)))
         for body_name in (_body_names and _valid_names)]
        for n in self._current_body_names:
            assert (n in _body_names)
        self._current_body_names = tuple([sb.name for sb in self.data])
        self._body_count = len(self.data)
        self._sys_primary = [sb for sb in self.data if sb.body.parent is None][0]
        [self._set_parentage(sb) for sb in self.data if sb.body.parent]
        self.IS_POPULATED = True
        self._sys_rel_pos = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._sys_rel_vel = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._bod_tot_acc = np.zeros((self._body_count,),
                                     dtype=vec_type)
        self.update_state(epoch=self._sys_epoch)
        self._agg_fields = self._load_agg_fields(SimSystem.fields2agg)
        self.HAS_INIT = True

    def _load_agg_fields(self, fields):
        res = {'primary_name': self._sys_primary.name}
        for k in fields:
            agg = {}
            [agg.update({sb.name: self._get_fields(sb, k)}) for sb in self.data]
            res.update({k: agg})

        return res

    def _get_fields(self, simbod, field):
        """
            This method is used to get the values of a particular field for a given SimBody object.
        Parameters
        ----------
        simbod  : SimBody            The SimBody object for which the field value is to be retrieved.
        field   : str                The field for which the value is to be retrieved.

        Returns
        -------
        res     : float or list       The value of the field for the given SimBody object.
        """
        match field:
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
                return sys_data.vizz_data(simbod.name)['body_alpha']
            case 't_alpha':
                return sys_data.vizz_data(simbod.name)['track_alpha']
            case 'symb':
                return sys_data.vizz_data(simbod.name)['body_mark']
            case 'color':
                return sys_data.vizz_data(simbod.name)['body_color']

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
    def send_panel(self, target):
        #   This method will receive the selected body name and
        #   the data block requested from Controls
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

        self.panel_data.emit(target, data_set)
        pass

    @property
    def agg_pos(self):
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
    def trajects(self):
        traj_dict = {}
        [traj_dict.update({sb.name: sb.track}) for sb in self.data]
        return traj_dict


if __name__ == "__main__":
    start = time.monotonic_ns()
    model = SimSystem()
    init_time = start = time.monotonic_ns() - start
    print(f"Setup time: {(init_time / 1e+09):0.4f} seconds")
    model.update_state()
    done_time = time.monotonic_ns() - init_time
    print(f'Update time: {(done_time / 1e+09):0.4f} seconds')
