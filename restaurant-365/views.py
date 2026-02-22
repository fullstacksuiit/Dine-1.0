from django.shortcuts import redirect


def some_view(request):
    if request.user.is_authenticated:
        return redirect("order")
    else:
        return redirect("login")
