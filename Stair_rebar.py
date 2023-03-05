# -*- coding: utf-8 -*- 
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInParameter
from Autodesk.Revit.DB.Structure import RebarBarType, Rebar, RebarHookOrientation, RebarStyle, RebarHookType
from common_scripts import echo
from math import pi, ceil, cos, tan, sin, floor

class Stair_rebar(object):
    def __init__(self):
        self.safe_layer = self.to_feet(25)
        self.anchoring_length = self.to_feet(500)
        self.general_rebar_diameter = self.to_feet(10)
        self.stud_rebar_diameter = self.to_feet(6)
        self.rebar_step = self.to_feet(50)
        self.steel_general_class = 500
        self.steel_studs_class = 240
        self.rebar_mesures()
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

    def rebar_mesures(self):
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
        p1 = self.bottom_diagonal_point + self.diagornal_normal * layer_diam_len
        p2 = p1 + self.diagonal_vector
        p3 = self.bottom_diagonal_point + self.vertical_vector * (self.bottom_floor_thick - layer_diam_len - self.general_rebar_diameter)
        p4 = p3 + self.stair_directioin

        p5 = self.get_common_points(self.front_face, self.last_tred_face, self.gen_side_face)[0]
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

        p1 = self.bottom_diagonal_point + self.diagornal_normal * (self.stair_thick - layer_diam_len - self.general_rebar_diameter)
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
        p1 = self.bottom_diagonal_point + self.diagornal_normal * layer_diam_len
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
        p1 = self.top_diagonal_point + self.diagornal_normal * (self.stair_thick - layer_diam_len - self.general_rebar_diameter)
        p2 = p1 + self.diagonal_vector

        p3 = self.get_common_points(self.front_face, self.last_tred_face, self.gen_side_face)[0]
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

        p3 = self.bottom_diagonal_point + self.diagornal_normal * layer_diam_len
        p4 = p3 + self.diagonal_vector

        point_1 = self.intersect_point(p1, p2, p3, p4)
        point_1 += self.gen_side_direction * self.safe_layer
        point_2 = point_1 + (self.stair_width - 2 * self.safe_layer) * self.gen_side_direction

        points = [point_1, point_2]

        p5 = self.top_diagonal_point + self.diagornal_normal * layer_diam_len
        distance = p5.DistanceTo(p3)
        rebar_count = floor(distance / self.rebar_step) + 1

        reb = self.create_rebar(self.rebar_general_type, self.diagonal_vector, points, count=rebar_count, step=self.rebar_step)

        point_1 += self.diagornal_normal * (self.stair_thick - layer_diam_len * 2 + self.general_rebar_diameter)
        point_2 += self.diagornal_normal * (self.stair_thick - layer_diam_len * 2 + self.general_rebar_diameter)
        points = [point_1, point_2]

        reb = self.create_rebar(self.rebar_general_type, self.diagonal_vector, points, count=rebar_count, step=self.rebar_step)

    def create_studs(self):
        layer_diam_len = self.safe_layer + self.general_rebar_diameter * 1.5
        p1 = self.bottom_diagonal_point + self.vertical_vector * layer_diam_len
        p2 = p1 + self.stair_directioin

        p3 = self.bottom_diagonal_point + self.diagornal_normal * layer_diam_len
        p4 = p3 + self.diagonal_vector

        p5 = self.top_diagonal_point + self.diagornal_normal * layer_diam_len
        distance = p5.DistanceTo(p3)
        rebar_count = floor(distance / self.rebar_step) + 1

        bend_radius = self.rebar_stud_type.get_Parameter(BuiltInParameter.REBAR_STANDARD_HOOK_BEND_DIAMETER).AsDouble() / 2
        point_1 = self.intersect_point(p1, p2, p3, p4)
        point_1 -= self.diagonal_vector * (bend_radius + self.stud_rebar_diameter / 2)
        point_1 -= self.diagornal_normal * (self.general_rebar_diameter / 2 + self.stud_rebar_diameter )
        point_1 += self.gen_side_direction * self.diagonal_side_space
        point_2 = point_1 + self.diagornal_normal * (self.stair_thick - layer_diam_len * 2 + self.general_rebar_diameter * 2 + self.stud_rebar_diameter * 2)
        hook = self.get_RebarHookType("Стандартный - 180")
        for i in range(1, int(rebar_count), 2):
            cur_point_1 = point_1 + self.rebar_step * i * self.diagonal_vector
            cur_point_2 = point_2 + self.rebar_step * i * self.diagonal_vector
            points = [cur_point_1, cur_point_2]
            reb = self.create_rebar(self.rebar_stud_type, self.gen_side_direction, points, hook_1=hook, hook_2=hook, step=self.diagonal_step_calculate, count=self.diagonal_rebar_count)


    def create_step_rebar(self):

        p3 = self.bottom_diagonal_point + self.diagornal_normal * self.safe_layer
        p4 = self.top_diagonal_point + self.diagornal_normal * self.safe_layer
        for i in self.tred_faces:
            if i == self.first_tred_face:
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
            if i != self.last_tred_face:
                point_3 = self.intersect_point(p1, p2, p3, p4)
            else:
                last_points = self.get_common_points(self.front_face, self.gen_side_face)
                last_p3 = last_points[0] + self.stair_directioin * self.safe_layer
                last_p4 = last_points[1] + self.stair_directioin * self.safe_layer
                point_3 = self.intersect_point(p1, p2, last_p3, last_p4)
                    
            point_1 += self.gen_side_direction * self.diagonal_side_space
            point_2 += self.gen_side_direction * self.diagonal_side_space
            point_3 += self.gen_side_direction * self.diagonal_side_space
            points = [point_1, point_2, point_3]
            reb = self.create_rebar(self.rebar_stud_type, self.gen_side_direction, points, step=self.diagonal_step_calculate, count=self.diagonal_rebar_count)

            point_2 += (self.stud_rebar_diameter / 2 + self.general_rebar_diameter / 2) * self.vertical_vector.Negate()
            point_2 += (self.stud_rebar_diameter / 2 + self.general_rebar_diameter / 2) * self.stair_directioin.Negate()
            point_3 = point_2 + self.gen_side_direction * (self.stair_width - self.safe_layer * 2)
            points = [point_2, point_3]
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