(function($) {
    $(document).ready(function() {
        // Add tooltips
        $('[title]').tooltip();
        
        // Highlight rows based on status
        $('#result_list tbody tr').each(function() {
            const status = $(this).find('.status-progress').text().toLowerCase().trim();
            if (status.includes('pending')) {
                $(this).css('background', '#fff9e6');
            } else if (status.includes('completed')) {
                $(this).css('background', '#f0fff4');
            }
        });
        
        // Quick filter buttons
        const filterBar = `
            <div class="quick-filters" style="margin: 15px 0; display: flex; gap: 10px;">
                <button class="quick-filter" data-filter="all" style="background: #34495e; color: white; border: none; padding: 8px 20px; border-radius: 20px; cursor: pointer;">All</button>
                <button class="quick-filter" data-filter="pending" style="background: #f39c12; color: white; border: none; padding: 8px 20px; border-radius: 20px; cursor: pointer;">Pending</button>
                <button class="quick-filter" data-filter="processing" style="background: #3498db; color: white; border: none; padding: 8px 20px; border-radius: 20px; cursor: pointer;">Processing</button>
                <button class="quick-filter" data-filter="completed" style="background: #27ae60; color: white; border: none; padding: 8px 20px; border-radius: 20px; cursor: pointer;">Completed</button>
            </div>
        `;
        
        $('#changelist-filter').before(filterBar);
        
        // Quick filter functionality
        $('.quick-filter').click(function() {
            const filter = $(this).data('filter');
            if (filter === 'all') {
                window.location.href = window.location.pathname;
            } else {
                window.location.href = window.location.pathname + '?status__exact=' + filter;
            }
        });
        
        // Add keyboard shortcuts
        $(document).keydown(function(e) {
            // Alt + P for pending
            if (e.altKey && e.key === 'p') {
                window.location.href = window.location.pathname + '?status__exact=pending';
            }
            // Alt + C for completed
            if (e.altKey && e.key === 'c') {
                window.location.href = window.location.pathname + '?status__exact=completed';
            }
        });
        
        // Confirm bulk actions
        $('select[name="action"]').change(function() {
            if ($(this).val() === 'delete_selected') {
                if (!confirm('Are you sure you want to delete selected payments?')) {
                    $(this).val('');
                }
            }
        });
        
        // Animate row on click
        $('#result_list tbody tr').click(function(e) {
            if (!$(e.target).is('input, a, button')) {
                $(this).css('background', '#e3f2fd').delay(200).queue(function() {
                    $(this).css('background', '').dequeue();
                });
            }
        });
    });
})(django.jQuery);