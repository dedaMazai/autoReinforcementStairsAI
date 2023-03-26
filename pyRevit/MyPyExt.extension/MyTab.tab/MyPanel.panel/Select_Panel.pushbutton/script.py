import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('IronPython.Wpf')

clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import Options, Transaction, ElementId
# from Geometry import Geometry
# from Stair_rebar import Stair_rebar
# doc = __revit__.ActiveUIDocument.Document

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

class MyWindow(Windows.Window):

    def __init__(self):
        wpf.LoadComponent(self, xamlfile)

    def RUN_Click(self, sender, args):
        print(self.safeyer)
        # findPanel = self.PanelFind.Text
        # replacePanel = self.PanelReplace.Text
        # findCircuit = self.CircuitFind.Text
        # replaceCircuit = self.CircuitReplace.Text
        # self.Close()

MyWindow().ShowDialog()








class MyWindow(Windows.Window):

    def __init__(self):
        self.safeyer = None
        wpf.LoadComponent(self, xamlfile)

    def End_Click(self, sender, args):
        self.Close()
        self.safeyer = revit.pick_element()
        print(self.safeyer)
        MyWindow().ShowDialog()

    def RUN_Click(self, sender, args):
        print(self.safeyer)

MyWindow().ShowDialog()
