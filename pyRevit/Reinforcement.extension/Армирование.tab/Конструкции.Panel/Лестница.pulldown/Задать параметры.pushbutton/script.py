import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('IronPython.Wpf')

clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import Options, Transaction, ElementId
from Geometry import Geometry
from Stair_rebar import Stair_rebar
doc = __revit__.ActiveUIDocument.Document

clr.AddReference('RevitNodes')
import Revit
clr.ImportExtensions(Revit.Elements)
clr.ImportExtensions(Revit.GeometryConversion)

import wpf
from System import Windows

from pyrevit import revit
from pyrevit import script
xamlfile = script.get_bundle_file('ui.xaml')

logger = script.get_logger()

with revit.Transaction('Update Keynotes'):

    class Stair(Geometry, Stair_rebar):

        def __init__(
            self,
            element,
            doc,
            safeLayer,
            anchoringLength,
            generalRebarDiameter,
            studRebarDiameter,
            rebarStep,
            steelGeneralClass,
            steelStudsClass,
        ):
            self.element = element
            self.doc = doc
            self.geometry = self.element.Geometry[Options()]
            super(Stair, self).__init__(
                safeLayer,
                anchoringLength,
                generalRebarDiameter,
                studRebarDiameter,
                rebarStep,
                steelGeneralClass,
                steelStudsClass,
            )

    class MyWindow(Windows.Window):

        def __init__(self):
            wpf.LoadComponent(self, xamlfile)

        def RUN_Click(self, sender, args):
            self.Close()
            stair = revit.pick_element()

            newStair = Stair(
                stair,
                doc,
                int(self.safeLayer.Text),
                int(self.anchoringLength.Text),
                int(self.generalRebarDiameter.Text),
                int(self.studRebarDiameter.Text),
                int(self.rebarStep.Text),
                int(self.steelGeneralClass.Text),
                int(self.steelStudsClass.Text),
            )

    MyWindow().ShowDialog()
