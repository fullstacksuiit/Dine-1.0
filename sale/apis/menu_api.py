from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.response import Response
from rest_framework import status
from sale.models.course import Course
from sale.models.menu import Menu
from sale.serializers import CourseSerializer

class MenuAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get the current course ordering for the restaurant's menu."""
        menu = Menu.get_menu_by_restaurant(request.restaurant)
        ordering = menu.ordering if menu else []
        courses = Course.get_courses_for_restaurant(request.restaurant)
        courses_data = CourseSerializer(courses, many=True).data
        return Response({'ordering': ordering, "courses": courses_data}, status=status.HTTP_200_OK)

    def post(self, request):
        """Update the course ordering for the restaurant's menu."""
        ordering = request.data.get('ordering', [])
        if not isinstance(ordering, list):
            return Response({'detail': 'Invalid ordering format.'}, status=status.HTTP_400_BAD_REQUEST)
        menu = Menu.get_menu_by_restaurant(request.restaurant)
        if not menu:
            menu = Menu.objects.create(restaurant=request.restaurant, ordering=ordering)
        else:
            if menu.ordering == ordering:
                return Response({'ordering': menu.ordering}, status=status.HTTP_200_OK)

            menu.ordering = ordering
            menu.updated_by = request.user
            menu.save()
        return Response({'ordering': menu.ordering}, status=status.HTTP_200_OK)
