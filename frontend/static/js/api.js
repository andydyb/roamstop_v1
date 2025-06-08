// frontend/static/js/api.js

const API_BASE_URL = '/api/v1'; // Adjust if your API prefix is different

// Helper function to get the auth token from localStorage
function getAuthToken() {
    return localStorage.getItem('roamstop_access_token');
}

// Helper function to create headers, including Auth if token exists
function buildHeaders(isFormData = false) {
    const headers = {};
    if (!isFormData) {
        headers['Content-Type'] = 'application/json';
    }
    // For FormData, 'Content-Type' is set automatically by browser with boundary

    const token = getAuthToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

/**
 * Fetches a list of available countries that have active eSIM packages. (PUBLIC)
 * @returns {Promise<Array<string>>} A promise that resolves to an array of country codes.
 */
async function getCountryList() {
    try {
        const response = await fetch(`${API_BASE_URL}/products/countries/`); // No auth header
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching country list:', error);
        return []; // Return empty array on error
    }
}

/**
 * Fetches product packages for a given country code. (PUBLIC)
 * @param {string} countryCode - The ISO 2-letter country code.
 * @returns {Promise<Array<object>>} A promise that resolves to an array of product package objects.
 */
async function getProductsByCountry(countryCode) {
    if (!countryCode) {
        console.warn('getProductsByCountry called without countryCode');
        return [];
    }
    try {
        const response = await fetch(`${API_BASE_URL}/products/?country_code=${countryCode.toUpperCase()}&is_active=true`); // No auth header
        if (!response.ok) {
            let errorDetail = `HTTP error! status: ${response.status}`;
            try {
                const errorData = await response.json();
                if (errorData.detail) {
                    errorDetail = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
                }
            } catch (e) { /* Ignore if error response is not JSON */ }
            throw new Error(errorDetail);
        }
        return await response.json();
    } catch (error) {
        console.error(`Error fetching products for ${countryCode}:`, error);
        throw error;
    }
}

/**
 * Fetches details for a specific product package. (PUBLIC)
 * @param {number|string} productId - The ID of the product.
 * @returns {Promise<object|null>} A promise that resolves to the product object or null if not found.
 */
async function getProductDetails(productId) {
    if (!productId) {
        console.warn('getProductDetails called without productId');
        return null;
    }
    try {
        // Public users should only see active products, the ?show_inactive=false is handled by default by the API if user not admin
        const response = await fetch(`${API_BASE_URL}/products/${productId}`); // No auth header for public view
        if (!response.ok) {
            if (response.status === 404) {
                return null;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Error fetching product details for ID ${productId}:`, error);
        throw error;
    }
}

/**
 * Creates a new order using the public endpoint. (PUBLIC)
 * @param {object} orderData - The order data.
 * @param {string} orderData.customer_email - Customer's email.
 * @param {string|null} [orderData.customer_name] - Customer's name (optional).
 * @param {number|string} orderData.product_package_id - The ID of the product package.
 * @param {number|string} orderData.reseller_id - The ID of the reseller.
 * @returns {Promise<object>} A promise that resolves to the created order object.
 */
async function createPublicOrder(orderData) {
    if (!orderData || !orderData.product_package_id || !orderData.customer_email || !orderData.reseller_id) {
        console.error('createPublicOrder called with incomplete orderData:', orderData);
        throw new Error('Missing required fields for order creation.');
    }
    try {
        const response = await fetch(`${API_BASE_URL}/orders/public/`, {
            method: 'POST',
            headers: { // No auth token needed for this public endpoint
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(orderData),
        });
        if (!response.ok) {
            let errorDetail = `HTTP error! status: ${response.status}`;
            try {
                const errorData = await response.json();
                 if (errorData.detail) {
                    errorDetail = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
                }
            } catch (e) { /* Ignore */ }
            throw new Error(errorDetail);
        }
        return await response.json();
    } catch (error) {
        console.error('Error creating public order:', error);
        throw error;
    }
}

/**
 * Logs in a reseller. (PUBLIC - for obtaining token)
 * @param {string} email - The reseller's email.
 * @param {string} password - The reseller's password.
 * @returns {Promise<object>} A promise that resolves to the login response object (e.g., { access_token, token_type }).
 */
async function loginReseller(email, password) {
    if (!email || !password) {
        throw new Error('Email and password are required.');
    }
    try {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData,
        });
        if (!response.ok) {
            let errorDetail = `Login failed. Status: ${response.status}`;
            try {
                const errorData = await response.json();
                if (errorData.detail) {
                     errorDetail = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
                }
            } catch (e) { /* Ignore */ }
            throw new Error(errorDetail);
        }
        return await response.json();
    } catch (error) {
        console.error('Error logging in reseller:', error);
        throw error;
    }
}

/**
 * Creates a Stripe Payment Intent for a given order. (AUTH REQUIRED)
 * This assumes the currently logged-in user (reseller) is authorized for this order.
 * @param {number|string} orderId - The ID of the Roamstop order.
 * @returns {Promise<object>} A promise that resolves to the payment intent object (e.g., { client_secret, order_id, payment_intent_id }).
 */
async function createPaymentIntent(orderId) {
    if (!orderId) {
        throw new Error('Order ID is required to create a payment intent.');
    }
    try {
        const response = await fetch(`${API_BASE_URL}/payments/create-payment-intent`, {
            method: 'POST',
            headers: buildHeaders(), // Uses Authorization header with Bearer token
            body: JSON.stringify({ order_id: orderId }),
        });
        if (!response.ok) {
            let errorDetail = `Error creating payment intent. Status: ${response.status}`;
            try {
                const ed = await response.json();
                if(ed.detail) errorDetail = ed.detail;
            } catch (e) {/* Ignore */}
            throw new Error(errorDetail);
        }
        return await response.json();
    } catch (error) {
        console.error('Error creating payment intent:', error);
        throw error;
    }
}


// --- Authenticated API functions ---

/**
 * Fetches the profile of the currently logged-in reseller. (AUTH REQUIRED)
 * @returns {Promise<object>} A promise that resolves to the reseller's profile object.
 */
async function getResellerProfile() {
    try {
        const response = await fetch(`${API_BASE_URL}/resellers/me`, {
            method: 'GET',
            headers: buildHeaders(),
        });
        if (response.status === 401) {
            if (typeof window.logoutReseller === 'function') window.logoutReseller();
            throw new Error('Unauthorized. Please login again.');
        }
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching reseller profile:', error);
        throw error;
    }
}

/**
 * Fetches the sales for the currently logged-in reseller. (AUTH REQUIRED)
 * @param {string|null} status - Optional status to filter commissions by.
 * @param {number} [skip=0] - Number of records to skip for pagination.
 * @param {number} [limit=20] - Maximum number of records to return.
 * @returns {Promise<Array<object>>} A promise that resolves to an array of order objects.
 */
async function getMyCommissions(status = null, skip = 0, limit = 20) {
    let url = `${API_BASE_URL}/resellers/me/commissions?skip=${skip}&limit=${limit}`;
    if (status) {
        url += `&status=${encodeURIComponent(status)}`;
    }
    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: buildHeaders(),
        });
        if (response.status === 401) {
            if (typeof window.logoutReseller === 'function') window.logoutReseller();
            throw new Error('Unauthorized. Please login again.');
        }
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching reseller commissions:', error);
        throw error;
    }
}


/**
 * Fetches the sales for the currently logged-in reseller. (AUTH REQUIRED)
 * @param {number} [skip=0] - Number of records to skip for pagination.
 * @param {number} [limit=20] - Maximum number of records to return.
 * @returns {Promise<Array<object>>} A promise that resolves to an array of order objects.
 */
async function getResellerSales(skip = 0, limit = 20) {
    try {
        const response = await fetch(`${API_BASE_URL}/orders/my-sales/?skip=${skip}&limit=${limit}`, {
            method: 'GET',
            headers: buildHeaders(),
        });
        if (response.status === 401) {
            if (typeof window.logoutReseller === 'function') window.logoutReseller();
            throw new Error('Unauthorized. Please login again.');
        }
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching reseller sales:', error);
        throw error;
    }
}

/**
 * Fetches the total sales count for the currently logged-in reseller. (AUTH REQUIRED)
 * @returns {Promise<object>} A promise that resolves to an object like { "count": number }.
 */
async function getResellerSalesCount() {
    try {
        const response = await fetch(`${API_BASE_URL}/orders/my-sales/count`, {
            method: 'GET',
            headers: buildHeaders(),
        });
        if (response.status === 401) {
            if (typeof window.logoutReseller === 'function') window.logoutReseller();
            throw new Error('Unauthorized. Please login again.');
        }
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const count = await response.json();
        return { count: count };
    } catch (error) {
        console.error('Error fetching reseller sales count:', error);
        throw error;
    }
}


/**
 * Updates the promotion details for the currently logged-in reseller. (AUTH REQUIRED)
 * @param {string} promotionDetails - The new promotion content.
 * @returns {Promise<object>} A promise that resolves to the updated reseller profile object.
 */
async function updateResellerPromotionDetails(promotionDetails) {
    try {
        const response = await fetch(`${API_BASE_URL}/resellers/me/promotion-details`, {
            method: 'PUT',
            headers: buildHeaders(),
            body: JSON.stringify({ promotion_details: promotionDetails }),
        });
        if (response.status === 401) {
            if (typeof window.logoutReseller === 'function') window.logoutReseller();
            throw new Error('Unauthorized. Please login again.');
        }
        if (!response.ok) {
             let errorDetail = `HTTP error! status: ${response.status}`;
            try {
                const errorData = await response.json();
                 if (errorData.detail) {
                    errorDetail = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
                }
            } catch (e) { /* Ignore */ }
            throw new Error(errorDetail);
        }
        return await response.json();
    } catch (error) {
        console.error('Error updating promotion details:', error);
        throw error;
    }
}

// Expose functions to global scope if not using modules (standard for simple script includes)
window.api = {
    getCountryList,
    getProductsByCountry,
    getProductDetails,
    createPublicOrder,
    loginReseller,
    createPaymentIntent, // Added new function
    getResellerProfile,
    getResellerSales,
    getResellerSalesCount,
    updateResellerPromotionDetails,
    getMyCommissions
};
