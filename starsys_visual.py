# -*- coding: utf-8 -*-

import sys
import math
import logging
import numpy as np
import vispy.visuals.transforms as tr
from vispy.visuals import CompoundVisual
from vispy.scene.visuals import (create_visual_node,
                                 Markers, XYZAxis,
                                 Compound, Polygon)
from starsys_data import vec_type
from sysbody_visual import Planet
from sys_skymap import SkyMap
from sysbody_model import SimBody

# these quantities can be served from DATASTORE class
MIN_SYMB_SIZE = 5
MAX_SYMB_SIZE = 30
ST = tr.STTransform
MT = tr.MatrixTransform
SUN_COLOR = tuple(np.array([253, 184, 19]) / 256)
DEF_MARKS_INIT = dict(scaling=False,
                      alpha=1,
                      antialias=1,
                      spherical=True,
                      light_color=SUN_COLOR,
                      light_position=(0.01, 0.01, 0.01),
                      light_ambient=0.3,
                      )
DEF_MARKS_DATA = dict(pos=None,
                      size=None,
                      edge_width=None,
                      edge_width_rel=None,
                      edge_color=None,
                      face_color=None,
                      symbol=None,
                      )


class StarSystemVisual(CompoundVisual):
    """
    """
    def __init__(self, system_model=None, system_view=None):
        if self._check_simbods(model=system_model):
            self._simbods       = system_model.simbodies
            self._init_state    = 0
            self._mainview      = system_view
            self._cam           = self._mainview.camera
            self._cam_rel_pos   = np.zeros((len(self._simbods.keys()),), dtype=vec_type)
            self._cam_rel_vel   = None  # there is no readily available velocity for camera
            self._skymap        = SkyMap(edge_color=(0, 0, 1, 0.4))
            self._bods_pos      = [sb.pos2primary for sb in self._simbods.values()]
            self._sb_symbols    = [sb.mark for sb in self._simbods.values()]
            self._symbol_sizes  = []
            self._sb_planets    = {}       # a dict of Planet visuals
            self._sb_tracks     = {}       # a dict of Polygon visuals
            self._plnt_markers = Markers(parent=self._skymap, **DEF_MARKS_INIT)  # a single instance of Markers
            self._cntr_markers = Markers(parent=self._skymap,
                                         symbol='+',
                                         size=[MIN_SYMB_SIZE - 2 for sb in self._simbods.values()],
                                         **DEF_MARKS_INIT)  # another instance of Markers
            # self._system_viz    = self._setup_sysviz(sbs=sim_bods)
            super(StarSystemVisual, self).__init__(subvisuals=self._setup_sysviz(sbs=system_model.simbodies))
        else:
            print("Must provide a dictionary of SimBody objects...")
            sys.exit(1)

    def _setup_sysviz(self, sbs=None):
        # TODO: generate/assign visuals here to build SystemVizual instance
        if sbs is not None:
            self._frame_viz = XYZAxis(parent=self._mainview.scene)  # set parent in MainSimWindow ???
            self._frame_viz.transform = MT()
            self._frame_viz.transform.scale((1e+08, 1e+08, 1e+08))
            self._plnt_markers.parent = self._mainview.scene
            self._cntr_markers.set_data(symbol=['+' for sb in sbs.values()])
            self._sb_symbols = [sb.mark for sb in sbs.values()]
            for sb_name, sb in sbs.items():
                plnt = Planet(sb_ref=sb,
                              body=sb.body,
                              color=sb.base_color,
                              edge_color=sb.base_color,
                              texture=sb.texture,
                              parent=self._mainview.scene,
                              visible=False,
                              method='oblate',
                              )
                plnt.transform = MT()
                self._sb_planets.update({sb_name: plnt})
                if sb.sb_parent is not None:
                    # print(f"Body: %s / Track: %s / Parent.pos: %s", sb.name, sb.track, sb.sb_parent.pos)
                    poly = Polygon(pos=sb.track,  # + sb.sb_parent.pos,
                                   border_color=np.array(list(sb.base_color) + [0, ]) +
                                                np.array([0, 0, 0, sb.track_alpha]),
                                   triangulate=False,
                                   parent=self._mainview.scene,
                                   )
                    poly.transform = MT()
                    self._sb_tracks.update({sb_name: poly})
            for sb_name, sb in sbs.items():
                if sb.body.parent is not None:
                    sb.sb_parent = self._sb_planets[sb.body.parent.name]
                    self._sb_planets[sb_name].parent = self._mainview.scene
                    self._sb_planets[sb_name].transform.translate(sb.pos2bary + np.array([0, 0, 0, 0]))
                    self._sb_tracks[sb_name].parent = self._mainview.scene
                    self._sb_tracks[sb_name].transform.translate(sb.sb_parent.pos2bary + np.array([0, 0, 0, 0]))

            subvisuals = [self._skymap,
                          self._frame_viz,
                          self._plnt_markers,
                          self._cntr_markers,
                          Compound(self._sb_tracks.values()),
                          Compound(self._sb_planets.values()),
                          ]
            return subvisuals
        else:  # list of body names available in sim
            print("Must provide SimBody dictionary...")

    def update_sysviz(self):
        self._symbol_sizes = self.get_symb_sizes()  # update symbol sizes based upon FOV of body
        _bods_pos = []
        for sb_name, sb in self._simbods.items():
            # print(sb.pos2primary - sb.pos)
            if self._sb_planets[sb_name].visible:
                sb_pos = np.zeros((4,))
                sb_pos[0:3] = sb.pos2bary
                _bods_pos.append(sb_pos[0:3])
                xform = self._sb_planets[sb_name].transform
                xform.reset()
                xform.rotate(sb.state[2, 2], sb.z_ax)
                xform.rotate(np.pi * sb.state[2, 1] / 2, sb.y_ax)
                xform.rotate(sb.state[2, 0], sb.z_ax)
                xform.translate(sb_pos)
                self._sb_planets[sb_name].transform = xform
                # if self._sb_planets[sb_name].transform == xform:
                #     print("SAME")
                # else:
                #     print("DIFFERENT")
                #     self._sb_planets[sb_name].transform = xform

        self._bods_pos = np.array(_bods_pos)
        # collect the body positions relative to the camera location
        self._cam_rel_pos = [sb.rel2pos(pos=self._mainview.camera.center)['rel_pos']
                             for sb in self._simbods.values()]

        self._plnt_markers.set_data(pos=self._bods_pos,
                                    face_color=[np.array(list(sb.base_color) + [0,]) +
                                                np.array([0, 0, 0, sb.track_alpha])
                                                for sb in self._simbods.values()
                                                ],
                                    edge_color=[1, 0, 0, .6],
                                    size=self._symbol_sizes,
                                    symbol=self._sb_symbols,
                                    )
        self._cntr_markers.set_data(pos=self._bods_pos,
                                    edge_color=[0, 1, 0, .6],
                                    size=MIN_SYMB_SIZE,
                                    symbol=['diamond' for sb in self._simbods.values()],
                                    )
        logging.info("\nSYMBOL SIZES :\t%s", self._symbol_sizes)
        logging.info("\nCAM_REL_DIST :\n%s", [np.linalg.norm(rel_pos) for rel_pos in self._cam_rel_pos])

    def get_symb_sizes(self, camera=None):
        if camera is None:
            camera = self._cam

        pix_diams = []
        self._bods_pos = []
        for sb_name, sb in self._simbods.items():
            self._bods_pos.append(sb.pos2bary)
            # if sb.type not in ['star', 'planet']:
            #     self._bods_pos[-1] += sb.sb_parent.pos

            body_fov = sb.rel2pos(pos=camera.center)['fov']
            pix_diam = 0
            raw_diam = math.ceil(self._mainview.size[0] * body_fov / self._cam.fov)

            if raw_diam < MIN_SYMB_SIZE:
                pix_diam = MIN_SYMB_SIZE
            elif raw_diam < MAX_SYMB_SIZE:
                pix_diam = raw_diam
            elif raw_diam >= MAX_SYMB_SIZE:
                pix_diam = 0
                self._sb_planets[sb_name].visible = True
            else:
                self._sb_planets[sb_name].visible = False

            pix_diams.append(pix_diam)

        return np.array(pix_diams)

    @staticmethod
    def _check_simbods(model=None):
        """ Make sure that the simbods argument actually consists of
            a dictionary of SimBody objects.
        """
        check = True
        if model is None:
            print("Must provide something... FAILED")
            check = False
        elif type(model.simbodies) is not dict:
            print("Must provide SimBody dictionary... FAILED")
            check = False
        else:
            for key, val in model.simbodies.items():
                if type(val) is not SimBody:
                    print(key, "is NOT a SimBody... FAILED.")
                    check = False

        return check

    @property
    def skymap(self):
        if self._skymap is None:
            print("No SkyMap defined...")
        else:
            return self._skymap

    @skymap.setter
    def skymap(self, new_skymap=None):
        if type(new_skymap) is SkyMap:
            self._skymap = new_skymap
        else:
            print("Must provide a SkyMap object...")


StarSystem = create_visual_node(StarSystemVisual)


def main():
    print("MAIN FUNCTION...")


if __name__ == "__main__":
    main()