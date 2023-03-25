# -*- coding: utf-8 -*-
import sys
import clr
from clr import StrongBox

from Autodesk.Revit.DB import *
from Autodesk.Revit.DB import Options, Solid,GeometryInstance, Transaction, ElementId, SketchPlane
from Autodesk.Revit.DB import Line, XYZ, SetComparisonResult, FilteredElementCollector, IntersectionResultArray, BuiltInParameter
from Autodesk.Revit.DB.Structure import RebarBarType, Rebar, RebarHookOrientation, RebarStyle, RebarHookType
from math import pi, ceil

clr.AddReference('RevitServices')
from RevitServices.Persistence import DocumentManager
clr.AddReference('RevitNodes')
import Revit
clr.ImportExtensions(Revit.GeometryConversion)
clr.ImportExtensions(Revit.Elements)

clr.AddReference('RevitAPI')

doc = DocumentManager.Instance.CurrentDBDocument

def to_mm(length):
    return length * 304.8

def to_feet(length):
    return length / 304.8

def to_deg(rad):
    return rad / pi * 180

# doc = IN[8]

dataEnteringNode = IN

element = IN[7]
geometry = element.Geometry()
# защитный слой
safe_layer = to_feet(IN[0])
# длина анкеровки
anchoring_length = to_feet(IN[1])
# диамер основной арматуры
general_rebar_diameter = to_feet(IN[2])
# диамер дополнительной арматуры
stud_rebar_diameter = to_feet(IN[3])
# шаг арматуры
rebar_step = to_feet(IN[4])
# класс основной арматуры
steel_general_class = IN[5]
# класс дополнительной арматуры
steel_studs_class = IN[6]
# Толщина марша
stair_thick = None
# Вектор направления марша
stair_directioin = None
# Угол уклона марша
diagonal_angle = None
# Ширина марша
stair_width = None
# Боковая грань которую мы принимаем за главную
gen_side_face = None
# Основное направление армирования лестницы
gen_side_direction = None
# Вертикальный вектор
vertical_vector = None
# Вектор лестницы
diagonal_normal = None

# Нижняя площадка толщина
bottom_floor_thick = None
# Нижняя диагональная точка и верхняя диагональная точка
# Начальная точка вектора - нижняя
bottom_diagonal_point = None
# Конечная точка диагонали стержня - верхняя
top_diagonal_point = None
# Диагональный вектор
diagonal_vector = None

bottom_face = None
front_face = None
tread_faces = []

floors = UnwrapElement(IN[7])
faces = []

for floor in floors:
    face = floor.GetGeometryObjectFromReference(
        DB.HostObjectUtils.GetTopFaces(floor)[0]
    )
    faces.append(face.ToProtoType())

# def faces():
#     if not hasattr(element, "_faces"):
#         _faces = []
#         for i in geometry:
#             if isinstance(i, GeometryInstance):
#                 for j in i.GetInstanceGeometry():
#                     if isinstance(j, Solid):
#                         if j.Volume > 0:
#                             _faces += list(j.Faces)
#     return _faces

def get_RebarBarType(diam, mark, is_pag):
    "Получает тип арматурного стержня."
    rebars = FilteredElementCollector(doc).OfClass(RebarBarType).ToElements()
    for rebar in rebars:
        if rebar.LookupParameter('Рзм.Диаметр').AsDouble() == diam:
            if rebar.LookupParameter('Арм.КлассЧисло').AsDouble() == mark:
                if bool(rebar.LookupParameter('Рзм.ПогМетрыВкл').AsInteger()) == is_pag:
                    return rebar

def rebar_general_type():
    if not hasattr(element, "_rebar_general_type"):
        _rebar_general_type = get_RebarBarType(general_rebar_diameter, steel_general_class, False)
    return _rebar_general_type

def rebar_stud_type():
    if not hasattr(element, "_rebar_stud_type"):
        _rebar_stud_type = get_RebarBarType(stud_rebar_diameter, steel_studs_class, False)
    return _rebar_stud_type

def rebar_measures():
    # Размеры для диагональных стержней
    # Ширина для расчета количесва дианональных стержней
    diagonal_width_calculate = stair_width - general_rebar_diameter - safe_layer * 2
    # Количество диагональных стержней
    diagonal_rebar_count = ceil(diagonal_width_calculate / rebar_step)
    # Пересчитываем шаг от полученной длины и округляем до 10 мм
    diagonal_step_calculate = round(diagonal_width_calculate / diagonal_rebar_count / to_feet(10)) * to_feet(10)
    # Пересчитываем ширину раскладки диагональных стержней
    diagonal_width_calculate = diagonal_step_calculate * diagonal_rebar_count
    # Добавляем 1 стержень
    diagonal_rebar_count += 1
    # Рассчитываем отступ первого стержня от боковой грани
    diagonal_side_space = (stair_width - diagonal_width_calculate) / 2

def get_face_edges(face):
    "Возвращает список из edges."
    edges = []
    for j in face.GetEdgesAsCurveLoops():
        for i in j:
            edges.append(i)
    return edges

def get_all_face_point(face):
    "Возьмем все точки с поверхности."
    points = []
    for edge in get_face_edges(face):
        if isinstance(edge, Line):
            points.append(edge.GetEndPoint(0))
    return points

def _get_common_points(points_1, points_2):
    points = []
    for i in points_1:
        for j in points_2:
            if i.IsAlmostEqualTo(j):
                points.append(i)
                break
    return points

def get_common_points(*arg):
    if len(arg) > 1:
        first_points = get_all_face_point(arg[0])
        for i in range(1, len(arg)):
            first_points = _get_common_points(first_points, get_all_face_point(arg[i]))
        return first_points

def last_tread_face():
    last = None
    max_z = float("-inf")
    for i in tread_faces:
        if i.Origin.Z > max_z:
            last = i
            max_z = i.Origin.Z
    return last

def intersect_point(start_one, end_one, start_two, end_two):
    "Находит пересечения между линиями на основе точек."
    l1 = Line.CreateBound(start_one, end_one)
    l1.MakeUnbound()
    l2 = Line.CreateBound(start_two, end_two)
    l2.MakeUnbound()
    res = StrongBox[IntersectionResultArray]()
    l1.Intersect(l2, res)
    return res.Value[0].XYZPoint

def create_lines_from_points(points):
    lines = []
    point_0 = None
    for point in points:
        if point_0 is None:
            point_0 = point
        else:
            lines.append(Line.CreateBound(point_0, point))
            point_0 = point
    return lines

def create_rebar(bar_type, normal, points, step=0, count=0, hook_1=None, hook_2=None):
    rho = RebarHookOrientation.Right
    rs = RebarStyle.Standard
    lines = create_lines_from_points(points)
    reb = Rebar.CreateFromCurves(doc, rs, bar_type, hook_1, hook_2, element, normal, lines, rho, rho, True, True)
    if step and count:
        da = reb.GetShapeDrivenAccessor()
        da.SetLayoutAsNumberWithSpacing(count, step, True, True, True)
    return reb

def create_diagonal_rebar():
    "Создаем диагональные стержни марша."
    layer_diam_len = safe_layer + general_rebar_diameter / 2
    # Теперь подними точки на высоту защитного слоя
    p1 = bottom_diagonal_point + diagonal_normal * layer_diam_len
    p2 = p1 + diagonal_vector
    p3 = bottom_diagonal_point + vertical_vector * (bottom_floor_thick - layer_diam_len - general_rebar_diameter)
    p4 = p3 + stair_directioin

    p5 = get_common_points(front_face, last_tread_face, gen_side_face)[0]
    p5 -= layer_diam_len * vertical_vector
    p6 = p5 + stair_directioin

    point_2 = intersect_point(p1, p2, p3, p4)
    point_2 += gen_side_direction * diagonal_side_space
    point_3 = intersect_point(p1, p2, p5, p6)
    point_3 += gen_side_direction * diagonal_side_space

    # Расчитываем крайние точки стержней
    point_1 = point_2  + stair_directioin * anchoring_length
    point_4 = point_3  - stair_directioin * anchoring_length
    # Упорядоченный список точек стержня
    points = [point_1, point_2, point_3, point_4]
    # Создаем арматруный стержень на основе точек
    reb = create_rebar(rebar_general_type, gen_side_direction, points, count=diagonal_rebar_count, step=diagonal_step_calculate)

    p1 = bottom_diagonal_point + diagonal_normal * (stair_thick - layer_diam_len - general_rebar_diameter)
    p2 = p1 + diagonal_vector
    p3 = bottom_diagonal_point + vertical_vector * layer_diam_len
    p4 = p3 + stair_directioin

    p5 = top_diagonal_point + vertical_vector * layer_diam_len
    p6 = p5 + stair_directioin

    point_2 = intersect_point(p1, p2, p3, p4)
    point_2 += gen_side_direction * diagonal_side_space
    point_3 = intersect_point(p1, p2, p5, p6)
    point_3 += gen_side_direction * diagonal_side_space

    point_1 = point_2  + stair_directioin * anchoring_length
    point_4 = point_3  - stair_directioin * anchoring_length

    points = [point_1, point_2, point_3, point_4]
    # Создаем арматруный стержень на основе точек
    reb = create_rebar(rebar_general_type, gen_side_direction, points, count=diagonal_rebar_count, step=diagonal_step_calculate)

    # Расставим угловые стержни
    p1 = bottom_diagonal_point + diagonal_normal * layer_diam_len
    p2 = p1 + diagonal_vector

    p3 = bottom_diagonal_point + vertical_vector * layer_diam_len
    p4 = p3 + stair_directioin

    point_2 = intersect_point(p1, p2, p3, p4)
    point_2 += gen_side_direction * diagonal_side_space
    point_1 = point_2 + stair_directioin * anchoring_length
    point_3 = point_2 + diagonal_vector * anchoring_length

    points = [point_1, point_2, point_3]

    reb = create_rebar(rebar_general_type, gen_side_direction, points, count=diagonal_rebar_count, step=diagonal_step_calculate)

    # Второй угловой стержень
    p1 = top_diagonal_point + diagonal_normal * (stair_thick - layer_diam_len - general_rebar_diameter)
    p2 = p1 + diagonal_vector

    p3 = get_common_points(front_face, last_tread_face, gen_side_face)[0]
    p3 -= layer_diam_len * vertical_vector
    p4 = p3 + stair_directioin


    point_2 = intersect_point(p1, p2, p3, p4)
    point_2 += gen_side_direction * diagonal_side_space
    point_1 = point_2 - stair_directioin * anchoring_length
    point_3 = point_2 - diagonal_vector * anchoring_length

    points = [point_1, point_2, point_3]

    reb = create_rebar(rebar_general_type, gen_side_direction, points, count=diagonal_rebar_count, step=diagonal_step_calculate)

def create_cross_rebar():
    "Создаем поперечные стержни."
    layer_diam_len = safe_layer + general_rebar_diameter * 1.5
    p1 = bottom_diagonal_point + vertical_vector * layer_diam_len
    p2 = p1 + stair_directioin

    p3 = bottom_diagonal_point + diagonal_normal * layer_diam_len
    p4 = p3 + diagonal_vector

    point_1 = intersect_point(p1, p2, p3, p4)
    point_1 += gen_side_direction * safe_layer
    point_2 = point_1 + (stair_width - 2 * safe_layer) * gen_side_direction

    points = [point_1, point_2]

    p5 = top_diagonal_point + diagonal_normal * layer_diam_len
    distance = p5.DistanceTo(p3)
    rebar_count = floor(distance / rebar_step) + 1

    reb = create_rebar(rebar_general_type, diagonal_vector, points, count=rebar_count, step=rebar_step)

    point_1 += diagonal_normal * (stair_thick - layer_diam_len * 2 + general_rebar_diameter)
    point_2 += diagonal_normal * (stair_thick - layer_diam_len * 2 + general_rebar_diameter)
    points = [point_1, point_2]

    reb = create_rebar(rebar_general_type, diagonal_vector, points, count=rebar_count, step=rebar_step)

def get_RebarHookType(name):
    "Получает отгиб по имени."
    rebars = FilteredElementCollector(doc).OfClass(RebarHookType).ToElements()
    for rebar in rebars:
        if name in rebar.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString():
            return rebar

def create_studs():
    "Создаем шпильки."
    layer_diam_len = safe_layer + general_rebar_diameter * 1.5
    p1 = bottom_diagonal_point + vertical_vector * layer_diam_len
    p2 = p1 + stair_directioin

    p3 = bottom_diagonal_point + diagonal_normal * layer_diam_len
    p4 = p3 + diagonal_vector

    p5 = top_diagonal_point + diagonal_normal * layer_diam_len
    distance = p5.DistanceTo(p3)
    rebar_count = floor(distance / rebar_step) + 1

    bend_radius = rebar_stud_type.get_Parameter(BuiltInParameter.REBAR_STANDARD_HOOK_BEND_DIAMETER).AsDouble() / 2
    point_1 = intersect_point(p1, p2, p3, p4)
    point_1 -= diagonal_vector * (bend_radius + stud_rebar_diameter / 2)
    point_1 -= diagonal_normal * (general_rebar_diameter / 2 + stud_rebar_diameter )
    point_1 += gen_side_direction * diagonal_side_space
    point_2 = point_1 + diagonal_normal * (stair_thick - layer_diam_len * 2 + general_rebar_diameter * 2 + stud_rebar_diameter * 2)
    hook = get_RebarHookType("Стандартный - 180")
    for i in range(1, int(rebar_count), 2):
        cur_point_1 = point_1 + rebar_step * i * diagonal_vector
        cur_point_2 = point_2 + rebar_step * i * diagonal_vector
        points = [cur_point_1, cur_point_2]
        reb = create_rebar(rebar_stud_type, gen_side_direction, points, hook_1=hook, hook_2=hook, step=diagonal_step_calculate, count=diagonal_rebar_count)


def create_step_rebar():
    "Создаем стержни ступеней."
    p3 = bottom_diagonal_point + diagonal_normal * safe_layer
    p4 = top_diagonal_point + diagonal_normal * safe_layer
    for i in tread_faces:
        if i == first_tread_face:
            continue
        points = get_common_points(i, gen_side_face)
        p1 = points[0]
        p2 = points[1]

        p1 = p1 if stair_directioin.DotProduct(p1) > stair_directioin.DotProduct(p2) else p2

        p1 += vertical_vector.Negate() * (safe_layer + stud_rebar_diameter / 2)
        p1 += stair_directioin.Negate() * (safe_layer + stud_rebar_diameter / 2)

        p2 = p1 + vertical_vector

        point_2 = p1
        point_1 = intersect_point(p1, p2, p3, p4)
        p2 = p1 + stair_directioin
        # if i != last_tread_face:
        point_3 = intersect_point(p1, p2, p3, p4)
        # else:
        #     last_points = get_common_points(front_face, gen_side_face)
        #     last_p3 = last_points[0] + stair_directioin * safe_layer
        #     last_p4 = last_points[1] + stair_directioin * safe_layer
        #     point_3 = intersect_point(p1, p2, last_p3, last_p4)

        point_1 += gen_side_direction * diagonal_side_space
        point_2 += gen_side_direction * diagonal_side_space
        point_3 += gen_side_direction * diagonal_side_space
        points = [point_1, point_2, point_3]
        # Создаем стержни проступи.
        reb = create_rebar(rebar_stud_type, gen_side_direction, points, step=diagonal_step_calculate, count=diagonal_rebar_count)

        point_2 += (stud_rebar_diameter / 2 + general_rebar_diameter / 2) * vertical_vector.Negate()
        point_2 += (stud_rebar_diameter / 2 + general_rebar_diameter / 2) * stair_directioin.Negate()
        point_3 = point_2 + gen_side_direction * (stair_width - safe_layer * 2)
        points = [point_2, point_3]
        # Создаем горизонтальные стержни проступи.
        reb = create_rebar(rebar_general_type, stair_directioin.Negate(), points, step=to_feet(55), count=3)

def define_measures():
        "Снимаем недостающие размеры."

        plane = diagonal_face.GetSurface()
        stair_thick = float("inf")
        for i in tread_faces:
            for point in get_all_face_point(i):
                cur_distance = plane.Project(point)[1]
                if stair_thick > cur_distance:
                    stair_thick = cur_distance

        # Толщина марша
        stair_thick = stair_thick
        # Вектор направления марша
        stair_directioin = ricer_faces[0].FaceNormal
        # Угол уклона марша
        diagonal_angle = diagonal_face.FaceNormal.AngleTo(stair_directioin) - pi / 2
        # Ширина марша
        stair_width = side_faces[0].GetSurface().Project(side_faces[1].Origin)[1]
        # Боковая грань которую мы принимаем за главную
        gen_side_face = side_faces[0]
        # Основное направление армирования лестницы
        gen_side_direction = gen_side_face.FaceNormal.Negate()
        # Вертикальный вектор
        vertical_vector = XYZ(0, 0, 1)
        # Вектор лестницы
        diagonal_normal = diagonal_face.FaceNormal.Negate()

        # Нижняя площадка толщина
        bottom_floor_thick = first_tread_face.GetSurface().Project(bottom_face.Origin)[1]
        # Нижняя диагональная точка и верхняя диагональная точка
        # Начальная точка вектора - нижняя
        bottom_diagonal_point = get_common_points(diagonal_face, bottom_face, gen_side_face)[0]
        # Конечная точка диагонали стержня - верхняя
        top_diagonal_point = get_common_points(diagonal_face, front_face, gen_side_face)[0]
        # Диагональный вектор
        diagonal_vector = (top_diagonal_point - bottom_diagonal_point).Normalize()

def first_tread_face():
    first = None
    min_z = float("inf")
    for i in tread_faces:
        if i.Origin.Z < min_z:
            first = i
            min_z = i.Origin.Z
    return first

def longest_or_shortest_edge(face):
    "Возвращает самые длинные edges."
    max_len = float("-inf")
    edges = get_face_edges(face)
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

def get_common_edge(edge, face, face_2):
    "Возвращает общие edge."
    res = []
    if face != face_2:
        for i in get_face_edges(face):
            if i.Intersect(edge) == SetComparisonResult.Equal:
                res.append(i)
    return res

def have_common_edge(face_1, face_2, except_faces=[]):
    "Есть ли у поверхностей общая грань."
    if face_1 not in except_faces:
        for i in get_face_edges(face_1):
            for j in get_face_edges(face_2):
                if i.Intersect(j) == SetComparisonResult.Equal:
                    return True

def analysis_faces():
    vert_vect = XYZ(0, 0, 1)
    for i in faces:
        if i.FaceNormal.IsAlmostEqualTo(vert_vect):
            tread_faces.append(i)

    ricer_faces = []
    for i in tread_faces:
        for j in longest_or_shortest_edge(i):
            for k in faces:
                if get_common_edge(j, k, i) and k not in ricer_faces:
                    ricer_faces.append(k)

    # Боковые плоскости имеют общие линии с каждой проступью
    side_faces = []
    for face_1 in faces:
        all_face_have_common_edge = True
        for face_2 in tread_faces:
            if not have_common_edge(face_1, face_2):
                all_face_have_common_edge = False
        if all_face_have_common_edge:
            side_faces.append(face_1)

    diagonal_face = None
    for face in faces:
        normal = face.FaceNormal
        if (abs(round(normal.X, 7)) > 0 or abs(round(normal.Y, 7)) > 0) and abs(round(normal.Z, 7)) > 0:
            diagonal_face = face

    for face in faces:
        if have_common_edge(face, diagonal_face, except_faces=side_faces + [diagonal_face]):
            if face.FaceNormal.IsAlmostEqualTo(vert_vect.Negate()):
                bottom_face = face
            else:
                front_face = face

    ricer_faces.remove(front_face)

def print_face(face):
    "Посмотреть какая плоскость нам нужна."
    plane = face.GetSurface()
    sketchPlane = SketchPlane.Create(doc, plane)
    for j in face.GetEdgesAsCurveLoops():
        for i in j:
            doc.Create.NewModelCurve(i, sketchPlane)

analysis_faces()
define_measures()
rebar_measures()
create_diagonal_rebar()
create_cross_rebar()
create_studs()
create_step_rebar()
# Назначьте вывод переменной OUT.
OUT = 0