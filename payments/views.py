from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from workers.models import WorkerProfile
from .models import Payment
from users.models import UserSubscription # Import from services app
from booking.models import ServiceRequest
from django.http import JsonResponse
import json
import random
import string
import uuid
from django.utils import timezone
import datetime
from django.db import models
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count
from datetime import datetime, timedelta
from decimal import Decimal 
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from .models import WorkerPayment
from workers.models import WorkerProfile
from booking.models import ServiceRequest
from booking.forms import ServiceRequestForm

@staff_member_required
def admin_partial_refund(request, payment_id):
    """Admin view to process partial refund"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        refund_amount = request.POST.get('refund_amount')
        refund_reason = request.POST.get('refund_reason')
        
        if refund_amount:
            payment.status = 'partial_refunded'
            payment.refund_amount = refund_amount
            payment.refund_date = timezone.now()
            payment.refund_reason = refund_reason
            payment.refunded_by = request.user
            payment.save()
            
            messages.success(request, f'Partial refund of ₹{refund_amount} processed successfully!')
            return redirect('admin:payments_payment_changelist')
    
    return render(request, 'admin/payments/payment/partial_refund.html', {'payment': payment})

@login_required
def payment_page(request, booking_id):
    """Show payment page for a booking"""
    booking = get_object_or_404(ServiceRequest, id=booking_id, user=request.user)
    
    # Check if payment already exists
    # if hasattr(booking, 'payment') and booking.payment:
    #     messages.info(request, 'Payment already completed for this booking')
    #     return redirect('user_dashboard')
    
    # ✅ Safe check — no exception
    try:
        existing_payment = booking.payment
        if existing_payment and existing_payment.status == 'completed':
            messages.info(request, 'Payment already completed for this booking.')
            return redirect('user_dashboard')
    except:
        pass

    # Check if user has active subscription with remaining visits
    active_sub = UserSubscription.objects.filter(
        user=request.user,
        status='active'
    ).first()
    
    can_use_subscription = False
    if active_sub and active_sub.is_valid:
        can_use_subscription = True
    
    context = {
        'booking': booking,
        'amount': booking.service.price if booking.service else 0,
        'can_use_subscription': can_use_subscription,
        'active_subscription': active_sub,
    }
    
    return render(request, 'payments/payment_page.html', context)


@login_required
def process_payment_api(request, booking_id):
    """Process payment via AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # Get the booking
            booking = get_object_or_404(ServiceRequest, id=booking_id, user=request.user)

            # ✅ Check if payment already exists
            try:
                existing = booking.payment
                return JsonResponse({
                    'success': False,
                    'message': 'Payment already exists for this booking'
                })
            except Exception:
                pass  # No payment yet — continue

            # Check if using subscription
            use_subscription = data.get('use_subscription', False)
            amount = booking.service.price if booking.service else 0

            if use_subscription:
                from users.models import UserSubscription
                subscription = UserSubscription.objects.filter(
                    user=request.user,
                    status='active'
                ).first()

                if not subscription or not subscription.is_valid:
                    return JsonResponse({
                        'success': False,
                        'message': 'No valid subscription found'
                    })

                subscription.use_visit()
                amount = 0
                booking.subscription = subscription
                booking.save()

            # Get payment method
            payment_method = data.get('payment_method', 'cash')

            # Generate transaction ID
            import random, string
            transaction_id = 'TXN' + ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=10)
            )

            # ✅ Create payment with correct status
            payment = Payment.objects.create(
                user=request.user,
                booking=booking,
                amount=booking.service.price,
                status='pending_collection' if payment_method == 'cash' else 'completed',
                payment_method=payment_method,
                transaction_id=transaction_id,
                payment_date=timezone.now()
            )

            # Add UPI ID if provided
            if payment_method == 'upi' and data.get('upi_id'):
                payment.upi_id = data.get('upi_id')
                payment.save()

            return JsonResponse({
                'success': True,
                'transaction_id': transaction_id,
                'amount': str(payment.amount),
                'message': 'Payment successful!' if amount > 0 else 'Booking completed with subscription!',
                'payment_id': payment.id,
                'used_subscription': use_subscription
            })

        except Exception as e:
            print('❌ Error:', str(e))
            return JsonResponse({
                'success': False,
                'message': str(e)
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def process_payment(request, booking_id):
    """Process payment via regular form post"""
    if request.method == 'POST':
        try:
            # Get the booking
            booking = get_object_or_404(ServiceRequest, id=booking_id, user=request.user)
            
            # Get payment method from request
            payment_method = request.POST.get('payment_method', 'upi')
            
            # Generate transaction ID
            import random
            import string
            transaction_id = 'TXN' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            
            # Create payment record
            payment = Payment.objects.create(
                user=request.user,
                booking=booking,
                amount=booking.service.price,
                status='completed',
                payment_method=payment_method,
                transaction_id=transaction_id,
                payment_date=timezone.now()
            )
            
            # Redirect to dashboard with success message
            messages.success(request, 'Payment successful!')
            return redirect('user_dashboard')
            
        except Exception as e:
            messages.error(request, f'Payment failed: {str(e)}')
            return redirect('payment_page', booking_id=booking_id)
    
    return redirect('user_dashboard')

@login_required
def payment_history(request):
    """Show user's payment history"""
    payments = Payment.objects.filter(
        user=request.user
    ).select_related(
        'booking', 'booking__service'
    ).order_by('-payment_date', '-created_at')
    
    # Calculate statistics
    total_paid = payments.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0
    total_payments = payments.count()
    completed_payments = payments.filter(status='completed').count()
    pending_payments = payments.filter(status='pending').count()
    
    context = {
        'payments': payments,
        'total_paid': total_paid,
        'total_payments': total_payments,
        'completed_payments': completed_payments,
        'pending_payments': pending_payments,
    }
    
    return render(request, 'payments/payment_history.html', context)


@login_required
def payment_receipt(request, payment_id):
    """Show payment receipt"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    context = {
        'payment': payment,
    }
    
    return render(request, 'payments/payment_receipt.html', context)

@login_required
def process_plan_payment(request, plan_id):
    from users.models import SubscriptionPlan, UserSubscription
    from datetime import date, timedelta
    import random, string, json

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method'})

    try:
        # ✅ Read JSON body (sent by JS fetch)
        try:
            data = json.loads(request.body)
            payment_method = data.get('payment_method', 'cash')
        except Exception:
            payment_method = request.POST.get('payment_method', 'cash')

        plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)

        # Check if already subscribed
        existing = UserSubscription.objects.filter(
            user=request.user, status='active'
        ).first()
        if existing:
            return JsonResponse({
                'success': False,
                'message': f'You already have an active {existing.plan.name} subscription.'
            })

        # Create subscription
        start_date = date.today()
        # end_date = start_date + timedelta(days=30)
        # ✅ Calculate end date based on plan name/type
        plan_name_lower = plan.name.lower()

        if 'premium' in plan_name_lower or 'annual' in plan_name_lower or 'year' in plan_name_lower:
            # Annual — 12 months = 365 days
            end_date = start_date + timedelta(days=365)
            duration_label = '1 Year'

        elif 'standard' in plan_name_lower or 'quarterly' in plan_name_lower or '3 month' in plan_name_lower:
            # Quarterly — 3 months = 90 days
            end_date = start_date + timedelta(days=90)
            duration_label = '3 Months'

        else:
            # Basic / Monthly — 1 month = 30 days
            end_date = start_date + timedelta(days=30)
            duration_label = '1 Month'

        txn_id = 'SUB' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))


        UserSubscription.objects.create(
            user=request.user,
            plan=plan,
            start_date=start_date,
            end_date=end_date,
            visits_used=0,
            total_visits_allowed=plan.visits_allowed,
            amount_paid=plan.price,
            transaction_id=txn_id,
            payment_date=timezone.now(),
            status='active',
            auto_renew=True
        )

        # ✅ Return JSON — JS shows success modal with transaction ID
        return JsonResponse({
            'success': True,
            'transaction_id': txn_id,
            'message': f'Successfully subscribed to {plan.name}!',
            'valid_until': end_date.strftime('%d %b %Y'),
            'duration': duration_label,
            'visits': plan.visits_allowed,
            'amount': str(plan.price),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()  # see full error in terminal
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def process_cash_payment(request):
    """Process cash payment confirmation"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            booking_id = data.get('booking_id')
            
            booking = get_object_or_404(ServiceRequest, id=booking_id, user=request.user)
            
            # Check if payment already exists
            if hasattr(booking, 'payment'):
                return JsonResponse({
                    'success': False,
                    'message': 'Payment already exists for this booking'
                })
            
            # Generate transaction ID
            transaction_id = 'CASH' + ''.join(random.choices(string.digits, k=8))
            
            # ✅ CREATE CASH PAYMENT RECORD
            payment = Payment.objects.create(
                user=request.user,
                booking=booking,
                amount=booking.service.price,
                payment_method='cash',
                status='pending',  # Cash payments start as pending
                transaction_id=transaction_id,
                cash_received=False  # Not received yet
            )
            
            return JsonResponse({
                'success': True,
                'transaction_id': transaction_id,
                'amount': str(payment.amount),
                'message': 'Cash payment confirmed! Pay the worker when service is done.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def worker_confirm_cash(request, job_id):
    if request.method == 'POST':
        job = get_object_or_404(ServiceRequest, id=job_id)
        action = request.POST.get('action')

        try:
            payment = job.payment
        except Exception:
            messages.error(request, 'No payment found for this job.')
            return redirect('worker_dashboard')

        if action == 'received':
            payment.cash_received      = True
            payment.cash_received_date = timezone.now()
            payment.cash_received_by   = request.user
            payment.status             = 'completed'
            payment.save()
            messages.success(request,
                'Cash payment of Rs.{} confirmed!'.format(payment.amount))

        elif action == 'rejected':
            reason   = request.POST.get('reason', 'Not collected')
            comments = request.POST.get('comments', '')

            payment.cash_rejection_date   = timezone.now()
            payment.cash_rejection_reason = '{} - {}'.format(
                reason, comments).strip(' -')
            payment.notes = 'CASH REJECTED by worker {} on {}. Reason: {} {}'.format(
                request.user.username,
                timezone.now().strftime('%d %b %Y %H:%M'),
                reason,
                comments
            )
            payment.save()

            # ✅ Django 6 compatible
            try:
                from django.contrib.admin.models import LogEntry, CHANGE
                from django.contrib.contenttypes.models import ContentType
                LogEntry.objects.create(
                    user_id         = request.user.pk,
                    content_type_id = ContentType.objects.get_for_model(payment).pk,
                    object_id       = str(payment.pk),
                    object_repr     = 'CASH REJECTED - Job #{} - Rs.{} - Worker: {} - Customer: {}'.format(
                        job.id,
                        payment.amount,
                        request.user.username,
                        job.user.username,
                    ),
                    action_flag    = CHANGE,
                    change_message = 'Cash rejected. Reason: {} {}'.format(
                        reason, comments)
                )
            except Exception as e:
                print('LogEntry error:', e)

            messages.warning(request,
                'Cash rejection recorded. Admin has been notified.')

        return redirect('worker_dashboard')  # ✅ outside if/elif — always runs

    return redirect('worker_dashboard')

def pay_now(request, id):
    booking = Booking.objects.get(id=id)
    booking.payment_status = True
    booking.save()
    return redirect('user_dashboard')


@login_required
def reject_cash_payment(request, payment_id):
    """Reject a cash payment request"""
    if request.user.role != 'worker':
        messages.error(request, "Access denied.")
        return redirect('login')
    
    payment = get_object_or_404(Payment, id=payment_id, cash_received_by=request.user)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        payment.cash_received = False
        payment.notes = f"Cash payment rejected: {reason}"
        payment.save()
        
        messages.warning(request, "Cash payment rejected. Please contact admin.")
        return redirect('worker_dashboard')
    
    return render(request, 'payments/reject_cash.html', {'payment': payment})

@login_required
def payment_history(request):
    """User payment history"""
    payments = Payment.objects.filter(user=request.user).order_by('-payment_date')
    
    # Calculate statistics
    completed_count = payments.filter(status='completed').count()
    total_spent = payments.filter(status='completed').aggregate(
        total=models.Sum('amount')
    )['total'] or 0
    
    context = {
        'payments': payments,
        'completed_count': completed_count,
        'total_spent': total_spent,
    }
    return render(request, 'payments/payment_history.html', context)



@login_required
def confirm_cash_received(request, job_id):
    """Worker confirms they received cash payment"""
    if request.user.role != 'worker':
        messages.error(request, "Access denied.")
        return redirect('login')
    
    job = get_object_or_404(ServiceRequest, id=job_id, assigned_worker=request.user)
    
    if job.status != 'completed':
        messages.error(request, "Job must be completed first.")
        return redirect('worker_dashboard')
    
    if not hasattr(job, 'payment') or job.payment.payment_method != 'cash':
        messages.error(request, "This is not a cash payment.")
        return redirect('worker_dashboard')
    
    payment = job.payment
    payment.cash_received = True
    payment.cash_received_date = timezone.now()
    payment.cash_received_by = request.user
    payment.save()
    
    messages.success(request, f"Cash payment of ₹{payment.amount} confirmed!")
    return redirect('worker_dashboard')

# ============= SUBSCRIPTION VIEWS =============

@login_required
def my_subscriptions(request):
    """View user's active subscriptions"""
    subscriptions = UserSubscription.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    return render(request, 'payments/subscriptions.html', {'subscriptions': subscriptions})

@login_required
def subscription_detail(request, sub_id):
    """View subscription details"""
    subscription = get_object_or_404(UserSubscription, id=sub_id, user=request.user)
    return render(request, 'payments/subscription_detail.html', {'subscription': subscription})

@login_required
def cancel_subscription(request, sub_id):
    """Cancel an active subscription"""
    subscription = get_object_or_404(UserSubscription, id=sub_id, user=request.user)
    
    if request.method == 'POST':
        subscription.status = 'cancelled'
        subscription.auto_renew = False
        subscription.save()
        messages.success(request, 'Subscription cancelled successfully.')
        return redirect('my_subscriptions')
    
    return render(request, 'payments/cancel_subscription.html', {'subscription': subscription})

@login_required
def renew_subscription(request, sub_id):
    """Renew an expired subscription"""
    subscription = get_object_or_404(UserSubscription, id=sub_id, user=request.user)
    
    if request.method == 'POST':
        # Extend by plan duration
        new_end_date = timezone.now() + datetime.timedelta(days=30 * subscription.plan.duration_months)
        subscription.end_date = new_end_date
        subscription.next_billing_date = new_end_date
        subscription.status = 'active'
        subscription.save()
        
        messages.success(request, 'Subscription renewed successfully.')
        return redirect('subscription_detail', sub_id=subscription.id)
    
    return render(request, 'payments/renew_subscription.html', {'subscription': subscription})

@login_required
def request_refund(request, payment_id):
    """User request for refund"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    # Check if refund is possible
    if payment.status != 'completed':
        messages.error(request, "This payment cannot be refunded.")
        return redirect('payment_history')
    
    if request.method == 'POST':
        refund_type = request.POST.get('refund_type')
        reason = request.POST.get('reason')
        
        # Mark that refund was requested
        payment.refund_requested = True
        payment.refund_request_date = timezone.now()
        payment.refund_reason = reason
        payment.save()
        
        if refund_type == 'partial':
            refund_amount = request.POST.get('refund_amount')
            messages.success(request, f"Partial refund request for ₹{refund_amount} submitted successfully!")
        else:
            messages.success(request, "Full refund request submitted successfully!")
        
        return redirect('user_dashboard')  # Go back to dashboard to see status
    
    return render(request, 'payments/request_refund.html', {'payment': payment})

@login_required
def admin_refund_payment(request, payment_id):
    """Admin directly process refund"""
    if request.user.role != 'admin':
        messages.error(request, "Access denied.")
        return redirect('login')
    
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        refund_type = request.POST.get('refund_type')
        reason = request.POST.get('reason', 'Admin initiated refund')
        
        if refund_type == 'full':
            payment.process_refund(
                amount=payment.amount,
                reason=reason,
                refunded_by=request.user
            )
            messages.success(request, f"Full refund processed for ₹{payment.amount}")
        else:
            refund_amount = request.POST.get('refund_amount')
            if refund_amount:
                payment.process_refund(
                    amount=refund_amount,
                    reason=reason,
                    refunded_by=request.user
                )
                messages.success(request, f"Partial refund of ₹{refund_amount} processed")
        
        return redirect('admin:payments_payment_changelist')
    
    return render(request, 'payments/admin_refund.html', {'payment': payment})





@staff_member_required
def admin_unpaid_cash(request):
    """Show all cash payments that were not received"""
    unpaid_payments = Payment.objects.filter(
        payment_method='cash',
        cash_received=False,
        status='pending'
    ).select_related('user', 'booking')
    
    return render(request, 'admin/unpaid_cash.html', {
        'payments': unpaid_payments
    })

@login_required
def admin_process_payments(request):
    if request.user.role != 'admin':
        return redirect('login')
    
    from workers.models import WorkerProfile
    from datetime import datetime, timedelta
    from django.db.models import Sum
    
    # Calculate date range (last week)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    
    workers = WorkerProfile.objects.filter(verified=True)
    
    for worker in workers:
        # Get completed jobs for this worker in the last week
        completed_jobs = ServiceRequest.objects.filter(
            assigned_worker=worker.user,
            status='completed',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        total_earnings = 0
        for job in completed_jobs:
            if job.service and job.service.price:
                # Company takes 20% commission
                worker_share = job.service.price * 0.8
                total_earnings += worker_share
        
        # Create payment record
        WorkerPayment.objects.create(
            worker=worker,
            amount=total_earnings,
            period_start=start_date,
            period_end=end_date,
            jobs_count=completed_jobs.count(),
            status='pending'
        )
    
    messages.success(request, "Weekly payments calculated successfully!")
    return redirect('admin_dashboard')


def request_service(request):
    if request.method == 'POST':
        form = ServiceRequestForm(request.POST, request.FILES)
        if form.is_valid():
            service_request = form.save(commit=False)
            service_request.user = request.user
            service_request.save()
            return redirect('user_dashboard')
    else:
        form = ServiceRequestForm()
    
    return render(request, 'booking/request_service.html', {'form': form})

# worker cash

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib import messages
from .models import WorkerPayment
from workers.models import WorkerProfile
import json
import uuid

@staff_member_required
def payment_dashboard(request):
    """Dashboard showing payment summary"""
    
    # Get statistics
    total_pending = WorkerPayment.objects.filter(status='pending').count()
    total_processing = WorkerPayment.objects.filter(status='processing').count()
    total_completed = WorkerPayment.objects.filter(status='completed').count()
    
    pending_amount = WorkerPayment.objects.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0
    completed_amount = WorkerPayment.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Workers with pending payments
    workers_with_pending = WorkerProfile.objects.filter(
        payments__status='pending'
    ).distinct().annotate(
        pending_count=Count('payments'),
        pending_total=Sum('payments__amount')
    )
    
    # Recent payments
    recent_payments = WorkerPayment.objects.select_related(
        'worker', 'worker__user', 'job'
    ).order_by('-created_at')[:10]
    
    context = {
        'total_pending': total_pending,
        'total_processing': total_processing,
        'total_completed': total_completed,
        'pending_amount': pending_amount,
        'completed_amount': completed_amount,
        'workers_with_pending': workers_with_pending,
        'recent_payments': recent_payments,
    }
    
    return render(request, 'admin/payments/dashboard.html', context)

@staff_member_required
def process_payment_view(request, payment_id):
    """Process a single payment"""
    payment = get_object_or_404(WorkerPayment, id=payment_id)
    
    if request.method == 'POST':
        # Process the payment
        payment.status = 'completed'
        payment.payment_date = timezone.now()
        payment.transaction_id = request.POST.get('transaction_id', f'TXN{payment.id}')
        payment.payment_method = request.POST.get('payment_method', 'bank')
        payment.payment_reference = request.POST.get('reference', '')
        payment.processed_by = request.user
        payment.save()
        
        # Update worker's pending payment
        if payment.worker:
            payment.worker.pending_payment -= payment.amount
            payment.worker.total_earnings += payment.amount
            payment.worker.last_payment_date = timezone.now()
            payment.worker.save()
        
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Payment of ₹{payment.amount} processed successfully!',
                'transaction_id': payment.transaction_id,
                'amount': str(payment.amount)
            })
        
        messages.success(request, f'✅ Payment of ₹{payment.amount} processed successfully!')
        return redirect('admin:payments_workerpayment_changelist')
    
    # GET request - show the payment processing page
    context = {
        'payment': payment,
        'worker': payment.worker,
        'title': f'Process Payment - {payment.worker.user.username}',
        'now': timezone.now(),
    }
    
    return render(request, 'payments/process_payment.html', context)

@staff_member_required
def get_worker_payment_details(request, worker_id):
    """Get worker payment details for modal"""
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    
    # Get pending jobs for this worker
    from booking.models import ServiceRequest
    pending_jobs = ServiceRequest.objects.filter(
        assigned_worker=worker.user,
        status='completed',
        payment__isnull=True
    ).select_related('service')
    
    jobs_list = []
    total_amount = 0
    
    for job in pending_jobs:
        amount = float(worker.fixed_rate_per_job)
        total_amount += amount
        jobs_list.append({
            'id': job.id,
            'service': job.service.name if job.service else 'Service',
            'date': job.created_at.strftime('%d %b %Y'),
            'amount': amount,
            'customer': job.user.username
        })
    
    data = {
        'worker_id': worker.id,
        'worker_name': worker.user.get_full_name() or worker.user.username,
        'worker_email': worker.user.email,
        'worker_phone': getattr(worker.user, 'phone', ''),
        'account_holder': worker.account_holder_name or 'Not provided',
        'account_number': worker.get_masked_account(),
        'full_account': worker.account_number,  # For backend processing
        'ifsc': worker.ifsc_code or 'Not provided',
        'bank_name': worker.bank_name or 'Not provided',
        'upi_id': worker.upi_id or 'Not provided',
        'fixed_rate': float(worker.fixed_rate_per_job),
        'pending_jobs_count': len(jobs_list),
        'pending_jobs': jobs_list,
        'total_pending_amount': total_amount,
        'payment_methods': ['bank', 'upi', 'cash', 'cheque']
    }
    
    return JsonResponse(data)

from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils import timezone
from .models import WorkerPayment

@staff_member_required
def process_payment_page(request):
    payment_ids = request.GET.get('ids', '')
    
    if not payment_ids:
        return render(request, 'payments/process_payment.html', {
            'error': 'No payments selected'
        })
    
    # Get payment IDs
    id_list = [int(id) for id in payment_ids.split(',') if id]
    payments = WorkerPayment.objects.filter(id__in=id_list).select_related(
        'worker', 'worker__user', 'job', 'job__service'
    )
    
    if not payments:
        return render(request, 'payments/process_payment.html', {
            'error': 'No valid payments found'
        })
    
    # Group by worker
    workers = {}
    for payment in payments:
        worker_id = payment.worker.id
        if worker_id not in workers:
            workers[worker_id] = {
                'worker': payment.worker,
                'payments': [],
                'total': 0
            }
        workers[worker_id]['payments'].append(payment)
        workers[worker_id]['total'] += payment.amount
    
    total_amount = sum(p.amount for p in payments)
    
    context = {
        'payments': payments,
        'workers': workers.values(),
        'total_amount': total_amount,
        'payment_count': payments.count(),
        'payment_ids': payment_ids,
    }
    
    return render(request, 'payments/process_payment.html', context)


@staff_member_required
def complete_payment(request):
    """Mark payments as completed"""
    if request.method == 'POST':
        payment_ids = request.POST.get('payment_ids', '')
        payment_method = request.POST.get('payment_method', 'bank')
        transaction_id = request.POST.get('transaction_id', '')
        upi_id = request.POST.get('upi_id', '')
        
        id_list = [int(id) for id in payment_ids.split(',') if id]
        payments = WorkerPayment.objects.filter(id__in=id_list)
        
        # Generate batch ID
        batch_id = f"BATCH{timezone.now().strftime('%Y%m%d%H%M%S')}"
        
        # Update all payments
        for payment in payments:
            payment.status = 'completed'
            payment.payment_date = timezone.now()
            payment.transaction_id = transaction_id or f"{batch_id}-{payment.id}"
            payment.payment_method = payment_method
            payment.payment_reference = upi_id if payment_method == 'upi' else transaction_id
            payment.processed_by = request.user
            payment.save()
            
            # Update worker stats
            if payment.worker:
                payment.worker.pending_payment -= payment.amount
                payment.worker.total_earnings += payment.amount
                payment.worker.last_payment_date = timezone.now()
                payment.worker.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{payments.count()} payments completed successfully',
            'batch_id': batch_id,
            'total_amount': float(sum(p.amount for p in payments)),
            'count': payments.count()
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})



