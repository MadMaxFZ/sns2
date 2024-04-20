# -*- coding: utf-8 -*-
# x
import sys
import math
import logging
import numpy as np
import astropy.units as u
import vispy.visuals.transforms as trx
from vispy.color import *
from vispy.visuals import CompoundVisual
from vispy.scene.visuals import (create_visual_node,
                                 Markers, XYZAxis,
                                 Compound, Polygon)
# from starsys_data import vec_type
from simbody_visual import Planet
from skymap_visual import SkyMap
from simbody_model import SimBody, MIN_FOV
from PyQt5.QtCore import pyqtSlot
from camera_dict import CameraSet

# these quantities can be served from DATASTORE class
MIN_SYMB_SIZE = 5
MAX_SYMB_SIZE = 30
EDGE_COLOR = Color('red')
EDGE_COLOR.alpha = 0.6
ST = trx.STTransform
MT = trx.MatrixTransform
SUN_COLOR = Color(tuple(np.array([253, 184, 19]) / 256))

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
                      edge_color=EDGE_COLOR,
                      face_color=SUN_COLOR,
                      symbol=None,
                      )

_pm_e_alpha = 0.6
_cm_e_alpha = 0.6
_SCALE_FACTOR = np.array([50.0,] * 3)


def from_pos(pos, tgt_pos, tgt_R):
    rel_2pos = (pos - tgt_pos)
    dist = np.linalg.norm(rel_2pos)
    dist_unit = tgt_R / tgt_R.value
    if dist < 1e-09:
        dist = 0.0 * dist_unit
        rel_pos = np.zeros((3,), dtype=type(tgt_pos))
        fov = MIN_FOV
    else:
        fov = np.float64(1.0 * math.atan(tgt_R.value / dist))

    return {"rel_pos": rel_2pos * dist_unit,
            "dist": dist * dist_unit,
            "fov": fov,
            }


class StarSystemVisuals:
    """
    """
    def __init__(self, body_names=None):
        """
        Constructs a collection of Visuals that represent entities in the system model,
        updating periodically based upon the quantities propagating in the model.
        TODO:   Remove the model from this module. The data required here must now
                be obtained using Signals to the QThread that the model will be running within.
        Parameters
        ----------
        body_names   : list of str
            list of SimBody names to make visuals for
        """
        self._IS_INITIALIZED = False
        self._body_names   = []
        self._bods_pos     = []
        self._scene        = None
        self._skymap       = None
        self._planets      = {}      # a dict of Planet visuals
        self._tracks       = {}      # a dict of Polygon visuals
        self._symbols      = []
        self._symbol_sizes = []
        self._view         = None
        self._curr_camera  = None
        self._pos_rel2cam  = None
        self._frame_viz    = None
        self._plnt_markers = None
        self._cntr_markers = None
        self._subvizz      = None
        self._agg_cache    = None
        self._vizz_data    = None
        self._body_radsets = None
        self.dist_unit     = u.km       # TODO: resolve any confusion with the fucking units...!

        if body_names:
            self._body_names   = [n for n in body_names]
        self._body_count   = len(self._body_names)
        self._bods_pos     = []

    '''--------------------------- END StarSystemVisuals.__init__() -----------------------------------------'''

    def generate_visuals(self, view,  agg_data):
        """
        Parameters
        ----------
        view        :  View object
                            The view in which the visuals are to be rendered.
        agg_data    :  dict
                            The data to be used for generating the visuals.

        Returns
        -------
        None            : No return value, however all of the visuals for the sim rendering are
                          created here, collected together and then added to the scene.
        """
        self._agg_cache = agg_data
        self._view = view
        self._scene = self._view.scene
        self._curr_camera = self._view.camera
        self._skymap = SkyMap(parent=self._scene)
        self._frame_viz = XYZAxis(parent=self._scene)  # set parent in MainSimWindow ???
        self._frame_viz.transform = MT()
        self._frame_viz.transform.scale((1e+08, 1e+08, 1e+08))
        self._bods_pos = list(self._agg_cache['pos'].values())

        for name in self._body_names:
            self._generate_planet_viz(body_name=name)
            print(f'Planet Visual for {name} created...')
            if name != self._agg_cache['is_primary']:
                self._generate_trajct_viz(body_name=name)
                print(f'Trajectory Visual for {name} created...')

        self._generate_marker_viz()
        self._subvizz = dict(sk_map=self._skymap,
                             r_fram=self._frame_viz,
                             p_mrks=self._plnt_markers,
                             c_mrks=self._cntr_markers,
                             tracks=self._tracks,
                             surfcs=self._planets,
                             )
        self._upload2view()

    def _generate_planet_viz(self, body_name):
        """ Generate Planet visual object for each SimBody
        """
        viz_dat = {}
        [viz_dat.update({k: v[body_name]}) for k, v in self._agg_cache.items()]     # if list(v.keys())[0] == body_name]
        plnt = Planet(body_name=body_name,
                      rows=18,
                      color=Color((1, 1, 1, self._agg_cache['body_alpha'][body_name])),
                      edge_color=Color((0, 0, 0, 0)),  # sb.base_color,
                      parent=self._scene,
                      visible=True,
                      method='oblate',
                      vizz_data=viz_dat,
                      body_radset=self._agg_cache['radius'][body_name]
                      )
        plnt.transform = trx.MatrixTransform()  # np.eye(4, 4, dtype=np.float64)
        self._planets.update({body_name: plnt})

    def _generate_trajct_viz(self, body_name):
        """ Generate Polygon visual object for each SimBody orbit
        """
        t_color = Color(self._agg_cache['body_color'][body_name])
        t_color.alpha = self._agg_cache['track_alpha'][body_name]
        poly = Polygon(pos=self._agg_cache['track_data'][body_name],
                       border_color=t_color,
                       triangulate=False,
                       parent=self._scene,
                       )
        poly.transform = trx.MatrixTransform()  # np.eye(4, 4, dtype=np.float64)
        self._tracks.update({body_name: poly})

    def _generate_marker_viz(self):
        # put init of markers into a method
        self._symbols = [pl.mark for pl in self._planets.values()]
        self._plnt_markers = Markers(parent=self._scene, **DEF_MARKS_INIT)  # a single instance of Markers
        self._cntr_markers = Markers(parent=self._scene,
                                     symbol=['+' for _ in range(self._body_count)],
                                     size=[(MIN_SYMB_SIZE - 2) for _ in range(self._body_count)],
                                     **DEF_MARKS_INIT)  # another instance of Markers
        # self._plnt_markers.parent = self._mainview.scene
        self._cntr_markers.set_data(symbol=['+' for _ in range(self._body_count)])

    def _upload2view(self):
        for k, v in self._subvizz.items():
            if "_" in k:
                print(k)
                self._scene.parent.add(v)
            else:
                [self._scene.parent.add(t) for t in v.values()]
        self._IS_INITIALIZED = True

    @pyqtSlot(dict)
    def update_vizz(self, agg_data):
        """
            Collects needed fields from model, calculates transforms and applies them to the visuals
        Returns
        -------
        Has no return value, but updates the transforms for the Planet and Polygon visuals,
        also, updates the positions and sizes of the Markers icons.
        """
        self._symbol_sizes = self.get_symb_sizes()  # update symbol sizes based upon FOV of body
        _p_face_colors = []
        _c_face_colors = []
        _edge_colors = []
        self._agg_cache = agg_data
        self._bods_pos = list(self._agg_cache['pos'].values())
        """
                TODO:: Fix the fact that self._agg_cache[][] is NOT getting updated with sys_epoch!!!
        """
        for sb_name in self._body_names:                                                    # <--
            x_ax = self._agg_cache['axes'][sb_name][0]
            y_ax = self._agg_cache['axes'][sb_name][1]
            z_ax = self._agg_cache['axes'][sb_name][2]
            RA   = self._agg_cache['rot'][sb_name][0]
            DEC  = self._agg_cache['rot'][sb_name][1]
            W    = self._agg_cache['rot'][sb_name][2]
            pos  = self._agg_cache['pos'][sb_name]
            parent = self._agg_cache['parent_name'][sb_name]
            is_primary = self._agg_cache['is_primary'][sb_name]

            if self._planets[sb_name].visible:
                xform = self._planets[sb_name].transform
                xform.reset()
                xform.rotate(W * np.pi / 180, x_ax)
                xform.rotate(DEC * np.pi / 180, y_ax)
                xform.rotate(RA * np.pi / 180, z_ax)
                # if not is_primary:
                #     xform.scale(_SCALE_FACTOR)

                xform.translate(pos.value)
                self._planets[sb_name].transform = xform

            if not is_primary:
                self._tracks[sb_name].transform.reset()
                self._tracks[sb_name].transform.translate(self._agg_cache['pos'][parent].value)

            _pf_clr = Color(self._agg_cache['body_color'][sb_name])
            _pf_clr.alpha = self._agg_cache['body_alpha'][sb_name]
            _cf_clr = _pf_clr
            _p_face_colors.append(_pf_clr)
            _c_face_colors.append(_cf_clr)

        self._plnt_markers.set_data(pos=np.array(self._bods_pos),
                                    face_color=ColorArray(_p_face_colors),
                                    edge_color=Color([1, 0, 0, _pm_e_alpha]),
                                    size=self._symbol_sizes,
                                    symbol=self._symbols,
                                    )
        self._cntr_markers.set_data(pos=np.array(self._bods_pos),
                                    face_color=ColorArray(_c_face_colors),
                                    edge_color=[0, 1, 0, _cm_e_alpha],
                                    size=MIN_SYMB_SIZE,
                                    symbol=['diamond' for _ in range(self._body_count)],                  # <--
                                    )
        self._scene.update()
        logging.info("\nSYMBOL SIZES :\t%s", self._symbol_sizes)
        # logging.info("\nCAM_REL_DIST :\n%s", [np.linalg.norm(rel_pos) for rel_pos in self._pos_rel2cam])

    def get_symb_sizes(self, obs_cam=None):
        """
            Calculates the s=ize in pixels at which a SimBody will appear in the view from
            the perspective of a specified camera.
        Parameters
        ----------
        obs_cam :  A Camera object from which the apparent sizes are measured

        Returns
        -------
        An np.array containing a pixel width for each SimBody

        TODO: instead of only symbol sizes, include face and edge color, etc.
                  Probably rename this method to 'get_mark_data(self, from_cam=None)'
        """
        if not obs_cam:
            obs_cam = self._curr_camera

        symb_sizes = []
        sb_name: str
        for sb_name in self._body_names:                                                       # <--
            body_fov = from_pos(obs_cam.center,
                                self._agg_cache['pos'][sb_name].value,
                                self._agg_cache['radius'][sb_name][0],
                                )['fov']
            pix_diam = 0
            raw_diam = math.ceil(self._scene.parent.size[0] * body_fov / obs_cam.fov)                # <--

            if raw_diam < MIN_SYMB_SIZE:
                pix_diam = MIN_SYMB_SIZE
            elif raw_diam < MAX_SYMB_SIZE:
                pix_diam = raw_diam
            elif raw_diam >= MAX_SYMB_SIZE:
                pix_diam = 0
                self._planets[sb_name].visible = True
            else:
                self._planets[sb_name].visible = False

            symb_sizes.append(pix_diam)

        return np.array(symb_sizes)

    @staticmethod
    def _check_simbods(simbods=None):
        """ Make sure that the simbods argument actually consists of
            a dictionary of SimBody objects.
        """
        check = True
        if simbods is None:
            print("Must provide a SimBody dict... FAILED")
            check = False
        elif type(simbods) is not dict:
            print("must provide a dictionary of SimBody objects... FAILED")
            check = False
        else:
            for key, val in simbods.items():
                if type(val) is not SimBody:
                    print(key, "is NOT a SimBody... FAILED.")
                    check = False

        return check

    @property
    def bods_pos(self):
        return self._bods_pos

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

    @property
    def planets(self, name=None):
        if name:
            return self._planets[name]
        else:
            return self._planets

    @property
    def vizz_bounds(self):
        outmost = np.max(np.linalg.norm(self.bods_pos)) / 2
        rng = (-outmost, outmost)
        return rng


if __name__ == "__main__":

    def main():
        print("MAIN FUNCTION...")

    main()
