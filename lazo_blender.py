"""
Lazo de cordel de yute en Blender: modela el lazo, lo renderiza y exporta
una secuencia de PNG (fondo transparente) del desatado.

USO:
1. Instala Blender (gratis) desde blender.org.
2. Abre Blender, cambia a la pestaña "Scripting" (arriba).
3. Pulsa "New", pega TODO este código y pulsa el botón ▶ "Run Script".
4. Espera. Se crea la carpeta "lazo_frames" junto al archivo .blend
   (o en la carpeta de Documentos si el archivo no está guardado).

Requisitos: Blender 3.6 o 4.x.
"""
import bpy
import math
import os
from mathutils import Vector

# ---------- Ajustes ----------
FRAMES = 16              # fotogramas del desatado
RES_X, RES_Y = 1200, 1200
SAMPLES = 128            # más = más calidad y más lento
CORD_RADIUS = 0.012      # grosor del cordón

OUT_DIR = bpy.path.abspath("//lazo_frames") if bpy.data.filepath else os.path.join(os.path.expanduser("~"), "Documents", "lazo_frames")
os.makedirs(OUT_DIR, exist_ok=True)

# ---------- Limpiar escena ----------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for block in bpy.data.curves:
    bpy.data.curves.remove(block)

# ---------- Puntos de control (anudado y suelto) ----------
KNOTTED = {
    "loopL": [(0, 0, 0), (-0.25, 0.32, 0.10), (-0.66, 0.38, 0.10), (-0.80, 0.02, 0.06), (-0.56, -0.24, 0.04), (-0.18, -0.08, 0.02)],
    "loopR": [(0, 0, 0), (0.25, 0.32, 0.10), (0.66, 0.38, 0.10), (0.80, 0.02, 0.06), (0.56, -0.24, 0.04), (0.18, -0.08, 0.02)],
    "tailL": [(-0.03, -0.03, 0.02), (-0.14, -0.34, 0.06), (-0.27, -0.66, 0.10), (-0.38, -0.94, 0.08), (-0.42, -1.06, 0.05)],
    "tailR": [(0.03, -0.03, 0.02), (0.16, -0.38, 0.06), (0.32, -0.70, 0.10), (0.46, -0.96, 0.08), (0.54, -1.10, 0.05)],
}
LOOSE = {
    "loopL": [(0, 0, 0.02), (-0.34, 0.28, 0.04), (-0.86, 0.46, 0.04), (-1.12, 0.10, 0.03), (-0.86, -0.32, 0.03), (-0.40, -0.14, 0.02)],
    "loopR": [(0, 0, 0.02), (0.38, 0.30, 0.04), (0.88, 0.52, 0.04), (1.08, 0.12, 0.03), (0.82, -0.40, 0.03), (0.34, -0.16, 0.02)],
    "tailL": [(-0.03, -0.03, 0.02), (-0.32, -0.40, 0.03), (-0.56, -0.76, 0.03), (-0.84, -0.94, 0.03), (-0.96, -1.14, 0.03)],
    "tailR": [(0.03, -0.03, 0.02), (0.40, -0.56, 0.03), (0.60, -0.90, 0.03), (0.84, -1.10, 0.03), (0.96, -1.32, 0.03)],
}
CLOSED = {"loopL": True, "loopR": True, "tailL": False, "tailR": False}

# ---------- Material de cordel de yute ----------
def make_jute_material():
    mat = bpy.data.materials.new("Yute")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.85
    if "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = 0.3
    # Color natural del yute con variación suave
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 40
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.42, 0.31, 0.18, 1)
    ramp.color_ramp.elements[1].color = (0.78, 0.66, 0.46, 1)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    # Relieve de fibras diagonales (efecto trenzado)
    wave = nodes.new("ShaderNodeTexWave")
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'DIAGONAL'
    wave.inputs["Scale"].default_value = 90
    wave.inputs["Distortion"].default_value = 3
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    links.new(wave.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

jute = make_jute_material()

# ---------- Crear cordones como curvas con grosor ----------
curves = {}
for name, pts in KNOTTED.items():
    cdata = bpy.data.curves.new(name, 'CURVE')
    cdata.dimensions = '3D'
    cdata.bevel_depth = CORD_RADIUS
    cdata.bevel_resolution = 6
    cdata.resolution_u = 24
    spline = cdata.splines.new('BEZIER')
    spline.bezier_points.add(len(pts) - 1)
    for p, co in zip(spline.bezier_points, pts):
        p.co = Vector(co)
        p.handle_left_type = 'AUTO'
        p.handle_right_type = 'AUTO'
    spline.use_cyclic_u = CLOSED[name]
    obj = bpy.data.objects.new(name, cdata)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(jute)
    curves[name] = obj

# ---------- Nudo central: pequeña vuelta de cordel ----------
wrap = bpy.data.curves.new("nudo", 'CURVE')
wrap.dimensions = '3D'
wrap.bevel_depth = CORD_RADIUS * 1.4
wrap.bevel_resolution = 6
ws = wrap.splines.new('BEZIER')
wrap_pts = [(math.cos(a) * 0.07, math.sin(a) * 0.035, math.sin(a) * 0.045 + 0.02)
            for a in [i / 24 * math.pi * 4 for i in range(25)]]
ws.bezier_points.add(len(wrap_pts) - 1)
for p, co in zip(ws.bezier_points, wrap_pts):
    p.co = Vector(co)
    p.handle_left_type = 'AUTO'
    p.handle_right_type = 'AUTO'
ws.use_cyclic_u = True
knot_obj = bpy.data.objects.new("nudo", wrap)
bpy.context.collection.objects.link(knot_obj)
knot_obj.data.materials.append(jute)

# ---------- Mesa de papel (sombra) ----------
bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, -0.001))
table = bpy.context.active_object
table.name = "mesa"
table_mat = bpy.data.materials.new("Papel")
table_mat.use_nodes = True
table_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.90, 0.87, 0.80, 1)
table_mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
table.data.materials.append(table_mat)

# ---------- Luz suave (caja de luz) y cámara ----------
bpy.ops.object.light_add(type='AREA', location=(-1.5, -2.0, 3.0))
key = bpy.context.active_object
key.data.energy = 300
key.data.size = 2.5
key.rotation_euler = (math.radians(35), 0, math.radians(-30))

bpy.ops.object.light_add(type='AREA', location=(2.0, -1.0, 2.0))
fill = bpy.context.active_object
fill.data.energy = 80
fill.data.size = 3

bpy.ops.object.camera_add(location=(0, -3.2, 2.3))
cam = bpy.context.active_object
cam.rotation_euler = (math.radians(55), 0, 0)
bpy.context.scene.camera = cam

# ---------- Render ----------
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.render.resolution_x = RES_X
scene.render.resolution_y = RES_Y
scene.render.film_transparent = True    # fondo transparente
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'

def ease(t):
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2

def set_state(e):
    lift = math.sin(math.pi * e)
    for name, obj in curves.items():
        spline = obj.data.splines[0]
        for i, p in enumerate(spline.bezier_points):
            a = KNOTTED[name][i]
            b = LOOSE[name][i]
            x = a[0] + (b[0] - a[0]) * e + math.sin(e * math.pi + i) * 0.03 * lift
            y = a[1] + (b[1] - a[1]) * e
            z = a[2] + (b[2] - a[2]) * e + lift * (0.08 + i * 0.015)
            p.co = Vector((x, y, z))
            p.handle_left_type = 'AUTO'
            p.handle_right_type = 'AUTO'
    knot_obj.scale = (max(0.001, 1 - e * 0.8),) * 3
    knot_obj.hide_render = e > 0.97

for f in range(FRAMES):
    t = f / (FRAMES - 1)
    set_state(ease(t))
    scene.render.filepath = os.path.join(OUT_DIR, f"lazo_{f:02d}.png")
    bpy.ops.render.render(write_still=True)
    print("Render", f + 1, "de", FRAMES)

print("Listo. Imágenes en:", OUT_DIR)
