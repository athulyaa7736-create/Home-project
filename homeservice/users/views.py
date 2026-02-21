from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .forms import LoginForm
from .forms import RegisterForm
from django.contrib.auth import logout

def login_view(request):
    form = LoginForm(request, data=request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")

            user = authenticate(username=username, password=password)

            if user:
                login(request, user)

                # role based redirect
                if user.role == "admin":
                    return redirect("admin_dashboard")

                elif user.role == "worker":
                    return redirect("worker_dashboard")

                else:
                    return redirect("user_dashboard")

    return render(request, "users/login.html", {"form": form})


def register_view(request):
    form = RegisterForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("login")

    return render(request, "users/register.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("login")
