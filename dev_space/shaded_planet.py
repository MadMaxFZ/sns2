import numpy as np
from vispy import app, gloo
from vispy.visuals.transforms import STTransform
from vispy.scene import SceneCanvas
from vispy.visuals import SphereVisual, TextureFilter

# Define your custom fragment shader
fragment_shader = """
#version 330

uniform sampler2D texture1;
uniform sampler2D texture2;
uniform sampler2D mask;

in vec2 v_texcoord;
out vec4 fragColor;

void main()
{
    // Sample the mask texture to determine which texture to use
    float maskValue = texture(mask, v_texcoord).r;

    // Use texture1 if maskValue is below 0.5, otherwise use texture2
    vec4 texColor = (maskValue < 0.5) ? texture(texture1, v_texcoord) : texture(texture2, v_texcoord);

    fragColor = texColor;
}
"""


# Create a custom SphereVisual with two textures and a mask
class CustomSphereVisual(SphereVisual):
    def __init__(self, radius=1, **kwargs):
        SphereVisual.__init__(self, radius=radius, **kwargs)

        # Load your textures (texture1, texture2, mask)
        texture1 = Texture2D(data=np.random.rand(512, 512, 4), wrapping='repeat', interpolation='linear')
        texture2 = Texture2D(data=np.random.rand(512, 512, 4), wrapping='repeat', interpolation='linear')
        mask = Texture2D(data=np.random.rand(512, 512, 1), wrapping='repeat', interpolation='linear')

        # Assign the textures to the visual
        self.shared_program['texture1'] = texture1
        self.shared_program['texture2'] = texture2
        self.shared_program['mask'] = mask


# Create a canvas and add the custom SphereVisual
canvas = SceneCanvas(keys='interactive', bgcolor='white')
view = canvas.central_widget.add_view()

# Create the custom SphereVisual
sphere = CustomSphereVisual(radius=1, method='latitude', parent=view.scene)

# Set up camera and transformations
view.camera = 'turntable'
view.camera.set_range((-2, 2), (-2, 2), (-2, 2))
sphere.transform = STTransform(translate=(0, 0, 0))

# Run the app
canvas.show()
app.run()

"""
{
    'constants': {
        'DEF_UNITS': ...,
        'DEF_EPOCH0': ...,
        'DEF_TEX_FNAME': ...,
    },
    'logging': {
        'log_config': ...,
    },
    'simulation_params': {
        'SYS_PARAMS': ...,
        'TEXTR_PATH': ...,
        'TEX_FNAMES': ...,
    },
    'body_data': {
        'Earth': {
            'body_name': ...,
            'body_obj': ...,
            'parent_name': ...,
            ...
        },
        'Sun': {
            'body_name': ...,
            'body_obj': ...,
            'parent_name': ...,
            ...
        },
        ...
    },
    'visualization_data': {
        'Earth': {
            'body_color': ...,
            'body_alpha': ...,
            'track_alpha': ...,
            ...
        },
        'Sun': {
            'body_color': ...,
            'body_alpha': ...,
            'track_alpha': ...,
            ...
        },
        ...
    },
    'texture_data': {
        'Earth': ...,
        'Sun': ...,
        ...
    },
}

"""


class SystemDataStore:
    # Existing code...

    def get_nested_data(self):
        """
        Output the collected data as a nested dictionary.
        """
        nested_data = {
            'constants': {
                'DEF_UNITS': self._dist_unit,
                'DEF_EPOCH0': self.default_epoch,
                'DEF_TEX_FNAME': DEF_TEX_FNAME,
            },
            'logging': {
                'log_config': log_config,
            },
            'simulation_params': {
                'SYS_PARAMS': self.system_params,
                'TEXTR_PATH': self.texture_path,
                'TEX_FNAMES': self.texture_fname,
            },
            'body_data': {
                name: self.body_data(name) for name in self.body_names
            },
            'visualization_data': {
                name: self.vizz_data(name) for name in self.body_names
            },
            'texture_data': {
                name: self.texture_data(name) for name in self.body_names
            },
        }
        return nested_data


if __name__ == "__main__":
    def main():
        logging.debug("-------->> RUNNING SYSTEM_DATASTORE() STANDALONE <<---------------")
        dict_store = SystemDataStore()
        nested_data = dict_store.get_nested_data()
        print(nested_data)
        # You can now use nested_data for further processing or output.
    main()

# ===================================================================================================


import json


class SystemDataStore:
    # Existing code...

    def output_to_json(self, filename):
        """
        Output the collected data to a JSON file.
        """
        nested_data = self.get_nested_data()
        with open(filename, 'w') as json_file:
            json.dump(nested_data, json_file, indent=4)


if __name__ == "__main__":
    def main():
        logging.debug("-------->> RUNNING SYSTEM_DATASTORE() STANDALONE <<---------------")
        dict_store = SystemDataStore()
        dict_store.output_to_json("system_data.json")
    main()
