import numpy as np
from vispy.scene import SceneCanvas
from vispy.scene.cameras import FlyCamera

# Create a canvas
canvas = SceneCanvas(keys='interactive')

# Create a camera
camera = FlyCamera(fov=60)

# Attach the camera to the canvas
canvas.camera = camera


# Function to make the camera aim at a specific point
def aim_camera_at_point(point):
    # Get the current camera position
    camera_pos = camera.center

    # Calculate the direction vector from camera position to the target point
    direction = point - camera_pos

    # Calculate the rotation quaternion
    rotation_quat = quaternion_from_vector_to_vector(np.array([0, 0, 1]), direction)

    # Update the camera rotation
    camera.rotation1 = rotation_quat


# Helper function to calculate quaternion from one vector to another
def quaternion_from_vector_to_vector(v1, v2):
    v1 = v1 / np.linalg.norm(v1)
    v2 = v2 / np.linalg.norm(v2)
    axis = np.cross(v1, v2)
    angle = np.arccos(np.dot(v1, v2))
    return quaternion_from_axis_angle(axis, angle)


# Helper function to create quaternion from axis-angle representation
def quaternion_from_axis_angle(axis, angle):
    norm_axis = axis / np.linalg.norm(axis)
    half_angle = angle / 2
    w = np.cos(half_angle)
    xyz = norm_axis * np.sin(half_angle)
    return np.array([w, *xyz])


# Example target point
target_point = np.array([0, 0, 0])

# Aim the camera at the target point
aim_camera_at_point(target_point)

# Show the canvas
canvas.show()

# Run the application
canvas.app.run()
