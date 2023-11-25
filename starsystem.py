# -*- coding: utf-8 -*-

from vispy.app.timer import *
from astropy.time import TimeDelta
from astropy.coordinates import solar_system_ephemeris
from poliastro.util import time_range
from data_functs import *
from simbody import SimBody
from astropy import units as u
from astropy.constants.codata2014 import G
from vispy.scene.visuals import Markers, Compound, Polygon, XYZAxis
import vispy.visuals.transforms as tr
import math

logging.basicConfig(filename="logs/sb_viewer.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )
MIN_SYMB_SIZE = 5
MAX_SYMB_SIZE = 20
ST = tr.STTransform
MT = tr.MatrixTransform


class StarSystem:
    def __init__(self, system_view=None):
        self._INIT = False
        self._DATASET = setup_datastore()
        self._body_count = self._DATASET["BODY_COUNT"]
        self._body_names = self._DATASET["BODY_NAMES"]
        self._body_data  = self._DATASET["BODY_DATA"]
        self._skymap     = self._DATASET["SKYMAP"]          # place this in new graphics class
        self._sim_params = self._DATASET["SYS_PARAMS"]
        self._sys_epoch = Time(self._DATASET["DEF_EPOCH"],
                               format='jd',
                               scale='tdb',
                               )
        self._simbodies = self.init_simbodies(body_names=self._body_names)
        self._sb_list = [self._simbodies[name] for name in self._body_names]
        self._sys_rel_pos = np.zeros((self._body_count, self._body_count), dtype=vec_type)
        self._sys_rel_vel = np.zeros((self._body_count, self._body_count), dtype=vec_type)
        self._body_accel = np.zeros((self._body_count,), dtype=vec_type)
        self._mainview = system_view
        self._cam = self._mainview.camera
        self._cam_rel_pos = np.zeros((self._body_count,), dtype=vec_type)
        self._cam_rel_vel = None    # there is no readily available velocity for camera

        self._bods_pos = None
        self._symbol_sizes = self.get_symb_sizes()
        self._bod_symbols  = [sb.body_symb for sb in self._sb_list]
        self._body_markers = Markers(edge_color=(0, 1, 0, 1),
                                     size=self._symbol_sizes,
                                     scaling=False, )
        self._track_polys = []
        self._track_alpha = 0.5
        self._orb_vizz = None
        self._frame_viz = None

        self._w_last = 0
        self._d_epoch = None
        self._avg_d_epoch = None
        self._end_epoch = None
        self._w_clock = Timer(interval='auto',
                              connect=self.update_epochs,  # change this
                              iterations=-1,
                              )
        print("Target FPS:", 1 / self._w_clock.interval)
        self._t_warp = 10000            # multiple to apply to real time in simulation
        self.set_ephems()

    def init_simbodies(self, body_names=None):
        solar_system_ephemeris.set("jpl")
        sb_dict = {}
        for name in self._body_names:
            sb_dict.update({name: SimBody(body_name=name,
                                          epoch=self._sys_epoch,
                                          sim_param=self._sim_params,
                                          body_data=self._body_data[name],
                                          # add marker symbol to body_data
                                          )})
        logging.info("\t>>> SimBody objects created....\n")
        return sb_dict

    # TODO: Consider making a new class containing all the system's graphical components
    def init_sysviz(self):
        self._frame_viz = XYZAxis(parent=self._mainview.scene)       # set parent in MainSimWindow ???
        self._frame_viz.transform = ST(scale=[1e+08, 1e+08, 1e+08])
        for sb in self._sb_list:
            if sb.sb_parent is not None:
                new_poly = Polygon(pos=sb.o_track,
                                   border_color=sb.base_color + np.array([0, 0, 0, self._track_alpha]),
                                   triangulate=False,
                                   )
                sb.trk_poly = new_poly
                self._track_polys.append(sb.trk_poly)

        self._orb_vizz = Compound(self._track_polys)
        viz = Compound([self._frame_viz, self.bods_viz, self._orb_vizz])
        viz.parent = self._mainview.scene
        return viz

    def set_ephems(self, epoch=None, span=1):   # TODO: make default span to Time(1 day)
        if epoch is None:
            epoch = self._sys_epoch
        else:
            span = self._simbodies["Earth"].orbit.period / 365.25

        _t_range = time_range(epoch,
                              periods=365,
                              spacing=span,
                              format="jd",
                              scale="tdb",
                              )
        [sb.set_ephem(t_range=_t_range) for sb in self._sb_list]
        self._end_epoch = _t_range[-1]
        logging.info("END_EPOCH:\n%s\n", self._end_epoch)

    def update_epochs(self, event=None):
        if self._INIT:
            w_now = self._w_clock.elapsed     # not the first call
            dt = w_now - self._w_last
            self._w_last = w_now
        else:
            w_now = 0                       # the first call sets up self.w_last
            dt = 0
            self._w_last = w_now - dt
            self._INIT = True

        d_epoch = TimeDelta(dt * u.s * self._t_warp)
        if self._avg_d_epoch is None:
            self._avg_d_epoch = d_epoch

        self._sys_epoch += d_epoch
        self._avg_d_epoch = (self._avg_d_epoch + d_epoch) / 2
        if (self._end_epoch - self._sys_epoch) < 2 * self._avg_d_epoch:
            logging.debug("RELOAD EPOCHS/EPHEM SETS...")
            self.set_ephems(epoch=self._sys_epoch)               # reset ephem range

        self.update_states(new_epoch=self._sys_epoch)
        logging.debug("AVG_dt: %s\n\t>>> NEW EPOCH: %s\n",
                      self._avg_d_epoch,
                      self._sys_epoch.jd)

    def update_states(self, new_epoch=None):
        for sb in self._sb_list:
            sb.update_state(epoch=new_epoch)

        # collect positions of the bodies into an array
        self._bods_pos = []
        self._bods_pos.extend([sb.pos for sb in self._sb_list])
        self._bods_pos[4] += self._bods_pos[3]                        # add Earth pos to Moon pos
        # self.trk_polys[3].transform = ST(translate=self.bods_pos[3])  # move moon orbit to Earth pos
        self._bods_pos = np.array(self._bods_pos)

        i = 0
        for sb1 in self._sb_list:
            j = 0
            # collect the position relative to the camera location
            self._cam_rel_pos[i] = sb1.rel2pos(pos=self._mainview.camera.center)['rel_pos']

            # collect the relative position and velocity to the other bodies
            for sb2 in self._sb_list:
                self._sys_rel_pos[i][j] = sb2.rel2pos(pos=sb1.pos)['rel_pos']
                self._sys_rel_vel[i][j] = sb2.vel - sb1.vel
                if i != j:
                    # accumulate the acceleration from the other bodies
                    self._body_accel[i] += (G * sb1.body.mass * sb2.body.mass) / (
                            self._sys_rel_pos[i][j] * self._sys_rel_pos[i][j] * u.m * u.m)
                j += 1
            i += 1

        self._symbol_sizes = self.get_symb_sizes()        # update symbol sizes based upon FOV of body
        self._body_markers.set_data(pos=self._bods_pos,
                                    face_color=np.array([sb.base_color + np.array([0, 0, 0, self._track_alpha])
                                                         for sb in self._sb_list]),
                                    edge_color=[1, 0, 0, .6],
                                    size=self._symbol_sizes,
                                    symbol=self._bod_symbols,
                                    )
        logging.info("\nSYMBOL SIZES :\t%s", self._symbol_sizes)
        logging.info("\nCAM_REL_DIST :\n%s", [np.linalg.norm(rel_pos) for rel_pos in self._cam_rel_pos])
        logging.debug("\nREL_POS :\n%s\nREL_VEL :\n%s\nACCEL :\n%s",
                      self._sys_rel_pos, self._sys_rel_vel, self._body_accel)

    def get_symb_sizes(self):
        body_fovs = []
        for sb in self._sb_list:
            body_fovs.append(sb.rel2pos(pos=self._cam.center)['fov'])
            sb.update_alpha()

        raw_diams = [math.ceil(self._mainview.size[0] * b_fov / self._cam.fov) for b_fov in body_fovs]
        pix_diams = []
        for rd in raw_diams:
            if rd < MIN_SYMB_SIZE:
                pix_diams.append(MIN_SYMB_SIZE)
            elif rd > MAX_SYMB_SIZE:
                pix_diams.append(0)
            else:
                pix_diams.append(rd)

        return np.array(pix_diams)

    def run(self):
        self._w_clock.start()

    @property
    def bods_viz(self):
        return self._body_markers

    @property
    def t_warp(self):
        return self._t_warp

    @t_warp.setter
    def t_warp(self, new_twarp):
        self._t_warp = new_twarp


def main():
    my_starsys = StarSystem()
    my_starsys.run()


if __name__ == "__main__":
    main()
