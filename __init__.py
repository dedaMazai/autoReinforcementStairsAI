# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import Options, Transaction, ElementId
from Geometry import Geometry
from Stair_rebar import Stair_rebar
doc = __revit__.ActiveUIDocument.Document

class Stair(Geometry, Stair_rebar):

    def __init__(self, element, doc):
        self.element = element
        self.doc = doc
        self.geometry = self.element.Geometry[Options()]
        super(Stair, self).__init__()

stair = doc.GetElement(ElementId(2111225))
with Transaction(doc, "Анализ геометрии") as t:
    t.Start()
    stair = Stair(stair, doc)
    t.Commit()



