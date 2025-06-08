document.addEventListener('DOMContentLoaded', function () {
    const token = localStorage.getItem('roamstop_access_token');
    if (!token) {
        window.location.href = '/reseller/login'; // Redirect if not logged in
        return;
    }

    // Placeholders for dashboard elements
    const resellerNamePlaceholder = document.getElementById('reseller-name-placeholder');
    const totalSalesCountSpan = document.getElementById('total-sales-count');
    const totalEarningsSpan = document.getElementById('total-earnings'); // Earnings not implemented yet
    const salesListContainer = document.getElementById('sales-list-container');

    const resellerQrCodeContainer = document.getElementById('reseller-qr-code-container');
    const recruitmentLinkDisplay = document.getElementById('recruitment-link-display');
    const copyRecruitmentLinkBtn = document.getElementById('copy-recruitment-link-btn');
    const recruitmentQrCodeContainer = document.getElementById('recruitment-qr-code-container');

    const promotionDetailsForm = document.getElementById('promotion-details-form');
    const promotionDetailsInput = document.getElementById('promotion-details-input');
    const promotionUpdateMessage = document.getElementById('promotion-update-message');
    // const logoutButton = document.getElementById('logout-button'); // Listener is in reseller_dashboard.html

    // Fetch and display reseller profile
    if (typeof api !== 'object' || typeof api.getResellerProfile !== 'function') {
        console.error("api.js or required functions not loaded");
        // Optionally display an error to the user
        if(resellerNamePlaceholder) resellerNamePlaceholder.textContent = "Error loading data.";
        return; // Stop further execution if API functions are not available
    }

    api.getResellerProfile().then(profile => {
        if (resellerNamePlaceholder) {
            resellerNamePlaceholder.textContent = profile.business_name || profile.email;
        }
        if (promotionDetailsInput) {
            promotionDetailsInput.value = profile.promotion_details || '';
        }

        const landingPageBaseUrl = `${window.location.origin}/?ref=`;
        if (recruitmentLinkDisplay && profile.id) {
            recruitmentLinkDisplay.value = landingPageBaseUrl + profile.id;
        }

        if (resellerQrCodeContainer && profile.id) {
             resellerQrCodeContainer.innerHTML = `<p>Your landing page URL: <strong>${landingPageBaseUrl + profile.id}</strong> (QR code generation TBD)</p>`;
        }
        if (recruitmentQrCodeContainer && profile.id) {
             recruitmentQrCodeContainer.innerHTML = `<p>Recruitment URL: <strong>${landingPageBaseUrl + profile.id}</strong> (QR code generation TBD)</p>`;
        }

    }).catch(error => {
        console.error('Failed to load reseller profile:', error);
        if (error.message.includes('Unauthorized')) {
             if(typeof window.logoutReseller === 'function') window.logoutReseller(); else window.location.href = '/reseller/login';
        }
        if(resellerNamePlaceholder) resellerNamePlaceholder.textContent = "Error";
    });

    // Function to render sales table
    function renderSales(sales) {
        if (!salesListContainer) return;
        salesListContainer.innerHTML = '';

        if (!sales || sales.length === 0) {
            salesListContainer.innerHTML = '<p>No sales found yet.</p>';
            return;
        }

        const table = document.createElement('table');
        table.className = 'sales-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Order ID</th>
                    <th>Date</th>
                    <th>Product</th>
                    <th>Customer Email</th>
                    <th>Price Paid</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
            </tbody>
        `;
        const tbody = table.querySelector('tbody');
        sales.forEach(order => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${order.id}</td>
                <td>${new Date(order.created_at).toLocaleDateString()}</td>
                <td>${order.product_package.name}</td>
                <td>${order.customer_email}</td>
                <td>$${parseFloat(order.price_paid).toFixed(2)} ${order.currency_paid}</td>
                <td>${order.order_status}</td>
            `;
        });
        salesListContainer.appendChild(table);
    }

    // Fetch and display reseller sales and count
    if (salesListContainer) salesListContainer.innerHTML = '<p>Loading recent sales...</p>';
    if (totalSalesCountSpan) totalSalesCountSpan.textContent = 'Loading...';
    if (totalEarningsSpan) totalEarningsSpan.textContent = 'N/A'; // Placeholder

    api.getResellerSales(0, 20)
        .then(sales => {
            renderSales(sales);
            // For total count, we'll use a dedicated API call later
        })
        .catch(error => {
            console.error('Failed to load reseller sales:', error);
            if (salesListContainer) salesListContainer.innerHTML = '<p>Error loading sales data.</p>';
        });

    // Fetch total sales count
    if (typeof api.getResellerSalesCount === 'function' && totalSalesCountSpan) {
        api.getResellerSalesCount().then(countData => {
            totalSalesCountSpan.textContent = countData.count !== undefined ? countData.count : 'N/A';
        }).catch(error => {
            console.error('Failed to load total sales count:', error);
            if (totalSalesCountSpan) totalSalesCountSpan.textContent = 'Error';
        });
    } else if (totalSalesCountSpan) {
        totalSalesCountSpan.textContent = 'N/A (count API missing)';
    }


    // Handle promotion details form submission
    if (promotionDetailsForm) {
        promotionDetailsForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const details = promotionDetailsInput.value;
            if (promotionUpdateMessage) promotionUpdateMessage.textContent = 'Updating...';

            api.updateResellerPromotionDetails(details)
                .then(updatedProfile => {
                    if (promotionUpdateMessage) {
                        promotionUpdateMessage.textContent = 'Promotion details updated successfully!';
                        promotionUpdateMessage.style.color = 'green';
                    }
                    if (promotionDetailsInput) promotionDetailsInput.value = updatedProfile.promotion_details || '';
                    setTimeout(() => { if(promotionUpdateMessage) promotionUpdateMessage.textContent = '';}, 3000);
                })
                .catch(error => {
                    console.error('Failed to update promotion details:', error);
                    if (promotionUpdateMessage) {
                        promotionUpdateMessage.textContent = `Error: ${error.message}`;
                        promotionUpdateMessage.style.color = 'red';
                    }
                });
        });
    }

    // Copy recruitment link
    if (copyRecruitmentLinkBtn && recruitmentLinkDisplay) {
        copyRecruitmentLinkBtn.addEventListener('click', function() {
            recruitmentLinkDisplay.select();
            recruitmentLinkDisplay.setSelectionRange(0, 99999);
            try {
                document.execCommand('copy'); // Deprecated but common
                alert('Recruitment link copied to clipboard!');
            } catch (err) {
                // Fallback for browsers that don't support execCommand or if it fails
                navigator.clipboard.writeText(recruitmentLinkDisplay.value).then(() => {
                    alert('Recruitment link copied to clipboard! (using new API)');
                }).catch(e => {
                    alert('Failed to copy the link. Please copy it manually.');
                    console.error('Failed to copy text: ', e);
                });
            }
        });
    }
});
