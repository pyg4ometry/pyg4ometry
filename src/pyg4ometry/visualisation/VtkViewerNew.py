import vtk as _vtk

from .. import transformation as _transformation
from . import ViewerBase as _ViewerBase
from . import Convert as _Convert
from . import VisualisationOptions as _VisOptions
from .VisualisationOptions import (
    getPredefinedMaterialVisOptions as _getPredefinedMaterialVisOptions,
)

# from pyg4ometry.pycgal.Polygon_mesh_processing import isotropic_remeshing as _isotropic_remeshing


class VtkViewerNew(_ViewerBase):
    """
    Visualiser.

    :param defaultCutters: whether to overlay the default red, green, blue outlines throughout the geometry
    :type defaultCutters: bool
    :param axisCubeWidget: whether to add the orientation cube in the bottom left or not
    :type axisCubeWidget: bool
    """

    def __init__(self, defaultCutters=True, axisCubeWidget=True):
        super().__init__()

        self.initVtk()
        self.clear()

        self.cutterOrigins = {}
        self.cutterNormals = {}
        self.cutterColors = {}

        self.bClipper = False
        self.bClipperCutter = False
        self.clipperOrigin = None
        self.clipperNormal = None

        self.clipperPlaneWidget = None

        if defaultCutters:
            self.addCutterXYZ()
        if axisCubeWidget:
            self.addAxesWidget()

    def initVtk(self):
        # create a renderer
        self.ren = _vtk.vtkRenderer()
        self.ren.SetBackground(1.0, 1.0, 1.0)

        # create a rendering window
        self.renWin = _vtk.vtkRenderWindow()
        self.renWin.AddRenderer(self.ren)
        self.renWin.SetSize(1024, 1024)

        # create a rendering window interactor
        self.iren = _vtk.vtkRenderWindowInteractor()
        self.iren.SetRenderWindow(self.renWin)

        # add the custom style
        self.interactorStyle = MouseInteractorNamePhysicalVolume(self.ren, self)
        self.interactorStyle.SetDefaultRenderer(self.ren)
        self.iren.SetInteractorStyle(self.interactorStyle)

    def clear(self):
        super().clear()

        self.polydata = {}
        self.actors = {}
        self.cutters = {}  # cut filters
        self.clippers = []  # clip filters
        self.axes = []  # axes actors

        self.instanceNameDict = {}  # instance transformation to PV name

        self.bBuiltPipelines = False

        # remove all actors
        for a in self.ren.GetActors():
            self.ren.RemoveActor(a)

    def addAxes(self, length=20.0, origin=(0, 0, 0)):
        """
        Add x,y,z axis to the scene.

        :param length: float - length of each axis in mm
        :param origin: (float,float,float) - (x,y,z) of origin in mm
        """
        axes = _vtk.vtkAxesActor()

        # transform to move axes
        tran = _vtk.vtkTransform()
        tran.Translate(origin[0], origin[1], origin[2])
        axes.SetUserTransform(tran)

        self.axes.append(axes)

        axes.SetTotalLength(length, length, length)
        self.ren.AddActor(axes)

    def setAxes(self, iAxes, length, origin):
        aa = self.axes[iAxes]

    def addAxesWidget(self):
        axesActor = _vtk.vtkAnnotatedCubeActor()
        axesActor.SetXPlusFaceText("+x")
        axesActor.SetXMinusFaceText("-x")
        axesActor.SetYPlusFaceText("+y")
        axesActor.SetYMinusFaceText("-y")
        axesActor.SetZPlusFaceText("+z")
        axesActor.SetZMinusFaceText("-z")
        axesActor.GetTextEdgesProperty().SetColor(1, 1, 1)
        axesActor.GetTextEdgesProperty().SetLineWidth(2)
        axesActor.GetCubeProperty().SetColor(0.4, 0.4, 0.4)
        self.axesWidget = _vtk.vtkOrientationMarkerWidget()
        self.axesWidget.SetOrientationMarker(axesActor)
        self.axesWidget.SetInteractor(self.iren)
        self.axesWidget.EnabledOn()
        self.axesWidget.InteractiveOn()

    def addCutter(self, name, origin, normal, rgb=None):
        if self.bBuiltPipelines:
            msg = "Need to add cutter before pipelines are built"
            raise RuntimeError(msg)

        if rgb is None:
            rgb = [0.8, 0, 0]
        self.cutterOrigins[name] = origin
        self.cutterNormals[name] = normal
        self.cutterColors[name] = rgb

    def addCutterXYZ(self):
        self.addCutter("yz", [0, 0, 0], [1, 0, 0], [0.8, 0, 0])
        self.addCutter("xz", [0, 0, 0], [0, 1, 0], [0, 0.8, 0])
        self.addCutter("xy", [0, 0, 0], [0, 0, 1], [0, 0, 0.8])

    def setCutter(self, name, origin, normal):
        for c in self.cutters[name]:
            p = c.GetCutFunction()
            p.SetOrigin(*origin)
            p.SetNormal(*normal)

    def addCutterWidget(self):
        pass

    def exportCutter(self, name, fileName):
        self.cuttersAppFlt = _vtk.vtkAppendPolyData()

        for c in self.cutters[name]:
            self.cuttersAppFlt.AddInputConnection(c.GetOutputPort())

        w = _vtk.vtkPolyDataWriter()
        w.SetFileName(fileName)
        w.SetInputConnection(self.cuttersAppFlt.GetOutputPort())
        w.Write()

    def getCutterPolydata(self, name):
        self.cuttersAppFlt = _vtk.vtkAppendPolyData()

        for c in self.cutters[name]:
            self.cuttersAppFlt.AddInputConnection(c.GetOutputPort())

        self.cuttersAppFlt.Update()

        return self.cuttersAppFlt.GetOutput()

    def exportOBJScene(self, fileName="scene"):
        rw = _vtk.vtkRenderWindow()
        rw.AddRenderer(self.renWin.GetRenderers().GetFirstRenderer())

        exporter = _vtk.vtkOBJExporter()
        exporter.SetRenderWindow(rw)
        exporter.SetFilePrefix("./" + fileName)  # create mtl and obj file.
        exporter.Write()

    def exportVRMLScene(self, fileName="scene"):
        rw = _vtk.vtkRenderWindow()
        rw.AddRenderer(self.renWin.GetRenderers().GetFirstRenderer())

        exporter = _vtk.vtkVRMLExporter()
        exporter.SetRenderWindow(rw)
        exporter.SetFileName("./" + fileName)  # create mtl and obj file.
        exporter.Write()

    def exportVTPScene(self, fileName="scene.vtp"):
        rw = _vtk.vtkRenderWindow()
        rw.AddRenderer(self.renWin.GetRenderers().GetFirstRenderer())

        exporter = _vtk.vtkSingleVTPExporter()
        exporter.SetRenderWindow(rw)
        exporter.SetFileName("./" + fileName)  # create mtl and obj file.
        exporter.Write()

    def exportVtkGLTFScene(self, fileName="scene.gltf"):
        rw = _vtk.vtkRenderWindow()
        rw.AddRenderer(self.renWin.GetRenderers().GetFirstRenderer())

        exporter = _vtk.vtkGLTFExporter()
        exporter.SetRenderWindow(rw)
        exporter.InlineDataOn()
        exporter.SetFileName("./" + fileName)
        exporter.Write()

    def addClipper(self, origin, normal, bClipperCutter=False, bClipperCloseCuts=True):
        if self.bBuiltPipelines:
            msg = "Need to add clipper before pipelines are built"
            raise RuntimeError(msg)

        self.bClipper = True
        self.clipperOrigin = origin
        self.clipperNormal = normal
        self.bClipperCutter = bClipperCutter
        self.bClipperCloseCuts = bClipperCloseCuts

        if self.bClipperCutter:
            self.addCutter("clipperCutter", origin, normal)

    def setClipper(self, origin, normal):
        for c in self.clippers:
            p = c.GetClipFunction()
            p.SetOrigin(*origin)
            p.SetNormal(*normal)

        if self.bClipperCutter:
            self.setCutter("clipperCutter", origin, normal)

        if self.clipperPlaneWidget:
            self.clipperPlaneWidget.GetRepresentation().SetNormal(*normal)
            self.clipperPlaneWidget.GetRepresentation().SetOrigin(*origin)

    def addClipperWidget(self):
        if not self.bBuiltPipelines:
            msg = (
                "Need to build pipelines before adding clipper widget e.g. v.bulidPipelinesAppend()"
            )
            raise RuntimeError(msg)

        if len(self.clippers) == 0:
            msg = "Need to add a clipping plane adding clipper widget e.g. v.addClipper([0, 0, 0], [0, 0, 1], True"
            raise RuntimeError(msg)

        plaRep = _vtk.vtkImplicitPlaneRepresentation()
        # plaRep.SetPlaceFactor(1.25)
        plaRep.PlaceWidget(next(iter(self.actors.values())).GetBounds())
        plaRep.SetNormal(self.clippers[0].GetClipFunction().GetNormal())
        plaRep.SetOrigin(self.clippers[0].GetClipFunction().GetOrigin())

        self.clipperPlaneWidget = _vtk.vtkImplicitPlaneWidget2()
        self.clipperPlaneWidget.SetInteractor(self.iren)
        self.clipperPlaneWidget.SetRepresentation(plaRep)

        self.clipperPlaneWidget.AddObserver("InteractionEvent", self.updateClipperPlaneCallback)

    def updateClipperPlaneCallback(self, obj, event):
        rep = obj.GetRepresentation()

        plane = _vtk.vtkPlane()
        rep.GetPlane(plane)
        self.setClipper(plane.GetOrigin(), plane.GetNormal())

    def _polydata2Actor(self, polydata):
        pass

    def buildPipelines(self):
        pass

    def buildPipelinesSeparate(self):
        # loop over meshes and create polydata
        for k in self.localmeshes:
            pd = _Convert.pycsgMeshToVtkPolyData(self.localmeshes[k])
            self.polydata[k] = pd

        # loop over polydata and create actors for instances
        for k in self.instancePlacements:
            ips = self.instancePlacements[k]  # (i)nstance (p)placement(s)
            vos = self.instanceVisOptions[k]  # (v)isualisation (o)ption(s)
            pd = self.polydata[k]
            for ip, i in zip(ips, range(len(ips))):
                triFlt = _vtk.vtkTriangleFilter()  # (tri)angle (F)i(lt)er
                triFlt.AddInputData(pd)
                map = _vtk.vtkPolyDataMapper()  # vtkPolyData(Map)per
                map.ScalarVisibilityOff()
                map.SetInputConnection(triFlt.GetOutputPort())
                actor = _vtk.vtkActor()  # vtk(Actor)
                actor.SetMapper(map)
                vtrans = _Convert.pyg42VtkTransformation(ip["transformation"], ip["translation"])
                actor.SetUserMatrix(vtrans)
                visopt = vos[i]
                rgb = visopt.colour
                alpha = visopt.alpha
                actor.GetProperty().SetColor(rgb)
                actor.GetProperty().SetOpacity(alpha)

                self.actors[k + str(i)] = actor
                self.ren.AddActor(actor)

                #################
                # Cutters
                #################
                normFlt = _vtk.vtkPolyDataNormals()  #
                normFlt.SetFeatureAngle(179)
                normFlt.SetInputConnection(triFlt.GetOutputPort())

                normFlt = triFlt  # bypass the normal filter

                # Add cutters
                for ck in self.cutterOrigins:
                    p = self.cutterOrigins[ck]
                    n = self.cutterNormals[ck]

                    plane = _vtk.vtkPlane()
                    plane.SetOrigin(*p)
                    plane.SetNormal(*n)

                    cutTransFlt = _vtk.vtkTransformPolyDataFilter()
                    vtransCut = _vtk.vtkTransform()
                    vtransCut.SetMatrix(vtrans)
                    cutTransFlt.SetTransform(vtransCut)
                    cutTransFlt.SetInputConnection(normFlt.GetOutputPort())

                    cutFlt = _vtk.vtkCutter()
                    cutFlt.SetCutFunction(plane)
                    cutFlt.SetInputConnection(cutTransFlt.GetOutputPort())

                    try:
                        self.cutters[ck].append(cutFlt)
                    except KeyError:
                        self.cutters[ck] = []
                        self.cutters[ck].append(cutFlt)

                    cutMap = _vtk.vtkPolyDataMapper()
                    cutMap.ScalarVisibilityOff()
                    cutMap.SetInputConnection(cutFlt.GetOutputPort())

                    cutActor = _vtk.vtkActor()  # vtk(Actor)
                    cutActor.SetMapper(cutMap)
                    cutActor.GetProperty().SetLineWidth(2)
                    cc = self.cutterColors[ck]
                    cutActor.GetProperty().SetColor(*cc)
                    cutActor.GetProperty().SetRepresentationToSurface()
                    self.actors[k + "_" + ck] = cutActor
                    self.ren.AddActor(cutActor)

        self.bBuiltPipelines = True

    def buildPipelinesAppend(self):
        # loop over meshes and create polydata
        for k in self.localmeshes:
            pd = _Convert.pycsgMeshToVtkPolyData(self.localmeshes[k])
            # pd.SetObjectName(k)
            self.polydata[k] = pd

        appFltDict = {}
        visOptDict = {}

        # loop over polydata and create actors for instances
        for k in self.instancePlacements:
            vos = self.instanceVisOptions[k]  # (v)isualisation (o)ption(s)

            ips = self.instancePlacements[k]  # (i)nstance (p)placement(s)
            pd = self.polydata[k]

            for ip, i in zip(ips, range(len(ips))):
                if str(vos[i]) in appFltDict:
                    appFlt = appFltDict[str(vos[i])]
                else:
                    appFlt = _vtk.vtkAppendPolyData()
                    appFltDict[str(vos[i])] = appFlt
                    visOptDict[str(vos[i])] = vos[i]

                triFlt = _vtk.vtkTriangleFilter()  # (tri)angle (F)i(lt)er
                triFlt.AddInputData(pd)

                traFlt = _vtk.vtkTransformPolyDataFilter()  # (tra)nsform (F)i(lt)er
                vtramat = _Convert.pyg42VtkTransformation(ip["transformation"], ip["translation"])
                vtra = _vtk.vtkGeneralTransform()
                vtra.Concatenate(vtramat)
                traFlt.SetInputConnection(triFlt.GetOutputPort())
                traFlt.SetTransform(vtra)

                appFlt.AddInputConnection(traFlt.GetOutputPort())

                self.instanceNameDict[traFlt] = ip["name"]

        for k in appFltDict:
            normFlt = _vtk.vtkPolyDataNormals()  #
            normFlt.SetFeatureAngle(179)
            normFlt.SetInputConnection(appFltDict[k].GetOutputPort())

            normFlt = appFltDict[k]  # bypass the normal filter

            # Add cutters
            for ck in self.cutterOrigins:
                p = self.cutterOrigins[ck]
                n = self.cutterNormals[ck]

                plane = _vtk.vtkPlane()
                plane.SetOrigin(*p)
                plane.SetNormal(*n)

                cutFilt = _vtk.vtkCutter()
                cutFilt.SetCutFunction(plane)
                cutFilt.SetInputConnection(normFlt.GetOutputPort())

                try:
                    self.cutters[ck].append(cutFilt)
                except KeyError:
                    self.cutters[ck] = []
                    self.cutters[ck].append(cutFilt)

                cutMap = _vtk.vtkPolyDataMapper()
                cutMap.ScalarVisibilityOff()
                cutMap.SetInputConnection(cutFilt.GetOutputPort())

                cutActor = _vtk.vtkActor()  # vtk(Actor)
                cutActor.SetMapper(cutMap)
                cutActor.GetProperty().SetLineWidth(2)
                cc = self.cutterColors[ck]
                cutActor.GetProperty().SetColor(*cc)
                cutActor.GetProperty().SetRepresentationToSurface()
                self.actors[k + "_" + ck] = cutActor
                self.ren.AddActor(cutActor)

            # Add clippers
            if self.clipperNormal is not None:
                p = self.clipperOrigin
                n = self.clipperNormal

                plane = _vtk.vtkPlane()
                plane.SetOrigin(*p)
                plane.SetNormal(*n)

                cliFlt = _vtk.vtkClipPolyData()
                cliFlt.SetInputConnection(normFlt.GetOutputPort())
                cliFlt.SetClipFunction(plane)
                cliFlt.GenerateClipScalarsOn()
                cliFlt.GenerateClippedOutputOn()

                edgFlt = _vtk.vtkFeatureEdges()
                edgFlt.SetInputConnection(cliFlt.GetOutputPort())
                edgFlt.BoundaryEdgesOn()
                edgFlt.FeatureEdgesOff()
                edgFlt.NonManifoldEdgesOff()
                edgFlt.ManifoldEdgesOff()

                edgTriFlt = _vtk.vtkTriangleFilter()
                edgTriFlt.SetInputConnection(edgFlt.GetOutputPort())

                cleFlt = _vtk.vtkContourLoopExtraction()
                cleFlt.SetInputConnection(edgTriFlt.GetOutputPort())
                # cleFlt.SetLoopClosureToBoundary()
                # cleFlt.SetLoopClosureToOff()

                strFlt = _vtk.vtkStripper()
                strFlt.SetInputConnection(cleFlt.GetOutputPort())

                visOpt = visOptDict[k]

                edgMap = _vtk.vtkPolyDataMapper()
                edgMap.SetInputConnection(strFlt.GetOutputPort())
                edgMap.SetResolveCoincidentTopologyToPolygonOffset()
                edgMap.SetRelativeCoincidentTopologyPolygonOffsetParameters(0, -3 * visOpt.depth)
                edgMap.ScalarVisibilityOff()
                edgActor = _vtk.vtkActor()
                edgActor.SetMapper(edgMap)

                if visOpt.representation == "wireframe":
                    edgActor.GetProperty().SetRepresentationToWireframe()

                edgActor.GetProperty().SetOpacity(visOpt.alpha)
                edgActor.GetProperty().SetColor(*visOpt.colour)

                if self.bClipperCloseCuts:
                    self.actors[k + "_clipper"] = edgActor
                    self.ren.AddActor(edgActor)

                self.clippers.append(cliFlt)

            visOpt = visOptDict[k]

            map = _vtk.vtkPolyDataMapper()  # vtkPolyData(Map)per
            map.ScalarVisibilityOff()
            map.SetResolveCoincidentTopologyToPolygonOffset()
            map.SetRelativeCoincidentTopologyPolygonOffsetParameters(0, 3 * visOpt.depth)

            if not self.bClipper:
                map.SetInputConnection(normFlt.GetOutputPort())
            else:
                map.SetInputConnection(cliFlt.GetClippedOutputPort())
                self.ren.GetActiveCamera().SetFocalPoint(0, 0, 0)

            actor = _vtk.vtkActor()  # vtk(Actor)
            actor.SetMapper(map)
            self.actors[k] = actor

            if visOpt.representation == "wireframe":
                actor.GetProperty().SetRepresentationToWireframe()

            actor.GetProperty().SetOpacity(visOpt.alpha)
            actor.GetProperty().SetColor(*visOpt.colour)

            self.ren.AddActor(actor)

        self.bBuiltPipelines = True

    def buildPipelinesTransformed(self):
        pass

    def render(self):
        if not self.bBuiltPipelines:
            msg = "Pipelines have not been built"
            raise RuntimeError(msg)

        # Render
        self.renWin.Render()

    def view(self, interactive=True, resetCamera=False):
        if not self.bBuiltPipelines:
            msg = "Pipelines have not been built"
            raise RuntimeError(msg)

        # enable user interface interactor
        self.iren.Initialize()

        # Camera setup
        if resetCamera:
            self.ren.ResetCamera()

        # Render
        self.renWin.Render()

        if self.clipperPlaneWidget:
            self.clipperPlaneWidget.On()

        if interactive:
            self.iren.Start()

    def __repr__(self):
        return ""

    def addTracks(self, pd):
        mapper = _vtk.vtkPolyDataMapper()
        if _vtk.VTK_MAJOR_VERSION <= 5:
            # mapper.SetInput(reader.GetOutput())
            mapper.SetInput(pd)
        else:
            mapper.SetInputData(pd)

        mapper.ScalarVisibilityOff()
        actor = _vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetRepresentationToWireframe()
        actor.GetProperty().SetColor(1, 0, 0)
        actor.GetProperty().SetOpacity(0.5)
        actor.GetProperty().SetLineWidth(2)

        self.ren.AddActor(actor)

    def addScoringMesh(self, gd):
        colorFunc = _vtk.vtkColorTransferFunction()
        colorFunc.AddRGBPoint(-10, 1, 1, 1)
        colorFunc.AddRGBPoint(0, 0, 1, 0)

        opacity = _vtk.vtkPiecewiseFunction()

        volumeProperty = _vtk.vtkVolumeProperty()
        volumeProperty.SetColor(colorFunc)
        volumeProperty.SetScalarOpacity(opacity)
        volumeProperty.SetInterpolationTypeToLinear()
        volumeProperty.SetIndependentComponents(2)

        volumeMapper = _vtk.vtkOpenGLGPUVolumeRayCastMapper()
        volumeMapper.SetInputData(gd)
        volumeMapper.SetBlendModeToMaximumIntensity()

        volume = _vtk.vtkVolume()
        volume.SetMapper(volumeMapper)
        volume.SetProperty(volumeProperty)
        volume.RotateY(-90)

        self.ren.AddVolume(volume)


class VtkViewerColouredNew(VtkViewerNew):
    """
    Visualiser that extends VtkViewer. Introduces control over colours.

    :Keyword Arguments:
        * **materialVisOptions**: {"materialName": :class:`VisualisationOptions` or list or tuple, ...}
        * **defaultColour** (str): "random" or [r,g,b]

    :Examples:

    >>> vMaterialMap = VtkViewerColoured(materialVisOptions={"G4_WATER":[0,0,1]})
    >>> vRandom = VtkViewerColoured(defaultColour="random")
    >>> vColoured = VtkViewerColoured(defaultColour=[0.1,0.1,0.1])
    >>> vColourAlpha = VtkViewerColoured(defaultColour=[0.1,0.1,0.1,0.5])

    of use visualisation options instances

    >>> vo = pyg4ometry.visualisation.VisualisationOptions()
    >>> vo.colour = [0.1,1.0,0.5]
    >>> vo.alpha = 0.3
    >>> options = {'G4_WATER':vo}
    >>> vis = VtkViewerColoured(materialVisOptions=options)

    If the value in the materialVisOptions is a list or a tuple, it will be upgraded
    to a :class:`VisualisationOptions` instance.
    """

    def __init__(self, *args, defaultColour=None, materialVisOptions=None, **kwargs):
        super().__init__(*args, **kwargs)

        self._defaultVis = _VisOptions()
        self._defaultVis.randomColour = defaultColour == "random"
        if type(defaultColour) is list:
            self._defaultVis.colour = defaultColour

        # loop over dictionary of material vis options - if value is list(rgba)
        # convert to vis options instance, make invisible if alpha is 0
        if materialVisOptions:
            for k, v in materialVisOptions.items():
                if type(v) is list or type(v) is tuple:
                    vi = _VisOptions()
                    vi.colour = v[:3]
                    if any(i > 1 for i in vi.colour):
                        vi.colour = [i / 255.0 for i in vi.colour]
                    if len(v) > 3:
                        vi.alpha = v[3]
                        vi.visible = vi.alpha != 0
                    self.materialVisOptions[k] = vi
                else:
                    self.materialVisOptions[k] = v

    def _getDefaultVis(self, pv):
        return self._defaultVis


class VtkViewerColouredMaterialNew(VtkViewerColouredNew):
    """
    Extension of VtkViewerColoured that uses a default material dictionary for
    several common materials. Material colours are in defined Colour.py for many
    Geant4, FLUKA and BDSIM materials.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, materialVisOptions=_getPredefinedMaterialVisOptions(), **kwargs)


class MouseInteractorNamePhysicalVolume(_vtk.vtkInteractorStyleTrackballCamera):
    def __init__(self, renderer, vtkviewer):
        self.AddObserver("RightButtonPressEvent", self.rightButtonPressEvent)

        self.ren = renderer
        self.vtkviewer = vtkviewer

        self.highLightActor = None
        self.highLightTextActor = None

    def removeHighLight(self):
        if self.highLightActor:
            self.ren.RemoveActor(self.highLightActor)
            self.ren.GetRenderWindow().Render()

    def removeHighLightText(self):
        if self.highLighTextActor:
            self.ren.RemoveActor(self.highLightTextActor)
            self.ren.GetRenderWindow().Render()

    def rightButtonPressEvent(self, obj, event):
        if self.highLightActor:
            self.ren.RemoveActor(self.highLightActor)

        clickPos = self.GetInteractor().GetEventPosition()
        # print("clickPos> ", clickPos)

        picker = _vtk.vtkPropPicker()
        picker.Pick(clickPos[0], clickPos[1], 0, self.ren)
        actor = picker.GetActor()

        pointPicker = _vtk.vtkPointPicker()
        pointPicker.Pick(clickPos[0], clickPos[1], 0, self.ren)
        # print("pointId>", pointPicker.GetPointId())

        cellPicker = _vtk.vtkCellPicker()
        cellPicker.SetPickClippingPlanes(False)
        cellPicker.Pick(clickPos[0], clickPos[1], 0, self.ren)
        actor = cellPicker.GetActor()

        # possible we don't hit an actor
        if actor is None:
            return

        map = actor.GetMapper()
        self.inalgo = map.GetInputAlgorithm()

        if self.inalgo.GetClassName() == "vtkClipPolyData":
            appPolyData = self.inalgo.GetInputAlgorithm()
        elif self.inalgo.GetClassName() == "vtkAppendPolyData":
            appPolyData = self.inalgo
        else:
            appPolyData = (
                self.inalgo.GetInputAlgorithm()
                .GetInputAlgorithm()
                .GetInputAlgorithm()
                .GetInputAlgorithm()
                .GetInputAlgorithm()
            )

        # print(self.inalgo.GetClassName(), appPolyData.GetClassName())

        point = self.inalgo.GetOutput().GetPoint(cellPicker.GetPointId())
        # print("pointPos>", point)

        # loop over appendPolyData and find closest
        dmin = 1e99
        di = -1
        pdmin = None
        pdamin = None
        for ipd in range(0, appPolyData.GetNumberOfInputConnections(0), 1):
            pd = appPolyData.GetInput(ipd)  # polydata
            pda = appPolyData.GetInputAlgorithm(0, ipd)  # polydata algorithm
            pdd = _vtk.vtkImplicitPolyDataDistance()
            pdd.SetInput(pd)
            dist = pdd.EvaluateFunction(*point)
            if dist < dmin:
                di = ipd
                dmin = dist
                pdmin = pd
                pdamin = pda

        for name, pd in self.vtkviewer.polydata.items():
            if pd == pdamin.GetInputAlgorithm().GetInput():
                lvName = name
        pvName = self.vtkviewer.instanceNameDict[pdamin]
        pvTrans = pdamin.GetTransform()
        [mtra, tra] = _Convert.vtkTransformation2PyG4(pvTrans.GetConcatenatedTransform(0))
        globalExtent = pdmin.GetBounds()
        localExtent = pdamin.GetInput().GetBounds()

        tba = _transformation.matrix2tbxyz(mtra)

        # print("minimum pd>", di, dmin, lvName, pvName, tba, tra, localExtent, globalExtent)

        if self.highLightActor:
            self.ren.RemoveActor(self.highLightActor)

        highLightMapper = _vtk.vtkPolyDataMapper()
        highLightMapper.SetInputData(appPolyData.GetInput(di))

        self.highLightActor = _vtk.vtkActor()
        self.highLightActor.SetMapper(highLightMapper)
        self.highLightActor.GetProperty().SetColor(0, 1, 0)
        self.highLightActor.GetProperty().SetOpacity(0.5)

        self.ren.AddActor(self.highLightActor)

        if self.highLightTextActor:
            self.ren.RemoveActor(self.highLightTextActor)

        self.highLightTextActor = _vtk.vtkTextActor()
        self.highLightTextActor.GetTextProperty().SetFontSize(30)
        self.highLightTextActor.GetTextProperty().SetColor(0, 0, 0)
        self.highLightTextActor.SetInput(
            "lv   : "
            + lvName
            + "\n"
            + "pv   : "
            + pvName
            + "\n"
            + "tbr  :"
            + str([f"{v:5.2f}" for v in tba]).strip("'")
            + "\n"
            + "tra  :"
            + str([f"{v:5.2f}" for v in tra]).strip("'")
            + "\n"
            + "local aabb :"
            + str([f"{v:5.2f}" for v in localExtent]).strip("'")
            + "\n"
            + "global aabb :"
            + str([f"{v:5.2f}" for v in globalExtent]).strip("'")
        )
        self.highLightTextActor.SetDisplayPosition(20, 30)
        self.ren.AddActor(self.highLightTextActor)

        # update rendering
        self.ren.GetRenderWindow().Render()
