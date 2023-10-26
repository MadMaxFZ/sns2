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
STAR_SIZE = 20
MIN_MARK_SIZE = 5


class StarSystem:
    def __init__(self, view=None):
        self.INIT = False
        self.DATASET = setup_datastore()
        self.body_count = self.DATASET["BODY_COUNT"]
        self.body_names = self.DATASET["BODY_NAMES"]    # cast this to a tuple?
        self.body_data  = self.DATASET["BODY_DATA"]
        self.skymap     = self.DATASET["SKYMAP"]
        self.sim_params = self.DATASET["SYS_PARAMS"]
        self.w_last = 0
        self.d_epoch = None
        self.avg_d_epoch = None
        self.end_epoch = None
        self._sys_epoch = Time(self.DATASET["DEF_EPOCH"],
                               format='jd',
                               scale='tdb',
                               )
        self.wclock = Timer(interval='auto',
                            connect=self.update_epoch,  # change this
                            iterations=-1,
                            )
        print("Target FPS:", 1 / self.wclock.interval)
        self.simbods = self.init_simbodies(body_names=self.body_names)
        self.sb_list = list(self.simbods.values())
        self.sys_rel_pos = np.zeros((self.body_count, self.body_count), dtype=vec_type)
        self.sys_rel_vel = np.zeros((self.body_count, self.body_count), dtype=vec_type)
        self.body_accel = np.zeros((self.body_count,), dtype=vec_type)
        self._mainview = view
        self._win_size = int(view.size[0])
        self.cam = self._mainview.camera
        self.cam_rel_pos = np.zeros((self.body_count,), dtype=vec_type)
        self.cam_rel_vel = None
        self.frame_viz = None
        self.bods_pos = None
        self._mark_sizes = np.array([23, 6, 6, 6, 6, 6, 7, 7, 6, 6, 6])
        self._bods_viz = Markers(edge_color=(0, 1, 0, 1),
                                 size=self._mark_sizes,
                                 scaling=False,)   # TODO: Add size array and set scaling
        self.bod_symbs = None
        self.orb_vizz = None
        self.t_warp = 100000            # multiple to apply to real time in simulation
        self.set_wide_ephems()
        # self.wclock.start()

    def get_mark_sizes(self):
        body_fovs = [sb.dist2pos(pos=self.cam.center)['fov'] for sb in self.sb_list]
        raw_diams = [math.ceil(self._win_size * b_fov / self.cam.fov) for b_fov in body_fovs]
        pix_diams = []
        for rd in raw_diams:
            if rd > MIN_MARK_SIZE:
                pix_diams.append(rd)
            else:
                pix_diams.append(rd + MIN_MARK_SIZE)

        return np.array(pix_diams)

    def set_wide_ephems(self, epoch=None, span=None):
        year_span = self.simbods["Earth"].orbit.period
        if epoch is None:
            epoch = self._sys_epoch

        if span is None:
            span = year_span

        full_t_range = time_range(epoch,
                                  periods=365,
                                  spacing=span,
                                  format="jd",
                                  scale="tdb",
                                  )
        for sb in self.sb_list:
            sb.set_ephem(t_range=full_t_range)

        self.end_epoch = full_t_range[-1]
        logging.info("END_EPOCH:\n%s\n", self.end_epoch)

    def update_epoch(self, event=None):
        if self.INIT:
            w_now = self.wclock.elapsed     # not the first call
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
            self.set_wide_ephems(epoch=new_epoch)               # reset ephem range

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
                                          # add marker symbol and marker size to body_data
                                          )})
        logging.info("\t>>> SimBody objects created....\n")
        return sb_dict

    def do_updates(self, new_epoch=None):
        for sb in self.sb_list:
            sb.update_state(epoch=new_epoch)
        # TODO: rework this to not require recomputing lists unless necessary
        self.bods_pos = []
        self.bods_pos.extend([sb.state[0] for sb in self.sb_list])
        self.bods_pos[4] += self.simbods['Earth'].state[0, :]       # add Earth pos to Moon pos
        self.bods_pos = np.array(self.bods_pos)
        self.bod_symbs = []
        self.bod_symbs.extend([sb.body_symb for sb in self.sb_list])

        i = 0
        for sb1 in self.sb_list:
            j = 0
            self.cam_rel_pos[i] = sb1.dist2pos(pos=self._mainview.camera.center)['rel_pos']
            # self.cam_rel_vel[i] = sb1.state[1] - self._mainview.camera.
            for sb2 in self.sb_list:
                self.sys_rel_pos[i][j] = sb2.dist2pos(pos=sb1.state[0])['rel_pos']
                self.sys_rel_vel[i][j] = sb2.state[1] - sb1.state[1]
                if i != j:
                    self.body_accel[i] += (G * sb2.body.mass) / (
                            self.sys_rel_pos[i][j] * self.sys_rel_pos[i][j] * u.m * u.m)
                j += 1
            i += 1

        self._mark_sizes = self.get_mark_sizes()
        self._bods_viz.set_data(pos=self.bods_pos,
                                face_color=self.DATASET["COLOR_SET"],
                                edge_color=[0, 1, 0, .2],
                                size=self._mark_sizes,
                                symbol=self.bod_symbs,
                                )
        logging.info("\nMARK SIZES:\t%s", self._mark_sizes)
        logging.debug("\nCAM_REL_DIST :\n%s", [np.linalg.norm(rel_pos) for rel_pos in self.cam_rel_pos])
        logging.debug("\nREL_POS :\n%s\nREL_VEL :\n%s\nACCEL :\n%s",
                      self.sys_rel_pos, self.sys_rel_vel, self.body_accel)

    def init_sysviz(self, poly_alpha=0.4):
        self.frame_viz = XYZAxis(parent=self._mainview.scene)          # set parent in MainSimWindow ???
        self.frame_viz.transform = tr.STTransform(scale=(1e+08, 1e+08, 1e+08))
        self.orb_vizz = Compound([Polygon(pos=sb.o_track,
                                          border_color=sb.colormap,
                                          connect="strip",
                                          triangulate=False)
                                  for sb in self.sb_list])

        viz = Compound([self.frame_viz, self.bods_viz, self.orb_vizz])
        viz.parent = self._mainview.scene

        return viz

    def run(self):
        self.wclock.start()

    @property
    def bods_viz(self):
        return self._bods_viz

def main():
    my_starsys = StarSystem()
    my_starsys.run()


if __name__ == "__main__":
    main()
