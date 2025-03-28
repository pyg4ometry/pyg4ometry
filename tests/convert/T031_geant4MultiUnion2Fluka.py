import os as _os
import pathlib as _pl
import pyg4ometry.gdml as _gd
import pyg4ometry.geant4 as _g4
import pyg4ometry.convert as _convert
import pyg4ometry.fluka as _fluka
import pyg4ometry.visualisation as _vi
import random as _rand
import numpy as _np
import pyg4ometry.misc as _mi


def Test(
    vis=False, interactive=False, fluka=True, outputPath=None, refFilePath=None, bakeTransform=False
):
    if not outputPath:
        outputPath = _pl.Path(__file__).parent

    reg = _g4.Registry()

    # defines
    wx = _gd.Constant("wx", "100", reg, True)
    wy = _gd.Constant("wy", "100", reg, True)
    wz = _gd.Constant("wz", "100", reg, True)

    bx = _gd.Constant("bx", "10", reg, True)
    by = _gd.Constant("by", "10", reg, True)
    bz = _gd.Constant("bz", "10", reg, True)

    # materials
    wm = _g4.nist_material_2geant4Material("G4_Galactic", reg)
    bm = _g4.nist_material_2geant4Material("G4_Au", reg)

    # solids
    ws = _g4.solid.Box("ws", wx, wy, wz, reg, "cm")
    bs = _g4.solid.Box("bs", bx, by, bz, reg, "cm")

    _rand.seed(1234567890)

    nbox = 15
    solids = []
    transforms = []
    for i in range(0, nbox, 1):
        r = 2 * bx.eval() * _rand.uniform(0, 1)
        t = _np.pi * _rand.uniform(0, 1)
        p = 2 * _np.pi * _rand.uniform(0, 1)
        x = r * _np.sin(t) * _np.cos(p)
        y = r * _np.sin(t) * _np.sin(p)
        z = r * _np.cos(t)
        solids.append(bs)
        transforms.append([[0, t, p], [x, y, z, "cm"]])

    mu = _g4.solid.MultiUnion("mu", solids, transforms, reg, True)
    mu_trans = mu.evaluateParameterWithUnits("transformations")
    for i in range(0, nbox, 1):
        for j in range(0, 2, 1):
            for k in range(0, 3, 1):
                assert round(mu_trans[i][j][k], 6) == round((10.0**j) * transforms[i][j][k], 6)

    # structure
    wl = _g4.LogicalVolume(ws, wm, "wl", reg)
    bl = _g4.LogicalVolume(mu, bm, "ml", reg)
    mp = _g4.PhysicalVolume([0, 0, 0], [0, 0, 0], bl, "m_pv1", wl, reg)

    # set world volume
    reg.setWorld(wl.name)

    # test extent of physical volume
    extentBB = wl.extent(includeBoundingSolid=True)

    # gdml output
    w = _gd.Writer()
    w.addDetector(reg)
    w.write(outputPath / "T031_geant4MultiUnion2Fluka.gdml")

    # fluka conversion
    if not bakeTransform:
        outputFile = outputPath / "T031_geant4MultiUnion2Fluka.inp"
    else:
        outputFile = outputPath / "T031_geant4MultiUnion2Fluka_baked.inp"

    if fluka:
        freg = _convert.geant4Reg2FlukaReg(reg, bakeTransforms=bakeTransform)

        # fluka running
        freg.addDefaults(default="PRECISIO")
        freg.addBeam(energy=10)
        freg.addBeamPos()
        freg.addUsrBin(name="bin1")
        freg.addUsrBin(name="bin2")
        freg.addLowMatAllMaterials()
        # freg.addLowPwxs()
        freg.addRandomiz()
        freg.addStart(maxPrimHistories=100)

        w = _fluka.Writer()
        w.addDetector(freg)
        w.write(outputFile)

    # flair output file
    f = _fluka.Flair(outputFile, extentBB)
    f.write(outputPath / "T031_geant4MultiUnion2Fluka.flair")

    # visualisation
    v = None
    if vis:
        v = _vi.VtkViewer()
        v.addLogicalVolume(reg.getWorldVolume())
        v.addAxes(_vi.axesFromExtents(extentBB)[0])
        v.view(interactive=interactive)

    _mi.compareNumericallyWithAssert(refFilePath, outputFile)

    return {"greg": reg, "freg": freg}


if __name__ == "__main__":
    Test()
