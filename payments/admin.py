from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.urls import path, reverse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count

from .models import Payment, WorkerPayment
from workers.models import WorkerProfile
from booking.models import ServiceRequest

from django.contrib import admin
from django.utils import timezone
from payments.models import Payment


# ── CASH REJECTION FILTER — must be defined BEFORE PaymentAdmin ──
class CashRejectionFilter(admin.SimpleListFilter):
    title = 'Cash Status'
    parameter_name = 'cash_status'

    def lookups(self, request, model_admin):
        return (
            ('rejected', 'Cash Rejected'),
            ('pending',  'Pending Collection'),
            ('received', 'Cash Received'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'rejected':
            return queryset.filter(
                payment_method='cash',
                cash_rejection_date__isnull=False
            )
        if self.value() == 'pending':
            return queryset.filter(
                payment_method='cash',
                cash_received=False,
                cash_rejection_date__isnull=True
            )
        if self.value() == 'received':
            return queryset.filter(
                payment_method='cash',
                cash_received=True
            )


class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'get_user', 'get_booking', 'amount',
        'payment_method', 'status', 'transaction_id',
        'payment_date', 'get_refund',
    ]
    # ✅ CashRejectionFilter as class reference — not string
    list_filter  = ['status', 'payment_method', 'cash_received',
                    'refund_requested', CashRejectionFilter]
    search_fields = ['user__username', 'user__email', 'transaction_id']
    list_per_page = 20
    ordering = ['-created_at']
    actions = ['approve_refunds', 'mark_as_completed', 'export_payments']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'booking', 'booking__service'
        )

    fieldsets = (
        ('Customer', {'fields': ('user',)}),
        ('Booking',  {'fields': ('booking',)}),
        ('Payment',  {'fields': ('amount', 'status', 'payment_method',
                                  'transaction_id', 'payment_date')}),
        ('Cash', {
            'fields': ('cash_received', 'cash_received_date', 'cash_received_by',
                       'cash_rejection_date', 'cash_rejection_reason'),
            'classes': ('collapse',),
        }),
        ('Refund', {
            'fields': ('refund_requested', 'refund_request_date', 'refund_amount',
                       'refund_date', 'refund_reason', 'refunded_by'),
            'classes': ('collapse',),
        }),
        ('Other', {
            'fields': ('notes', 'subscription'),
            'classes': ('collapse',),
        }),
    )

    def get_user(self, obj):
        return obj.user.username if obj.user else '-'
    get_user.short_description = 'Customer'

    def get_booking(self, obj):
        if obj.booking:
            try:
                service = obj.booking.service.name if obj.booking.service else ''
                return 'Booking #{} - {}'.format(obj.booking.id, service)
            except Exception:
                return 'Booking #{}'.format(obj.booking.id)
        return '-'
    get_booking.short_description = 'Booking'

    def get_refund(self, obj):
        if obj.refund_requested:
            if obj.status == 'refunded':
                return 'Refunded Rs.{}'.format(obj.refund_amount or obj.amount)
            return 'Pending Refund'
        return '-'
    get_refund.short_description = 'Refund'

    def approve_refunds(self, request, queryset):
        updated = 0
        for payment in queryset.filter(refund_requested=True).exclude(status='refunded'):
            payment.status = 'refunded'
            payment.refund_date = timezone.now()
            payment.refunded_by = request.user
            if not payment.refund_amount:
                payment.refund_amount = payment.amount
            payment.save()
            updated += 1
        self.message_user(request, '{} refund(s) approved.'.format(updated))
    approve_refunds.short_description = 'Approve selected refund requests'

    def mark_as_completed(self, request, queryset):
        count = queryset.update(status='completed', payment_date=timezone.now())
        self.message_user(request, '{} payment(s) marked as completed.'.format(count))
    mark_as_completed.short_description = 'Mark as completed'

    def export_payments(self, request, queryset):
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payments.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Customer', 'Email', 'Booking', 'Amount',
                         'Method', 'Status', 'Transaction ID', 'Date'])
        for p in queryset:
            writer.writerow([
                p.id,
                p.user.username if p.user else '',
                p.user.email if p.user else '',
                p.booking.id if p.booking else '',
                p.amount, p.payment_method, p.status,
                p.transaction_id,
                p.payment_date.strftime('%Y-%m-%d %H:%M') if p.payment_date else '',
            ])
        return response
    export_payments.short_description = 'Export to CSV'


# ── REFUND PROXY ──
class RefundRequestProxy(Payment):
    class Meta:
        proxy = True
        verbose_name = 'Refund Request'
        verbose_name_plural = 'Refund Requests'


class RefundRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'get_customer', 'get_service', 'amount',
        'get_reason', 'refund_request_date', 'refund_amount', 'status',
    ]
    list_filter   = ['status', 'payment_method']
    search_fields = ['user__username', 'refund_reason']
    list_per_page = 20
    ordering      = ['-refund_request_date']
    actions       = ['approve_refunds', 'reject_refunds']
    list_display_links = ['id', 'get_customer']

    readonly_fields = [
        'user', 'booking', 'amount', 'payment_method',
        'transaction_id', 'payment_date',
        'refund_requested', 'refund_request_date', 'refund_reason',
    ]
    fieldsets = (
        ('Payment Info', {
            'fields': ('user', 'booking', 'amount', 'payment_method',
                       'transaction_id', 'payment_date'),
        }),
        ('Refund Request', {
            'fields': ('refund_requested', 'refund_request_date', 'refund_reason'),
        }),
        ('Process Refund', {
            'fields': ('status', 'refund_amount', 'refund_date', 'refunded_by', 'notes'),
            'description': 'Change status to refunded to approve.',
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            refund_requested=True
        ).select_related('user', 'booking', 'booking__service')

    def get_customer(self, obj):
        return obj.user.username if obj.user else '-'
    get_customer.short_description = 'Customer'

    def get_service(self, obj):
        try:
            return obj.booking.service.name
        except Exception:
            return '-'
    get_service.short_description = 'Service'

    def get_reason(self, obj):
        return obj.refund_reason[:50] if obj.refund_reason else '-'
    get_reason.short_description = 'Reason'

    def approve_refunds(self, request, queryset):
        updated = 0
        for payment in queryset.exclude(status='refunded'):
            payment.status = 'refunded'
            payment.refund_date = timezone.now()
            payment.refunded_by = request.user
            if not payment.refund_amount:
                payment.refund_amount = payment.amount
            payment.save()
            updated += 1
        self.message_user(request, '{} refund(s) approved.'.format(updated))
    approve_refunds.short_description = 'Approve selected refunds'

    def reject_refunds(self, request, queryset):
        updated = queryset.exclude(status='refunded').update(
            refund_requested=False, status='completed',
        )
        self.message_user(request, '{} refund(s) rejected.'.format(updated))
    reject_refunds.short_description = 'Reject selected refunds'


# ── CASH REJECTION PROXY ──
class CashRejectionProxy(Payment):
    class Meta:
        proxy = True
        verbose_name = 'Cash Rejection'
        verbose_name_plural = 'Cash Rejections'


class CashRejectionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'get_worker', 'get_customer', 'amount',
        'cash_rejection_date', 'get_rejection_reason', 'status',
    ]
    ordering = ['-cash_rejection_date']
    list_per_page = 20
    readonly_fields = [
        'user', 'booking', 'amount', 'payment_method',
        'cash_rejection_date', 'cash_rejection_reason', 'notes',
    ]
    actions = ['mark_as_resolved']

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            payment_method='cash',
            cash_rejection_date__isnull=False
        ).select_related('user', 'booking')

    def get_worker(self, obj):
        if obj.notes:
            try:
                # Notes format: "CASH REJECTED by worker <username> on ..."
                return obj.notes.split('worker ')[1].split(' on ')[0]
            except Exception:
                pass
        return '-'
    get_worker.short_description = 'Worker'

    def get_customer(self, obj):
        return obj.user.username if obj.user else '-'
    get_customer.short_description = 'Customer'

    def get_rejection_reason(self, obj):
        return obj.cash_rejection_reason[:60] if obj.cash_rejection_reason else '-'
    get_rejection_reason.short_description = 'Reason'

    def mark_as_resolved(self, request, queryset):
        queryset.update(
            cash_received=True,
            cash_received_date=timezone.now(),
            cash_received_by=request.user,
            status='completed',
        )
        self.message_user(request,
            '{} rejection(s) marked as resolved.'.format(queryset.count()))
    mark_as_resolved.short_description = 'Mark as resolved'


# ── REGISTER ──
try:
    admin.site.unregister(Payment)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(RefundRequestProxy)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(CashRejectionProxy)
except admin.sites.NotRegistered:
    pass

admin.site.register(Payment, PaymentAdmin)
admin.site.register(RefundRequestProxy, RefundRequestAdmin)
admin.site.register(CashRejectionProxy, CashRejectionAdmin)




# worker
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count
from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import HttpResponseRedirect
from .models import WorkerPayment

class WorkerPaymentAdmin(admin.ModelAdmin):
    # These are CRITICAL for showing the action dropdown
    actions_on_top = True
    actions_on_bottom = False
    actions_selection_counter = True
    
    list_display = [
        'action_checkbox',  # This MUST be first
        'id',
        'worker_link',
        'worker_rate',
        'job_link',
        'amount_display',
        'status_colored',
        'created_at_date',
        'payment_date_short',
        'action_buttons'
    ]
    
    list_filter = ['status', 'created_at', 'payment_method']
    search_fields = ['worker__user__username', 'job__id', 'transaction_id']
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    # Define your actions here
    actions = ['process_selected_payments', 'mark_as_completed', 'generate_report']
    
    fieldsets = (
        ('Worker Information', {
            'fields': ('worker', 'job')
        }),
        ('Payment Details', {
            'fields': ('fixed_rate', 'amount', 'status')
        }),
        ('Transaction Details', {
            'fields': ('payment_date', 'payment_method', 'transaction_id', 'payment_reference')
        }),
        ('Bank Snapshot', {
            'fields': ('account_holder_name', 'bank_name', 'account_number', 'ifsc_code', 'upi_id'),
            'classes': ('collapse',)
        }),
        ('Admin', {
            'fields': ('admin_notes', 'processed_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def worker_link(self, obj):
        if obj.worker and obj.worker.user:
            try:
                url = reverse('admin:workers_workerprofile_change', args=[obj.worker.id])
                username = str(obj.worker.user.username)
                service = str(obj.worker.service_type) if obj.worker.service_type else ''
                return format_html(
                    '<a href="{}" style="font-weight: bold;">{}</a><br><small style="color: #666;">{}</small>',
                    url,
                    username,
                    service
                )
            except:
                return '-'
        return '-'
    worker_link.short_description = 'Worker'
    
    def worker_rate(self, obj):
        try:
            return format_html('₹{}/job', str(obj.fixed_rate))
        except:
            return '-'
    worker_rate.short_description = 'Rate'
    
    def job_link(self, obj):
        if obj.job:
            try:
                url = reverse('admin:booking_servicerequest_change', args=[obj.job.id])
                job_id = str(obj.job.id)
                service_name = str(obj.job.service.name) if obj.job.service else 'Unknown'
                return format_html(
                    '<a href="{}">Job #{}</a><br><small>{}</small>',
                    url,
                    job_id,
                    service_name
                )
            except:
                return '-'
        elif obj.job_ids:
            try:
                return format_html(
                    '<span style="background: #17a2b8; color: white; padding: 3px 8px; border-radius: 12px;">📦 Bulk ({} jobs)</span>',
                    str(obj.job_count)
                )
            except:
                return '-'
        return '-'
    job_link.short_description = 'Job'
    
    def amount_display(self, obj):
        try:
            color = {
                'pending': '#ffc107',
                'processing': '#17a2b8',
                'completed': '#28a745',
                'failed': '#dc3545'
            }.get(obj.status, '#6c757d')
            
            return format_html(
                '<span style="color: {}; font-weight: bold; font-size: 14px;">₹{}</span>',
                color,
                str(obj.amount)
            )
        except:
            return '-'
    amount_display.short_description = 'Amount'
    
    def status_colored(self, obj):
        try:
            colors = {
                'pending': ('#ffc107', '⏳ Pending'),
                'processing': ('#17a2b8', '🔄 Processing'),
                'completed': ('#28a745', '✅ Completed'),
                'failed': ('#dc3545', '❌ Failed'),
            }
            color, text = colors.get(obj.status, ('#6c757d', str(obj.status)))
            return format_html(
                '<span style="background: {}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px;">{}</span>',
                color,
                text
            )
        except:
            return '-'
    status_colored.short_description = 'Status'
    
    def created_at_date(self, obj):
        try:
            return format_html('{}', obj.created_at.strftime('%d/%m/%Y'))
        except:
            return '-'
    created_at_date.short_description = 'Created'
    
    def payment_date_short(self, obj):
        if obj.payment_date:
            try:
                return format_html('{}', obj.payment_date.strftime('%d/%m/%Y'))
            except:
                return '-'
        return '-'
    payment_date_short.short_description = 'Paid Date'
    
    def action_buttons(self, obj):
        if obj.status == 'pending':
            try:
                return format_html(
                    '<a class="button" href="/payments/process-payment/?ids={}" style="background: #28a745; color: white; padding: 5px 15px; border-radius: 20px; text-decoration: none; font-size: 12px; display: inline-block;">💰 Process</a>',
                    str(obj.id)
                )
            except:
                return '-'
        try:
            return format_html(
                '<span style="color: #28a745;">✓ Completed</span>'
            )
        except:
            return '-'
    action_buttons.short_description = 'Actions'
    
    # ========== BULK ACTIONS ==========
    
    def process_selected_payments(self, request, queryset):
        """Redirect to process-payment.html with selected payment IDs"""
        # Get all selected payment IDs
        payment_ids = ','.join([str(p.id) for p in queryset])
        count = queryset.count()
        
        self.message_user(
            request, 
            f'🔄 Redirecting to process {count} payments...',
            level='INFO'
        )
        
        # Redirect to the payment processing page
        return redirect(f'/payments/process-payment/?ids={payment_ids}')
    
    process_selected_payments.short_description = "💰 Process selected payments"
    
    def mark_as_completed(self, request, queryset):
        """Mark selected payments as completed"""
        count = queryset.update(
            status='completed',
            payment_date=timezone.now(),
            processed_by=request.user
        )
        self.message_user(request, f'✅ {count} payments marked as completed')
    
    mark_as_completed.short_description = "✅ Mark selected as completed"

    def generate_report(self, request, queryset):
        total = queryset.aggregate(Sum('amount'))['amount__sum'] or 0
        count = queryset.count()
        self.message_user(request, f'📊 Report: {count} payments, Total: ₹{total}', level='INFO')
    generate_report.short_description = "📊 Generate report"

# Unregister if already registered, then register
try:
    admin.site.unregister(WorkerPayment)
except admin.sites.NotRegistered:
    pass

admin.site.register(WorkerPayment, WorkerPaymentAdmin)