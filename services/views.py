from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import ServicePlan
from payments.models import Payment
from users.models import UserSubscription
from users.models import SubscriptionPlan   
from django.utils import timezone
import datetime
import json
import random
import string


def plan_list(request):
    """Display all available plans"""
    single_plans = ServicePlan.objects.filter(
        plan_type__in=['one_time', 'before_service', 'after_service'],
        is_active=True
    )
    subscription_plans = ServicePlan.objects.filter(
        plan_type__in=['monthly', 'yearly', 'quarterly'],
        is_active=True
    )
    
    context = {
        'single_plans': single_plans,
        'subscription_plans': subscription_plans,
    }
    return render(request, 'services/plans.html', context)

@login_required
def select_plan(request, plan_id):
    """Select a plan for purchase"""
    plan = get_object_or_404(ServicePlan, id=plan_id, is_active=True)
    return render(request, 'services/subscriptions.html', {'plan': plan})

@login_required
def plan_payment_page(request, plan_id):
    """Payment page for plans"""
    plan = get_object_or_404(ServicePlan, id=plan_id, is_active=True)
    return render(request, 'payments/plan_payment_page.html', {'plan': plan})
    
@login_required
def process_plan_payment(request):
    """Process subscription payment via AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            plan_id = data.get('plan_id')
            payment_method = data.get('payment_method', 'online')
            
            plan = get_object_or_404(ServicePlan, id=plan_id, is_active=True)
            
            # Calculate final price
            amount = plan.discount_price if plan.discount_price else plan.price
            
            # Generate transaction ID
            transaction_id = 'SUB' + ''.join(random.choices(string.digits, k=8))
            
            # Create payment record - WITHOUT booking
            payment = Payment.objects.create(
                user=request.user,
                amount=amount,
                status='completed',
                payment_method=payment_method,
                transaction_id=transaction_id
                # ✅ No booking field needed for subscription
            )
            
            # Calculate end date
            end_date = timezone.now() + datetime.timedelta(days=30 * plan.duration_months)
            
            # Create subscription
            subscription = UserSubscription.objects.create(
                user=request.user,
                plan=plan,
                start_date=timezone.now(),
                end_date=end_date,
                next_billing_date=end_date,
                total_visits_allowed=plan.visits_included,
                visits_used=0,
                amount_paid=amount,
                payment=payment,
                status='active'
                
            )
            
            # Also link subscription to payment
            payment.subscription = subscription
            payment.save()
              
            return JsonResponse({
                'success': True,
                'transaction_id': transaction_id,
                'subscription_id': subscription.id,
                'amount': str(amount),
                'message': f'Successfully subscribed to {plan.name}!'
            })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})



@login_required
def subscription_history(request):
    """View user's subscription history"""
    subscriptions = UserSubscription.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    context = {
        'subscriptions': subscriptions,
    }
    return render(request, 'services/subscription_history.html', context)


def plan_payment_page(request, plan_id):
    """Handle plan payment"""
    # Get the subscription plan from users app
    plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
    
    context = {
        'plan': plan,
        'amount': plan.price,  # Pass the price explicitly
        'plan_name': plan.name,
        'plan_type': plan.plan_type,
        'visits_allowed': plan.visits_allowed,
        'discount': plan.discount_percentage,
    }
    
    # Template is in payments app
    return render(request, 'payments/plan_payment_page.html', context)