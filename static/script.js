document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    // 1. Bootstrap 5 Form Custom Validation Styling
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // 2. Validate Password Match on Signup Screen
    const signupForm = document.querySelector('#signup-form');
    if (signupForm) {
        const passwordInput = signupForm.querySelector('#password');
        const confirmInput = signupForm.querySelector('#confirm_password');
        
        const validatePasswords = () => {
            if (passwordInput.value !== confirmInput.value) {
                confirmInput.setCustomValidity("Passwords do not match");
            } else {
                confirmInput.setCustomValidity(""); // Clear error state on match
            }
        };

        if (passwordInput && confirmInput) {
            passwordInput.addEventListener('change', validatePasswords);
            confirmInput.addEventListener('keyup', validatePasswords);
        }
    }

    // 3. Interactive Delete Confirmation Modal Configurator
    const deleteModal = document.getElementById('deleteConfirmModal');
    if (deleteModal) {
        deleteModal.addEventListener('show.bs.modal', function (event) {
            // Button that triggered the modal
            const button = event.relatedTarget;
            
            // Extract info from data-bs-* attributes
            const studentId = button.getAttribute('data-bs-id');
            const studentName = button.getAttribute('data-bs-name');
            
            // Find target elements inside the modal
            const nameSpan = deleteModal.querySelector('#delete-student-name');
            const form = deleteModal.querySelector('#delete-confirm-form');
            
            // Update the modal's content and action route
            if (nameSpan) nameSpan.textContent = studentName;
            if (form) form.action = `/students/delete/${studentId}`;
        });
    }

    // 4. Smooth Auto-dismiss for Flash Notification Banners
    const alerts = document.querySelectorAll('.alert-dismissible-custom');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            // Check if bootstrap is active and can dismiss
            try {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } catch (e) {
                // Fallback direct UI hide if Bootstrap instance has issues
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 300);
            }
        }, 5000); // Fades out automatically after 5 seconds
    });
});
