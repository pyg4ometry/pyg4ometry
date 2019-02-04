from SolidBase import SolidBase as _SolidBase
from pyg4ometry.geant4.Registry import registry as _registry

import pyg4ometry.exceptions
from pyg4ometry.transformation import *

import logging as _log
import copy as _copy

class Subtraction(_SolidBase):
    """
    output = obj1 - obj2
    name = name
    obj1 = unrotated, untranslated solid
    obj2 = solid rotated and translated according to tra2
    tra2 = [rot,tra] = [[a,b,g],[dx,dy,dz]]
    """
    def __init__(self,name, obj1name, obj2name, tra2, registry=None):
        self.type = "Subtraction"
        self.name = name
        self.obj1name = obj1name
        self.obj2name = obj2name
        self.tra2 = tra2
        self.mesh = None

        self.dependents = []
        obj1 = self.registry.solidDict[self.obj1name]
        obj2 = self.registry.solidDict[self.obj2name]
        obj1.dependents.append(self) 
        obj2.dependents.append(self)

        if registry:
            registry.addSolid(self)
            self.registry = registry 

    def __repr__(self):
        return 'Subtraction : ('+str(self.obj1)+') - ('+str(self.obj2)+')'

    def pycsgmesh(self):

        print 'subtraction.pycshmesh>' 

        # look up solids in registry 
        obj1 = self.registry.solidDict[self.obj1name]
        obj2 = self.registry.solidDict[self.obj2name]

        # transformation 
        rot = tbxyz(self.tra2[0].eval())
        tlate = self.tra2[1].eval()

        # get meshes 
        print 'subtraction.pycsgmesh> mesh1'
        m1 = obj1.pycsgmesh()
        print 'subtraction.pycsgmesh> mesh2'
        m2 = obj2.pycsgmesh().clone()

        m2.rotate(rot[0],-rad2deg(rot[1]))
        m2.translate(tlate)

        self.obj2mesh = m2

        print 'subtraction.pycshmsh> subtraction'
        mesh = m1.subtract(m2)
        if not mesh.toPolygons():
            raise pyg4ometry.exceptions.NullMeshError(self)

        return mesh
