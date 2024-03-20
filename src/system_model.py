# system_model.py

import psygnal
import numpy as np
from starsys_data import *
from src.simbody_list import SimBodyList
from sysbody_model import SimBody
from astropy.coordinates import solar_system_ephemeris
from astropy.time import Time
from vispy.scene.cameras import BaseCamera, FlyCamera, TurntableCamera, ArcballCamera, PanZoomCamera


class SimSystem(SimBodyList):
    """
        This
    """
    _body_count: int = 0
    initialized = psygnal.Signal(list)
    updating = psygnal.Signal(Time)
    ready = psygnal.Signal(float)
    data_return = psygnal.Signal(list, list)
    fields2agg = ('rad', 'rel2cam', 'pos', 'rot', 'b_alpha', 't_alpha', 'symb', 'color', 'track',)

    def __init__(self, cam=FlyCamera(fov=60), body_names=None, multi=False):
        """
        Parameters
        ----------
        cam
        body_names
        multi
        """
        if not body_names:
            self._current_body_names = sys_data.body_names
        else:
            self._current_body_names = [n for n in body_names if n in sys_data.body_names]

        super(SimSystem, self).__init__([])
        self._IS_POPULATED = False
        self._HAS_INIT = False
        self._IS_UPDATING = False
        self._USE_LOCAL_TIMER = False
        self._USE_MULTIPROC = multi
        self._USE_AUTO_UPDATE_STATE = False
        self._dist_unit = sys_data.dist_unit
        self._sys_epoch = Time(sys_data.default_epoch, format='jd', scale='tdb')
        # print(f'BODY_NAMES: {self._current_body_names}')
        self._system_primary = None
        self._sys_rel_pos = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._sys_rel_vel = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._bod_tot_acc = np.zeros((self._body_count,),
                                     dtype=vec_type)
        self._curr_cam = cam
        self.load_from_names(self._current_body_names)
        self.agg_fields = self._load_agg_fields(SimSystem.fields2agg)

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
        self._system_primary = [sb for sb in self.data if sb.body.parent is None][0]
        [self._set_parentage(sb) for sb in self.data if sb.body.parent]
        self._IS_POPULATED = True
        self.update_state(epoch=self._sys_epoch)
        self._HAS_INIT = True

    def _load_agg_fields(self, fields):
        res = {'primary_name': self._system_primary.name}
        for k in fields:
            agg = {}
            [agg.update({sb.name: self._get_fields(sb, k)}) for sb in self.data]
            res.update({k: agg})

        return res

    def _get_fields(self, simbody, field):
        """
            This method is used to get the values of a particular field for a given SimBody object.
        Parameters
        ----------
        simbody     : SimBody            The SimBody object for which the field value is to be retrieved.
        field       : str                The field for which the value is to be retrieved.

        Returns
        -------
        res         : float or list      The value of the field for the given SimBody object.
        """
        match field:
            case 'rad':
                return simbody.body.R

            case 'pos':
                return simbody.pos

            case 'attr':
                return simbody.body

            case 'rot':
                return simbody.rot

            case 'track':
                return simbody.track

            case 'axes':
                return simbody.axes

            case 'elem':
                return dict(classical=simbody.orbit.clasical(),
                            pqw=simbody.orbit.pqw(),
                            rv=simbody.orbit.rv,
                            )

            case '_rel2cam':
                return self.rel2cam(simbody.pos, simbody.body.R)

            case 'b_alpha':
                return sys_data.vizz_data(simbody.name)['body_alpha']

            case 't_alpha':
                return sys_data.vizz_data(simbody.name)['track_alpha']

            case 'symb':
                return sys_data.vizz_data(simbody.name)['body_mark']

            case 'color':
                return sys_data.vizz_data(simbody.name)['body_color']

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

        self.data_return.emit(target, data_set)
        pass

    @property
    def agg_pos(self):
        res = {}
        [res.update({sb.name: sb.r}) for sb in self.data]
        return res

    @property
    def body_names(self):
        return self._current_body_names

    @property
    def system_primary(self):
        return self._system_primary

    @property
    def trajects(self):
        traj_dict = {}
        [traj_dict.update({sb.name: sb.track}) for sb in self.data]
        return traj_dict


if __name__ == "__main__":
    model = SimSystem()
