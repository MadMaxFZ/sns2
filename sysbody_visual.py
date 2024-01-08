# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
# Modified by Max S. Whitten in order to address the "stripe" glitch

import numpy as np
from PIL import Image
import vispy.visuals.transforms as tr
from poliastro.bodies import Body, Sun
from sysbody_model import SimBody
from vispy.geometry import MeshData
from vispy.visuals.mesh import MeshVisual
from vispy.visuals.filters.mesh import TextureFilter
from vispy.visuals import CompoundVisual
from vispy.scene.visuals import create_visual_node, Compound


DEF_TEX_FNAME = "resources/textures/2k_5earth_daymap.png"


def get_texture_data(fname=DEF_TEX_FNAME):
    with Image.open(fname) as im:
        print(fname, im.format, f"{im.size}x{im.mode}")

        return im.copy()


def _oblate_sphere(rows, cols, radius, offset):
    """ Generate mesh for a sphere along with texture coordinates such that
        the 'stripe' anomaly is dealt with.

    Parameters
    ----------
    rows : int - number of rows (usually even)
    cols : int - number of columns (if None, set to rows * 2)
    radius : float - mean radius of sphere (if None, set to 1)
    offset : bool - offset each row by a column width?

    Returns
    -------
    MeshData - mesh description of sphere
    array - texture coordinates for each vertex

    """
    # TODO: fix the verts and/or tex coords to remove 'stripe'
    #       I think I finally figured it out! Just need to change the code!

    verts = np.empty((rows + 1, cols + 1, 3), dtype=np.float32)
    tex_coords = np.empty((rows + 1, cols + 1, 2), dtype=np.float32)
    # compute vertices
    phi = (np.arange(rows + 1) * np.pi / rows).reshape(rows + 1, 1)
    s = radius * np.sin(phi)
    verts[..., 2] = radius * np.cos(phi)
    th = ((np.arange(cols + 1) * 2 * np.pi / cols).reshape(1, cols + 1))
    if offset:
        # rotate each row by 1/2 column
        th = th + ((np.pi / cols) * np.arange(rows + 1).reshape(rows + 1, 1))

    verts[..., 0] = s * np.cos(th)
    verts[..., 1] = s * np.sin(th)
    # print(verts.size)
    verts = verts.reshape((cols + 1) * (rows + 1), 3)
    # print(verts.shape)

    # set easternmost vert coords to match westernmost vert coords
    for row in range(rows):
        verts[(cols + 1) * (row + 2) - 1] = verts[(cols + 1) * (row+1)]

    # compute texture coordinates here
    tex_coords[..., 0] = (th / (2 * np.pi))
    tex_coords[..., 1] = phi / np.pi

    # remove redundant vertices from north and south poles
    verts = verts.reshape((rows + 1) * (cols + 1), 3)[cols + 1:rows * (cols + 2)]
    tex_coords = tex_coords.reshape((rows + 1) * (cols + 1), 2)[cols + 1:rows * (cols + 2)]

    # compute faces as triplets of vertex indices
    faces = np.empty(((rows + 1) * (cols + 1) * 2, 3), dtype=np.uint32)
    rowtemplate1 = (((np.arange(cols + 1).reshape(cols + 1, 1) +
                      np.array([[1, 0, 0]])) % (cols + 1)) +
                    np.array([[0, 0, cols]]))
    rowtemplate2 = (((np.arange(cols + 1).reshape(cols + 1, 1) +
                      np.array([[1, 0, 1]])) % (cols + 1)) +
                    np.array([[0, cols, cols]]))
    for row in range(rows):
        start = row * (cols + 2)
        # print((faces[start:start + cols]).shape, "\n", (rowtemplate1 + row * cols).shape, "\n")
        faces[start:start + cols + 1] = rowtemplate1 + row * (cols + 1)
        faces[start + cols + 2:start + 2 * cols + 3] = rowtemplate2 + row * (cols + 1)

    # cut off zero-area triangles at top and bottom
    faces = faces[cols + 2:-(cols + 2)]

    # adjust for redundant vertices that were removed from top and bottom
    vmin = cols + 1
    faces[faces < vmin] = vmin
    faces -= vmin
    vmax = verts.shape[0] - 1
    faces[faces > vmax] = vmax
    return MeshData(vertices=verts, faces=faces), tex_coords


def _latitude(rows, cols, radius, offset):
    verts = np.empty((rows+1, cols, 3), dtype=np.float32)
    tex_coords = np.empty((rows + 1, cols, 2), dtype=np.uint32)

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
    tex_coords[..., 0] = th / 2 * np.pi
    tex_coords[..., 1] = phi / np.pi
    # remove redundant vertices from top and bottom
    verts = verts.reshape((rows + 1)*cols, 3)[cols-1:-(cols-1)]
    tex_coords = tex_coords.reshape((rows + 1) * cols, 2)[cols - 1:-(cols - 1)]

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
    return MeshData(vertices=verts, faces=faces), tex_coords


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

    def __init__(self, ref_simbod=None, radius=1.0, rows=10, cols=None, offset=False,
                 vertex_colors=None, face_colors=None,
                 color=(1, 1, 1, 1), edge_color=(0, 0, 1, 0.2),
                 shading=None, texture=None, method='oblate', **kwargs):
        if cols is None:        # auto set cols to 2 * rows
            cols = rows * 2

        self._radii = []
        if ref_simbod is not None:
            self._ref_sb = ref_simbod
            if type(self._ref_sb) is SimBody:        # if SimBody defined, get radii
                _body = self._ref_sb.body
                if _body.R_mean.value != 0:
                    self._radii.append(_body.R)
                    self._radii.append(_body.R_mean)
                    self._radii.append(_body.R_polar)
                else:                             # some have R only
                    self._radii.extend([_body.R,
                                        _body.R,
                                        _body.R
                                        ])

        else:
            texture = get_texture_data(fname=DEF_TEX_FNAME)
            self._radii = [10000.0, 10000.0, 10000.0]      # default to 1.0

        if type(texture) == str:                # assume filename
            self._texture_data = get_texture_data(fname=texture)
        elif texture is not None:               # assume image
            self._texture_data = texture
        else:                                   # use default
            self._texture_data = get_texture_data()

        if method == 'latitude':
            _mesh, self._tex_coords = _latitude(rows, cols, radius, offset)
            # print("Using 'latitude' method...")
        else:
            _mesh, self._tex_coords = _oblate_sphere(rows, cols, radius, offset)
            # print("Using 'oblate' method...")

        # print(self._tex_coords)
        self._mesh = MeshVisual(vertices=_mesh.get_vertices(),
                                faces=_mesh.get_faces(),
                                vertex_colors=vertex_colors,
                                face_colors=face_colors,
                                color=color,
                                shading=shading)
        self._filter = TextureFilter(texture=self._texture_data,
                                     texcoords=self._tex_coords,
                                     )
        self._mesh.attach(self._filter)
        if np.array(edge_color).any():
            self._border = MeshVisual(vertices=_mesh.get_vertices(),
                                      faces=_mesh.get_edges(),
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

    @property
    def border(self):
        """The vispy.visuals.MeshVisual that used to draw the border."""
        return self._border

    @property
    def texture(self):
        return self._texture_data

    @texture.setter
    def texture(self, new_texture=DEF_TEX_FNAME):
        self._texture_data = get_texture_data(fname=new_texture)
        self._filter = TextureFilter(texture=self._texture_data,
                                     texcoords=np.array(self._tex_coords),
                                     )
        self._mesh.attach(self._filter)

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, new_visible=False):
        self._visible = new_visible


Planet = create_visual_node(PlanetVisual)


def main():
    # put a little test code here...
    print("BodyViz test code...")
    from vispy import app
    from vispy.app.timer import Timer
    from vispy.scene import SceneCanvas, ArcballCamera, FlyCamera
    from sys_skymap import SkyMap
    # import vispy.visuals.transforms as tr

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
                 texture=get_texture_data(DEF_TEX_FNAME),
                 method='oblate',
                 parent=view.scene,
                 visible=True,
                 )
    view.add(bod)
    view.camera.set_range()
    # bod.transform = tr.MatrixTransform()
    # for rot in range(3600):
    #     bod.transform.rotate(rot * np.pi / 1800, [0, 0, 1])

    win.show()
    app.run()


if __name__ == "__main__":
    main()
