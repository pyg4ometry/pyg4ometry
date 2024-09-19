import vtk as _vtk

import pyg4ometry.transformation as _transformation
import pyg4ometry.visualisation.ViewerBase as _ViewerBase

import random as _random

try:
    import bpy as _bpy

    print("Blender pyg4ometry imported")
except ImportError:
    pass


class BlenderViewer(_ViewerBase):
    def __init__(self):
        super().__init__()
        self.instanceBlenderOptions = {}

    def createBlenderObjects(self, option="unique"):
        if option == "unique":
            self.createBlenderObjectsUnique()

    def createBlenderObjectsUnique(self):

        for motherKey in self.instancePlacements:
            print(motherKey)
            # print(self.instancePlacements[motherKey])

            placements = self.instancePlacements[motherKey]

            for placement in placements:
                mesh = self.localmeshes[motherKey].clone()

                axisAndAngle = _transformation.matrix2axisangle(placement["transformation"])
                # mesh.rotate(axisAndAngle[0], -_transformation.rad2deg(axisAndAngle[1]))
                # mesh.translate(placement["translation"])

                vertsAndPolys = mesh.toVerticesAndPolygons()

                mesh_blender = _bpy.data.meshes.new(placement["name"])
                mesh_blender.from_pydata(vertsAndPolys[0], [], vertsAndPolys[1])
                mesh_blender.update()

                # make object
                object_blender = _bpy.data.objects.new(placement["name"], mesh_blender)
                object_blender.scale = (0.001, 0.001, 0.001)
                object_blender.location = placement["translation"] * 0.001
                object_blender.rotation_mode = "AXIS_ANGLE"
                object_blender.rotation_axis_angle = (axisAndAngle[1], *axisAndAngle[0])

                # make random color material
                material_blender = _bpy.data.materials.new(placement["name"])
                material_blender.diffuse_color = (
                    _random.random(),
                    _random.random(),
                    _random.random(),
                    _random.random(),
                )
                object_blender.active_material = material_blender

                # make collection
                collection_blender = _bpy.data.collections.new(placement["name"])
                _bpy.context.scene.collection.children.link(collection_blender)

                # add object to scene collection
                collection_blender.objects.link(object_blender)
