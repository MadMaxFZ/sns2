# simsystem.py
import logging
import time
import psygnal
from astropy.time import Time, TimeDeltaSec
from multiprocessing import Queue
from simobj_dict import SimObjectDict
from multiprocessing import shared_memory
# from poliastro.bodies import Body
# from PyQt5.QtCore import QObject

logging.basicConfig(filename="../logs/sns_sysmod.log",
                    level=logging.ERROR,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )

# class SystemWrapper(QObject):
#     def __init__(self, *args, **kwargs):
#         """
#
#         Returns
#         -------
#         None
#         """
#         super(SystemWrapper, self).__init__(parent=None)
#         self.model = SimSystem(*args, **kwargs)


class SimSystem(SimObjectDict):
    """
    """
    initialized = psygnal.Signal(list)
    panel_data = psygnal.Signal(list, list)

    def __init__(self, comm_q, stat_q, *args, **kwargs):
        """
            Initialize the star system model. Two Queues are passed to provide
            communication with the main process

        Parameters
        ----------

        """
        self._t0 = self._base_t = time.perf_counter()
        super(SimSystem, self).__init__([], *args, **kwargs)
        self._t1 = time.perf_counter()
        self._t0 = self._t1
        print(f'SimSystem declaration took {(self._t1 - self._base_t) * 1e-06:.4f} seconds...')
        self._model_fields2agg = ('rad0', 'pos', 'rot', 'radius',
                                  'elem_coe_', 'elem_pqw_', 'elem_rv',
                                  'is_primary',
                                  )
        self.comm_q = comm_q
        self.stat_q = stat_q
        self.load_from_names()
        self.update_state(self.epoch)

        self._state_size = self.data['Earth'].state.nbytes
        self._shmem_0 = shared_memory.SharedMemory(create=True,
                                                   name="state_buff0",
                                                   size=self.num_bodies * self._state_size)
        self._shmem_1 = shared_memory.SharedMemory(create=True,
                                                   name="state_buff1",
                                                   size=self.num_bodies * self._state_size)
        self._state_buffers = None

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
                return _simbod.attr

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

            case 'is_primary':
                return _simbod.is_primary

            case 'parent_name':
                if _simbod.body.parent:
                    return _simbod.body.parent.name

            case 'tex_data':
                # TODO: Add a condition to check if texture data exists in an existing Planet visual.
                #       If it exists, return its texture data. Otherwise return the default texture data.
                return self.ref_data.vizz_data(name=_simbod.name)['tex_data']

            # these elements can should live in the viewer
            case 'body_alpha':
                return _simbod.body_alpha

            case 'track_alpha':
                return _simbod.track_alpha

            case 'body_mark':
                return _simbod.body_mark

            case 'body_color':
                return _simbod.body_color

        pass

    '''===== PROPERTIES ==========================================================================================='''

    @property
    def epoch(self):
        return self._sys_epoch

    @epoch.setter
    def epoch(self, new_epoch):
        if new_epoch:
            if type(new_epoch) == Time:
                self._sys_epoch = new_epoch

            elif type(new_epoch) == TimeDeltaSec:
                self._sys_epoch += new_epoch

        if self.USE_AUTO_UPDATE_STATE:
            self.update_state(self._sys_epoch)

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
        res    :   a dictionary of the mean radius of the bodies in the system keyed by name.
        """
        res = {}
        [res.update({sb.name: sb.radius}) for sb in self.data.values()]
        return res

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

        model.update_state(model.epoch)
        done_time = time.perf_counter()

        # print(f"Setup time: {((init_time - ref_time) / 1e+09):0.4f} seconds")
        # print(f'Update time: {((done_time - init_time) / 1e+09):0.4f} seconds')

        print(f"Setup time: {(init_time - ref_time)} seconds")
        print(f'Update time: {(done_time - init_time)} seconds')


    main()
