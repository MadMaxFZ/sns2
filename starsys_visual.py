# -*- coding: utf-8 -*-

import math
import logging
import numpy as np
import vispy.visuals.transforms as tr
from vispy.visuals import CompoundVisual
from vispy.scene.visuals import (create_visual_node,
                                 Markers, XYZAxis,
                                 Compound, Polygon)
from starsys_data import vec_type
from body_visual import Planet
from skymap import SkyMap
from simbody import SimBody

# these quantities can be served from DATASTORE class
MIN_SYMB_SIZE = 5
MAX_SYMB_SIZE = 30
ST = tr.STTransform
MT = tr.MatrixTransform
SUN_COLOR = tuple(np.array([253, 184, 19]) / 255)
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
    def __init__(self, sim_bods=None, system_view=None):
        if self._check_simbods(sbs=sim_bods):
            self._simbods       = sim_bods
            self._init_state    = 0
            self._mainview      = system_view
            self._cam           = self._mainview.camera
            self._cam_rel_pos   = np.zeros((len(self._simbods.keys()),), dtype=vec_type)
            self._cam_rel_vel   = None  # there is no readily available velocity for camera
            self._skymap        = SkyMap(edge_color=(0, 0, 1, 0.4))
            self._bods_pos      = [sb.pos2primary() for sb in self._simbods.values()]
            self._sb_symbols    = [sb.body_symbol for sb in self._simbods.values()]
            self._symbol_sizes  = []
            self._sb_planets    = {}       # a dict of Planet visuals
            self._sb_tracks     = {}       # a dict of Polygon visuals
            self._plnt_markers = Markers(parent=self._skymap, **DEF_MARKS_INIT)  # a single instance of Markers
            self._cntr_markers = Markers(parent=self._skymap,
                                         symbol='+',
                                         size=[MIN_SYMB_SIZE - 2 for sb in self._simbods.values()],
                                         **DEF_MARKS_INIT)  # another instance of Markers
            # self._system_viz    = self._setup_sysviz(sbs=sim_bods)
            super(StarSystemVisual, self).__init__(subvisuals=self._setup_sysviz(sbs=sim_bods))
        else:
            print("Must provide a dictionary of SimBody objects...")
            exit(1)

    def _setup_sysviz(self, sbs=None):
        # TODO: generate/assign visuals here to build SystemVizual instance
        if sbs is not None:
            self._frame_viz = XYZAxis(parent=self._skymap)  # set parent in MainSimWindow ???
            self._frame_viz.transform = ST(scale=[1e+08, 1e+08, 1e+08])
            # self._plnt_markers.parent = self._skymap
            self._cntr_markers.set_data(symbol=['+' for sb in sbs.values()])
            self._sb_symbols = [sb.body_symbol for sb in sbs.values()]
            for sb_name, sb in sbs.items():
                self._sb_planets.update({sb_name: Planet(body_ref=sb.body,
                                                         color=sb.base_color,
                                                         edge_color=sb.base_color,
                                                         texture=sb.texture,
                                                         parent=self._skymap,
                                                         visible=False,
                                                         )
                                         })
                if sb.sb_parent is not None:
                    # print(sb.base_color, sb.base_color.shape)
                    self._sb_tracks.update({sb_name: Polygon(pos=sb.o_track + sbs[sb.sb_parent.name].pos,
                                                             border_color=np.array(list(sb.base_color) + [0,]) +
                                                                          np.array([0, 0, 0, sb.track_alpha]),
                                                             triangulate=False,
                                                             parent=self._skymap,
                                                             )
                                            })
            for sb_name, sb in sbs.items():
                if sb.body.parent is not None:
                    self._sb_planets[sb_name].parent = self._sb_planets[sb.body.parent.name]
                    self._sb_tracks[sb_name].parent = self._sb_planets[sb.body.parent.name]

            subvisuals = [self._skymap,
                          self._frame_viz,
                          self._plnt_markers,
                          self._cntr_markers,
                          Compound(self._sb_tracks.values()),
                          Compound(self._sb_planets.values()),
                          ]
            return subvisuals
        else:# list of body names available in sim
            print("Must provide SimBody dictionary...")

    def update_sysviz(self):
        _bods_pos = {}
        self._bods_pos = []
        for sb_name, sb in self._simbods.items():
            # collect positions of the bodies into an array
            _bods_pos.update({sb_name: sb.pos2primary()})
            # self._sb_planets[sb_name].transform = ST(translate=_bods_pos[sb_name])
            # if sb.body.parent is not None:
            #     self._sb_tracks[sb_name].transform = ST(translate=_bods_pos[sb.body.parent.name])

        self._bods_pos = np.array(list(_bods_pos.values()))
        # collect the body positions relative to the camera location
        self._cam_rel_pos = [sb.rel2pos(pos=self._mainview.camera.center)['rel_pos']
                             for sb in self._simbods.values()]

        self._symbol_sizes = []                 # update symbol sizes based upon FOV of body
        for sb_name, sb in self._simbods.items():
            body_fov = sb.rel2pos(pos=self._cam.center)['fov']
            pix_diam = 0
            raw_diam = math.ceil(self._mainview.size[0] * body_fov / self._cam.fov)
            self._sb_planets[sb_name].visible = False
            if raw_diam < MIN_SYMB_SIZE:
                pix_diam = MIN_SYMB_SIZE
            elif raw_diam < MAX_SYMB_SIZE:
                pix_diam = raw_diam
            elif raw_diam >= MAX_SYMB_SIZE:
                pix_diam = 0
                self._sb_planets[sb_name].visible = True

            self._symbol_sizes.append(pix_diam)

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

    def get_symb_sizes(self):
        # TODO: Rework this method to have only one loop
        pix_diams = []
        for sb_name, sb in self._simbods.items():
            body_fov = sb.rel2pos(pos=self._cam.center)['fov']
            pix_diam = 0
            raw_diam = math.ceil(self._mainview.size[0] * body_fov / self._cam.fov)
            self._sb_planets[sb_name].visible = False
            if raw_diam < MIN_SYMB_SIZE:
                pix_diam = MIN_SYMB_SIZE
            elif raw_diam < MAX_SYMB_SIZE:
                pix_diam = raw_diam
            elif raw_diam >= MAX_SYMB_SIZE:
                pix_diam = 0
                self._sb_planets[sb_name].visible = True

            pix_diams.append(pix_diam)

        return np.array(pix_diams)

    @staticmethod
    def _check_simbods(sbs=None):
        """ Make sure that the simbods argument actually consists of
            a dictionary of SimBody objects.
        """
        check = True
        if sbs is None:
            print("Must provide something... FAILED")
            check = False
        elif type(sbs) is not dict:
            print("Must provide SimBody dictionary... FAILED")
            check = False
        else:
            for key, val in sbs.items():
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