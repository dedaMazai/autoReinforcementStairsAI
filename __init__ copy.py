# -*- coding: utf-8 -*-
import sys
import clr

clr.AddReference('RevitAPI')

from Autodesk.Revit.DB import Options, Solid,GeometryInstance, Transaction, ElementId, SketchPlane
from Autodesk.Revit.DB import Line, XYZ, SetComparisonResult, FilteredElementCollector, IntersectionResultArray
from math import pi, ceil
doc = IN[8]

dataEnteringNode = IN

stair = IN[7]

with Transaction(doc, "Анализ геометрии") as t:
    t.Start()
    t.Commit()

class Stair_rebar(object):
    def __init__(self):
        # защитный слой
        self.safe_layer = self.to_feet(IN[0])
        # длина анкеровки
        self.anchoring_length = self.to_feet(IN[1])
        # диамер основной арматуры
        self.general_rebar_diameter = self.to_feet(IN[2])
        # диамер дополнительной арматуры
        self.stud_rebar_diameter = self.to_feet(IN[3])
        # шаг арматуры
        self.rebar_step = self.to_feet(IN[4])
        # класс основной арматуры
        self.steel_general_class = IN[5]
        # класс дополнительной арматуры
        self.steel_studs_class = IN[6]
        self.rebar_measures()
        self.create_diagonal_rebar()
        self.create_cross_rebar()
        self.create_studs()
        self.create_step_rebar()

    @property
    def rebar_general_type(self):
        if not hasattr(self, "_rebar_general_type"):
            self._rebar_general_type = self.get_RebarBarType(self.general_rebar_diameter, self.steel_general_class, False)
        return self._rebar_general_type

    @property
    def rebar_stud_type(self):
        if not hasattr(self, "_rebar_stud_type"):
            self._rebar_stud_type = self.get_RebarBarType(self.stud_rebar_diameter, self.steel_studs_class, False)
        return self._rebar_stud_type

    def rebar_measures(self):
        # Размеры для диагональных стержней
        # Ширина для расчета количесва дианональных стержней
        self.diagonal_width_calculate = self.stair_width - self.general_rebar_diameter - self.safe_layer * 2
        # Количество диагональных стержней
        self.diagonal_rebar_count = ceil(self.diagonal_width_calculate / self.rebar_step)
        # Пересчитываем шаг от полученной длины и округляем до 10 мм
        self.diagonal_step_calculate = round(self.diagonal_width_calculate / self.diagonal_rebar_count / self.to_feet(10)) * self.to_feet(10)
        # Пересчитываем ширину раскладки диагональных стержней
        self.diagonal_width_calculate = self.diagonal_step_calculate * self.diagonal_rebar_count
        # Добавляем 1 стержень
        self.diagonal_rebar_count += 1
        # Рассчитываем отступ первого стержня от боковой грани
        self.diagonal_side_space = (self.stair_width - self.diagonal_width_calculate) / 2

    def create_diagonal_rebar(self):
        "Создаем диагональные стержни марша."
        layer_diam_len = self.safe_layer + self.general_rebar_diameter / 2
        # Теперь подними точки на высоту защитного слоя
        p1 = self.bottom_diagonal_point + self.diagonal_normal * layer_diam_len
        p2 = p1 + self.diagonal_vector
        p3 = self.bottom_diagonal_point + self.vertical_vector * (self.bottom_floor_thick - layer_diam_len - self.general_rebar_diameter)
        p4 = p3 + self.stair_directioin

        p5 = self.get_common_points(self.front_face, self.last_tread_face, self.gen_side_face)[0]
        p5 -= layer_diam_len * self.vertical_vector
        p6 = p5 + self.stair_directioin

        point_2 = self.intersect_point(p1, p2, p3, p4)
        point_2 += self.gen_side_direction * self.diagonal_side_space
        point_3 = self.intersect_point(p1, p2, p5, p6)
        point_3 += self.gen_side_direction * self.diagonal_side_space

        # Расчитываем крайние точки стержней
        point_1 = point_2  + self.stair_directioin * self.anchoring_length
        point_4 = point_3  - self.stair_directioin * self.anchoring_length
        # Упорядоченный список точек стержня
        points = [point_1, point_2, point_3, point_4]
        # Создаем арматруный стержень на основе точек
        reb = self.create_rebar(self.rebar_general_type, self.gen_side_direction, points, count=self.diagonal_rebar_count, step=self.diagonal_step_calculate)

        p1 = self.bottom_diagonal_point + self.diagonal_normal * (self.stair_thick - layer_diam_len - self.general_rebar_diameter)
        p2 = p1 + self.diagonal_vector
        p3 = self.bottom_diagonal_point + self.vertical_vector * layer_diam_len
        p4 = p3 + self.stair_directioin

        p5 = self.top_diagonal_point + self.vertical_vector * layer_diam_len
        p6 = p5 + self.stair_directioin

        point_2 = self.intersect_point(p1, p2, p3, p4)
        point_2 += self.gen_side_direction * self.diagonal_side_space
        point_3 = self.intersect_point(p1, p2, p5, p6)
        point_3 += self.gen_side_direction * self.diagonal_side_space

        point_1 = point_2  + self.stair_directioin * self.anchoring_length
        point_4 = point_3  - self.stair_directioin * self.anchoring_length

        points = [point_1, point_2, point_3, point_4]
        # Создаем арматруный стержень на основе точек
        reb = self.create_rebar(self.rebar_general_type, self.gen_side_direction, points, count=self.diagonal_rebar_count, step=self.diagonal_step_calculate)

        # Расставим угловые стержни
        p1 = self.bottom_diagonal_point + self.diagonal_normal * layer_diam_len
        p2 = p1 + self.diagonal_vector

        p3 = self.bottom_diagonal_point + self.vertical_vector * layer_diam_len
        p4 = p3 + self.stair_directioin

        point_2 = self.intersect_point(p1, p2, p3, p4)
        point_2 += self.gen_side_direction * self.diagonal_side_space
        point_1 = point_2 + self.stair_directioin * self.anchoring_length
        point_3 = point_2 + self.diagonal_vector * self.anchoring_length

        points = [point_1, point_2, point_3]

        reb = self.create_rebar(self.rebar_general_type, self.gen_side_direction, points, count=self.diagonal_rebar_count, step=self.diagonal_step_calculate)

        # Второй угловой стержень
        p1 = self.top_diagonal_point + self.diagonal_normal * (self.stair_thick - layer_diam_len - self.general_rebar_diameter)
        p2 = p1 + self.diagonal_vector

        p3 = self.get_common_points(self.front_face, self.last_tread_face, self.gen_side_face)[0]
        p3 -= layer_diam_len * self.vertical_vector
        p4 = p3 + self.stair_directioin


        point_2 = self.intersect_point(p1, p2, p3, p4)
        point_2 += self.gen_side_direction * self.diagonal_side_space
        point_1 = point_2 - self.stair_directioin * self.anchoring_length
        point_3 = point_2 - self.diagonal_vector * self.anchoring_length

        points = [point_1, point_2, point_3]

        reb = self.create_rebar(self.rebar_general_type, self.gen_side_direction, points, count=self.diagonal_rebar_count, step=self.diagonal_step_calculate)

    def create_cross_rebar(self):
        "Создаем поперечные стержни."
        layer_diam_len = self.safe_layer + self.general_rebar_diameter * 1.5
        p1 = self.bottom_diagonal_point + self.vertical_vector * layer_diam_len
        p2 = p1 + self.stair_directioin

        p3 = self.bottom_diagonal_point + self.diagonal_normal * layer_diam_len
        p4 = p3 + self.diagonal_vector

        point_1 = self.intersect_point(p1, p2, p3, p4)
        point_1 += self.gen_side_direction * self.safe_layer
        point_2 = point_1 + (self.stair_width - 2 * self.safe_layer) * self.gen_side_direction

        points = [point_1, point_2]

        p5 = self.top_diagonal_point + self.diagonal_normal * layer_diam_len
        distance = p5.DistanceTo(p3)
        rebar_count = floor(distance / self.rebar_step) + 1

        reb = self.create_rebar(self.rebar_general_type, self.diagonal_vector, points, count=rebar_count, step=self.rebar_step)

        point_1 += self.diagonal_normal * (self.stair_thick - layer_diam_len * 2 + self.general_rebar_diameter)
        point_2 += self.diagonal_normal * (self.stair_thick - layer_diam_len * 2 + self.general_rebar_diameter)
        points = [point_1, point_2]

        reb = self.create_rebar(self.rebar_general_type, self.diagonal_vector, points, count=rebar_count, step=self.rebar_step)

    def create_studs(self):
        "Создаем шпильки."
        layer_diam_len = self.safe_layer + self.general_rebar_diameter * 1.5
        p1 = self.bottom_diagonal_point + self.vertical_vector * layer_diam_len
        p2 = p1 + self.stair_directioin

        p3 = self.bottom_diagonal_point + self.diagonal_normal * layer_diam_len
        p4 = p3 + self.diagonal_vector

        p5 = self.top_diagonal_point + self.diagonal_normal * layer_diam_len
        distance = p5.DistanceTo(p3)
        rebar_count = floor(distance / self.rebar_step) + 1

        bend_radius = self.rebar_stud_type.get_Parameter(BuiltInParameter.REBAR_STANDARD_HOOK_BEND_DIAMETER).AsDouble() / 2
        point_1 = self.intersect_point(p1, p2, p3, p4)
        point_1 -= self.diagonal_vector * (bend_radius + self.stud_rebar_diameter / 2)
        point_1 -= self.diagonal_normal * (self.general_rebar_diameter / 2 + self.stud_rebar_diameter )
        point_1 += self.gen_side_direction * self.diagonal_side_space
        point_2 = point_1 + self.diagonal_normal * (self.stair_thick - layer_diam_len * 2 + self.general_rebar_diameter * 2 + self.stud_rebar_diameter * 2)
        hook = self.get_RebarHookType("Стандартный - 180")
        for i in range(1, int(rebar_count), 2):
            cur_point_1 = point_1 + self.rebar_step * i * self.diagonal_vector
            cur_point_2 = point_2 + self.rebar_step * i * self.diagonal_vector
            points = [cur_point_1, cur_point_2]
            reb = self.create_rebar(self.rebar_stud_type, self.gen_side_direction, points, hook_1=hook, hook_2=hook, step=self.diagonal_step_calculate, count=self.diagonal_rebar_count)


    def create_step_rebar(self):
        "Создаем стержни ступеней."
        p3 = self.bottom_diagonal_point + self.diagonal_normal * self.safe_layer
        p4 = self.top_diagonal_point + self.diagonal_normal * self.safe_layer
        for i in self.tread_faces:
            if i == self.first_tread_face:
                continue
            points = self.get_common_points(i, self.gen_side_face)
            p1 = points[0]
            p2 = points[1]

            p1 = p1 if self.stair_directioin.DotProduct(p1) > self.stair_directioin.DotProduct(p2) else p2

            p1 += self.vertical_vector.Negate() * (self.safe_layer + self.stud_rebar_diameter / 2)
            p1 += self.stair_directioin.Negate() * (self.safe_layer + self.stud_rebar_diameter / 2)

            p2 = p1 + self.vertical_vector

            point_2 = p1
            point_1 = self.intersect_point(p1, p2, p3, p4)
            p2 = p1 + self.stair_directioin
            # if i != self.last_tread_face:
            point_3 = self.intersect_point(p1, p2, p3, p4)
            # else:
            #     last_points = self.get_common_points(self.front_face, self.gen_side_face)
            #     last_p3 = last_points[0] + self.stair_directioin * self.safe_layer
            #     last_p4 = last_points[1] + self.stair_directioin * self.safe_layer
            #     point_3 = self.intersect_point(p1, p2, last_p3, last_p4)

            point_1 += self.gen_side_direction * self.diagonal_side_space
            point_2 += self.gen_side_direction * self.diagonal_side_space
            point_3 += self.gen_side_direction * self.diagonal_side_space
            points = [point_1, point_2, point_3]
            # Создаем стержни проступи.
            reb = self.create_rebar(self.rebar_stud_type, self.gen_side_direction, points, step=self.diagonal_step_calculate, count=self.diagonal_rebar_count)

            point_2 += (self.stud_rebar_diameter / 2 + self.general_rebar_diameter / 2) * self.vertical_vector.Negate()
            point_2 += (self.stud_rebar_diameter / 2 + self.general_rebar_diameter / 2) * self.stair_directioin.Negate()
            point_3 = point_2 + self.gen_side_direction * (self.stair_width - self.safe_layer * 2)
            points = [point_2, point_3]
            # Создаем горизонтальные стержни проступи.
            reb = self.create_rebar(self.rebar_general_type, self.stair_directioin.Negate(), points, step=self.to_feet(55), count=3)


    def get_RebarBarType(self, diam, mark, is_pag):
        "Получает тип арматурного стержня."
        rebars = FilteredElementCollector(self.doc).OfClass(RebarBarType).ToElements()
        for rebar in rebars:
            if rebar.LookupParameter('Рзм.Диаметр').AsDouble() == diam:
                if rebar.LookupParameter('Арм.КлассЧисло').AsDouble() == mark:
                    if bool(rebar.LookupParameter('Рзм.ПогМетрыВкл').AsInteger()) == is_pag:
                        return rebar

    def get_RebarHookType(self, name):
        "Получает отгиб по имени."
        rebars = FilteredElementCollector(self.doc).OfClass(RebarHookType).ToElements()
        for rebar in rebars:
            if name in rebar.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString():
                return rebar

    def create_rebar(self, bar_type, normal, points, step=0, count=0, hook_1=None, hook_2=None):
        rho = RebarHookOrientation.Right
        rs = RebarStyle.Standard
        lines = self.create_lines_from_points(points)
        reb = Rebar.CreateFromCurves(self.doc, rs, bar_type, hook_1, hook_2, self.element, normal, lines, rho, rho, True, True)
        if step and count:
            da = reb.GetShapeDrivenAccessor()
            da.SetLayoutAsNumberWithSpacing(count, step, True, True, True)
        return reb


class Geometry(object):
    "Класс отвечающий за анализ геометрии."
    def __init__(self):
        self.analysis_faces()
        self.define_measures()
        super(Geometry, self).__init__()

    def define_measures(self):
        "Снимаем недостающие размеры."

        plane = self.diagonal_face.GetSurface()
        stair_thick = float("inf")
        for i in self.tread_faces:
            for point in self.get_all_face_point(i):
                cur_distance = plane.Project(point)[1]
                if stair_thick > cur_distance:
                    stair_thick = cur_distance

        # Толщина марша
        self.stair_thick = stair_thick
        # Вектор направления марша
        self.stair_directioin = self.ricer_faces[0].FaceNormal
        # Угол уклона марша
        self.diagonal_angle = self.diagonal_face.FaceNormal.AngleTo(self.stair_directioin) - pi / 2
        # Ширина марша
        self.stair_width = self.side_faces[0].GetSurface().Project(self.side_faces[1].Origin)[1]
        # Боковая грань которую мы принимаем за главную
        self.gen_side_face = self.side_faces[0]
        # Основное направление армирования лестницы
        self.gen_side_direction = self.gen_side_face.FaceNormal.Negate()
        # Вертикальный вектор
        self.vertical_vector = XYZ(0, 0, 1)
        # Вектор лестницы
        self.diagonal_normal = self.diagonal_face.FaceNormal.Negate()

        # Нижняя площадка толщина
        self.bottom_floor_thick = self.first_tread_face.GetSurface().Project(self.bottom_face.Origin)[1]
        # Нижняя диагональная точка и верхняя диагональная точка
        # Начальная точка вектора - нижняя
        self.bottom_diagonal_point = self.get_common_points(self.diagonal_face, self.bottom_face, self.gen_side_face)[0]
        # Конечная точка диагонали стержня - верхняя
        self.top_diagonal_point = self.get_common_points(self.diagonal_face, self.front_face, self.gen_side_face)[0]
        # Диагональный вектор
        self.diagonal_vector = (self.top_diagonal_point - self.bottom_diagonal_point).Normalize()

    def intersect_point(self, start_one, end_one, start_two, end_two):
        "Находит пересечения между линиями на основе точек."
        l1 = Line.CreateBound(start_one, end_one)
        l1.MakeUnbound()
        l2 = Line.CreateBound(start_two, end_two)
        l2.MakeUnbound()
        res = StrongBox[IntersectionResultArray]()
        l1.Intersect(l2, res)
        return res.Value[0].XYZPoint

    @property
    def first_tread_face(self):
        first = None
        min_z = float("inf")
        for i in self.tread_faces:
            if i.Origin.Z < min_z:
                first = i
                min_z = i.Origin.Z
        return first

    @property
    def last_tread_face(self):
        last = None
        max_z = float("-inf")
        for i in self.tread_faces:
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

    def analysis_faces(self):
        self.tread_faces = []
        vert_vect = XYZ(0, 0, 1)
        for i in self.faces:
            if i.FaceNormal.IsAlmostEqualTo(vert_vect):
                self.tread_faces.append(i)

        self.ricer_faces = []
        for i in self.tread_faces:
            for j in self.longest_or_shortest_edge(i):
                for k in self.faces:
                    if self.get_common_edge(j, k, i) and k not in self.ricer_faces:
                        self.ricer_faces.append(k)

        # Боковые плоскости имеют общие линии с каждой проступью
        self.side_faces = []
        for face_1 in self.faces:
            all_face_have_common_edge = True
            for face_2 in self.tread_faces:
                if not self.have_common_edge(face_1, face_2):
                    all_face_have_common_edge = False
            if all_face_have_common_edge:
                self.side_faces.append(face_1)

        self.diagonal_face = None
        for face in self.faces:
            normal = face.FaceNormal
            if (abs(round(normal.X, 7)) > 0 or abs(round(normal.Y, 7)) > 0) and abs(round(normal.Z, 7)) > 0:
                self.diagonal_face = face

        self.bottom_face = None
        self.front_face = None

        for face in self.faces:
            if self.have_common_edge(face, self.diagonal_face, except_faces=self.side_faces + [self.diagonal_face]):
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

class Stair(Geometry, Stair_rebar):

    def __init__(self, element, doc):
        self.element = element
        self.doc = doc
        self.geometry = self.element.Geometry[Options()]
        super(Stair, self).__init__()

stair = Stair(stair, doc)

# Назначьте вывод переменной OUT.
OUT = 0