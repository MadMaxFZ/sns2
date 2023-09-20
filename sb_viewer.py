# -*- coding: utf-8 -*-

import functiontrace
import numpy as np
import math
import subprocess
import vispy.visuals.transforms as tr
# from vispy.util.transforms import *
from vispy.scene.visuals import Markers, Compound, Polygon
# from vispy.color import Color
# from viz_functs import get_tex_data, get_viz_data
from vispy import app, scene
from vispy.app.timer import *
from astropy.time import TimeDelta
from astropy.coordinates import solar_system_ephemeris
from poliastro.util import time_range
from data_functs import *
from simbody import SimBody
from multiprocessing import Process
import threading

print(subprocess.run(["cp", "logs/sb_viewer.log", "logs/OLD_sb_viewer.log"]))
print(subprocess.run(["rm", "logs/sb_viewer.log"]))
print(subprocess.run(["touch","logs/sb_viewer.log",]))
logging.basicConfig(filename="logs/sb_viewer.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )


class SBViewer(scene.SceneCanvas):
    def __init__(self):
        self.INIT = False
        self.dat_store = setup_datastore()
        self.b_names = self.dat_store["BODY_NAMES"]
        self.body_data = self.dat_store["BODY_DATA"]
        self.skymap = self.dat_store["SKYMAP"]
        self.sim_params = self.dat_store["SYS_PARAMS"]
        self.w_last = 0
        # self.viz_dicts = {}
        # self.batches = {}
        # self.viz_tr = {}
        self.end_epoch = None
        self.d_epoch = None
        self.avg_d_epoch = None
        self._sys_epoch = Time(self.dat_store["DEF_EPOCH"],
                               format='jd',
                               scale='tdb',
                               )
        self.wclock = Timer(interval='auto',
                            connect=self.update_bodies,     # change this
                            iterations=-1,
                            )
        print("Target FPS:", 1 / self.wclock.interval)
        self.simbods = self.init_simbodies(body_names=self.b_names)
        self.sb_set = tuple(self.simbods.values())
        self.t_warp = 500000
        super(SBViewer, self).__init__(keys="interactive",
                                       size=(1024, 768),
                                       show=False,
                                       bgcolor='black',
                                       )
        self.unfreeze()
        self.view = self.central_widget.add_view()
        self.view.camera = scene.cameras.FlyCamera(fov=30)
        self.view.camera.scale_factor = 0.01
        self.view.camera.zoom_factor = 0.001
        self.b_states = None
        self.b_symbs = ['star', 'o', 'o', 'o', '+', 'o', 'o', 'o', 'o', 'o', 'o', ]
        self.bods_viz = None
        self.sys_viz = None
        self.freeze()
        self.sys_viz = self.init_sysviz()
        self.set_wide_ephems()
        self.skymap.parent = self.view.scene
        self.view.add(self.sys_viz)
        self.view.add(self.skymap)
        self.view.camera.set_range((-1e+09, 1e+09),
                                   (-1e+09, 1e+09),
                                   (-1e+09, 1e+09),
                                   )
        # self.init_vizuals()
        # self.run_cycle()
        # self.skymap.visible = False
        # functiontrace.trace()
        self.wclock.start()

    def run_cycle(self, event):        # this never gets called,,,
        self.update_bodies(event=None)
        for name in self.b_names:
            self.xform_vizuals(sb_name=name)

        if not self.INIT:
            self.INIT = True
            self.view.camera.center = (0, 0, 0)
            self.view.camera.set_range()
            self.view.camera.auto_roll = False
        else:
            self.update()

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
        for sb_name in self.b_names:
            sb = self.simbods[sb_name]
            sb.set_ephem(t_range=full_t_range)

        self.end_epoch = full_t_range[-1]
        print("END_EPOCH:", self.end_epoch)

    def init_sysviz(self):
        frame = scene.visuals.XYZAxis(parent=self.view.scene)
        # frame.transform = tr.STTransform(scale=(1e+08, 1e+08, 1e+08))
        self.bods_viz = Markers(edge_color=(0, 1, 0, 1))
        orb_vizz = Compound([Polygon(pos=self.simbods[name].o_track,
                                     border_color=self.simbods[name].base_color,
                                     triangulate=False)
                             for name in self.b_names])
        viz = Compound([frame, self.bods_viz, orb_vizz])
        viz.parent = self.view.scene

        return viz

    def update_bodies(self, event=None):
        if self.INIT:
            w_now = self.wclock.elapsed
            dt = w_now - self.w_last
            self.w_last = w_now
        else:
            w_now = 0
            dt = 0
            self.w_last = w_now - dt
            self.INIT = True

        d_epoch = TimeDelta(dt * u.s * self.t_warp)
        if self.avg_d_epoch is None:
            self.avg_d_epoch = d_epoch

        new_epoch = self._sys_epoch + d_epoch
        self.avg_d_epoch = (self.avg_d_epoch + d_epoch) / 2
        update_t = threading.Thread(target=self.do_updates,
                                    kwargs=dict(new_epoch=new_epoch)
                                    )
        update_t.start()
        update_t.join()

        self.b_states = np.array([self.simbods[name].state[0, :] for name in self.b_names])
        self.b_states[4] += self.simbods['Earth'].state[0, :]
        self.bods_viz.set_data(pos=self.b_states,
                               face_color=self.dat_store["COLOR_SET"],
                               edge_color=(0, 1, 0, .2),
                               symbol=self.b_symbs,
                               )
        if (self.end_epoch - new_epoch) < 2 * self.avg_d_epoch:
            logging.debug("RELOAD EPOCHS/EPHEM SETS...")
            self.set_wide_ephems(epoch=new_epoch)

        self._sys_epoch = new_epoch

        logging.info("AVG_dt: %s\n\t>>> NEW EPOCH: %s\n",
                     self.avg_d_epoch,
                     new_epoch.jd)
        # print("\n\t>>> NEW EPOCH:", new_epoch.jd)

    def init_simbodies(self, body_names=None):
        solar_system_ephemeris.set("jpl")
        sb_dict = {}
        for name in self.b_names:
            sb_dict.update({name: SimBody(body_name=name,
                                          epoch=self._sys_epoch,
                                          sim_param=self.sim_params,
                                          body_data=self.body_data[name],
                                          )})
        logging.info("\t>>> SimBody objects created....\n")
        return sb_dict
        # self.simbods = sb_dict
        # self.sb_list = list(sb_dict.values())

    def do_updates(self, new_epoch=None):
        for sb in self.simbods.values():
            sb.update_state(new_epoch)

    def init_vizuals(self):             # this never gets called,,,
        MT = tr.MatrixTransform
        skymap_tr = MT()
        skymap_tr.scale([8e+09, 8e+09, 8e+09])
        self.skymap.parent = self.view.scene
        self.view.add(self.skymap)
        for sb_name in self.b_names:
            logging.info("\tCollecting vizuals for %s", sb_name)
            self.batches.update({sb_name: Compound([])})
            self.viz_dicts.update({sb_name: get_viz_data(body_name=sb_name,
                                                         body_type=self.body_data[sb_name]["body_type"],
                                                         viz_names=self.body_data[sb_name]["viz_names"],
                                                         trk_color=self.body_data[sb_name]["body_color"],
                                                         texture=self.body_data[sb_name]["tex_data"],
                                                         )})

        for sb_name in self.b_names:
            [self.batches[sb_name].add_subvisual(self.viz_dicts[sb_name][viz_name])
                for viz_name in self.simbods[sb_name].viz_names]

            for viz_name in self.simbods[sb_name].viz_names:
                self.viz_dicts[sb_name][viz_name].parent = self.batches[sb_name]
                if sb_name == "Sun":
                    self.batches[sb_name].parent = self.view.scene
                elif sb_name == "Moon":
                    self.batches[sb_name].parent = self.batches["Earth"]
                else:
                    self.batches[sb_name].parent = self.batches["Sun"]

        for sb_name in self.b_names:
            self.simbods[sb_name].vizuals = self.viz_dicts[sb_name]
            self.view.add(self.batches[sb_name])

        if self.simbods[sb_name].type != "star":
            self.simbods[sb_name].vizuals["oscorbit"].pos = np.array(self.simbods[sb_name].track.xyz.transpose().value)

    def xform_vizuals(self, sb_name=None):          # this never gets called,,,
        logging.debug("%s vizuals used: %s", sb_name, self.simbods[sb_name].viz_names)
        self.set_viz_xform(sb_name=sb_name)
        for viz_name in self.simbods[sb_name].viz_names:
            self.apply_xforms2viz(sb_name=sb_name,
                                  viz_name=viz_name,
                                  viz_tr=self.viz_tr[sb_name][viz_name],
                                  )
            logging.debug("Applied xform to %s:%s\n\t\t\t\t>>>:<%s>...",
                          sb_name,
                          viz_name,
                          self.viz_tr[sb_name][viz_name],
                          )
        logging.debug("\tTransforms available: %s",
                      self.viz_tr[sb_name].keys(),
                      )

    def apply_xforms2viz(self, sb_name=None, viz_name=None, viz_tr=None):       # this never gets called,,,
        self.viz_dicts[sb_name][viz_name].transform = self.viz_tr[sb_name][viz_name]
        # self.view.camera.set_range()

    def set_viz_xform(self, sb_name=None):              # this never gets called,,,
        body_data = self.body_data[sb_name]
        sb = self.simbods[sb_name]
        R = body_data["r_set"][0]
        Rm = body_data["r_set"][1]
        Rp = body_data["r_set"][2]
        if sb_name == "Sun":
            R = 0.05 * R
            Rm = 0.05 * Rm
            Rp = 0.05 * Rp

        logging.debug("SimBody.set_transforms(" + str(sb_name) + ").")

        n_bods = len(self.dat_store["BODY_NAMES"])
        n = self.b_names.index(sb_name)
        th = 2 * math.pi * n / n_bods
        # print("THETA>>> ", th)
        r = np.array(sb.state[0])
        v = np.array(sb.state[1])
        ra, dec, W = sb.state[2]

        mag_r = np.linalg.norm(r)
        mag_v = np.linalg.norm(v)
        norm_r = r / mag_r
        norm_v = v / mag_v
        # print(sb.name, ": mag(r)=", mag_r)

        MT = tr.MatrixTransform
        tr_surface = MT()
        tr_surface.rotate(+W, sb.z_ax)
        tr_surface.rotate(90 - dec, sb.y_ax)
        tr_surface.rotate(ra, sb.z_ax)
        tr_surface.scale([R, R, Rp])
        tr_surface.translate(r)

        tr_nametag = MT()
        tr_nametag.translate([R * math.cos(th), R * math.sin(th), 0])

        viz_tr = {}
        if sb.type != "star":
            r_1 = sb._sb_parent.R_mean.value
            r_2 = Rm
            fact = 1 - (r_1 + r_2) / mag_r
            tr_r_vec = MT()
            tr_r_vec.scale([fact, ] * 3)
            # tr_r_vec.translate(-r)
            trns_vec = norm_r * r_1
            # print(type(trns_vec), trns_vec, r_1, norm_r)
            tr_r_vec.translate(trns_vec)

            tr_oscorb = MT()
            tr_oscorb.translate(-r)

            v_scale = [sb.v_mult, ] * 3
            tr_v_vec = MT()
            tr_v_vec.scale(v_scale)
            tr_v_vec.translate(r)
            tr_v_vec.translate(r_2 * norm_v)
            viz_tr.update({"radvec": tr_r_vec})
            viz_tr.update({"velvec": tr_v_vec})
            viz_tr.update({"oscorbit": tr_oscorb})

        tr_xyz = MT()
        tr_xyz.scale([sb.xyz_mult * R, ] * 3)

        viz_tr.update({"refframe": tr_xyz})
        viz_tr.update({"surface": tr_surface})
        viz_tr.update({"nametag": tr_nametag})

        self.viz_tr.update({sb_name: viz_tr})

    def run(self):
        self.wclock.start()
        self.show()
        app.run()

    def stop(self):
        app.quit()


def main():
    my_can = SBViewer()
    my_can.run()


if __name__ == "__main__":

    main()
