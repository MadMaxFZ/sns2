# x

import logging
import numpy as np
from vispy.visuals import CompoundVisual
from vispy.scene.visuals import create_visual_node, Mesh
# from poliastro.bodies import Sun
from vispy.visuals.filters import TextureFilter
from vispy.geometry.meshdata import MeshData
# from multiprocessing import get_logger
from PIL import Image


class SkyMapVisual(CompoundVisual):
    """
    """

    DEF_TEX_FNAME = "../resources/textures/8k_zzESO_Milky_Way.png"
    with Image.open(DEF_TEX_FNAME) as im:
        print("-->SKYMAP:", DEF_TEX_FNAME, im.format, f"{im.size}x{im.mode}")
        DEF_TEX = im.copy()

    def __init__(self,
                 rows=18, cols=36,
                 radius=8e+09,
                 edge_color=(0, 0, 1, 0.4),
                 color=(0.3, 0.3, 0.3, 1),
                 texture=None,
                 **kwargs,
                 ):
        """This visual replaces the SphereVisual object and adds elements to compute, store and
        recall texture coordinates, and vector normals of the mesh.

        Parameters
        ----------
        cols : int
            Number of cols that make up the sphere mesh
        rows : int
            Number of rows that make up the sphere mesh
        radius : float
        """
        # TODO: Enhance the set of methods to implement additional controls of this object.

        logging.debug('\n<--------------------------------->')
        logging.info('\tInitializing SkyMap object...')
        self._verts = []        # verts and faces are parameters for
        self._faces = []        # the MeshData object
        self._edges = []
        self._txcds = []        # native sphere screws these up somehow
        self._norms = []
        self._h_edges = []
        self._v_edges = []
        self._edge_colors = []  # EIGHT friggin' lists !!!
        self._radius = radius
        if texture is None:
            self._texture = SkyMapVisual.DEF_TEX
        else:
            self._texture = texture

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
        mesh._vertex_normals = np.array(-1 * self._norms)
        self._mesh = Mesh(vertices=mesh.get_vertices(),
                                  faces=mesh.get_faces(),
                                  color=color,
                                  meshdata=mesh,
                                  )
        logging.debug('MeshVisual initialized, setting up the TextureFilter...')
        self._mesh.attach(TextureFilter(texcoords=np.array(self._txcds),
                                        texture=self._texture,
                                        )
                          )
        logging.debug('Initializing border mesh, cram into Compound ans set the gl_state...')
        if edge_color:
            self._border = Mesh(vertices=mesh.get_vertices(),
                                faces=mesh.get_edges(),
                                color=edge_color,
                                mode='lines',
                                meshdata=mesh,
                                )
        else:
            self._border = Mesh()

        # create instance of inherited class, in this case a CompoundVisual
        super(SkyMapVisual, self).__init__([self._mesh, self._border])  # initialize the CompoundVisual
        self._mesh.set_gl_state(polygon_offset_fill=True,
                                polygon_offset=(1, 1),
                                depth_test=True,
                                )
        logging.info('\tSkyMap initialization has been completed...\n')

    """ end SkyMap.__init__() ======================================================================"""

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
        return self._radius[0].value

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
        logging.debug("SkyMap._oblate_mesh(" + str(radius) + ").")
        logging.debug('>>> Generating data for spherical mesh...')
        colstep = 2 * np.pi / cols
        rowstep = np.pi / rows
        num_v = -1  # these counters are for logging/debuging
        num_f = -1
        num_e = -1
        num_eh = -1
        num_ev = -1
        c_rgb = [1, 0, 0]

        for row in range(0, rows + 1):

            phi = np.pi / 2 - row * rowstep
            xy = radius * np.cos(phi)
            z = radius * np.sin(phi)

            for col in range(0, cols + 1):
                theta = col * colstep
                x = xy * np.cos(theta)
                y = xy * np.sin(theta)
                vert = np.array([x, y, z])
                # print(vert)
                self._verts.append(vert)
                self._norms.append(vert / np.sqrt(vert.dot(vert)))
                self._txcds.append(np.array([(col / cols), 1 - (row / rows)]))
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
                    self._edge_colors.append(c_rgb + [1,])
                    self._edge_colors.append(c_rgb + [0,])
                    self._edge_colors.append(c_rgb + [1,])
                    num_f += 1
                    num_e += 3
                if i != (rows - 1):
                    self._faces.append(np.array([k1 + 1, k2, k2 + 1]))
                    self._edges.append(np.array([k1 + 1, k2]))
                    self._edges.append(np.array([k2, k2 + 1]))
                    self._edges.append(np.array([k2 + 1, k1 + 1]))
                    self._edge_colors.append(c_rgb + [0,])
                    self._edge_colors.append(c_rgb + [0,])
                    self._edge_colors.append(c_rgb + [0,])
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
        return [self._verts,       # vertex coordinates
                self._norms,       # vertex normals
                self._txcds,       # texture coordinates
                self._faces,       # face triangle vertex indices
                self._edges,       # complete set of edge vertex indices
                self._h_edges,     # horizontal edge vertex indices
                self._v_edges,     # vertical edge vertex indices
                self._edge_colors  # color assigned to each edge
                ]


SkyMap = create_visual_node(SkyMapVisual)