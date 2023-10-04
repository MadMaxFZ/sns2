import logging
from vispy.scene.visuals import Markers, Text, Arrow, XYZAxis, Axis, Polygon
from planet_visual import Planet
from PIL import Image

#viz2ignore = ["ruler", "oscorbit", "radvec", "velvec"]


def get_tex_data(idx=None, fname=None):
    with Image.open(fname) as im:
        print("Getting texture:", fname, im.format, f"{im.size}x{im.mode}")
        tex_data = im.copy()
    return tex_data


def make_marker(*args, **kwargs):
    """
    :param args:
    :param parent:
    :param kwargs:
    :return:
    """
    print("args:", *args, "\n**kwargs", **kwargs)
    markerviz = Markers(**kwargs)
    logging.info("maker_functs.make_marker(" + str("") + ").")
    return markerviz


def make_text(*args, **kwargs):
    nametagviz = Text(*args, **kwargs)
    logging.info("\tmaker_functs.make_text(" + str(**kwargs) + ").")
    return nametagviz


def make_rad(*args, **kwargs):
    radviz = Arrow(**kwargs)
    logging.info("maker_functs.make_rad(" + str("") + ").")
    return radviz


def make_vel(*args, **kwargs):
    velviz = Arrow(**kwargs)
    logging.info("maker_functs.make_vel(" + str("") + ").")
    return velviz


def make_frame(*args, **kwargs):
    frameviz = XYZAxis(**kwargs)
    logging.info("\tmaker_functs.make_frame(" + str("") + ").")
    return frameviz


def make_ruler(*args, **kwargs):
    rulerviz = Axis(*args, **kwargs)
    logging.info("maker_functs.make_ruler(" + str("") + ").")
    return rulerviz


def make_surf(*args, **kwargs):
    surfviz = Planet(**kwargs)
    logging.info("\tmaker_functs.make_surf(" + str("") + ").")
    return surfviz


def make_oscorb(*args, **kwargs):
    oscorbviz = Polygon(**kwargs)
    logging.info("maker_functs.make_oscorb(" + str("") + ").")
    return oscorbviz


def make_rings(*args, **kwargs):
    # ringviz = Polygon(*args, **kwargs)
    # ringviz.parent = parent
    logging.info("maker_functs.make_rings(" + str("") + ").")
    pass


def get_viz_data(
    body_name=None,
    body_type=None,
    viz_names=None,
    r_color=(1, 0, 0, 1),
    v_color=(0, 1, 0, 1),
    trk_color=(0, 0, 1, 1),
    texture=None,
):
    """Returns dictionary of visuals for this body.
    Parentage and transforms must still be applied!
    This function will not work unless all SimBody objects that are to
    be in the StarSystem are instantiated. If we traverse the scenegraph
    graph tree from root outward, any referenced visuals should exist when needed.
        :param body_name:
        :type body_name:
    :param body_type:
    :param r_color:
        :type r_color:
    :param v_color:
        :type v_color:
    :param trk_color:
        :type trk_color:
    :param texture:
        :type texture:

    :return:
    :rtype:
    """
    logging.debug("get_viz_data(" + str(body_name) + ") starting...")
    # print("get_viz_data():-->\n", type(texture), texture)

    _reticle = dict(
        gen_func=make_marker,
        pos=[0, 0, 0],
        size=5,
        edge_width=2,
        edge_width_rel=None,
        edge_color=(1, 1, 1, 1),
        face_color=(1, 0, 0, 1),
        symbol="cross",  # 14 possible symbols
        scaling="scene",  # ("fixed", "scene" or "visual)
        alpha=0.9,
        antialias=3.0,
        spherical=False,
        light_color=(1, 1, 0),
        light_position=[0, 0, 0],
        light_ambient=None,
        name=str(body_name) + "_reticle",
    )

    _nametag = dict(
        gen_func=make_text,
        text=str(body_name),
        color="black",
        bold=False,
        italic=False,
        face="OpenSans",
        font_size=12,
        pos=[0, 0, 0],
        rotation=0.0,
        anchor_x="center",
        anchor_y="center",
        method="cpu",
        font_manager=None,
        depth_test=False,
        name=str(body_name) + "_nametag",
    )

    _refframe = dict(
        gen_func=make_frame,
        pos=[0, 0, 0],
        color=(0.5, 0.5, 0.5, 1),
        width=1,
        connect="strip ",
        method="gl ",
        antialias=False,
        name=str(body_name) + "_refframe",
    )

    _ruler = dict(
        gen_func=make_ruler,
        pos=[0, 0, 0],
        domain=(0, 5),
        tick_direction=[(0, 0, 0), (0, 1, 0)],
        scale_type="linear",
        axis_color=(0, 0, 0, 1),
        tick_color=(1, 0, 0, 1),
        text_color=(0, 1, 0, 1),
        minor_tick_length=4,
        major_tick_length=8,
        tick_width=2,
        tick_label_margin=5,
        axis_width=3,
        axis_label="Length",
        axis_label_margin=5,
        anchors=("center", "middle"),
        # also ( "left ", "right ")/( "top ", "bottom ")
        font_size=12,
        tick_font_size=None,  # these two are ignored if
        axis_font_size=None,  # the font_size parameter is set
        name=str(body_name) + "_ruler",
    )

    _surface = dict(
        gen_func=make_surf,
        pos=[0, 0, 0],
        rows=18,
        cols=36,
        refbody=str(body_name),
        edge_color=(0, 0, 1, 0),
        color=(1, 1, 1, 1),
        texture=texture,
        name=str(body_name) + "_surface",
    )

    VIZ_PARAMS = dict(
        reticle=_reticle,
        nametag=_nametag,
        surface=_surface,
        refframe=_refframe,
        ruler=_ruler,
    )
    # The Sun (or any Body of type  "star " do not get any visuals below

    if body_type != "star":
        _oscorbit = dict(
            gen_func=make_oscorb,
            pos=None,
            color=5,
            border_color=trk_color[0:2] + (0.1,),
            border_width=1,
            border_method="gl",
            triangulate=False,
            name=str(body_name) + "_oscorbit",
        )

        _radvec = dict(
            gen_func=make_rad,
            pos=[(0, 0), (1, 0)],
            color=[[r_color], [r_color[0:2] + (0.1,)]],
            connect="strip",
            method="gl",
            antialias=True,
            arrows=[(1, 0, 0), (1, 0, 0)],
            arrow_type="stealth",
            arrow_size=1,
            arrow_color=r_color,
            name=str(body_name) + "_radvec",
        )

        _velvec = dict(
            gen_func=make_vel,
            pos=[(0, 0), (1, 0)],
            color=[[v_color], [v_color[0:2] + (0.1,)]],
            connect="strip",
            method="gl",
            antialias=True,
            arrows=[(1, 0, 0), (1, 0, 0)],
            arrow_type="stealth",
            arrow_size=1,
            arrow_color=v_color,
            name=str(body_name) + "_velvec",
        )

        for viz_param in [_oscorbit, _radvec, _velvec]:
            v_name = viz_param["name"].split("_")[1]
            for k in viz_param.keys():
                VIZ_PARAMS.update({v_name: viz_param})

        print(VIZ_PARAMS.keys())
    # Only Saturn (or maybe Uranus) will get this last visual
    # _make_rings = dict( sectors  = 36,
    #                    r_in  = 1.5,
    #                    r_out  = 2.0,
    #                    incl  = 0.0,
    #                    texture  = "ring_tex.png",
    #                    name  = str(body_name) + "_rings",
    #                    parent  = parent,
    #                   )

    # feed these parameters to the maker functions and store the results
    vizuals_dict = {}
    for k1 in VIZ_PARAMS.keys():
        if k1 in viz_names:
            # print("k1:\n", k1,  "...")
            viz_function = VIZ_PARAMS[k1]["gen_func"]
            VIZ_PARAMS[k1].pop("gen_func")
            vizuals_dict.update({k1: viz_function(VIZ_PARAMS[k1])})
            if k1 == "surface":
                vizuals_dict["surface"].set_texture(texture=texture)

    logging.info(">>> viz_functs.get_viz_data(" + str(body_name) + ") completed.\n")

    return vizuals_dict


def trfunc_sf(*args, **kwargs):

    pass


def trfunc_nt(*args, **kwargs):
    pass


def trfunc_rf(*args, **kwargs):
    pass


def trfunc_oo(*args, **kwargs):
    pass


def trfunc_rv(*args, **kwargs):
    pass


def trfunc_vv(*args, **kwargs):
    pass
