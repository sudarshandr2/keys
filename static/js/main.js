// Enable Bootstrap tooltips
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Handle key generation confirmation
    const generateForm = document.getElementById('generateKeyForm');
    if (generateForm) {
        generateForm.addEventListener('submit', function(e) {
            const duration = document.getElementById('duration').value;
            const price = {
                'day': 2,
                'week': 7.5,
                'month': 15
            }[duration];
            
            if (!confirm(`Generate key for ${duration} at $${price}?`)) {
                e.preventDefault();
            }
        });
    }

    // Handle reseller balance updates
    const balanceForm = document.getElementById('addBalanceForm');
    if (balanceForm) {
        balanceForm.addEventListener('submit', function(e) {
            const amount = document.getElementById('amount').value;
            if (!confirm(`Add $${amount} to reseller balance?`)) {
                e.preventDefault();
            }
        });
    }
});
