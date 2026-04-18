// service_request_actions.js - For handling AJAX worker assignment

document.addEventListener('DOMContentLoaded', function() {
    console.log('Service request actions JS loaded');
    
    // Handle worker assignment
    document.querySelectorAll('.assign-worker-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const requestId = this.dataset.requestId;
            const select = document.querySelector(`.worker-select[data-request-id="${requestId}"]`);
            
            if (!select) {
                alert('Worker selection not found');
                return;
            }
            
            const workerId = select.value;
            
            if (!workerId) {
                alert('Please select a worker first');
                return;
            }
            
            // Show loading state
            this.textContent = 'Assigning...';
            this.disabled = true;
            
            // Send AJAX request to assign worker
            fetch(`/booking/assign-worker-ajax/${requestId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    worker_id: workerId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Worker assigned successfully!');
                    location.reload(); // Reload page to show updated status
                } else {
                    alert(data.message || 'Error assigning worker');
                    // Reset button
                    this.textContent = 'Assign';
                    this.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error assigning worker. Check console for details.');
                // Reset button
                this.textContent = 'Assign';
                this.disabled = false;
            });
        });
    });
});

// Function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}