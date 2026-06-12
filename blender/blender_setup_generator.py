# blender_setup_generator.py
# Paste this code in Blender's "Scripting" workspace and click the play button.

import bpy
import math

def clear_scene():
    """Clear existing objects in the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def create_material(name, color, roughness=0.5, metallic=0.0):
    """Create a principled BSDF material, compatible with Blender 3.x and 4.x."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled:
        # Compatibility with different Blender versions
        for input_name in ["Base Color", "BaseColor", "Color"]:
            if input_name in principled.inputs:
                principled.inputs[input_name].default_value = color
                break
        else:
            # Fallback to first input
            principled.inputs[0].default_value = color
            
        for input_name in ["Roughness", "roughness"]:
            if input_name in principled.inputs:
                principled.inputs[input_name].default_value = roughness
                break
        for input_name in ["Metallic", "metallic"]:
            if input_name in principled.inputs:
                principled.inputs[input_name].default_value = metallic
                break
    return mat

def create_servo():
    """Create the SG90 Servo Motor representation."""
    # Servo body (blue)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.5))
    servo_body = bpy.context.active_object
    servo_body.name = "Servo_Body"
    servo_body.scale = (0.6, 1.2, 0.9) # SG90 proportions
    
    # Material for body (plastic blue)
    blue_mat = create_material("Servo_Blue", (0.05, 0.2, 0.8, 1.0), roughness=0.3)
    servo_body.data.materials.append(blue_mat)
    
    # Servo Shaft/Gear (brass/metal cylinder)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.3, location=(0, 0.3, 0.95))
    shaft = bpy.context.active_object
    shaft.name = "Servo_Shaft"
    brass_mat = create_material("Shaft_Metal", (0.8, 0.6, 0.2, 1.0), roughness=0.2, metallic=0.8)
    shaft.data.materials.append(brass_mat)
    
    # Servo Horn (white cross arm)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0.2, 1.1))
    horn = bpy.context.active_object
    horn.name = "Servo_Horn"
    horn.scale = (0.2, 0.9, 0.08)
    
    # Apply scale to the horn so its scale becomes (1.0, 1.0, 1.0)
    # This prevents its children (the camera mount, lens, etc.) from being squashed/distorted!
    bpy.context.view_layer.objects.active = horn
    horn.select_set(True)
    bpy.ops.object.transform_apply(scale=True)
    horn.select_set(False)
    
    white_mat = create_material("Horn_Plastic", (0.9, 0.9, 0.9, 1.0), roughness=0.5)
    horn.data.materials.append(white_mat)
    
    return horn

def create_camera_module(parent_obj):
    """Create a realistic flat webcam module mounted on top of the horn."""
    # Camera main body (horizontal flat rectangular shell)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0.2, 1.3))
    mount = bpy.context.active_object
    mount.name = "Camera_Body"
    mount.scale = (0.8, 0.25, 0.4)
    
    black_mat = create_material("Camera_Black", (0.1, 0.1, 0.1, 1.0), roughness=0.4)
    mount.data.materials.append(black_mat)
    
    # Camera Lens collar/housing (small square collar in front of the body)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0.33, 1.3))
    collar = bpy.context.active_object
    collar.name = "Lens_Collar"
    collar.scale = (0.25, 0.1, 0.25)
    collar.data.materials.append(black_mat)
    
    # Camera Lens (very short cylinder pointing forward)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.1, location=(0, 0.39, 1.3))
    lens_body = bpy.context.active_object
    lens_body.name = "Lens_Body"
    lens_body.rotation_euler = (math.radians(90), 0, 0)
    lens_body.data.materials.append(black_mat)
    
    # Camera Lens glass (small blue lens element)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.02, location=(0, 0.44, 1.3))
    glass = bpy.context.active_object
    glass.name = "Lens_Glass"
    glass.rotation_euler = (math.radians(90), 0, 0)
    
    glass_mat = create_material("Lens_Glass_Material", (0.0, 0.5, 0.8, 1.0), roughness=0.1)
    glass.data.materials.append(glass_mat)
    
    # FORCE world matrices update to ensure math is based on applied coordinates
    bpy.context.view_layer.update()
    
    # Parent all parts to the mounting horn with inverse matrices
    for part in [mount, collar, lens_body, glass]:
        part.parent = parent_obj
        part.matrix_parent_inverse = parent_obj.matrix_world.inverted()

def create_person(horn_obj):
    """Create a stylized low-poly human head with detailed features (eyes, eyebrows, mouth, hair, ears, glasses)."""
    # 1. Create Target Head (stylized oval UV sphere)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.5, location=(0, 4.0, 1.3))
    head = bpy.context.active_object
    head.name = "Target_Head"
    head.scale = (0.9, 0.85, 1.1)
    
    # Base skin material
    skin_mat = create_material("Head_Skin", (0.95, 0.75, 0.65, 1.0), roughness=0.6)
    head.data.materials.append(skin_mat)
    
    # Apply scale so features are relative to the final proportions
    bpy.context.view_layer.objects.active = head
    head.select_set(True)
    bpy.ops.object.transform_apply(scale=True)
    head.select_set(False)

    # 2. Neck
    bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=0.4, location=(0, 4.05, 0.75))
    neck = bpy.context.active_object
    neck.name = "Face_Neck"
    neck.data.materials.append(skin_mat)

    # 3. Ears
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.06, location=(-0.46, 4.0, 1.3))
    left_ear = bpy.context.active_object
    left_ear.name = "Left_Ear"
    left_ear.scale = (0.5, 1.0, 1.2)
    left_ear.data.materials.append(skin_mat)

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.06, location=(0.46, 4.0, 1.3))
    right_ear = bpy.context.active_object
    right_ear.name = "Right_Ear"
    right_ear.scale = (0.5, 1.0, 1.2)
    right_ear.data.materials.append(skin_mat)

    # 4. Eyes (Eyeballs & Pupils)
    white_mat = create_material("Eye_White", (0.95, 0.95, 0.95, 1.0), roughness=0.4)
    pupil_mat = create_material("Eye_Pupil", (0.1, 0.1, 0.1, 1.0), roughness=0.3)
    
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(-0.16, 3.55, 1.48))
    left_eyeball = bpy.context.active_object
    left_eyeball.name = "Left_Eyeball"
    left_eyeball.data.materials.append(white_mat)

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(0.16, 3.55, 1.48))
    right_eyeball = bpy.context.active_object
    right_eyeball.name = "Right_Eyeball"
    right_eyeball.data.materials.append(white_mat)

    # Pupils
    bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=0.01, location=(-0.16, 3.475, 1.48))
    left_pupil = bpy.context.active_object
    left_pupil.name = "Left_Pupil"
    left_pupil.rotation_euler = (math.radians(90), 0, 0)
    left_pupil.data.materials.append(pupil_mat)

    bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=0.01, location=(0.16, 3.475, 1.48))
    right_pupil = bpy.context.active_object
    right_pupil.name = "Right_Pupil"
    right_pupil.rotation_euler = (math.radians(90), 0, 0)
    right_pupil.data.materials.append(pupil_mat)

    # 5. Eyebrows
    hair_mat = create_material("Hair_Color", (0.25, 0.15, 0.08, 1.0), roughness=0.8) # Brown hair
    
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-0.16, 3.53, 1.58))
    left_eyebrow = bpy.context.active_object
    left_eyebrow.name = "Left_Eyebrow"
    left_eyebrow.scale = (0.08, 0.02, 0.015)
    left_eyebrow.rotation_euler = (0, math.radians(10), 0)
    left_eyebrow.data.materials.append(hair_mat)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.16, 3.53, 1.58))
    right_eyebrow = bpy.context.active_object
    right_eyebrow.name = "Right_Eyebrow"
    right_eyebrow.scale = (0.08, 0.02, 0.015)
    right_eyebrow.rotation_euler = (0, math.radians(-10), 0)
    right_eyebrow.data.materials.append(hair_mat)

    # 6. Nose (neat nose bridge)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 3.48, 1.34))
    nose = bpy.context.active_object
    nose.name = "Face_Nose"
    nose.scale = (0.04, 0.08, 0.12)
    nose.data.materials.append(skin_mat)

    # 7. Mouth (pink lips)
    lip_mat = create_material("Mouth_Lips", (0.85, 0.35, 0.35, 1.0), roughness=0.5)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 3.53, 1.18))
    mouth = bpy.context.active_object
    mouth.name = "Face_Mouth"
    mouth.scale = (0.12, 0.02, 0.02)
    mouth.data.materials.append(lip_mat)

    # 8. Glasses Frames (using round torus mesh for a high-quality stylized developer look)
    glasses_mat = create_material("Glasses_Frame", (0.08, 0.08, 0.08, 1.0), roughness=0.4)
    
    # Left Frame Torus
    bpy.ops.mesh.primitive_torus_add(align='WORLD', location=(-0.16, 3.45, 1.48), rotation=(math.radians(90), 0, 0), major_radius=0.08, minor_radius=0.012)
    left_glass = bpy.context.active_object
    left_glass.name = "Left_Glass_Frame"
    left_glass.data.materials.append(glasses_mat)
    
    # Right Frame Torus
    bpy.ops.mesh.primitive_torus_add(align='WORLD', location=(0.16, 3.45, 1.48), rotation=(math.radians(90), 0, 0), major_radius=0.08, minor_radius=0.012)
    right_glass = bpy.context.active_object
    right_glass.name = "Right_Glass_Frame"
    right_glass.data.materials.append(glasses_mat)
    
    # Glasses Bridge
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 3.44, 1.49))
    glasses_bridge = bpy.context.active_object
    glasses_bridge.name = "Glasses_Bridge"
    glasses_bridge.scale = (0.06, 0.01, 0.01)
    glasses_bridge.data.materials.append(glasses_mat)
    
    # Glasses temples (sides)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-0.25, 3.7, 1.49))
    left_temple = bpy.context.active_object
    left_temple.name = "Glasses_Left_Temple"
    left_temple.scale = (0.01, 0.25, 0.01)
    left_temple.data.materials.append(glasses_mat)
    
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.25, 3.7, 1.49))
    right_temple = bpy.context.active_object
    right_temple.name = "Glasses_Right_Temple"
    right_temple.scale = (0.01, 0.25, 0.01)
    right_temple.data.materials.append(glasses_mat)

    # 9. Stylized Hair (blocky volumetric hair)
    # Hair Top/Main
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.47, location=(0, 4.05, 1.48))
    hair_main = bpy.context.active_object
    hair_main.name = "Hair_Main"
    hair_main.scale = (1.0, 0.95, 0.95)
    hair_main.data.materials.append(hair_mat)
    
    # Hair Bangs
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 3.65, 1.68))
    hair_bangs = bpy.context.active_object
    hair_bangs.name = "Hair_Bangs"
    hair_bangs.scale = (0.42, 0.12, 0.1)
    hair_bangs.data.materials.append(hair_mat)
    
    # Hair Back
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 4.25, 1.15))
    hair_back = bpy.context.active_object
    hair_back.name = "Hair_Back"
    hair_back.scale = (0.47, 0.2, 0.4)
    hair_back.data.materials.append(hair_mat)
    
    # Sideburns
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-0.46, 4.05, 1.25))
    left_sideburn = bpy.context.active_object
    left_sideburn.name = "Hair_Sideburn_L"
    left_sideburn.scale = (0.02, 0.1, 0.2)
    left_sideburn.data.materials.append(hair_mat)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.46, 4.05, 1.25))
    right_sideburn = bpy.context.active_object
    right_sideburn.name = "Hair_Sideburn_R"
    right_sideburn.scale = (0.02, 0.1, 0.2)
    right_sideburn.data.materials.append(hair_mat)

    # 10. FOV Cone (Field of View indicator)
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.02, radius2=1.2, depth=3.61, location=(0, 2.195, 1.3))
    fov = bpy.context.active_object
    fov.name = "FOV_Cone"
    fov.rotation_euler = (math.radians(-90), 0, 0)
    fov.display_type = 'WIRE' # Set viewport display to wireframe so it doesn't block the view in Solid shading mode
    
    green_mat = create_material("FOV_Wire", (0.0, 1.0, 0.4, 0.2), roughness=0.5)
    if green_mat.node_tree.nodes.get("Principled BSDF"):
        # Set alpha transparency in material
        for input_name in ["Alpha", "alpha"]:
            if input_name in green_mat.node_tree.nodes["Principled BSDF"].inputs:
                green_mat.node_tree.nodes["Principled BSDF"].inputs[input_name].default_value = 0.15
    fov.data.materials.append(green_mat)
    green_mat.blend_method = 'BLEND'

    # Parent all parts to the main Head structure using matrix_parent_inverse
    bpy.context.view_layer.update()
    
    children_list = [
        neck, left_ear, right_ear, left_eyeball, right_eyeball,
        left_pupil, right_pupil, left_eyebrow, right_eyebrow,
        nose, mouth, left_glass, right_glass, glasses_bridge,
        left_temple, right_temple, hair_main, hair_bangs,
        hair_back, left_sideburn, right_sideburn
    ]
    
    for child in children_list:
        child.parent = head
        child.matrix_parent_inverse = head.matrix_world.inverted()
        
    # Parent the FOV Cone to the Servo Horn so it moves with the camera
    fov.parent = horn_obj
    fov.matrix_parent_inverse = horn_obj.matrix_world.inverted()
    
    return head, left_eyeball, right_eyeball, left_pupil, right_pupil, left_eyebrow, right_eyebrow, mouth

def setup_lights_and_scene():
    """Create a camera and clean lights for a premium render."""
    # Sun light
    bpy.ops.object.light_add(type='SUN', radius=1.0, location=(3, -3, 5))
    sun = bpy.context.active_object
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(45), 0, math.radians(45))
    
    # Soft fill light
    bpy.ops.object.light_add(type='AREA', radius=2.0, location=(-3, -3, 3))
    fill = bpy.context.active_object
    fill.data.energy = 50.0
    fill.rotation_euler = (math.radians(45), 0, math.radians(-45))

    # Render Camera (looking from the side/front isometric view)
    bpy.ops.object.camera_add(location=(3.5, -3.5, 3.2))
    cam = bpy.context.active_object
    cam.name = "Render_Camera"
    cam.rotation_euler = (math.radians(60), 0, math.radians(45))

def build_setup():
    clear_scene()
    horn = create_servo()
    create_camera_module(horn)
    
    # Create the detailed face and extract children for animation
    head, left_eyeball, right_eyeball, left_pupil, right_pupil, left_eyebrow, right_eyebrow, mouth = create_person(horn)
    
    setup_lights_and_scene()
    
    # Configure Track To constraint: makes the Servo Horn automatically face the Head
    constraint = horn.constraints.new(type='TRACK_TO')
    constraint.target = head
    constraint.track_axis = 'TRACK_Y' # Point the Y axis (camera front) at the target
    constraint.up_axis = 'UP_Z'       # Keep Z axis facing upwards
    
    # Configure Timeline animation loop (120 frames)
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 120
    
    # --- ANIMATION KEYFRAMING ---
    
    # 1. Animate Head Location and Rotation (Looking back and forth)
    # Frame 1: Center
    head.location = (0.0, 4.0, 1.3)
    head.rotation_euler = (0, 0, 0)
    head.keyframe_insert(data_path="location", frame=1)
    head.keyframe_insert(data_path="rotation_euler", frame=1)
    
    # Frame 30: Left (Looking left)
    head.location = (-1.5, 4.0, 1.3)
    head.rotation_euler = (0, 0, math.radians(20))
    head.keyframe_insert(data_path="location", frame=30)
    head.keyframe_insert(data_path="rotation_euler", frame=30)
    
    # Frame 90: Right (Looking right)
    head.location = (1.5, 4.0, 1.3)
    head.rotation_euler = (0, 0, math.radians(-20))
    head.keyframe_insert(data_path="location", frame=90)
    head.keyframe_insert(data_path="rotation_euler", frame=90)
    
    # Frame 120: Center
    head.location = (0.0, 4.0, 1.3)
    head.rotation_euler = (0, 0, 0)
    head.keyframe_insert(data_path="location", frame=120)
    head.keyframe_insert(data_path="rotation_euler", frame=120)

    # 2. Animate Eye Blinking (Scale eyeballs & pupils vertically on Z)
    for eye in [left_eyeball, right_eyeball, left_pupil, right_pupil]:
        # Clear scale keyframes if any
        eye.animation_data_clear()
        
        # Frame 1: Normal
        eye.scale = (1.0, 1.0, 1.0)
        eye.keyframe_insert(data_path="scale", frame=1)
        
        # First blink (around frame 15)
        eye.scale = (1.0, 1.0, 1.0)
        eye.keyframe_insert(data_path="scale", frame=13)
        eye.scale = (1.0, 1.0, 0.1) # Closed/Blinked
        eye.keyframe_insert(data_path="scale", frame=15)
        eye.scale = (1.0, 1.0, 1.0)
        eye.keyframe_insert(data_path="scale", frame=17)
        
        # Second blink (around frame 60)
        eye.scale = (1.0, 1.0, 1.0)
        eye.keyframe_insert(data_path="scale", frame=58)
        eye.scale = (1.0, 1.0, 0.1) # Closed/Blinked
        eye.keyframe_insert(data_path="scale", frame=60)
        eye.scale = (1.0, 1.0, 1.0)
        eye.keyframe_insert(data_path="scale", frame=62)
        
        # Frame 120: Normal
        eye.scale = (1.0, 1.0, 1.0)
        eye.keyframe_insert(data_path="scale", frame=120)

    # 3. Animate Eyebrows (Moving up for surprise on left, down for focus on right)
    # Left Eyebrow
    left_eyebrow.animation_data_clear()
    left_eyebrow.location = (-0.16, 3.53, 1.58)
    left_eyebrow.keyframe_insert(data_path="location", frame=1)
    
    # Surprised at frame 30 (raised)
    left_eyebrow.location = (-0.16, 3.53, 1.63)
    left_eyebrow.keyframe_insert(data_path="location", frame=30)
    
    # Normal back at frame 50
    left_eyebrow.location = (-0.16, 3.53, 1.58)
    left_eyebrow.keyframe_insert(data_path="location", frame=50)
    
    # Focused at frame 90 (furrowed/down)
    left_eyebrow.location = (-0.16, 3.53, 1.55)
    left_eyebrow.keyframe_insert(data_path="location", frame=90)
    
    # Normal at 110-120
    left_eyebrow.location = (-0.16, 3.53, 1.58)
    left_eyebrow.keyframe_insert(data_path="location", frame=110)
    left_eyebrow.location = (-0.16, 3.53, 1.58)
    left_eyebrow.keyframe_insert(data_path="location", frame=120)

    # Right Eyebrow
    right_eyebrow.animation_data_clear()
    right_eyebrow.location = (0.16, 3.53, 1.58)
    right_eyebrow.keyframe_insert(data_path="location", frame=1)
    
    # Surprised at frame 30 (raised)
    right_eyebrow.location = (0.16, 3.53, 1.63)
    right_eyebrow.keyframe_insert(data_path="location", frame=30)
    
    # Normal back at frame 50
    right_eyebrow.location = (0.16, 3.53, 1.58)
    right_eyebrow.keyframe_insert(data_path="location", frame=50)
    
    # Focused at frame 90 (furrowed/down)
    right_eyebrow.location = (0.16, 3.53, 1.55)
    right_eyebrow.keyframe_insert(data_path="location", frame=90)
    
    # Normal at 110-120
    right_eyebrow.location = (0.16, 3.53, 1.58)
    right_eyebrow.keyframe_insert(data_path="location", frame=110)
    right_eyebrow.location = (0.16, 3.53, 1.58)
    right_eyebrow.keyframe_insert(data_path="location", frame=120)

    # 4. Animate Mouth (surprised open at frame 30, talking/smiling at frame 90)
    mouth.animation_data_clear()
    # Frame 1: Normal Lip shape
    mouth.scale = (0.12, 0.02, 0.02)
    mouth.keyframe_insert(data_path="scale", frame=1)
    
    # Surprised open
    mouth.scale = (0.06, 0.02, 0.08) # Becomes a vertical O-shape
    mouth.keyframe_insert(data_path="scale", frame=30)
    
    # Normal back
    mouth.scale = (0.12, 0.02, 0.02)
    mouth.keyframe_insert(data_path="scale", frame=50)
    
    # Talking smile
    mouth.scale = (0.15, 0.02, 0.04) # Wider smile-like shape
    mouth.keyframe_insert(data_path="scale", frame=90)
    
    # Normal back
    mouth.scale = (0.12, 0.02, 0.02)
    mouth.keyframe_insert(data_path="scale", frame=110)
    mouth.scale = (0.12, 0.02, 0.02)
    mouth.keyframe_insert(data_path="scale", frame=120)

if __name__ == "__main__":
    build_setup()
    print("3D Servo-Camera tracking animation setup with detailed face built successfully!")
