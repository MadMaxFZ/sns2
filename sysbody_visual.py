# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
# Modified by Max S. Whitten in order to address the "stripe" glitch
# x
import os
import sys

import numpy as np
import logging
from astropy import units as u
from PIL import Image
from vispy.visuals import CompoundVisual
from vispy.visuals.mesh import MeshVisual
from vispy.visuals.filters.mesh import TextureFilter
from vispy.scene.visuals import create_visual_node
from vispy.geometry.meshdata import MeshData
from starsys_model import SimBody
from starsys_data import DEF_TEX_FNAME, sys_data, _latitude, _oblate_sphere, get_texture_data

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

    def __init__(self, body_name='Earth', sim_body=None,
                 radius=1.0, rows=10, cols=None, offset=False,
                 vertex_colors=None, face_colors=None,
                 color=(1, 1, 1, 1), edge_color=(0, 0, 1, 0.2),
                 shading=None, texture=None, method='oblate', **kwargs):

        self._radii = np.zeros((3,),dtype=np.float64)
        self._pos = np.zeros((3,), dtype=np.float64)
        self._sb_ref = sim_body
        if self._sb_ref is not None and type(self._sb_ref) == SimBody:
            self._vizz_data = sys_data.vizz_data(body_name)
            self._tex_data = self._vizz_data['tex_data']
            self._mark = self._vizz_data['body_mark']
            self._base_color = self._vizz_data['body_color']
            self._body_alpha = 1.0
            self._track_alpha = 0.6
            if texture is None:
                self._texture_data = self._tex_data
            else:
                self._texture_data = texture

            self._radii = self._sb_ref.radius

        else:           # no SimBody provided
            self._radii = [1.0, 1.0, 1.0] * u.km  # default to 1.0
            self._texture_data = get_texture_data(DEF_TEX_FNAME)

        self._texture_data = self._texture_data.transpose(Image.Transpose.ROTATE_270)
        if cols is None:        # auto set cols to 2 * rows
            cols = rows * 2

        if method == 'latitude':
            radius = self._radii[0]
            self._mesh_data = _latitude(rows, cols, radius, offset)
            # print("Using 'latitude' method...")
        else:
            radius = self._radii
            self._surface_data = _oblate_sphere(rows, cols, radius, offset)
            self._mesh_data = MeshData(vertices=self._surface_data['verts'],
                                       faces=self._surface_data['faces'])
            self._surface_data['edges'] = self._mesh_data.get_edges()

        self._mesh = MeshVisual(vertices=self._mesh_data.get_vertices(),
                                faces=self._mesh_data.get_faces(),
                                vertex_colors=vertex_colors,
                                face_colors=face_colors,
                                color=color,
                                shading=shading)

        if np.array(edge_color).any():
            self._border = MeshVisual(vertices=self._mesh_data.get_vertices(),
                                      faces=self._mesh_data.get_edges(),
                                      color=edge_color, mode='lines')
        else:
            self._border = MeshVisual()

        self._mesh.set_gl_state(polygon_offset_fill=True,
                                polygon_offset=(1, 1),
                                depth_test=True)
        super(PlanetVisual, self).__init__([v for v in [self._mesh, self._border]])
        self.texture = self._texture_data

    @property
    def mesh(self):
        """The vispy.visuals.MeshVisual that used to fil in."""
        return self._mesh

    @mesh.setter
    def mesh(self, new_mesh):
        self._mesh = new_mesh

    @property
    def mesh_data(self):
        return self._mesh.mesh_data.save()

    @property
    def base_color(self):
        return self._base_color

    @base_color.setter
    def base_color(self, new_color):
        self._base_color = new_color

    @property
    def track_alpha(self):
        return self._track_alpha

    @track_alpha.setter
    def track_alpha(self, new_alpha=1):
        self._track_alpha = 0.6

    @property
    def border(self):
        """The vispy.visuals.MeshVisual that used to draw the border."""
        return self._border

    @property
    def texture(self):
        return self._texture_data

    @texture.setter
    def texture(self, new_data=None):
        if new_data is None:
            new_data = self._texture_data

        _filter = TextureFilter(new_data.transpose(Image.Transpose.ROTATE_270),
                                self._surface_data['tcord'],
                                enabled=True,
                                )
        self._mesh.attach(_filter)
        # self.update()

    # @property
    # def pos(self):
    #     return self._pos
    #
    # @pos.setter
    # def pos(self, new_pos):
    #     if new_pos is not None:
    #         self._pos = new_pos
    #         self.transform = trx.STTransform().as_matrix()
    #         self.transform.translate(self._pos)
    #         self.update()
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
    from vispy.scene import SceneCanvas, ArcballCamera, FlyCamera, TurntableCamera
    from sys_skymap import SkyMap
    import vispy.visuals.transforms as trx

    print("BodyViz test code...")
    win = SceneCanvas(title="BodyViz Test",
                      keys="interactive",
                      bgcolor='black',
                      )
    view = win.central_widget.add_view()
    view.camera = TurntableCamera()
    skymap = SkyMap(edge_color=(0, 0, 1, 0.3),
                    color=(1, 1, 1, 1),
                    parent=view.scene)
    view.add(skymap)
    skymap.visible = True
    bod = Planet(rows=36,
                 body_name='Mars',
                 method='oblate',
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
    view.camera.scale_factor = 15761445.040766222
    rps = 1.0

    def on_timer(event=None):
        bod.transform.reset()
        bod.transform.rotate(bod_timer.elapsed * 2 * np.pi * rps, (0, 0, 1))
        bod.transform.rotate(23.5 * np.pi / 360, (1, 0, 0))
        # bod.transform.scale((1200, 1200, 1200))
        # bod.transform = bod_trx
        logging.debug("transform = %s", bod.transform)
        logging.debug("ZOOM FACTOR: %s", view.camera.zoom_factor)
        logging.debug("SCALE FACTOR: %s", view.camera.scale_factor)
        logging.debug("CENTER: %s", view.camera.center)

    bod_timer = Timer(interval='auto',
                      connect=on_timer,
                      iterations=-1,
                      start=True,
                      # app=win.app,
                      )
    # on_timer()
    win.show()
    win.app.cmd_timer()


if __name__ == "__main__":

    # for rot in range(3600):
    #     bod.transform.rotate(rot * np.pi / 1800, [0, 0, 1])
    main()
