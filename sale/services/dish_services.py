from collections import OrderedDict


def organize_menu_by_category(dishes_queryset):
    """Organize dishes by category for menu display"""
    dishes_dict = OrderedDict()

    # Use a more efficient approach by processing in batches
    # This reduces the number of loops in Python
    dishes_queryset = list(dishes_queryset)  # Evaluate the queryset once

    # Precompute unique categories to minimize lookups
    categories = {
        dish["category"].upper() for dish in dishes_queryset if dish.get("category")
    }
    for category in sorted(categories):
        dishes_dict[category] = [
            dish
            for dish in dishes_queryset
            if dish.get("category") and dish["category"].upper() == category
        ]

    return dishes_dict


def organize_menu_by_course(dishes_queryset):
    """Organize dishes by course for menu display (new, preferred, optimized)"""
    dishes_dict = OrderedDict()
    # Evaluate queryset only once, and prefetch course name if possible
    dishes_queryset = list(dishes_queryset)

    # Group dishes by course_id (None for no course)
    course_map = {}
    for dish in dishes_queryset:
        course_id = dish.get("course_id")
        course_name = dish.get("course__name", "")
        key = (course_id, course_name.strip() if course_name else None)
        course_map.setdefault(key, []).append(dish)

    # Sort by course name (case-insensitive, None last)
    sorted_keys = sorted(
        course_map.keys(),
        key=lambda x: (x[1] or "ZZZ").upper()  # None/empty course names go last
    )
    for course_id, course_name in sorted_keys:
        label = course_name.upper() if course_name else "NO COURSE"
        dishes_dict[label] = course_map[(course_id, course_name)]
    return dishes_dict
