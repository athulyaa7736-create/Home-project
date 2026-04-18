from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from django.utils import timezone
from .models import ChatMessage, EscalatedIssue, Notification
from booking.models import ServiceRequest
from payments.models import Payment
from users.models import UserSubscription
from django.db.models import Sum
import json
from datetime import date

# Create a new app called 'chat' or add to existing app
@login_required
def ai_chat(request):

    # ✅ Get bookings
    service_requests = ServiceRequest.objects.filter(
        user=request.user
    ).select_related('service').order_by('-created_at')

    bookings_json = json.dumps([{
        'id':             b.id,
        'service_name':   b.service.name if b.service else 'Unknown',
        'status':         b.status,
        'status_display': b.get_status_display(),
        'date':           b.created_at.strftime('%d %b %Y'),
        'preferred_date': b.preferred_date.strftime('%d %b %Y') if hasattr(b, 'preferred_date') and b.preferred_date else None,
        'preferred_time': str(b.preferred_time) if hasattr(b, 'preferred_time') and b.preferred_time else None,
    } for b in service_requests])

    # ✅ Get payments
    payments = Payment.objects.filter(
        user=request.user
    ).select_related('booking__service').order_by('-payment_date')[:10]

    payments_json = json.dumps([{
        'id':           p.id,
        'amount':       str(p.amount),
        'status':       p.status,
        'payment_method': p.payment_method,
        'service_name': p.booking.service.name if p.booking and p.booking.service else 'Unknown',
        'date':         p.payment_date.strftime('%d %b %Y') if p.payment_date else '',
        'transaction_id': p.transaction_id,
    } for p in payments])

    # ✅ Total spent
    total_spent = Payment.objects.filter(
        user=request.user, status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # ✅ Active subscription
    active_sub = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        end_date__gte=date.today()
    ).select_related('plan').first()

    if active_sub:
        days_remaining = (active_sub.end_date - date.today()).days
        usage_pct = (active_sub.visits_used / active_sub.total_visits_allowed * 100) if active_sub.total_visits_allowed else 0
        subscription_json = json.dumps({
            'plan_name':        active_sub.plan.name,
            'status':           active_sub.status,
            'start_date':       active_sub.start_date.strftime('%d %b %Y'),
            'end_date':         active_sub.end_date.strftime('%d %b %Y'),
            'visits_used':      active_sub.visits_used,
            'total_visits':     active_sub.total_visits_allowed,
            'visits_remaining': active_sub.visits_remaining,
            'days_remaining':   days_remaining,
            'usage_percentage': round(usage_pct, 1),
            'auto_renew':       active_sub.auto_renew,
            'amount_paid':      str(active_sub.amount_paid),
        })
    else:
        subscription_json = 'null'  # ✅ null not empty string
    
      
    from chat.models import EscalatedIssue
    resolved_issues = EscalatedIssue.objects.filter(
        user=request.user,
        status='resolved',
        seen_by_user=False  # ✅ only show unseen ones
    ).order_by('-resolved_at')
   

    context = {
        'bookings_json':           bookings_json,
        'payments_json':           payments_json,
        'subscription_json':       subscription_json,
        'total_spent':             total_spent,
        'pending_bookings_count':  service_requests.filter(status='pending').count(),
        'completed_bookings_count': service_requests.filter(status='completed').count(),
        'resolved_issues': resolved_issues,
    }

    return render(request, 'chat/ai_chat.html', context)

@login_required
def escalate_to_admin(request):
    """Escalate complex issues to admin panel"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user = request.user
            reason = data.get('reason', '')
            message = data.get('message', '')
            
            # Create an escalated issue (you'll need to create this model)
            from .models import EscalatedIssue
            EscalatedIssue.objects.create(
                user=user,
                reason=reason,
                message=message,
                status='pending'
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Issue escalated successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required  
def mark_resolved_seen(request):
    if request.method == 'POST':
        import json
        try:
            data     = json.loads(request.body)
            issue_id = data.get('issue_id')
            from chat.models import EscalatedIssue
            updated = EscalatedIssue.objects.filter(
                id=issue_id,
                user=request.user  # ✅ security check
            ).update(seen_by_user=True)
            return JsonResponse({'success': True, 'updated': updated})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})




