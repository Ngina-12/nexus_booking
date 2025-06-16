// Form Toggle Function
function toggleForm(formToShow) {
    document.querySelectorAll('.login-form, .signup-form, .reset-form').forEach(form => {
        form.style.display = 'none';
    });
    document.getElementById(formToShow).style.display = 'block';
    document.getElementById('errorMessage').style.display = 'none';
}

// Password Strength Checker
function checkPasswordStrength(password) {
    const strengthMeter = document.getElementById('strengthMeter');
    if (!strengthMeter) return;

    let strength = 0;
    
    // Length check
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    
    // Complexity checks
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[!@#$%^&*]/.test(password)) strength++;
    
    // Update meter
    strengthMeter.className = 'strength-meter';
    if (password.length > 0) {
        if (strength <= 2) {
            strengthMeter.classList.add('strength-weak');
        } else if (strength <= 4) {
            strengthMeter.classList.add('strength-medium');
        } else {
            strengthMeter.classList.add('strength-strong');
        }
    }
}

// Form Handlers
document.addEventListener('DOMContentLoaded', function() {
    // Password strength real-time feedback
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(input => {
        input.addEventListener('input', function() {
            checkPasswordStrength(this.value);
        });
    });

    // Form submissions
    document.getElementById('loginForm')?.addEventListener('submit', handleLogin);
    document.getElementById('signupForm')?.addEventListener('submit', handleSignup);
    document.getElementById('resetForm')?.addEventListener('submit', handleReset);
});

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`
        });
        
        if (response.redirected) {
            window.location.href = response.url;
        } else {
            const data = await response.text();
            showMessage(data.includes('error') ? 'error' : 'success', data);
        }
    } catch (error) {
        showMessage('error', 'Network error. Please try again.');
    }
}

async function handleSignup(e) {
    e.preventDefault();
    const email = document.getElementById('signup-email').value;
    const username = document.getElementById('signup-username').value;
    const password = document.getElementById('signup-password').value;
    const confirmPassword = document.getElementById('signup-confirm').value;
    
    if (password !== confirmPassword) {
        showMessage('error', 'Passwords do not match');
        return;
    }
    
    try {
        const response = await fetch('/signup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `email=${encodeURIComponent(email)}&username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}&confirm_password=${encodeURIComponent(confirmPassword)}`
        });
        
        if (response.redirected) {
            window.location.href = response.url;
        } else {
            const data = await response.text();
            showMessage(data.includes('error') ? 'error' : 'success', data);
        }
    } catch (error) {
        showMessage('error', 'Network error. Please try again.');
    }
}

async function handleReset(e) {
    e.preventDefault();
    const email = document.getElementById('reset-email').value;
    
    try {
        const response = await fetch('/forgot-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `email=${encodeURIComponent(email)}`
        });
        
        if (response.redirected) {
            window.location.href = response.url;
        } else {
            const data = await response.text();
            showMessage(data.includes('error') ? 'error' : 'success', data);
        }
    } catch (error) {
        showMessage('error', 'Network error. Please try again.');
    }
}

function showMessage(type, text) {
    const messageEl = document.getElementById('errorMessage');
    messageEl.textContent = text;
    messageEl.className = type === 'error' ? 'error-message' : 'success-message';
    messageEl.style.display = 'block';
    
    setTimeout(() => {
        messageEl.style.display = 'none';
    }, 5000);
}