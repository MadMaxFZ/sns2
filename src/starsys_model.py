# starsys_model.py
import time
import urllib.parse

import psygnal
from starsys_data import *
from simbody_dict import SimBodyDict
from simbody_model import SimBody
from starsys_visual import from_pos
from vispy.color import *
from astropy.coordinates import solar_system_ephemeris
from astropy.time import Time, TimeDeltaSec


class SimSystem(SimBodyDict):
    """
    """
    initialized = psygnal.Signal(list)
    has_updated = psygnal.Signal()
    panel_data = psygnal.Signal(list, list)
    _body_count: int = 0

    def __init__(self, ref_data=None, epoch=None, body_names=None, use_multi=False):
        """
            Initialize a star system model to include SimBody objects indicated by a list of names.
            If no list of names is provided, the complete default star system will be loaded.
            The 'multi' argument indicates if the multiprocessing routines should be used or not.

        Parameters
        ----------
        epoch        : Time     #   Epoch of the system.
        body_names   : list     #   List of names of bodies to include in the model.
        use_multi    : bool     #   If True, use multiprocessing to speed up calculations.
        """
        t0 = time.perf_counter()
        super(SimSystem, self).__init__([])
        self._IS_POPULATED = False
        self._HAS_INIT = False
        self._IS_UPDATING = False
        self._USE_LOCAL_TIMER = False
        self._USE_MULTIPROC = use_multi
        self._USE_AUTO_UPDATE_STATE = False
        self._sys_primary = None
        self._sys_rel_pos = None
        self._sys_rel_vel = None
        self._bod_tot_acc = None
        self._model_fields2agg = ('rad0', 'pos', 'rot', 'radius',
                                  'elem_coe_', 'elem_pqw_', 'elem_rv',
                                  'is_primary',
                                  )
        if ref_data:
            if isinstance(ref_data, SystemDataStore):
                print('<sys_date> input is valid...')
            else:
                print('Bad <sys_data> input... Reverting to defaults...')
                ref_data = SystemDataStore()

        else:
            ref_data = SystemDataStore()

        self.ref_data = ref_data
        self._dist_unit = self.ref_data.dist_unit
        self._vec_type = self.ref_data.vec_type

        if epoch:
            self._sys_epoch = epoch
        else:
            self._sys_epoch = Time(self.ref_data.default_epoch, format='jd', scale='tdb')

        self._valid_body_names = self.ref_data.body_names
        if body_names:
            self._current_body_names = tuple([n for n in body_names if n in self._valid_body_names])
        else:
            self._current_body_names = tuple(self._valid_body_names)

        solar_system_ephemeris.set("jpl")
        # self.load_from_names(self._current_body_names)
        t1 = time.perf_counter()
        print(f'SimSystem initialization took {t1 - t0:.6f} seconds...')

    def load_from_names(self, _body_names=None):
        """
            This method creates one or more SimBody objects based upon the provided list of names.
            CONSIDER: Should this be a class method that returns a SimSystem() when given names?

        Parameters
        ----------
        _body_names :

        Returns
        -------
        nothing     : Leaves the model usable with SimBody objects loaded
        """
        if _body_names is None:
            self._current_body_names = self._valid_body_names
        else:
            self._current_body_names = [n for n in _body_names if n in self._valid_body_names]

        # populate the list with SimBody objects
        self.data.clear()
        [self.data.update({body_name: SimBody(body_data=self.ref_data.body_data[body_name],
                                              vizz_data=self.ref_data.vizz_data()[body_name])})
         for body_name in self._current_body_names]

        self._body_count = len(self.data)
        self._sys_primary = [sb for sb in self.data.values() if sb.body.parent is None][0]
        [self._set_parentage(sb) for sb in self.data.values() if sb.body.parent]
        self._IS_POPULATED = True
        self._sys_rel_pos = np.zeros((self._body_count, self._body_count),
                                     dtype=self._vec_type)
        self._sys_rel_vel = np.zeros((self._body_count, self._body_count),
                                     dtype=self._vec_type)
        self._bod_tot_acc = np.zeros((self._body_count,),
                                     dtype=self._vec_type)
        self.update_state(epoch=self._sys_epoch)
        self._HAS_INIT = True

    def update_state(self, epoch=None):
        t0 = time.perf_counter()
        if epoch:
            if type(epoch) == Time:
                self._sys_epoch = epoch
            elif type(epoch) == str:
                self._sys_epoch = Time(epoch, format='jd')

        else:
            epoch = self._sys_epoch

        for sb in self.data.values():
            sb.epoch = epoch
            sb.update_state(sb, epoch)

        t1 = time.perf_counter()
        update_time = t1 - t0
        print(f'> Time to update: {update_time:.4f} seconds.')
        self.has_updated.emit()

    def _set_parentage(self, sb):
        sb.plane = Planes.EARTH_ECLIPTIC
        this_parent = sb.body.parent
        if this_parent is None:
            sb.type = 'star'
            sb.sb_parent = None
            sb.is_primary = True
        else:
            if this_parent.name in self._current_body_names:
                sb.sb_parent = self.data[this_parent.name]
                if sb.sb_parent.type == 'star':
                    sb.type = 'planet'
                elif sb.sb_parent.type == 'planet':
                    sb.type = 'moon'
                    if this_parent.name == "Earth":
                        sb.plane = Planes.EARTH_EQUATOR

    def data_group(self, sb_name, tgt_key=None):
        """
            This method returns the data group associated with the provided body name and key.
        Parameters
        ----------
        sb_name :   the name of the SimBody object targeted
        tgt_key :   the key associated with the data group requested

        Returns
        -------
        data_list : a list containing the data associated with the provided body name and key.
        """
        sb_names = None
        tgt_keys = None

        if type(sb_name) == str and sb_name in self._current_body_names:
            pass
        else:
            raise KeyError("Must provide exactly one SimBody name...")

        if type(tgt_key) == str and tgt_key in self._model_fields2agg:
            tgt_keys = [tgt_key, ]
        elif type(tgt_key) == list:
            tgt_keys = [k for k in tgt_key if k in self.ref_data.model_data_group_keys]
        else:
            raise KeyError("Must provide at least one target key...")

        print(f'sb_names = {sb_name},\n tgt_keys = {tgt_keys}')
        if sb_name and tgt_keys:
            print("\tNAME  AND  TARGET(S)\n")
            res = {}
            [res.update({(sb_name, t): self.data[sb_name].field(t)})
             for t in tgt_keys
             ]

        elif tgt_keys and not sb_name:
            print("\tTARGET  AND  NO NAME\n")
            res = {}
            [[res.update({(n, t): self.data[n].field(t)})
              for n in self._current_body_names
              ]
             for t in tgt_keys
             ]

        else:
            res = {}

        [print(f'model.data_group({k[0]}, {k[1]}) = {self.data[k[0]].field(k[1])}')
         for k, v in res.items()]
        return list(res.values())[0]

    def get_agg_fields(self, field_ids):
        # res = {'primary_name': self.system_primary.name}
        res = {}
        for f_id in field_ids:
            agg = {}
            [agg.update({sb.name: self.get_sbod_field(sb, f_id)})
             for sb in self.data.values()]
            res.update({f_id: agg})

        return res

    def get_sbod_field(self, _simbod, field_id):
        """
            This method retrieves the values of a particular field for a given SimBody object.
            Uses the field_id key to indicate which property to return.
        Parameters
        ----------
        _simbod             : SimBody            The SimBody object for which the field value is to be retrieved.
        field_id            : str                The field for which the value is to be retrieved.

        Returns
        -------
        simbod.<field_id>   : float or list       The value of the field for the given SimBody object.
        """
        match field_id:
            case 'attr_':
                res = []
                for a in _simbod.body:
                    if type(a) == Body:
                        a = a.name
                    res.append(a)
                return res

            case 'elem_coe_':
                return _simbod.elem_coe

            case 'elem_pqw_':
                return _simbod.elem_pqw

            case 'elem_rv_':
                return _simbod.elem_rv

            case 'radius':
                return _simbod.radius

            case 'pos':
                return _simbod.pos

            case 'rot':
                return _simbod.rot

            case 'axes':
                return _simbod.axes

            case 'track_data':
                return _simbod.track

            case 'radius':
                return _simbod.radius

            case 'body_alpha':
                return _simbod.body_alpha

            case 'track_alpha':
                return _simbod.track_alpha

            case 'body_mark':
                return _simbod.body_mark

            case 'body_color':
                return _simbod.body_color

            case 'is_primary':
                return _simbod.is_primary

            case 'tex_data':
                # TODO: Add a condition to check if texture data exists in an existing Planet visual.
                #       If it exists, return its texture data. Otherwise return the default texture data.
                return self.ref_data.vizz_data(name=_simbod.name)['tex_data']

            # case 'rel2cam':
            #     return from_pos(tgt_pos=_simbod.pos, tgt_radius=_simbod.radius[0] * self.model.dist_unit)

        pass

    '''===== PROPERTIES ==========================================================================================='''

    @property
    def dist_unit(self):
        return self._dist_unit

    @property
    def positions(self):
        """
        Returns
        -------
        dict    :   a dictionary of the positions of the bodies in the system keyed by name.
        """
        return dict.fromkeys(list(self.data.keys()),
                             [sb.pos for sb in self.data.values()])

    @property
    def radii(self):
        """
        Returns
        -------
        dict    :   a dictionary of the mean radius of the bodies in the system keyed by name.
        """
        return dict.fromkeys(list(self.data.keys()),
                             [sb.body.R for sb in self.data.values()])

    @property
    def body_names(self):
        return tuple(self.data.keys())

    @property
    def system_primary(self):
        return self._sys_primary

    @property
    def tracks_data(self):
        """
        Returns
        -------
        dict    :   a dictionary of the orbit tracks of the bodies in the system keyed by name.
        """
        res = {}
        [res.update({k: self.data[k].track}) for k in self.data.keys() if not self.data[k].is_primary]

        return res

    @property
    def body_color(self):
        res = {}
        return res

    @property
    def body_alpha(self):
        res = {}
        return res

    @property
    def track_color(self):
        res = {}
        return res

    @property
    def body_mark(self):
        res = {}
        return res


'''==============================================================================================================='''
if __name__ == "__main__":
    def main():
        ref_time = time.perf_counter()

        model = SimSystem({})
        model.load_from_names()
        init_time = time.perf_counter()

        model.update_state()
        done_time = time.perf_counter()

        # print(f"Setup time: {((init_time - ref_time) / 1e+09):0.4f} seconds")
        # print(f'Update time: {((done_time - init_time) / 1e+09):0.4f} seconds')

        print(f"Setup time: {(init_time - ref_time)} seconds")
        print(f'Update time: {(done_time - init_time)} seconds')


    main()
