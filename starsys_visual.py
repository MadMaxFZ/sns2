# -*- coding: utf-8 -*-

from planet_visual import *
from data_functs import vec_type
from vispy.scene.visuals import *
import vispy.visuals.transforms as tr
import math

MIN_SYMB_SIZE = 5
MAX_SYMB_SIZE = 20
ST = tr.STTransform
MT = tr.MatrixTransform
SUN_COLOR = [253 / 255, 184 / 255, 19 / 255]
DEF_MARKS_INIT = dict(scaling=False,
                      alpha=1,
                      antialias=1,
                      spherical=False,
                      light_color=SUN_COLOR,
                      light_position=(0, 0, 0),
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


class SystemVizual(Compound):
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
            self._sb_symbols    = []
            self._symbol_sizes  = []
            self._bods_pos      = []
            self._sb_planets    = {}       # a dict of Planet visuals
            self._sb_tracks     = {}       # a dict of Polygon visuals
            self._sb_markers    = Markers(parent=self._skymap, **DEF_MARKS_INIT)  # a single instance of Markers
            self._system_viz    = self._setup_sysviz(sbs=sim_bods)
            super(SystemVizual, self).__init__([])
        else:
            print("Must provide a dictionary of SimBody objects...")
            exit(1)

    def abs_body_pos(self, name=None):
        if (name is not None) and (name in self._simbods.keys()):
            _pos = self._simbods[name].pos
            if self._simbods[name].body.parent is None:
                return _pos
            else:
                return _pos + self.abs_body_pos(name=self._simbods[name].body.parent.name)

    def _setup_sysviz(self, sbs=None):
        if sbs is not None:
            self._frame_viz = XYZAxis(parent=self._skymap)  # set parent in MainSimWindow ???
            self._frame_viz.transform = ST(scale=[1e+08, 1e+08, 1e+08])
            self._sb_markers.parent = self._skymap

            # generate Planet and Polygon visuals
            for sb_name, sb in self._simbods.items():
                self._sb_symbols.append(sb.body_symbol)
                self._sb_planets.update({sb_name: Planet(refbody=sb,
                                                         color=sb.base_color,
                                                         edge_color=sb.base_color,
                                                         texture=sb.texture,
                                                         parent=self._skymap,
                                                         )
                                         })
                if sb.body.parent is not None:
                    self._sb_tracks.update({sb_name: Polygon(pos=sb.o_track + self.abs_body_pos(name=sb.body.parent.name),
                                                             border_color=sb.base_color + np.array([0, 0, 0,
                                                                                                    sb.track_alpha]),
                                                             triangulate=False,
                                                             parent=self._skymap,
                                                             )
                                            })

            # now, go through and set the parents appropriately
            for sb_name, sb in self._simbods.items():
                if sb.body.parent is not None:
                    self._sb_planets[sb_name].parent = self._sb_planets[sb.body.parent.name]
                    self._sb_tracks[sb_name].parent = self._sb_planets[sb.body.parent.name]

            viz = Compound([self._skymap,
                            self._frame_viz,
                            self._sb_markers,
                            Compound(self._sb_tracks.values()),
                            Compound(self._sb_planets.values()),
                            ])
            viz.parent = self._mainview.scene
            return viz

        else:
            print("Must provide SimBody dictionary...")

    def update_sysviz(self):
        # collect positions of the bodies into an array
        self._bods_pos = []
        self._cam_rel_pos = []
        for sb_name, sb in self._simbods.items():
            _body_pos = self.abs_body_pos(name=sb_name) * sb.dist_unit
            self._bods_pos.append(_body_pos)
            self._sb_planets[sb_name].transform = ST(translate=_body_pos)
            self._cam_rel_pos.append(sb.rel2pos(pos=self._mainview.camera.center)['rel_pos'])

        edge_colors = []
        self._symbol_sizes = self.get_symb_sizes()      # update symbol sizes based upon FOV of body
        for sym_size in self._symbol_sizes:
            if (sym_size > MIN_SYMB_SIZE) and (sym_size < MAX_SYMB_SIZE):
                edge_colors.append((0, 1, 0, .6))
            else:
                edge_colors.append((1, 0, 0, .6))

        self._sb_markers.set_data(pos=np.array(self._bods_pos),
                                  size=self._symbol_sizes,
                                  face_color=np.array([sb.base_color + np.array([0, 0, 0, sb.track_alpha])
                                                       for sb in self._simbods.values()]),
                                  edge_color=np.array(edge_colors),
                                  symbol=self._sb_symbols,
                                  )
        logging.info("\nSYMBOL SIZES :\t%s", self._symbol_sizes)
        logging.info("\nCAM_REL_DIST :\n%s", [np.linalg.norm(rel_pos) for rel_pos in self._cam_rel_pos])

    def get_symb_sizes(self):
        # TODO: Rework this method to have only one loop!
        pix_diams = []
        for sb_name, sb in self._simbods.items():
            body_fov = sb.rel2pos(pos=self._cam.center)['fov']
            raw_diam = math.ceil(self._mainview.size[0] * body_fov / self._cam.fov)
            self._sb_planets[sb_name].visible = False
            if raw_diam < MIN_SYMB_SIZE:
                pix_diam = MIN_SYMB_SIZE
            elif raw_diam < MAX_SYMB_SIZE:
                pix_diam = raw_diam
            else:
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

