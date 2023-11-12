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


class StarSystem:
    def __init__(self, view=None):
        self.INIT = False
        self.DATASET = setup_datastore()
        self.body_count = self.DATASET["BODY_COUNT"]
        self.body_names = self.DATASET["BODY_NAMES"]    # cast this to a tuple?
        self.body_data  = self.DATASET["BODY_DATA"]
        self.skymap     = self.DATASET["SKYMAP"]
        self.sim_params = self.DATASET["SYS_PARAMS"]
        self._sys_epoch = Time(self.DATASET["DEF_EPOCH"],
                               format='jd',
                               scale='tdb',
                               )
        self.simbods = self.init_simbodies(body_names=self.body_names)
        self.sb_list = [self.simbods[name] for name in self.body_names]
        self.sys_rel_pos = np.zeros((self.body_count, self.body_count), dtype=vec_type)
        self.sys_rel_vel = np.zeros((self.body_count, self.body_count), dtype=vec_type)
        self.body_accel = np.zeros((self.body_count,), dtype=vec_type)
        self._mainview = view
        self.cam = self._mainview.camera
        self.cam_rel_pos = np.zeros((self.body_count,), dtype=vec_type)
        self.cam_rel_vel = None
        self.bods_pos = None
        self._symb_sizes = self.get_symb_sizes()
        self.bod_symbs = [sb.body_symb for sb in self.sb_list]
        self._bods_viz = Markers(edge_color=(0, 1, 0, 1),
                                 size=self._symb_sizes,
                                 scaling=False, )
        self.trk_polys = []
        self.poly_alpha = 0.5
        self.orb_vizz = None
        self.frame_viz = None
        self.w_last = 0
        self.d_epoch = None
        self.avg_d_epoch = None
        self.end_epoch = None
        self.w_clock = Timer(interval='auto',
                             connect=self.update_epoch,  # change this
                             iterations=-1,
                             )
        print("Target FPS:", 1 / self.w_clock.interval)
        self.t_warp = 10000            # multiple to apply to real time in simulation
        self.set_ephems()

    def get_symb_sizes(self):
        body_fovs = []
        for sb in self.sb_list:
            body_fovs.append(sb.dist2pos(pos=self.cam.center)['fov'])
            sb.update_alpha()

        raw_diams = [math.ceil(self._mainview.size[0] * b_fov / self.cam.fov) for b_fov in body_fovs]
        pix_diams = []
        for rd in raw_diams:
            if rd < MIN_SYMB_SIZE:
                pix_diams.append(MIN_SYMB_SIZE)
            else:
                pix_diams.append(rd)

        return np.array(pix_diams)

    def set_ephems(self, epoch=None, span=1):   # TODO: make default span to Time(1 day)
        if epoch is None:
            epoch = self._sys_epoch
        else:
            span = self.simbods["Earth"].orbit.period / 365.25

        _t_range = time_range(epoch,
                              periods=365,
                              spacing=span,
                              format="jd",
                              scale="tdb",
                              )
        [sb.set_ephem(t_range=_t_range) for sb in self.sb_list]
        self.end_epoch = _t_range[-1]
        logging.info("END_EPOCH:\n%s\n", self.end_epoch)

    def update_epoch(self, event=None):
        if self.INIT:
            w_now = self.w_clock.elapsed     # not the first call
            dt = w_now - self.w_last
            self.w_last = w_now
        else:
            w_now = 0                       # the first call sets up self.w_last
            dt = 0
            self.w_last = w_now - dt
            self.INIT = True

        d_epoch = TimeDelta(dt * u.s * self.t_warp)
        if self.avg_d_epoch is None:
            self.avg_d_epoch = d_epoch

        new_epoch = self._sys_epoch + d_epoch
        self.avg_d_epoch = (self.avg_d_epoch + d_epoch) / 2
        self.do_updates(new_epoch=new_epoch)

        if (self.end_epoch - new_epoch) < 2 * self.avg_d_epoch:
            logging.debug("RELOAD EPOCHS/EPHEM SETS...")
            self.set_ephems(epoch=new_epoch)               # reset ephem range

        self._sys_epoch = new_epoch

        logging.debug("AVG_dt: %s\n\t>>> NEW EPOCH: %s\n",
                      self.avg_d_epoch,
                      new_epoch.jd)

    def init_simbodies(self, body_names=None):
        solar_system_ephemeris.set("jpl")
        sb_dict = {}
        for name in self.body_names:
            sb_dict.update({name: SimBody(body_name=name,
                                          epoch=self._sys_epoch,
                                          sim_param=self.sim_params,
                                          body_data=self.body_data[name],
                                          # add marker symbol to body_data
                                          )})
        logging.info("\t>>> SimBody objects created....\n")
        return sb_dict

    def do_updates(self, new_epoch=None):
        for sb in self.sb_list:
            sb.update_state(epoch=new_epoch)

        # collect positions of the bodies into an array
        self.bods_pos = []
        self.bods_pos.extend([sb.pos for sb in self.sb_list])
        self.bods_pos[4] += self.bods_pos[3]                        # add Earth pos to Moon pos
        # self.trk_polys[3].transform = ST(translate=self.bods_pos[3])  # move moon orbit to Earth pos
        self.bods_pos = np.array(self.bods_pos)

        i = 0
        for sb1 in self.sb_list:
            j = 0
            # collect the position relative to the camera location
            self.cam_rel_pos[i] = sb1.dist2pos(pos=self._mainview.camera.center)['rel_pos']
            # if sb1.sb_parent is not None:
            #     if sb1.sb_parent.name != self.sb_list[0].name:
            #         pass
            #         # sb1.trk_poly.transform = ST(translate=list(self.simbods[sb1.sb_parent.name].state[0]))

            # collect the relative position and velocity to the other bodies
            for sb2 in self.sb_list:
                self.sys_rel_pos[i][j] = sb2.dist2pos(pos=sb1.pos)['rel_pos']
                self.sys_rel_vel[i][j] = sb2.vel - sb1.vel
                if i != j:

                    # accumulate the acceleration from the other bodies
                    self.body_accel[i] += (G * sb1.body.mass * sb2.body.mass) / (
                            self.sys_rel_pos[i][j] * self.sys_rel_pos[i][j] * u.m * u.m)
                j += 1
            i += 1

        self._symb_sizes = self.get_symb_sizes()        # update symbol sizes based upon FOV of body
        self._bods_viz.set_data(pos=self.bods_pos,
                                face_color=np.array([sb.base_color + np.array([0, 0, 0, self.poly_alpha])
                                                     for sb in self.sb_list]),
                                edge_color=[1, 0, 0, .6],
                                size=self._symb_sizes,
                                symbol=self.bod_symbs,
                                )
        logging.info("\nSYMBOL SIZES :\t%s", self._symb_sizes)
        logging.info("\nCAM_REL_DIST :\n%s", [np.linalg.norm(rel_pos) for rel_pos in self.cam_rel_pos])
        logging.debug("\nREL_POS :\n%s\nREL_VEL :\n%s\nACCEL :\n%s",
                      self.sys_rel_pos, self.sys_rel_vel, self.body_accel)

    def init_sysviz(self):
        self.frame_viz = XYZAxis(parent=self._mainview.scene)       # set parent in MainSimWindow ???
        self.frame_viz.transform = tr.STTransform()
        self.frame_viz.transform.scale = [1e+05, 1e+05, 1e+05]
        for sb in self.sb_list:
            if sb.sb_parent is not None:
                new_poly = Polygon(pos=sb.o_track,
                                   border_color=sb.base_color + np.array([0, 0, 0, self.poly_alpha]),
                                   triangulate=False,
                                   )
                sb.trk_poly = new_poly
                self.trk_polys.append(sb.trk_poly)

        self.orb_vizz = Compound(self.trk_polys)
        viz = Compound([self.frame_viz, self.bods_viz, self.orb_vizz])
        viz.parent = self._mainview.scene
        return viz

    def run(self):
        self.w_clock.start()

    @property
    def bods_viz(self):
        return self._bods_viz

def main():
    my_starsys = StarSystem()
    my_starsys.run()


if __name__ == "__main__":
    main()
