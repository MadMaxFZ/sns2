# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
# Modified by Max S. Whitten in order to address the "stripe" glitch
import os
import sys

import numpy as np
import logging
# import vispy.visuals.transforms as tr
from astropy import units as u
from vispy.visuals import CompoundVisual
from vispy.visuals.mesh import MeshVisual
from vispy.visuals.filters.mesh import TextureFilter
from vispy.visuals import transforms as trx
from vispy.scene.visuals import create_visual_node
from starsys_model import SimBody
from starsys_data import DEF_TEX_FNAME, SystemDataStore, _latitude, _oblate_sphere, get_texture_data

logging.basicConfig(filename="logs/sns_defs.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )


class PlanetVisual(CompoundVisual):
    """ Visual that displays an oblate sphere with a texture,
        representing a celestial body surface.

    Parameters
    ----------
    radius : float
        The size of the sphere.
    cols : int
        Number of cols that make up the sphere mesh
        (for method='latitude').
    rows : int
        Number of rows that make up the sphere mesh
        (for method='latitude').
    method : str
        Method for generating sphere. Accepts 'latitude' for
        latitude-longitude, 'ico' for icosahedron, and 'cube'
        for cube based tessellation.
    vertex_colors : ndarray
        Same as for `MeshVisual` class.
        See `create_sphere` for vertex ordering.
    face_colors : ndarray
        Same as for `MeshVisual` class.
        See `create_sphere` for vertex ordering.
    color : Color
        The `Color` to use when drawing the sphere faces.
    edge_color : tuple or Color
        The `Color` to use when drawing the sphere edges. If `None`, then no
        sphere edges are drawn.
    shading : str | None
        Shading to use.
    """

    def __init__(self, body_name='Earth', body=None, radius=1.0, rows=10, cols=None, offset=False,
                 vertex_colors=None, face_colors=None,
                 color=(1, 1, 1, 1), edge_color=(0, 0, 1, 0.2),
                 shading=None, texture=None, method='oblate', **kwargs):

        super(PlanetVisual, self).__init__([])
        self.unfreeze()
        self._radii = np.zeros((3,),dtype=np.float64)
        self._pos = np.zeros((3,), dtype=np.float64)
        self._sb_ref = SimBody(body_name=body_name)
        if self._sb_ref is not None and type(self._sb_ref) == SimBody:
            # self.pos = self._sb_ref.pos
            self._texture_data = self._sb_ref.texture
            if body is None:
                body = self._sb_ref.body
            if body.R_mean.value != 0:
                self._radii = np.array([body.R.value,
                                        body.R_mean.value,
                                        body.R_polar.value])
            else:                             # some have R only
                self._radii = np.array([body.R.value,
                                        body.R.value,
                                        body.R.value])

        else:           # no SimBody provided
            self._radii = [1.0, 1.0, 1.0] * u.km  # default to 1.0
            self._texture_data = None

        if cols is None:        # auto set cols to 2 * rows
            cols = rows * 2

        if method == 'latitude':
            radius = self._radii[0]
            self._mesh_data = _latitude(rows, cols, radius, offset)
            # print("Using 'latitude' method...")
        else:
            radius = self._radii
            self._mesh_data = _oblate_sphere(rows, cols, radius, offset)
            # print("Using 'oblate' method...")

        self._mesh = MeshVisual(vertices=self._mesh_data.get_vertices(),
                                faces=self._mesh_data.get_faces(),
                                vertex_colors=vertex_colors,
                                face_colors=face_colors,
                                color=color,
                                shading=shading)
        if self._texture_data is not None:
            self._tex_coords = np.empty((rows + 1, cols + 1, 2), dtype=np.float32)
            for row in np.arange(rows + 1):
                for col in np.arange(cols + 1):
                    self._tex_coords[row, col] = [row / rows, col / cols]

            self._tex_coords = self._tex_coords.reshape((rows + 1) * (cols + 1), 2)
            logging.info("TEXTURE_COORDS: %s", self._tex_coords)
            self._filter = TextureFilter(texture=self.texture,
                                         texcoords=self._tex_coords,
                                         enabled=True,
                                         )
            self._mesh.attach(self._filter)

        if np.array(edge_color).any():
            self._border = MeshVisual(vertices=self._mesh_data.get_vertices(),
                                      faces=self._mesh_data.get_edges(),
                                      color=edge_color, mode='lines')
        else:
            self._border = MeshVisual()

        self.freeze()
        self._mesh.set_gl_state(polygon_offset_fill=True,
                                polygon_offset=(1, 1),
                                depth_test=True)
        [self.add_subvisual(v) for v in [self._mesh, self._border]]

    @property
    def mesh(self):
        """The vispy.visuals.MeshVisual that used to fil in."""
        return self._mesh

    @mesh.setter
    def mesh(self, new_mesh):
        self._mesh = new_mesh

    @property
    def border(self):
        """The vispy.visuals.MeshVisual that used to draw the border."""
        return self._border

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, new_pos):
        if new_pos is not None:
            self._pos = new_pos
            self.transform = trx.STTransform().as_matrix()
            self.transform.translate(self._pos)
            self.update()

    @property
    def texture(self):
        return self._texture_data

    @texture.setter
    def texture(self, new_texture=None):
        self._texture_data = new_texture
        self._filter = TextureFilter(self._texture_data,
                                     self._tex_coords,
                                     enabled=True,
                                     )
        self._mesh.attach(self._filter)
        self.update()

    # @property
    # def visible(self):
    #     return self._visible
    #
    # @visible.setter
    # def visible(self, new_visible=False):
    #     self._visible = new_visible


Planet = create_visual_node(PlanetVisual)


def main():
    from vispy import app
    from vispy.app.timer import Timer
    from vispy.scene import SceneCanvas, ArcballCamera, FlyCamera
    from sys_skymap import SkyMap
    import vispy.visuals.transforms as trx

    print("BodyViz test code...")
    win = SceneCanvas(title="BodyViz Test",
                      keys="interactive",
                      bgcolor='black',
                      )
    view = win.central_widget.add_view()
    view.camera = FlyCamera()
    skymap = SkyMap(edge_color=(0, 0, 1, 0.3),
                    color=(1, 1, 1, 1),
                    parent=view.scene)
    # view.add(skymap)
    skymap.visible = False
    bod = Planet(rows=18,
                 body_name='Earth',
                 method='latitude',
                 parent=view.scene,
                 visible=True,
                 )
    # md_lat = _latitude()
    # md_obl = _oblate_sphere()
    # [print(i) for i in dir(md_obl)]
    bod.transform = trx.MatrixTransform()
    bod_trx = bod.transform
    view.add(bod)
    view.camera.set_range()
    rps = 0.5

    def on_timer(event=None):
        bod.transform.reset()
        bod.transform.rotate(bod_timer.elapsed * 2 * np.pi * rps, (0, 0, 1))
        # bod.transform = bod_trx
        logging.debug("transform = %s", bod.transform)

    bod_timer = Timer(interval=0.1,
                      connect=on_timer,
                      iterations=-1,
                      start=True,
                      # app=win.app,
                      )
    # on_timer()
    win.show()
    win.app.run()


if __name__ == "__main__":

    # for rot in range(3600):
    #     bod.transform.rotate(rot * np.pi / 1800, [0, 0, 1])
    main()


