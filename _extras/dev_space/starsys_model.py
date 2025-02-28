# -*- coding: utf-8 -*-
# x
import multiprocessing
import cProfile, pstats
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject
from astropy.constants.codata2014 import G
from astropy.coordinates import solar_system_ephemeris
from poliastro.util import time_range
from multiprocessing import Pool
from src.starsys_data import *
from src.simbody_model import SimBody

logging.basicConfig(filename="../../logs/sb_viewer.log",
                    level=logging.DEBUG,
                    format='%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s',
                    )


class StarSystemModel(QObject):
    """
    """
    # sim_params = SYS_DATA.system_params
    initialized = pyqtSignal(list)
    updating = pyqtSignal(Time)
    ready = pyqtSignal(float)
    data_return = pyqtSignal(list, list)

    def __init__(self, body_names=None, has_timer=False, multi=False):
        super(StarSystemModel, self).__init__()
        self._HAS_INIT        = False
        self._IS_UPDATING     = False
        self._USE_LOCAL_TIMER = False
        self._USE_MULTIPROC   = multi
        self._USE_AUTO_UPDATE_STATE = False

        solar_system_ephemeris.set("jpl")
        self._sys_epoch   = Time(sys_data.default_epoch, format='jd', scale='tdb')
        # TODO::  Add a method to allow the user to provide a list of Body names
        _body_names = sys_data.body_names
        if body_names is None:
            body_names = _body_names

        self._simbody_list = [self.add_simbody(body_name=_name) for _name in body_names
                              if _name in _body_names]
        self._simbody_dict = {}
        [self._simbody_dict.update({_sb.name: _sb}) for _sb in self._simbody_list]
        self._body_names = tuple(self._simbody_dict.keys())
        self._body_count = len(self._simbody_dict)
        self._set_parentage()
        self._sys_rel_pos = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._sys_rel_vel = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._bod_tot_acc = np.zeros((self._body_count,),
                                     dtype=vec_type)
        self.update_epoch(new_epoch=self._sys_epoch)
        if self._USE_MULTIPROC:
            self._pool = Pool(processes=os.cpu_count())

        # TODO:: Move all this stuff into an EpochEmitter class, which would emit a simulation epoch based upon
        #        the real time elapsed multiplied by a warp factor for the simulation time.
        self._ephem_span = (sys_data.system_params['periods']
                            * sys_data.system_params['spacing'])
        self._end_epoch   = self._sys_epoch + self._ephem_span
        if self._USE_LOCAL_TIMER:
            from vispy.app.timer import Timer
            if type(self._USE_LOCAL_TIMER) == Timer:
                timer = self._USE_LOCAL_TIMER
            else:
                timer = Timer(interval='auto', iterations=-1, start=False)
                
            self._w_clock = timer
            self._w_last = 0
            self._d_epoch = None
            self._avg_d_epoch = 0 * u.s
            self._t_warp = 1.0  # multiple to apply to real time in simulation
            self.assign_timer(self._w_clock)
            self._w_clock = Timer(interval='auto', iterations=-1, start=False)
            self._w_last = 0
            self._d_epoch = None
            self._avg_d_epoch = 0 * u.s
            self._t_warp = 1.0  # multiple to apply to real time in simulation
            self.assign_timer(self._w_clock)

    def _flip_update_flag(self):
        self._IS_UPDATING = not self._IS_UPDATING

    def _show_epoch(self):
        print(">> SYS_EPOCH:", self._sys_epoch)

    def assign_timer(self, clock):
        self._w_clock = clock
        # self._w_clock.connect(self.update_timer_epoch)

    def add_simbody(self, body_name):
        if body_name:
            new_simbody = SimBody(body_data=sys_data.body_data(body_name))
            new_simbody.epoch = self._sys_epoch
            logging.info("\t>>> SimBody object %s created....\n", body_name)
            return new_simbody
        else:
            print(self.__class__, self.__name__, "No Body name provided...")

    def _set_parentage(self):
        for sb in self._simbody_dict.values():
            parent = sb.body.parent
            sb.plane = Planes.EARTH_ECLIPTIC
            if parent is not None:
                if parent.name in self._body_names:
                    sb.sb_parent = self._simbody_dict[sb.body.parent.name]
                    if sb.sb_parent.type == 'star':
                        sb.type = 'planet'
                    elif sb.sb_parent.type == 'planet':
                        sb.type = 'moon'
                        if parent.name == "Earth":
                            sb.plane = Planes.EARTH_EQUATOR
            else:
                sb.type       = 'star'
                sb.sb_parent  = None
                sb.is_primary = True

        SimBody.simbody = self._simbody_dict

    def set_ephems(self,
                   epoch=None,
                   periods=365,
                   spacing=86400 * u.s,
                   ):
        if epoch is None:
            epoch = self._sys_epoch

        for sb in self.simbody_list:
            _t_range = time_range(epoch,
                                  periods=periods,
                                  spacing=sb.spacing,
                                  format="jd",
                                  scale="tdb",
                                  )
            sb.set_ephem(t_range=_t_range)
            sb.end_epoch = epoch + periods * spacing
            logging.info("END_EPOCH:\n%s\n", self._end_epoch)

    def set_orbits(self):
        [sb.set_orbit(ephem=sb.ephem) for sb in self.simbody_list]
        self.initialized.emit(self._body_names)

    def _check_ephem_range(self, sb):
        if self._sys_epoch > sb.end_epoch:
            self.epoch = sb.end_epoch  # reset ephem range
            sb.RESAMPLE = True
            logging.debug("RELOAD EPOCHS/EPHEM SETS...")

    def update_epoch(self, new_epoch):
        # self.updating.emit(self._sys_epoch)
        self._sys_epoch = new_epoch
        if self._USE_AUTO_UPDATE_STATE:
            self.update_state()
        # start = time.perf_counter()
        # self.update_state()
        # end = time.perf_counter()
        # self.ready.emit(end - start)

    def update_state(self, epoch=None):
        if epoch:
            if type(epoch) == Time:
                self._sys_epoch = epoch
        else:
            epoch = self._sys_epoch

        self.updating.emit(epoch)
        # update and ephems that are ended, flag for orbit resample
        # TODO:: the Ephem check should like within the SimBody class when its epoch is updated
        [self._check_ephem_range(sb) for sb in self.simbody_list]
        if self._USE_MULTIPROC:
            self.update_state_multi(epoch=epoch)
        else:
            [SimBody.update_state(sb, epoch=epoch) for sb in self.simbody_list]

        self._update_rel_data()
        # self.ready.emit(self._sys_epoch)

    def update_state_multi(self, epoch=None):
        # TODO:: implement multiprocessing        [sb.update_state(epoch=epoch) for sb in self.simbody_list]
        if epoch:
            self._sys_epoch = epoch

        procs = []
        for name in self._simbody_dict.keys():
            p = SimBodyUpdateProcess(name, epoch)
            p.start()
            procs.append(p)

        for p in procs:
            p.join()

    def update_state_by_name(self,name):
        return self._simbody_dict[name].update_state(self._sys_epoch)

    def _update_rel_data(self):
        i = 0
        for sb1 in self.simbody_list:
            j = 0
            # collect the relative position and velocity to the other bodies
            for sb2 in self.simbody_list:
                self._sys_rel_pos[i][j] = sb2.rel2pos(pos=sb1.pos2primary)['rel_pos']
                self._sys_rel_vel[i][j] = sb2.vel - sb1.vel
                if i != j:
                    # accumulate the acceleration from the other bodies
                    self.body_accel[i] += (G * sb2.body.mass) / (
                            self._sys_rel_pos[i][j] * self._sys_rel_pos[i][j] * u.km * u.km)
                j += 1
            i += 1

        # self.ready.emit(self._sys_epoch)
        logging.debug("\nREL_POS :\n%s\nREL_VEL :\n%s\nACCEL :\n%s",
                      self._sys_rel_pos,
                      self._sys_rel_vel,
                      self.body_accel)

    def cmd_timer(self, cmd=None):
        if not cmd:
            if self._w_clock.running:
                self._w_clock.stop()
            else:
                self._HAS_INIT = False
                self._w_clock.start()
        else:
            if cmd == "start":
                self._HAS_INIT = False
                self._w_clock.start()
            elif cmd == "stop":
                self._w_clock.stop()
        print(f"clock running: {self._w_clock.running} at {self._w_clock.elapsed}\n"
              f"with sys_epoch: {self._sys_epoch}")

    @pyqtSlot(list)
    def send_panel(self, target):
        #   This method will receive the selected body name and
        #   the data block requested from Controls
        data_set = []
        body = target[0]
        panel = target[1]
        if panel == "CAMS":
            pass
        elif panel == "tab_ATTR":
            body_obj: Body = self.simbodies[body].body
            data_set = [body_obj[i] for i in range(len(body_obj._fields))]

        self.data_return.emit(target, data_set)
        pass

    @property
    def epoch(self):
        return self._sys_epoch

    @epoch.setter
    def epoch(self, new_epoch=None):
        self._sys_epoch = new_epoch
        self.update_state()

    @property
    def body_names(self):
        return self._body_names

    @property
    def simbody_list(self):
        return [self._simbody_dict[name] for name in sorted(self._body_names)]

    @property
    def body_accel(self):
        return self._bod_tot_acc

    @property
    def t_warp(self):
        return self._t_warp

    @t_warp.setter
    def t_warp(self, new_twarp):
        self._t_warp = new_twarp

    @property
    def model_clock(self):
        return self._w_clock

    @property
    def simbodies(self):
        return self._simbody_dict

    @property
    def body_count(self):
        return self._body_count


def main():
    import cProfile, pstats
    my_starsys = StarSystemModel()
    cpro = cProfile.run('[my_starsys.update_epoch(e0 + n * u.d) for n in range(365)]', sort='cumtime')
    p = pstats.Stats(cpro)
    p.sort_stats('cumtime')('cumtime').print_callers()
    # my_starsys.t_warp = 1
    # my_starsys.assign_timer(Timer(interval=0.1, iterations=100))
    # my_starsys.cmd_timer()
    # while my_starsys.model_clock.running:
    #    pass    # my_starsys.update_epoch()


class SimBodyUpdateProcess(multiprocessing.Process):
    def __init__(self, name, epoch):
        super().__init__()
        self.simbody = SimBody._system(name)
        self.epoch = epoch

    def run(self):
        SimBody.update_state(self.simbody.name, self.epoch)


if __name__ == "__main__":

    my_starsys = StarSystemModel()
    e0 = my_starsys.epoch
    cProfile.run('[my_starsys.update_epoch(e0 + n * u.d) for n in range(365)]', sort='cumtime', filename='../profile.prof')
    p = pstats.Stats('profile.prof')
    p.sort_stats('cumtime').print_callers()


    # def update_timer_epoch(self, event=None):
    #     # get duration since last update
    #     if self._INIT:
    #         w_now = self._w_clock.elapsed   # not the first call
    #         if w_now is None:
    #             w_now = 0
    #         dt = w_now - self._w_last
    #         self._w_last = w_now
    #     else:
    #         w_now = 0                       # the first call sets up self.w_last
    #         dt = 0
    #         self._w_last = w_now - dt
    #         self._INIT = True
    #         self.initialized.emit(self._body_names)
    #
    #     # apply time factor, set new sys_epoch
    #     d_epoch = TimeDelta(dt * u.s * self._t_warp)
    #     self._sys_epoch += d_epoch
    #     self.updating.emit(self._sys_epoch)
    #     # if self._avg_d_epoch.value == 0:
    #     #     self._avg_d_epoch = d_epoch
    #     # self._avg_d_epoch = (self._avg_d_epoch + d_epoch) / 2
    #     self.update_state()
    #     self.ready.emit(dt)
    #     logging.info("AVG_dt: %s\n\t>>> NEW EPOCH: %s\n",
    #                  self._avg_d_epoch,
    #                  self._sys_epoch.jd)
