from collections import OrderedDict

from sale.models.course import Course
from sale.models.menu import Menu


class MenuService:
    """
    Service class for managing restaurant menus.
    Provides methods to retrieve and create menus.
    """

    @staticmethod
    def order_dishes(dishes, restaurant):
        """
        Return a dict of courses (in menu order if available) with their dishes for a restaurant.
        Only include courses that have at least one dish. Avoid multiple DB queries per course.
        """
        menu = Menu.get_or_create_menu_by_restaurant(restaurant)
        course_objs = MenuService._create_course_id_course_obj_map(dishes)
        if menu and menu.ordering:
            return MenuService._order_courses_by_menu(menu, dishes.values(), course_objs)
        else:
            return MenuService._order_courses_default(dishes.values(), course_objs)

    @staticmethod
    def _create_course_id_course_obj_map(dishes):
        """
        Create a mapping of course_id to Course objects from the given dishes.
        This is used to avoid multiple DB queries when ordering dishes by course.
        """
        course_objs = {}
        for dish in dishes:
            course = getattr(dish, 'course', None)
            course_id = getattr(course, 'id', None)
            if course_id not in course_objs:
                if course_id and course:
                    course_objs[str(course_id)] = course
        return course_objs

    @staticmethod
    def _order_courses_by_menu(menu, dishes, course_objs):
        ordered_dishes = OrderedDict()

        # Initialize with course names in the correct order
        for course_id in menu.ordering:
            # Get course name from first dish with this course_id
            course_name = next(
                (course_objs[str(dish['course_id'])].name for dish in dishes if str(dish['course_id']) == course_id),
                None
            )
            if course_name:
                ordered_dishes[course_name] = []

        # Group dishes by course name
        for dish in dishes:
            course_name = course_objs[str(dish['course_id'])].name
            if course_name in ordered_dishes:
                ordered_dishes[course_name].append(dish)
        return ordered_dishes

    @staticmethod
    def _order_courses_default(dishes, course_objs):
        """Order courses by name, only including those with dishes."""
        courses = {}
        for dish in dishes:
            course_id = str(dish['course_id'])
            if course_id not in course_objs:
                continue
            course_name = course_objs[course_id].name
            if course_name not in courses:
                courses[course_name] = []
            courses[course_name].append(dish)
        return courses
