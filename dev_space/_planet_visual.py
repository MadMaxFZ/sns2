# -*- coding: utf-8 -*-
#######################################################################################################################
"""
   Copyright 2023, Max S. Whitten : madmaxfz@protonmail.com
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the “Software”), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of
the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
#######################################################################################################################
# -*- coding: utf-8 -*-
# planet_visual.py
import logging
import numpy as np
from vispy.scene import visuals, SceneCanvas
# from poliastro.bodies import Sun
from vispy.visuals.filters import TextureFilter
from vispy.geometry.meshdata import MeshData
from multiprocessing import get_logger
# from PIL import Image
from sysbody_model import SimBody
# from skymap import SkyMap

"""------------------------------------------------------------------------------"""

logger = get_logger
# logging.basicConfig(filename='logs/x_spacenavsim.log',
#                     level=logging.INFO,
#                     format='PV_%(levelname)s:%(asctime)s:%(message)s'
#                     )


class Planet(visuals.Compound):
    """

    """
    DEF_TEX_FNAME = "resources/textures/2k_6earth_nightmap.png"
    # with Image.open(DEF_TEX_FNAME) as im:
    #     print(DEF_TEX_FNAME, im.format, f"{im.size}x{im.mode}")
    #     DEF_TEX = im.copy()

    def __init__(self, rows=36, cols=None,
                 refbody=None,
                 # pos=np.zeros((3,), dtype=float),
                 edge_color=np.array([0, 1, 0, 0.7]),
                 color=np.ones((4,), dtype=float),
                 texture=None,
                 **kwargs,
                 ):
        """ This visual replaces the SphereVisual object and adds elements to compute, store and
        recall texture coordinates, and vector normals of the mesh.

        Parameters
        ----------
        cols : int
            Number of cols that make up the sphere mesh
        rows : int
            Number of rows that make up the sphere mesh
        radius : float
        """

        logging.debug('\n<--------------------------------->')
        logging.debug('\tInitializing PlanetVisual object...')
        self._verts = []
        self._norms = []
        self._txcds = []
        self._faces = []
        self._edges = []
        self._h_edges = []
        self._v_edges = []
        self._edge_colors = []  # EIGHT friggin' lists !!!
        self._texture = texture
        self._filter = None
        if type(refbody) == SimBody:
            self._pos = refbody.pos
            if refbody.name == "Sun":
                self._radius = np.array([refbody.body.R.value,
                                         refbody.body.R.value,
                                         refbody.body.R.value,
                                         ])
            else:
                self._radius = np.array([refbody.body.R_mean.value,
                                         refbody.body.R.value,
                                         refbody.body.R_polar.value,
                                         ])
        else:
            self._radius = np.ones((3,), dtype=np.float64)
            self._pos = np.zeros((3,), dtype=np.float64)
            
        if cols is None:
            cols = rows * 2
            
        logging.debug('Generating mesh data for %i rows and %i columns...', rows, cols)
        m_data = self._oblate_mesh(rows, cols, self._radius)
        self._verts = m_data[0]
        self._norms = m_data[1]
        self._txcds = m_data[2]
        self._faces = m_data[3]
        self._edges = m_data[4]
        self._h_edges = m_data[5]
        self._v_edges = m_data[6]
        self._edge_colors = m_data[7]

        mesh = MeshData(vertices=np.array(self._verts),
                        faces=np.array(self._faces),
                        )
        mesh._edge_colors = np.array(self._edge_colors)
        mesh._edges = np.array(self._edges)
        mesh._vertex_normals = np.array(self._norms)

        self._mesh = visuals.Mesh(vertices=mesh.get_vertices(),
                                  faces=mesh.get_faces(),
                                  color=color,
                                  meshdata=mesh,
                                  **kwargs,
                                  )

        logging.debug('Initializing border mesh, cram into Compound and set the gl_state...')
        if edge_color.any():
            self._border = visuals.Mesh(vertices=mesh.get_vertices(),
                                        faces=mesh.get_edges(),
                                        color=edge_color,
                                        mode='lines',
                                        meshdata=mesh,
                                        )
        else:
            self._border = visuals.Mesh()

        # create instance of inherited class, in this case a CompoundVisual
        super(Planet, self).__init__([self._mesh,
                                      self._border,
                                      ]
                                     )

        self._mesh.set_gl_state(polygon_offset_fill=True,
                                polygon_offset=(1, 1),
                                depth_test=True,
                                )
        if texture is not None:
            self.set_texture(texture=texture)

        logging.info('\tPlanetVisual initialization has completed...')

    """ end PlanetVisual.__init__() ======================================================================"""

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, pos=None):
        self._pos = pos

    @property
    def mesh(self):
        """The vispy.visuals.MeshVisual that used to fill in."""
        return self._mesh

    @property
    def border(self):
        """The vispy.visuals.MeshVisual that used to draw the border."""
        return self._border

    @property
    def radius(self):
        return self._radius[1].value

    # @property
    # def texture(self):
    #     return self._texture

    def set_texture(self, texture=None):
        logging.debug("PlanetVisual.set_texture(" + str(type(texture)) + ").")
        """ This method detaches the existing texture and attaches another.

        :param texture:
        :type texture:
        :return:
        :rtype:
        """
        if texture is not None:
            self._texture = texture
        else:
            self._texture = Planet.DEF_TEX

        print("Applying texture:", type(texture))
        self._filter = TextureFilter(texture=self._texture,
                                     texcoords=np.array(self._txcds),
                                     )
        self._mesh.attach(self._filter)
        logging.info("PlanetVisual.set_texture(): TextureFilter attached...")

    def _oblate_mesh(self, rows, cols, radius):
        """
        Make a sphere

        Parameters
        ----------
        rows : int
            Number of rows
        cols : int
            Number of columns

        Returns
        -------
            : list
            Vertices and faces computed for a spherical surrface.
        """
        logging.debug("PlanetVisual._oblate_mesh(" + str(radius) + ").")
        logging.debug('>>> Generating data for spherical mesh...')
        colstep = 2 * np.pi / cols
        rowstep = np.pi / rows
        num_v = -1  # these counters are for logging/debuging
        num_f = -1
        num_e = -1
        num_eh = -1
        num_ev = -1

        for row in range(0, rows + 1):
            phi = np.pi / 2 - row * rowstep
            xy = radius[0] * np.cos(phi)
            z = radius[2] * np.sin(phi)

            for col in range(0, cols + 1):
                theta = col * colstep
                x = xy * np.cos(theta)
                y = xy * np.sin(theta)
                vert = np.array([x, y, z])
                self._verts.append(vert)
                self._norms.append(vert / np.sqrt(vert.dot(vert)))
                self._txcds.append(np.array([1 - (col / cols), (row / rows)]))
                num_v += 1

        logging.debug('----->>> Generated %r vertices...', num_v)
        for i in range(0, rows):

            k1 = i * (cols + 1)
            k2 = k1 + cols + 1

            for j in range(0, cols):
                if i != 0:
                    self._faces.append(np.array([k1, k2, k1 + 1]))
                    self._edges.append(np.array([k1, k2]))
                    self._edges.append(np.array([k2, k1 + 1]))
                    self._edges.append(np.array([k1 + 1, k1]))
                    self._edge_colors.append([0, 0, 0, 0.1])
                    self._edge_colors.append([0, 0, 0, 0])
                    self._edge_colors.append([0, 0, 0, 0.1])
                    num_f += 1
                    num_e += 3
                if i != (rows - 1):
                    self._faces.append(np.array([k1 + 1, k2, k2 + 1]))
                    self._edges.append(np.array([k1 + 1, k2]))
                    self._edges.append(np.array([k2, k2 + 1]))
                    self._edges.append(np.array([k2 + 1, k1 + 1]))
                    self._edge_colors.append([0, 0, 0, 0])
                    self._edge_colors.append([0, 0, 0, 0])
                    self._edge_colors.append([0, 0, 0, 0])
                    num_f += 1
                    num_e += 3

                k1 += 1
                k2 += 1

                self._v_edges.append(np.array([k1, k2]))
                num_ev += 1
                if i != 0:
                    self._h_edges.append(np.array([k1, k1 + 1]))
                    num_eh += 1
            logging.debug('>>sector[%r, %r]:', i, j)
        logging.debug('>>>Generated %r faces and %r edges...', num_f, num_e)

        #   TODO:   EIGHT fucking lists!?! Is there a better way???
        #       :   Yes! Put this mess inside a dictionary...
        return [self._verts,  # vertex coordinates
                self._norms,  # vertex normals
                self._txcds,  # texture coordinates
                self._faces,  # face triangle vertex indices
                self._edges,  # complete set of edge vertex indices
                self._h_edges,  # horizontal edge vertex indices
                self._v_edges,  # vertical edge vertex indices
                self._edge_colors  # color assigned to each edge
                ]


""" end class PlanetVisual ==============================================================================="""
""" ======================================================================================================"""


def main():
    from vispy.io.image import imread
    from poliastro.bodies import Earth
    canvas = SceneCanvas(keys="interactive",
                         size=(1000, 750),
                         title="Testing PlanetVisual",
                         )
    view = canvas.central_widget.add_view()

    view.camera = "fly"

    skymap_tex = "./resources/textures/8k_zstars.png"
    planet_tex = "./resources/textures/2k_6earth_nightmap.png"
    s_tex = imread(skymap_tex)
    p_tex = imread(planet_tex)
    print(skymap_tex, type(s_tex))
    print(planet_tex, type(p_tex))
    planet = Planet(# refbody=Earth,
                    parent=view.scene,
                    texture=p_tex,
                    edge_color=np.array([0.7, 0.7, 0.7, 0.3]),
                    )
    # planet.set_texture(texture=texture)
    # skymap.visible = True
    planet.visible = True
    # view.add(skymap)
    view.add(planet)
    canvas.show()
    canvas.app.cmd_timer()


"""---------------------------------------------------------------------------------------------------------"""

if __name__ == '__main__': # and sys.flags.interactive == 0:
    main()
