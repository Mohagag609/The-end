// Form Validation Functions

function validateArabicName(input) {
    // Allow Arabic letters, spaces, and numbers
    const arabicPattern = /^[\u0600-\u06FF\u0750-\u077F\s0-9]+$/;
    return arabicPattern.test(input) || input.length === 0;
}

function validatePositiveNumber(input) {
    const num = parseFloat(input);
    return !isNaN(num) && num >= 0;
}

function validatePercentage(input) {
    const num = parseFloat(input);
    return !isNaN(num) && num >= 0 && num <= 100;
}

function validateRequired(input) {
    return input && input.trim().length > 0;
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('ar-EG', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

// Real-time validation
document.addEventListener('DOMContentLoaded', function() {
    // Validate percentage inputs
    document.querySelectorAll('input[data-validate="percentage"]').forEach(input => {
        input.addEventListener('input', function() {
            if (!validatePercentage(this.value)) {
                this.classList.add('border-red-500');
                this.classList.remove('border-gray-300');
            } else {
                this.classList.remove('border-red-500');
                this.classList.add('border-gray-300');
            }
        });
    });
    
    // Validate positive number inputs
    document.querySelectorAll('input[data-validate="positive"]').forEach(input => {
        input.addEventListener('input', function() {
            if (!validatePositiveNumber(this.value)) {
                this.classList.add('border-red-500');
                this.classList.remove('border-gray-300');
            } else {
                this.classList.remove('border-red-500');
                this.classList.add('border-gray-300');
            }
        });
    });
    
    // Format currency on blur
    document.querySelectorAll('input[data-format="currency"]').forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value && validatePositiveNumber(this.value)) {
                const formatted = formatCurrency(this.value);
                this.setAttribute('data-raw-value', this.value);
                // Keep raw value for form submission
            }
        });
    });
});

// Form submission validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    let isValid = true;
    const errors = [];
    
    // Check required fields
    form.querySelectorAll('[required]').forEach(field => {
        if (!validateRequired(field.value)) {
            isValid = false;
            field.classList.add('border-red-500');
            errors.push(`حقل ${field.getAttribute('data-label') || field.name} مطلوب`);
        }
    });
    
    // Check percentage fields
    form.querySelectorAll('[data-validate="percentage"]').forEach(field => {
        if (field.value && !validatePercentage(field.value)) {
            isValid = false;
            field.classList.add('border-red-500');
            errors.push(`النسبة يجب أن تكون بين 0 و 100`);
        }
    });
    
    // Check positive number fields
    form.querySelectorAll('[data-validate="positive"]').forEach(field => {
        if (field.value && !validatePositiveNumber(field.value)) {
            isValid = false;
            field.classList.add('border-red-500');
            errors.push(`القيمة يجب أن تكون رقم موجب`);
        }
    });
    
    if (!isValid && errors.length > 0) {
        showErrors(errors);
    }
    
    return isValid;
}

function showErrors(errors) {
    const errorContainer = document.createElement('div');
    errorContainer.className = 'fixed top-20 left-4 z-50 bg-red-50 border border-red-200 rounded-lg p-4 max-w-md';
    errorContainer.innerHTML = `
        <div class="flex items-start">
            <svg class="w-5 h-5 text-red-600 mt-0.5 ml-2" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
            </svg>
            <div class="flex-1">
                <h3 class="text-sm font-medium text-red-800 mb-1">يرجى تصحيح الأخطاء التالية:</h3>
                <ul class="text-sm text-red-700 list-disc list-inside">
                    ${errors.map(error => `<li>${error}</li>`).join('')}
                </ul>
            </div>
            <button onclick="this.parentElement.parentElement.remove()" class="text-red-400 hover:text-red-600">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                </svg>
            </button>
        </div>
    `;
    document.body.appendChild(errorContainer);
    
    setTimeout(() => {
        errorContainer.remove();
    }, 5000);
}