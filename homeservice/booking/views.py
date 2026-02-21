from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ServiceRequestForm

@login_required
def request_service(request):
    if request.user.role != "user":
        return redirect("login")

    form = ServiceRequestForm(request.POST or None, request.FILES or None)

    if request.method == "POST":
        if form.is_valid():
            service_request = form.save(commit=False)
            service_request.user = request.user
            service_request.save()
            return redirect("user_dashboard")

    return render(request, "booking/request_service.html", {"form": form})
