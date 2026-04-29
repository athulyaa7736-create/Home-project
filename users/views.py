from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import LoginForm, RegisterForm
from workers.models import WorkerProfile
from .models import CustomUser
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import date, timedelta
from .models import SubscriptionPlan, UserSubscription
from booking.models import ServiceRequest



@login_required
def edit_profile(request):
    """Allow users to edit their profile"""
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        
        # Update user
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.phone = phone
        user.address = address
        user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('user_dashboard')
    
    return render(request, 'users/edit_profile.html', {'user': request.user})

def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {username}!")
            
            # Role-based redirect
            if user.is_superuser or user.is_staff:
                return redirect('/admin/')  
            elif user.role == "worker":
                return redirect('worker_dashboard')
            else:
                return redirect('user_dashboard')
        else:
            messages.error(request, "Invalid username or password!")
    
    return render(request, 'users/login.html')

def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'user'  # ✅ force role = user
            user.save()
            messages.success(request, "Account created successfully! Please login.")
            return redirect('login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegisterForm()
    
    return render(request, 'users/register.html', {'form': form})

def worker_register_view(request):
    if request.method == "POST":
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        service_type = request.POST.get('service_type')
        experience = request.POST.get('experience')
        
        # Debug print to see what's being received
        print(f"Received data: {username}, {email}, {phone}, {service_type}, {experience}")
        
        # Validation
        if not all([username, email, phone, address, password1, password2, service_type, experience]):
            missing = []
            if not username: missing.append('username')
            if not email: missing.append('email')
            if not phone: missing.append('phone')
            if not address: missing.append('address')
            if not password1: missing.append('password')
            if not password2: missing.append('confirm password')
            if not service_type: missing.append('service type')
            if not experience: missing.append('experience')
            
            messages.error(request, f"All fields are required! Missing: {', '.join(missing)}")
            return render(request, 'users/worker_register.html')
        
        if password1 != password2:
            messages.error(request, "Passwords do not match!")
            return render(request, 'users/worker_register.html')
        
        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters long!")
            return render(request, 'users/worker_register.html')
        
        # Check if username already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken! Please choose another.")
            return render(request, 'users/worker_register.html')
        
        # Check if email already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered! Please use another email.")
            return render(request, 'users/worker_register.html')
        
        try:
            # Create user with worker role
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password1,
                phone=phone,
                address=address,
                role='worker'  # Set role as worker
            )
            
            # Create worker profile
            WorkerProfile.objects.create(
                user=user,
                service_type=service_type,
                experience=int(experience) if experience else 0,
                job_rate=0,  # Default 0, admin will set later
                available=True,
                verified=False,  # Admin needs to verify worker
                skills="",  # Empty initially
                service_area="",  # Empty initially
                max_jobs_per_day=3,  # Default value
                current_jobs_count=0,
                availability_status='available'
            )
            
            messages.success(request, "Worker registration successful! Please wait for admin verification. You can login after admin approves your account.")
            return redirect('login')
            
        except IntegrityError as e:
            messages.error(request, f"Registration failed: Database error. Please try again.")
            return render(request, 'users/worker_register.html')
        except Exception as e:
            messages.error(request, f"Registration failed: {str(e)}")
            return render(request, 'users/worker_register.html')
    
    return render(request, 'users/worker_register.html')


@login_required
def edit_profile(request):
    """Allow users to edit their profile"""
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        
        # Update user
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.phone = phone
        user.address = address
        user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('user_dashboard')
    
    return render(request, 'users/edit_profile.html', {'user': request.user})

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully!")
    return redirect('login')



@login_required
def subscription_plans(request):
    """Show all available subscription plans"""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    
    # Get user's active subscription
    active_sub = UserSubscription.objects.filter(
        user=request.user,
        status='active'
    ).select_related('plan').first()
    
    context = {
        'plans': plans,
        'active_subscription': active_sub,
    }
    return render(request, 'plans.html', context)


@login_required
def subscribe_plan(request, plan_id):
    """Subscribe to a plan"""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
    
    if request.method == 'POST':
        # Check if user already has active subscription
        existing = UserSubscription.objects.filter(
            user=request.user,
            status='active'
        ).first()
        
        if existing:
            messages.error(request, 'You already have an active subscription')
            return redirect('subscription_plans')
        
        # Calculate dates
        start_date = date.today()
        end_date = start_date + timedelta(days=30)
        
        # Create subscription
        subscription = UserSubscription.objects.create(
            user=request.user,
            plan=plan,
            start_date=start_date,
            end_date=end_date,
            visits_used=0,
            total_visits_allowed=plan.visits_allowed,
            amount_paid=plan.price,
            transaction_id=f"SUB{timezone.now().strftime('%Y%m%d%H%M%S')}",
            payment_date=timezone.now(),
            status='active',
            auto_renew=True
        )
        
        messages.success(request, f'Successfully subscribed to {plan.name}!')
        return redirect('subscription_history')
    
    context = {
        'plan': plan,
    }
    return render(request, 'users/subscribe_confirm.html', context)


@login_required
def subscription_history(request):
    """Show user's subscription history"""
    subscriptions = UserSubscription.objects.filter(
        user=request.user
    ).select_related('plan').order_by('-created_at')
    
    # Get services used with each subscription
    for sub in subscriptions:
        sub.used_services = ServiceRequest.objects.filter(
            user=request.user,
            subscription=sub
        ).order_by('-created_at')[:5]
    
    context = {
        'subscriptions': subscriptions,
    }
    return render(request, 'users/subscription_history.html', context)


@login_required
def cancel_subscription(request, sub_id):
    """Cancel an active subscription"""
    subscription = get_object_or_404(
        UserSubscription, 
        id=sub_id, 
        user=request.user,
        status='active'
    )
    
    if request.method == 'POST':
        subscription.status = 'cancelled'
        subscription.auto_renew = False
        subscription.save()
        messages.success(request, 'Subscription cancelled successfully')
        return redirect('subscription_history')
    
    context = {
        'subscription': subscription,
    }
    return render(request, 'users/cancel_subscription.html', context)


@login_required
def renew_subscription(request, sub_id):
    """Renew an expired subscription"""
    subscription = get_object_or_404(
        UserSubscription, 
        id=sub_id, 
        user=request.user
    )
    
    if request.method == 'POST':
        # Create new subscription
        new_sub = UserSubscription.objects.create(
            user=request.user,
            plan=subscription.plan,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            visits_used=0,
            total_visits_allowed=subscription.plan.visits_allowed,
            amount_paid=subscription.plan.price,
            transaction_id=f"REN{timezone.now().strftime('%Y%m%d%H%M%S')}",
            payment_date=timezone.now(),
            status='active',
            auto_renew=True
        )
        messages.success(request, 'Subscription renewed successfully')
        return redirect('subscription_history')
    
    context = {
        'subscription': subscription,
    }
    return render(request, 'users/renew_subscription.html', context)
