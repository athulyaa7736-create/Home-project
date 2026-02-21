from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from booking.models import ServiceRequest

@login_required
def user_dashboard(request):
    if request.user.role != "user":
        return redirect("login")
    return render(request, "dashboard/user_dashboard.html")

@login_required
def worker_dashboard(request):
    if request.user.role != "worker":
        return redirect("login")
    jobs = ServiceRequest.objects.filter(assigned_worker=request.user)

    return render(request, "dashboard/worker_dashboard.html", {"jobs": jobs})

@login_required
def admin_dashboard(request):
    if request.user.role != "admin":
        return redirect("login")
    return render(request, "dashboard/admin_dashboard.html")

def home(request):
    return render(request, 'home.html')