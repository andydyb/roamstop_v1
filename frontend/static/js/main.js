// main.js - For index page logic etc.

document.addEventListener('DOMContentLoaded', function () {
    const countrySelect = document.getElementById('country_code_select');
    const showPackagesBtn = document.getElementById('show-packages-btn');
    const productListContainer = document.getElementById('product-list-container');
    // const resellerIdInput = document.getElementById('reseller_id_checkout'); // This ID is on checkout.html, not index.html

    // Function to get reseller_id from URL query parameter
    function getResellerIdFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('reseller_id') || urlParams.get('ref'); // Support ref as well
    }

    // Store reseller_id if present in URL
    const currentResellerId = getResellerIdFromUrl();
    if (currentResellerId) {
        localStorage.setItem('resellerId', currentResellerId);
        console.log('Reseller ID from URL:', currentResellerId);
    }


    // Populate country dropdown
    if (countrySelect) {
        api.getCountryList().then(countries => {
            countrySelect.innerHTML = '<option value="">Select a country</option>'; // Clear loading/default
            if (countries && countries.length > 0) {
                countries.forEach(countryCode => {
                    const option = document.createElement('option');
                    option.value = countryCode;
                    // Attempt to display full country name if possible (requires a mapping)
                    // For now, just using the code. A real app would use a country code to name map.
                    try {
                        const displayName = new Intl.DisplayNames(['en'], { type: 'region' }).of(countryCode.toUpperCase());
                        option.textContent = `${displayName} (${countryCode.toUpperCase()})`;
                    } catch (e) {
                        option.textContent = countryCode.toUpperCase(); // Fallback if DisplayNames is not supported or code is invalid
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

    // Function to render product packages
    function renderProducts(products) {
        productListContainer.innerHTML = ''; // Clear previous products
        if (!products || products.length === 0) {
            productListContainer.innerHTML = '<p>No packages found for this country.</p>';
            return;
        }

        products.forEach(product => {
            const card = document.createElement('div');
            card.className = 'product-card'; // From style.css
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

        // Add event listeners to new "Select Package" buttons
        document.querySelectorAll('.select-package-btn').forEach(button => {
            button.addEventListener('click', function() {
                const productId = this.dataset.productId;
                const productName = this.dataset.productName;
                const productPrice = this.dataset.productPrice;

                localStorage.setItem('selectedProductId', productId);
                localStorage.setItem('selectedProductName', productName);
                localStorage.setItem('selectedProductPrice', productPrice);

                // resellerId is already in localStorage if it was in the URL
                window.location.href = '/checkout';
            });
        });
    }

    // Event listener for "Show Packages" button or country select change
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
            productListContainer.innerHTML = ''; // Clear if no country selected
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
        const productId = localStorage.getItem('selectedProductId');
        const productName = localStorage.getItem('selectedProductName');
        const productPrice = localStorage.getItem('selectedProductPrice');
        const storedResellerId = localStorage.getItem('resellerId');

        const productDetailsDiv = document.getElementById('selected-product-details');
        const checkoutForm = document.getElementById('checkout-form');
        const checkoutMessageDiv = document.getElementById('checkout-message');
        const productIdCheckoutInput = document.getElementById('product_id_checkout');
        const resellerIdCheckoutInput = document.getElementById('reseller_id_checkout'); // Hidden input on checkout form

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
                // If no reseller ID from URL, this might be direct purchase or error.
                // For public QR code flow, reseller_id is mandatory.
                resellerIdCheckoutInput.value = '';
                console.warn('Reseller ID not found in localStorage for checkout.');
                // Potentially disable form or show message if reseller_id is strictly required
                 productDetailsDiv.innerHTML += `<p><small style="color:red;">Referral ID missing. Please use a valid referral link.</small></p>`;
                 const submitButton = checkoutForm ? checkoutForm.querySelector('button[type="submit"]') : null;
                 if (submitButton) submitButton.disabled = true;

            }
        } else if (productDetailsDiv) {
            productDetailsDiv.innerHTML = '<p>No product selected. Please go back and <a href="/">select a package</a>.</p>';
            if (checkoutForm) checkoutForm.style.display = 'none';
        }


        if (checkoutForm) {
            checkoutForm.addEventListener('submit', async function(event) { // Made async
                event.preventDefault();
                checkoutMessageDiv.textContent = 'Processing...';
                checkoutMessageDiv.style.color = 'blue';

                const finalResellerId = resellerIdCheckoutInput ? resellerIdCheckoutInput.value : storedResellerId;

                if (!finalResellerId) {
                    checkoutMessageDiv.textContent = 'Error: Reseller ID is missing. Cannot create order.';
                    checkoutMessageDiv.style.color = 'red';
                    console.error('Reseller ID missing for createPublicOrder');
                    return;
                }
                if (!productId) { // productId from localStorage
                    checkoutMessageDiv.textContent = 'Error: Product ID is missing. Please select a product.';
                    checkoutMessageDiv.style.color = 'red';
                    console.error('Product ID missing for createPublicOrder');
                    return;
                }

                const orderData = {
                    customer_email: document.getElementById('customer_email').value,
                    customer_name: document.getElementById('customer_name').value || null,
                    product_package_id: parseInt(productId),
                    reseller_id: parseInt(finalResellerId)
                };

                try {
                    const createdOrder = await api.createPublicOrder(orderData);

                    localStorage.setItem('lastOrderDetails', JSON.stringify(createdOrder));
                    localStorage.removeItem('selectedProductId');
                    localStorage.removeItem('selectedProductName');
                    localStorage.removeItem('selectedProductPrice');
                    // resellerId in localStorage is kept as it might be from URL for the session
                    window.location.href = '/order-success';
                } catch (error) {
                    console.error('Order creation failed:', error);
                    checkoutMessageDiv.textContent = `Order failed: ${error.message}`;
                    checkoutMessageDiv.style.color = 'red';
                }
            });
        }
    }

    // --- Logic for order_success.html ---
    if (window.location.pathname.endsWith('/order-success') || window.location.pathname.endsWith('/order-success.html')) {
        const orderDetailsData = localStorage.getItem('lastOrderDetails');
        if (orderDetailsData) {
            try {
                const order = JSON.parse(orderDetailsData);
                const contentDiv = document.querySelector('div.order-details-content');
                 if (contentDiv) {
                    contentDiv.innerHTML = `
                        <p>Your order (ID: <strong>${order.id}</strong>) for <strong>${order.product_package.name}</strong> has been received.</p>
                        <p>Customer Email: ${order.customer_email}</p>
                        <p>Price Paid: $${parseFloat(order.price_paid).toFixed(2)} ${order.currency_paid}</p>
                        <p>An email confirmation will be sent to you shortly (placeholder).</p>
                    `;
                }
                // Optional: Clear after display if desired, but might be useful for refresh
                // localStorage.removeItem('lastOrderDetails');
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
