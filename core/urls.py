from django.urls import path
from core.views import settings, team_page
from core.apis.staff_api import TeamListCreateAPI, TeamDetailAPI, CurrentUserAPI, RestaurantSettingsAPI
from core.apis.table_api import TableListCreateAPI, TableDetailAPI

urlpatterns = [
    path("team/", team_page, name="team"),
    path("api/team/", TeamListCreateAPI.as_view(), name="team_api"),
    path("api/team/<uuid:pk>", TeamDetailAPI.as_view(), name="team_detail_api"),
    path("api/me/", CurrentUserAPI.as_view(), name="current_user_api"),
    path("api/restaurant-settings/", RestaurantSettingsAPI.as_view(), name="restaurant_settings_api"),
    path("api/tables/", TableListCreateAPI.as_view(), name="table_api"),
    path("api/tables/<uuid:pk>", TableDetailAPI.as_view(), name="table_detail_api"),
    path("", settings, name="settings"),
]