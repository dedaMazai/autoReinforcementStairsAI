# -*- coding: utf-8 -*- 
from Autodesk.Revit.DB import Options, Solid,GeometryInstance, ElementId, SketchPlane
from Autodesk.Revit.DB import Line, XYZ, SetComparisonResult, FilteredElementCollector, IntersectionResultArray
from math import pi, ceil
from clr import StrongBox
from Stair_rebar import Stair_rebar

class Geometry(object):
    "Класс отвечающий за анализ геометрии."
    def __init__(self):
        self.analys_faces()
        self.define_mesures()
        super(Geometry, self).__init__()

    def define_mesures(self):
        "Снимаем недостающие размеры."
        # Получим толщину марша
        plane = self.diagornal_face.GetSurface()
        stair_thick = float("inf")
        for i in self.tred_faces:
            for point in self.get_all_face_point(i):
                cur_distance = plane.Project(point)[1]
                if stair_thick > cur_distance:
                    stair_thick = cur_distance

        # Толщина марша
        self.stair_thick = stair_thick
        # Вектор направления марша
        self.stair_directioin = self.ricer_faces[0].FaceNormal
        # Угол уклона марша
        self.diagonal_angle = self.diagornal_face.FaceNormal.AngleTo(self.stair_directioin) - pi / 2
        # Ширина марша
        self.stair_width = self.side_faces[0].GetSurface().Project(self.side_faces[1].Origin)[1]
        # Боковая грань которую мы принимаем за главную
        self.gen_side_face = self.side_faces[0]
        # Основное направление армирования лестницы
        self.gen_side_direction = self.gen_side_face.FaceNormal.Negate()
        # Вертикальный вектор
        self.vertical_vector = XYZ(0, 0, 1)
        # Вектор лестницы
        self.diagornal_normal = self.diagornal_face.FaceNormal.Negate()

        # Нижняя площадка толщина
        self.bottom_floor_thick = self.first_tred_face.GetSurface().Project(self.bottom_face.Origin)[1]
        # Нижняя диагональная точка и верхняя диагональная точка
        # Начальная точка вектора - нижняя
        self.bottom_diagonal_point = self.get_common_points(self.diagornal_face, self.bottom_face, self.gen_side_face)[0]
        # Конечная точка диагонали стержня - верхняя
        self.top_diagonal_point = self.get_common_points(self.diagornal_face, self.front_face, self.gen_side_face)[0]
        # Диагональный вектор
        self.diagonal_vector = (self.top_diagonal_point - self.bottom_diagonal_point).Normalize()

    def intersect_point(self, p1, p2, p3, p4):
        "Находит пересечения между линиями на основе точек."
        l1 = Line.CreateBound(p1, p2)
        l1.MakeUnbound()
        l2 = Line.CreateBound(p3, p4)
        l2.MakeUnbound()
        res = StrongBox[IntersectionResultArray]()
        l1.Intersect(l2, res)
        return res.Value[0].XYZPoint

    @property
    def first_tred_face(self):
        first = None
        min_z = float("inf")
        for i in self.tred_faces:
            if i.Origin.Z < min_z:
                first = i
                min_z = i.Origin.Z 
        return first

    @property
    def last_tred_face(self):
        last = None
        max_z = float("-inf")
        for i in self.tred_faces:
            if i.Origin.Z > max_z:
                last = i
                max_z = i.Origin.Z 
        return last

    def create_lines_from_points(self, points):
        lines = []
        point_0 = None
        for point in points:
            if point_0 is None:
                point_0 = point
            else:
                lines.append(Line.CreateBound(point_0, point))
                point_0 = point
        return lines

    def analys_faces(self):
        """
        Анализируем поверхности.

        Анализирует поверхности и разбивает их на несколько массивов
        side_faces - боковые поверхности
        tred_faces - проступь
        ricer_faces - подступенок
        diagornal_face - диагональное поверхность
        bottom_face - нижняя поверхность
        front_face - передняя часть(которая примыкает к плите)
        """
        self.tred_faces = []
        vert_vect = XYZ(0, 0, 1)
        for i in self.faces:
            if i.FaceNormal.IsAlmostEqualTo(vert_vect):
                self.tred_faces.append(i)
        self.ricer_faces = []
        for i in self.tred_faces:
            for j in self.longest_or_shortest_edge(i):
                for k in self.faces:
                    if self.get_common_edge(j, k, i) and k not in self.ricer_faces:
                        self.ricer_faces.append(k)
        self.side_faces = []
        for face_1 in self.faces:
            all_face_have_common_edge = True
            for face_2 in self.tred_faces:
                if not self.have_common_edge(face_1, face_2):
                    all_face_have_common_edge = False
            if all_face_have_common_edge:
                self.side_faces.append(face_1)

        self.diagornal_face = None
        for face in self.faces:
            normal = face.FaceNormal
            if (abs(round(normal.X, 7)) > 0 or abs(round(normal.Y, 7)) > 0) and abs(round(normal.Z, 7)) > 0:
                self.diagornal_face = face

        self.bottom_face = None
        self.front_face = None

        for face in self.faces:
            if self.have_common_edge(face, self.diagornal_face, except_faces=self.side_faces + [self.diagornal_face]):
                if face.FaceNormal.IsAlmostEqualTo(vert_vect.Negate()):
                    self.bottom_face = face
                else:
                    self.front_face = face

        self.ricer_faces.remove(self.front_face)

    @property
    def faces(self):
        if not hasattr(self, "_faces"):
            self._faces = []
            for i in self.geometry:
                if isinstance(i, GeometryInstance):
                    for j in i.GetInstanceGeometry():
                        if isinstance(j, Solid):
                            if j.Volume > 0:
                                self._faces += list(j.Faces)
        return self._faces

    def print_face(self, face):
        "Посмотреть какая плоскость нам нужна."
        plane = face.GetSurface()
        sketchPlane = SketchPlane.Create(self.doc, plane)
        for j in face.GetEdgesAsCurveLoops():
            for i in j:
                self.doc.Create.NewModelCurve(i, sketchPlane)

    def get_face_edges(self, face):
        "Возвращает список из edges."
        edges = []
        for j in face.GetEdgesAsCurveLoops():
            for i in j:
                edges.append(i)
        return edges

    def longest_or_shortest_edge(self, face):
        "Возвращает самые длинные edges."
        max_len = float("-inf")
        edges = self.get_face_edges(face)
        for i in edges:
            cur_len = round(i.ApproximateLength, 5)
            if cur_len > max_len:
                max_len = cur_len
        ret_edges = []
        for i in edges:
            cur_len = round(i.ApproximateLength, 5)
            if cur_len == max_len:
                ret_edges.append(i)
        return ret_edges

    def have_common_edge(self, face_1, face_2, except_faces=[]):
        "Есть ли у поверхностей общая грань."
        if face_1 not in except_faces:
            for i in self.get_face_edges(face_1):
                for j in self.get_face_edges(face_2):
                    if i.Intersect(j) == SetComparisonResult.Equal:
                        return True

    def get_common_edge(self, edge, face, face_2):
        "Возвращает общие edge."
        res = []
        if face != face_2:
            for i in self.get_face_edges(face):
                if i.Intersect(edge) == SetComparisonResult.Equal:
                    res.append(i)
        return res

    def get_all_face_point(self, face):
        "Возьмем все точки с поверхности."
        points = []
        for edge in self.get_face_edges(face):
            if isinstance(edge, Line):
                points.append(edge.GetEndPoint(0))
        return points

    def get_common_points(self, *arg):
        if len(arg) > 1:
            first_points = self.get_all_face_point(arg[0])
            for i in range(1, len(arg)):
                first_points = self._get_common_points(first_points, self.get_all_face_point(arg[i]))
            return first_points

    def _get_common_points(self, points_1, points_2):
        points = []
        for i in points_1:
            for j in points_2:
                if i.IsAlmostEqualTo(j):
                    points.append(i)
                    break
        return points

    @staticmethod
    def to_mm(length):
        return length * 304.8

    @staticmethod
    def to_feet(length):
        return length / 304.8

    @staticmethod
    def to_deg(rad):
        return rad / pi * 180