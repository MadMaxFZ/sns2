# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
# Modified by Max S. Whitten in order to address the "stripe" glitch

import numpy as np
# import vispy.visuals.transforms as tr
from astropy import units as u
from starsys_model import SimBody, get_texture_data, DEF_TEX_FNAME
from vispy.geometry import MeshData
from vispy.visuals import CompoundVisual
from vispy.visuals.mesh import MeshVisual
from vispy.visuals.filters.mesh import TextureFilter
from vispy.visuals import transforms as tr
from vispy.scene.visuals import create_visual_node


def _latitude(rows, cols, radius, offset):
    verts = np.empty((rows+1, cols, 3), dtype=np.float32)

    # compute vertices
    phi = (np.arange(rows+1) * np.pi / rows).reshape(rows+1, 1)
    s = radius * np.sin(phi)
    verts[..., 2] = radius * np.cos(phi)
    th = ((np.arange(cols) * 2 * np.pi / cols).reshape(1, cols))
    if offset:
        # rotate each row by 1/2 column
        th = th + ((np.pi / cols) * np.arange(rows+1).reshape(rows+1, 1))
    verts[..., 0] = s * np.cos(th)
    verts[..., 1] = s * np.sin(th)
    # remove redundant vertices from top and bottom
    verts = verts.reshape((rows+1)*cols, 3)[cols-1:-(cols-1)]

    # compute faces
    faces = np.empty((rows*cols*2, 3), dtype=np.uint32)
    rowtemplate1 = (((np.arange(cols).reshape(cols, 1) +
                      np.array([[1, 0, 0]])) % cols) +
                    np.array([[0, 0, cols]]))
    rowtemplate2 = (((np.arange(cols).reshape(cols, 1) +
                      np.array([[1, 0, 1]])) % cols) +
                    np.array([[0, cols, cols]]))
    for row in range(rows):
        start = row * cols * 2
        faces[start:start+cols] = rowtemplate1 + row * cols
        faces[start+cols:start+(cols*2)] = rowtemplate2 + row * cols
    # cut off zero-area triangles at top and bottom
    faces = faces[cols:-cols]

    # adjust for redundant vertices that were removed from top and bottom
    vmin = cols-1
    faces[faces < vmin] = vmin
    faces -= vmin
    vmax = verts.shape[0]-1
    faces[faces > vmax] = vmax
    return MeshData(vertices=verts, faces=faces)


def _oblate_sphere(rows, cols, radius, offset):
    verts = np.empty((rows + 1, cols + 1, 3), dtype=np.float32)
    # compute vertices
    phi = (np.arange(rows+1) * np.pi / rows).reshape(rows+1, 1)
    s = radius[0] * np.sin(phi)
    verts[..., 2] = radius[2] * np.cos(phi)
    th = ((np.arange(cols + 1) * 2 * np.pi / cols).reshape(1, cols + 1))
    if offset:
        # rotate each row by 1/2 column
        th = th + ((np.pi / cols) * np.arange(rows+1).reshape(rows+1, 1))

    verts[..., 0] = s * np.cos(th)
    verts[..., 1] = s * np.sin(th)
    # remove redundant vertices from top and bottom
    verts = verts.reshape((rows + 1) * (cols + 1), 3)[cols:-cols]
    # compute faces
    faces = np.empty((rows * (cols + 1) * 2, 3), dtype=np.uint32)
    rowtemplate1 = (((np.arange(cols + 1).reshape(cols + 1, 1) +
                      np.array([[1, 0, 0]])) % (cols + 1) +
                    np.array([[0, 0, cols + 2]])))
    rowtemplate2 = (((np.arange(cols + 1).reshape(cols + 1, 1) +
                      np.array([[1, 0, 1]])) % (cols + 1) +
                    np.array([[0, cols + 2, cols + 2]])))
    for row in range(rows):
        start = row * (cols + 1) * 2
        faces[start:start+(cols + 1)] = rowtemplate1 + row * (cols + 1)
        faces[start+(cols + 1):start+(cols + 1) * 2] = rowtemplate2 + row * (cols + 1)
    # cut off zero-area triangles at top and bottom
    faces = faces[cols:-cols]

    # adjust for redundant vertices that were removed from top and bottom
    vmin = cols
    faces[faces < vmin] = vmin
    faces -= vmin
    vmax = verts.shape[0]-1
    faces[faces > vmax] = vmax
    return MeshData(vertices=verts, faces=faces)


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

    def __init__(self, sb_ref=None, radius=1.0, rows=10, cols=None, offset=False,
                 vertex_colors=None, face_colors=None,
                 color=(1, 1, 1, 1), edge_color=(0, 0, 1, 0.2),
                 shading=None, texture=None, method='oblate', **kwargs):
        if cols is None:        # auto set cols to 2 * rows
            cols = rows * 2

        self._pos = None
        self._radii = []
        self._texture_data = sb_ref.texture
        if sb_ref is (not None and type(sb_ref) == SimBody):
            _body = sb_ref.body
            # self.pos = self._ref_sb.pos2bary
            if _body.R_mean.value != 0:
                self._radii.extend([_body.R,
                                    _body.R_mean,
                                    _body.R_polar])
            else:                             # some have R only
                self._radii.extend([_body.R,
                                    _body.R,
                                    _body.R])

            # self._texture = sb_ref.texture

        else:
            self._radii = [1.0, 1.0, 1.0] * u.km  # default to 1.0
            # self._texture = sb_ref.texture

        if method == 'latitude':
            radius = self._radii[0]
            self._mesh_data = _latitude(rows, cols, radius, offset)
            # print("Using 'latitude' method...")
        else:
            radius = self._radii
            self._mesh_data = _oblate_sphere(rows, cols, radius, offset)
            # print("Using 'oblate' method...")

        self._tex_coords = np.empty((rows + 1, cols + 1, 2), dtype=np.float32)
        for row in np.arange(rows + 1):
            for col in np.arange(cols + 1):
                self._tex_coords[row, col] = [row / rows, col / cols]
        self._tex_coords = self._tex_coords.reshape((rows + 1) * (cols + 1), 2)

        # print(self._tex_coords)
        self._mesh = MeshVisual(vertices=self._mesh_data.get_vertices(),
                                faces=self._mesh_data.get_faces(),
                                vertex_colors=vertex_colors,
                                face_colors=face_colors,
                                color=color,
                                shading=shading)
        print("TEXTURE:\n", self._texture_data,
              # "\nTEXCOORD:\n", self._tex_coords,
              )
        self._filter = TextureFilter(texture=self.texture,
                                     texcoords=self._tex_coords,
                                     enabled=True,
                                     # shape=(self._texture_data.height, self._texture_data.width)
                                     )
        self._mesh.attach(self._filter)
        if np.array(edge_color).any():
            self._border = MeshVisual(vertices=self._mesh_data.get_vertices(),
                                      faces=self._mesh_data.get_edges(),
                                      color=edge_color, mode='lines')
        else:
            self._border = MeshVisual()

        super(PlanetVisual, self).__init__([self._mesh, self._border])
        self.mesh.set_gl_state(polygon_offset_fill=True,
                               polygon_offset=(1, 1),
                               depth_test=True)

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
            self.transform = tr.MatrixTransform()
            self.transform.translate(self._pos)
            self.update()

    @property
    def texture(self):
        return self._texture_data

    @texture.setter
    def texture(self, new_texture=None):
        self._texture_data = new_texture
        self._filter = TextureFilter(self._texture_data,
                                     np.array(self._tex_coords),
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


def on_timer(event=None):
    pass


if __name__ == "__main__":
    from vispy import app
    from vispy.app.timer import Timer
    from vispy.scene import SceneCanvas, ArcballCamera, FlyCamera
    from sys_skymap import SkyMap
    import vispy.visuals.transforms as tr

    # put a little test code here...
    print("BodyViz test code...")
    win = SceneCanvas(title="BodyViz Test",
                      keys="interactive",
                      bgcolor='white',
                      )
    view = win.central_widget.add_view()
    view.camera = FlyCamera()
    skymap = SkyMap(edge_color=(0, 0, 1, 0.3),
                    color=(1, 1, 1, 1),
                    parent=view.scene)
    # view.add(skymap)
    skymap.visible = False
    bod = Planet(rows=36,
                 refbod_name="Earth",
                 method='oblate',
                 parent=view.scene,
                 visible=True,
                 )
    bod.transform = tr.MatrixTransform()
    view.add(bod)
    view.camera.set_range()

    bod_timer = Timer(interval='auto',
                      connect=on_timer,
                      iterations=-1,
                      start=True,
                      app=app.application)

    # for rot in range(3600):
    #     bod.transform.rotate(rot * np.pi / 1800, [0, 0, 1])

    win.show()
    app.run()

