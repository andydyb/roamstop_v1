// frontend/static/js/auth.js
document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('reseller-login-form');
    const errorMessageDiv = document.getElementById('login-error-message');

    if (loginForm) {
        loginForm.addEventListener('submit', function (event) {
            event.preventDefault();
            if (errorMessageDiv) errorMessageDiv.textContent = ''; // Clear previous errors

            const email = loginForm.email.value;
            const password = loginForm.password.value;

            if (!email || !password) {
                if (errorMessageDiv) errorMessageDiv.textContent = 'Please enter both email and password.';
                return;
            }

            // Assumes api.js is loaded and loginReseller is globally available
            if (typeof api === 'object' && typeof api.loginReseller === 'function') {
                 api.loginReseller(email, password)
                    .then(data => {
                        if (data.access_token) {
                            localStorage.setItem('roamstop_access_token', data.access_token);
                            // Redirect to dashboard or intended page
                            // Make sure this page exists or is created in a subsequent step
                            window.location.href = '/reseller/dashboard';
                        } else {
                            if (errorMessageDiv) errorMessageDiv.textContent = 'Login successful, but no token received.';
                        }
                    })
                    .catch(error => {
                        console.error('Login error:', error);
                        if (errorMessageDiv) errorMessageDiv.textContent = error.message || 'An unknown error occurred during login.';
                    });
            } else if (typeof loginReseller === 'function') { // Fallback if api object not used
                loginReseller(email, password)
                    .then(data => {
                        if (data.access_token) {
                            localStorage.setItem('roamstop_access_token', data.access_token);
                            window.location.href = '/reseller/dashboard';
                        } else {
                            if (errorMessageDiv) errorMessageDiv.textContent = 'Login successful, but no token received.';
                        }
                    })
                    .catch(error => {
                        console.error('Login error:', error);
                        if (errorMessageDiv) errorMessageDiv.textContent = error.message || 'An unknown error occurred during login.';
                    });
            } else {
                console.error('api.js or loginReseller function not found. Ensure api.js is loaded before auth.js');
                if (errorMessageDiv) errorMessageDiv.textContent = 'Login system error. Please try again later.';
            }
        });
    }

    // Logout functionality (can be triggered by a button on other pages)
    // Make it globally accessible for other scripts/inline calls if needed
    window.logoutReseller = function() {
        localStorage.removeItem('roamstop_access_token');
        // Optionally, inform the backend about logout if needed (e.g., token blacklisting)
        window.location.href = '/reseller/login'; // Redirect to login page
        console.log('Logged out');
    };
});
