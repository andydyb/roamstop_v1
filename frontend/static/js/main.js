// main.js - For index page logic etc.

document.addEventListener('DOMContentLoaded', function () {
    const countrySelect = document.getElementById('country_code_select');
    const showPackagesBtn = document.getElementById('show-packages-btn');
    const productListContainer = document.getElementById('product-list-container');

    function getResellerIdFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('reseller_id') || urlParams.get('ref');
    }

    const currentResellerId = getResellerIdFromUrl();
    if (currentResellerId) {
        localStorage.setItem('resellerId', currentResellerId);
        console.log('Reseller ID from URL:', currentResellerId);
    }

    if (countrySelect) {
        api.getCountryList().then(countries => {
            countrySelect.innerHTML = '<option value="">Select a country</option>';
            if (countries && countries.length > 0) {
                countries.forEach(countryCode => {
                    const option = document.createElement('option');
                    option.value = countryCode;
                    try {
                        const displayName = new Intl.DisplayNames(['en'], { type: 'region' }).of(countryCode.toUpperCase());
                        option.textContent = `${displayName} (${countryCode.toUpperCase()})`;
                    } catch (e) {
                        option.textContent = countryCode.toUpperCase();
                    }
                    countrySelect.appendChild(option);
                });
            } else {
                countrySelect.innerHTML = '<option value="">No countries available</option>';
            }
        }).catch(error => {
            console.error('Failed to load countries:', error);
            countrySelect.innerHTML = '<option value="">Error loading countries</option>';
        });
    }

    function renderProducts(products) {
        productListContainer.innerHTML = '';
        if (!products || products.length === 0) {
            productListContainer.innerHTML = '<p>No packages found for this country.</p>';
            return;
        }
        products.forEach(product => {
            const card = document.createElement('div');
            card.className = 'product-card';
            card.innerHTML = `
                <h3>${product.name}</h3>
                <p>${product.description || ''}</p>
                <p>Duration: ${product.duration_days} days</p>
                <p>Price: $${parseFloat(product.price).toFixed(2)}</p>
                <button class="select-package-btn" data-product-id="${product.id}"
                        data-product-name="${product.name}"
                        data-product-price="${product.price}">Select Package</button>
            `;
            productListContainer.appendChild(card);
        });
        document.querySelectorAll('.select-package-btn').forEach(button => {
            button.addEventListener('click', function() {
                localStorage.setItem('selectedProductId', this.dataset.productId);
                localStorage.setItem('selectedProductName', this.dataset.productName);
                localStorage.setItem('selectedProductPrice', this.dataset.productPrice);
                window.location.href = '/checkout';
            });
        });
    }

    const handleShowPackages = () => {
        const selectedCountry = countrySelect ? countrySelect.value : null;
        if (selectedCountry) {
            productListContainer.innerHTML = '<p>Loading packages...</p>';
            api.getProductsByCountry(selectedCountry)
                .then(renderProducts)
                .catch(error => {
                    console.error('Error fetching or rendering products:', error);
                    productListContainer.innerHTML = `<p style="color: red;">Error loading packages: ${error.message}</p>`;
                });
        } else {
            productListContainer.innerHTML = '';
        }
    };

    if (showPackagesBtn) {
        showPackagesBtn.addEventListener('click', handleShowPackages);
    }
    if (countrySelect) {
         countrySelect.addEventListener('change', handleShowPackages);
    }

    // --- Logic for checkout.html ---
    if (window.location.pathname.endsWith('/checkout') || window.location.pathname.endsWith('/checkout.html')) {
        // Stripe related variables
        let stripe, cardElement, elements;

        // Values from LocalStorage
        const productId = localStorage.getItem('selectedProductId');
        const productName = localStorage.getItem('selectedProductName');
        const productPrice = localStorage.getItem('selectedProductPrice');
        const storedResellerId = localStorage.getItem('resellerId');

        // DOM Elements
        const productDetailsDiv = document.getElementById('selected-product-details');
        const checkoutForm = document.getElementById('checkout-form');
        const checkoutMessageDiv = document.getElementById('checkout-message');
        const productIdCheckoutInput = document.getElementById('product_id_checkout');
        const resellerIdCheckoutInput = document.getElementById('reseller_id_checkout');
        const cardErrors = document.getElementById('card-errors');
        const submitButton = document.getElementById('submit-payment-btn');


        // Initialize Stripe Elements if stripePublishableKey is available
        if (typeof stripePublishableKey !== 'undefined' && stripePublishableKey && stripePublishableKey !== "pk_test_YOUR_STRIPE_PUBLISHABLE_KEY") {
            stripe = Stripe(stripePublishableKey);
            elements = stripe.elements();
            const style = { // Optional: Custom styling for card element
                base: { fontSize: '16px', color: '#32325d' }
            };
            cardElement = elements.create('card', { style: style });
            cardElement.mount('#card-element');

            cardElement.on('change', function(event) {
                if (cardErrors) {
                    cardErrors.textContent = event.error ? event.error.message : '';
                }
            });
        } else {
            console.warn('Stripe publishable key not found or is placeholder. Stripe Elements will not load.');
            if (cardErrors) cardErrors.textContent = 'Payment system not available. Key not configured.';
            if (submitButton) submitButton.disabled = true;
        }

        // Populate product and reseller details
        if (productId && productName && productPrice && productDetailsDiv) {
            productDetailsDiv.innerHTML = `
                <h4>Selected Package: ${productName}</h4>
                <p>Price: $${parseFloat(productPrice).toFixed(2)}</p>
            `;
            if (productIdCheckoutInput) productIdCheckoutInput.value = productId;

            if (storedResellerId && resellerIdCheckoutInput) {
                resellerIdCheckoutInput.value = storedResellerId;
                productDetailsDiv.innerHTML += `<p><small>Referral ID: ${storedResellerId}</small></p>`;
            } else if (resellerIdCheckoutInput) {
                resellerIdCheckoutInput.value = '';
                console.warn('Reseller ID not found in localStorage for checkout.');
                productDetailsDiv.innerHTML += `<p><small style="color:red;">Referral ID missing. Please use a valid referral link.</small></p>`;
                if (submitButton) submitButton.disabled = true;
            }
        } else if (productDetailsDiv) {
            productDetailsDiv.innerHTML = '<p>No product selected. Please go back and <a href="/">select a package</a>.</p>';
            if (checkoutForm) checkoutForm.style.display = 'none';
        }

        // Checkout form submission
        if (checkoutForm && stripe) { // Ensure stripe is initialized
            checkoutForm.addEventListener('submit', async function(event) {
                event.preventDefault();
                if (submitButton) submitButton.disabled = true;
                checkoutMessageDiv.textContent = 'Processing...';
                checkoutMessageDiv.style.color = 'blue';
                if (cardErrors) cardErrors.textContent = '';

                const finalResellerId = resellerIdCheckoutInput ? resellerIdCheckoutInput.value : storedResellerId;

                if (!finalResellerId || !productId) {
                    checkoutMessageDiv.textContent = 'Error: Reseller ID or Product ID is missing.';
                    checkoutMessageDiv.style.color = 'red';
                    if (submitButton) submitButton.disabled = false;
                    return;
                }

                const orderPayload = {
                    customer_email: document.getElementById('customer_email').value,
                    customer_name: document.getElementById('customer_name').value || null,
                    product_package_id: parseInt(productId),
                    reseller_id: parseInt(finalResellerId)
                };

                try {
                    // Step 1: Create Roamstop Order (Public)
                    const createdOrder = await api.createPublicOrder(orderPayload);
                    checkoutMessageDiv.textContent = 'Order created. Initializing payment...';

                    // Step 2: Create Payment Intent (this needs to be authenticated as the reseller)
                    // This assumes the 'roamstop_access_token' for the reseller is available
                    // If this checkout page is truly public for customers, the payment intent creation
                    // would need a different auth mechanism or be public itself (with security considerations).
                    // For now, we proceed assuming this flow is for a reseller completing a sale.
                    // The /create-payment-intent endpoint is protected by get_current_active_user

                    let paymentIntentResponse;
                    try {
                         paymentIntentResponse = await api.createPaymentIntent(createdOrder.id);
                    } catch (piError) {
                        // Attempt to update order status to FAILED_PAYMENT if PI creation fails
                        console.error("Payment Intent creation failed:", piError);
                        await api.updateOrderStatus(createdOrder.id, "FAILED_PAYMENT"); // Assumes updateOrderStatus API exists
                        throw piError; // Re-throw to be caught by outer catch
                    }


                    checkoutMessageDiv.textContent = 'Confirming payment...';

                    // Step 3: Confirm Card Payment with Stripe
                    const {paymentIntent, error: stripeError} = await stripe.confirmCardPayment(
                        paymentIntentResponse.client_secret, {
                            payment_method: {
                                card: cardElement,
                                billing_details: { email: orderPayload.customer_email },
                            },
                        }
                    );

                    if (stripeError) {
                        checkoutMessageDiv.textContent = stripeError.message || 'Payment failed.';
                        checkoutMessageDiv.style.color = 'red';
                        if (submitButton) submitButton.disabled = false;
                        // Optionally update order status to FAILED_PAYMENT here via API
                        await api.updateOrderStatus(createdOrder.id, "FAILED_PAYMENT");
                        return;
                    }

                    if (paymentIntent.status === 'succeeded') {
                        checkoutMessageDiv.textContent = 'Payment successful! Processing your order...';
                        checkoutMessageDiv.style.color = 'green';
                        // Order status will be updated by webhook, but can set to PROCESSING here too
                        await api.updateOrderStatus(createdOrder.id, "PROCESSING");

                        localStorage.setItem('lastOrderDetails', JSON.stringify(createdOrder)); // Store the Roamstop order
                        localStorage.setItem('lastPaymentIntentStatus', paymentIntent.status);

                        localStorage.removeItem('selectedProductId');
                        localStorage.removeItem('selectedProductName');
                        localStorage.removeItem('selectedProductPrice');
                        window.location.href = '/order-success';
                    } else {
                        checkoutMessageDiv.textContent = `Payment status: ${paymentIntent.status}. Please follow any instructions.`;
                        checkoutMessageDiv.style.color = 'orange';
                        // Update order status if needed based on other PI statuses
                        await api.updateOrderStatus(createdOrder.id, paymentIntent.status.toUpperCase());
                    }

                } catch (error) {
                    if (submitButton) submitButton.disabled = false;
                    checkoutMessageDiv.textContent = `Error: ${error.message}`;
                    checkoutMessageDiv.style.color = 'red';
                    console.error('Checkout process error:', error);
                }
            });
        }
    }

    // --- Logic for order_success.html ---
    if (window.location.pathname.endsWith('/order-success') || window.location.pathname.endsWith('/order-success.html')) {
        const orderDetailsData = localStorage.getItem('lastOrderDetails');
        const paymentStatus = localStorage.getItem('lastPaymentIntentStatus');
        if (orderDetailsData) {
            try {
                const order = JSON.parse(orderDetailsData);
                const contentDiv = document.querySelector('div.order-details-content');
                 if (contentDiv) {
                    contentDiv.innerHTML = `
                        <p>Your order (ID: <strong>${order.id}</strong>) for <strong>${order.product_package.name}</strong> has been received.</p>
                        <p>Customer Email: ${order.customer_email}</p>
                        <p>Price Paid: $${parseFloat(order.price_paid).toFixed(2)} ${order.currency_paid}</p>
                        ${paymentStatus ? `<p>Payment Status: ${paymentStatus}</p>` : ''}
                        <p>An email confirmation will be sent to you shortly (placeholder).</p>
                    `;
                }
                localStorage.removeItem('lastOrderDetails');
                localStorage.removeItem('lastPaymentIntentStatus');
            } catch (e) {
                console.error("Error parsing order details from localStorage", e);
                const contentDiv = document.querySelector('div.order-details-content');
                if (contentDiv) {
                    contentDiv.innerHTML = "<p>There was an issue displaying your order details. Please check your email.</p>";
                }
            }
        }
    }
});

// Add a placeholder for updateOrderStatus in api.js if it's not there
// This is speculative based on the error handling logic added above.
if (typeof api !== 'undefined' && typeof api.updateOrderStatus === 'undefined') {
    api.updateOrderStatus = async function(orderId, status) {
        console.warn(`api.updateOrderStatus called with ${orderId}, ${status} - but not fully implemented for frontend optimistic updates without a dedicated backend endpoint or by using the generic admin update.`);
        // Example: This might call the admin PATCH /orders/{order_id} endpoint
        // For now, this is a mock/placeholder.
        // In a real scenario, you'd need an endpoint that the current user (reseller) can call
        // to update status to FAILED_PAYMENT if they initiated the payment intent.
        // Or, this is purely handled by webhooks.
        return Promise.resolve();
    };
}
