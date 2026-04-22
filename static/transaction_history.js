function showSection(type) {
<<<<<<< HEAD
    const viewSection = document.getElementById("view-section");
    const updateSection = document.getElementById("update-section");
    const viewTab = document.getElementById("view-tab");
    const updateTab = document.getElementById("update-tab");

    viewSection.classList.add("hidden");
    updateSection.classList.add("hidden");
    viewTab.classList.remove("active");
    updateTab.classList.remove("active");

    if (type === "view") {
        viewSection.classList.remove("hidden");
        viewTab.classList.add("active");
    } else {
        updateSection.classList.remove("hidden");
        updateTab.classList.add("active");
    }
}

function escapeHtml(value) {
    if (value === null || value === undefined) return "-";
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function renderLoadingState(title, message) {
    return `
        <div class="empty-state-card">
            <div class="empty-state-icon">
                <i class="fa-solid fa-spinner fa-spin"></i>
            </div>
            <h3>${escapeHtml(title)}</h3>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}

function renderEmptyState(title, message, icon = "fa-folder-open") {
    return `
        <div class="empty-state-card">
            <div class="empty-state-icon">
                <i class="fa-solid ${icon}"></i>
            </div>
            <h3>${escapeHtml(title)}</h3>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}

async function fetchTransactionHistory() {
    const deedNumberInput = document.getElementById("view_deed_number");
    const resultDiv = document.getElementById("history-result");
    const deedNumber = deedNumberInput.value.trim();

    if (!deedNumber) {
        resultDiv.innerHTML = `<div class="error-msg">Please enter a deed number.</div>`;
        deedNumberInput.focus();
        return;
    }

    resultDiv.innerHTML = renderLoadingState(
        "Searching history...",
        "Please wait while we retrieve ownership records."
    );

    try {
        const response = await fetch("/get-transaction-history", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ deed_number: deedNumber })
        });

        const data = await response.json();

        if (data.error) {
            resultDiv.innerHTML = `<div class="error-msg">${escapeHtml(data.error)}</div>`;
            return;
        }

        let html = `
            <div class="history-overview">
                <div class="overview-card">
                    <span>Deed Number</span>
                    <strong>${escapeHtml(data.deed_number)}</strong>
                </div>
                <div class="overview-card">
                    <span>Current Owner</span>
                    <p>${escapeHtml(data.current_owner_name)}</p>
                </div>
                <div class="overview-card">
                    <span>Property Address</span>
                    <p>${escapeHtml(data.property_address)}</p>
                </div>
                <div class="overview-card">
                    <span>Location</span>
                    <p>${escapeHtml(data.location)}</p>
                </div>
            </div>
        `;

        if (!Array.isArray(data.history) || data.history.length === 0) {
            html += renderEmptyState(
                "No ownership history found",
                "No transaction records were returned for this deed number.",
                "fa-circle-info"
            );
            resultDiv.innerHTML = html;
            return;
        }

        html += `<h3 class="timeline-title">Ownership Timeline</h3>`;
        html += `<div class="timeline">`;

        data.history.forEach((item) => {
            html += `
                <div class="timeline-item">
                    <div class="timeline-top">
                        <span class="timeline-order">Order ${escapeHtml(item.ownership_order)}</span>
                        <span class="timeline-type">${escapeHtml(item.transaction_type || "-")}</span>
                    </div>

                    <div class="timeline-grid">
                        <div class="timeline-field">
                            <span>Owner Name</span>
                            <strong>${escapeHtml(item.owner_name)}</strong>
                        </div>

                        <div class="timeline-field">
                            <span>Transfer Date</span>
                            <strong>${escapeHtml(item.transfer_date)}</strong>
                        </div>

                        <div class="timeline-field">
                            <span>NIC</span>
                            <strong>${escapeHtml(item.owner_nic || "-")}</strong>
                        </div>

                        <div class="timeline-field">
                            <span>Phone</span>
                            <strong>${escapeHtml(item.owner_phone || "-")}</strong>
                        </div>

                        <div class="timeline-field" style="grid-column: 1 / -1;">
                            <span>Address</span>
                            <strong>${escapeHtml(item.owner_address || "-")}</strong>
                        </div>
                    </div>
                </div>
            `;
        });

        html += `</div>`;
        resultDiv.innerHTML = html;
    } catch (error) {
        resultDiv.innerHTML = `<div class="error-msg">Something went wrong while fetching transaction history.</div>`;
    }
=======
    document.getElementById("view-section").classList.add("hidden");
    document.getElementById("update-section").classList.add("hidden");

    if (type === "view") {
        document.getElementById("view-section").classList.remove("hidden");
    } else if (type === "update") {
        document.getElementById("update-section").classList.remove("hidden");
    }
}

async function fetchTransactionHistory() {
    const deedNumber = document.getElementById("view_deed_number").value;
    const resultDiv = document.getElementById("history-result");

    resultDiv.innerHTML = "";

    const response = await fetch("/get-transaction-history", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ deed_number: deedNumber })
    });

    const data = await response.json();

    if (data.error) {
        resultDiv.innerHTML = `<div class="error-msg">${data.error}</div>`;
        return;
    }

    let html = `
        <div class="history-card">
            <h3>Deed Number: ${data.deed_number}</h3>
            <p><strong>Property Address:</strong> ${data.property_address}</p>
            <p><strong>Location:</strong> ${data.location}</p>
            <p><strong>Current Owner:</strong> ${data.current_owner_name}</p>
        </div>
    `;

    html += `<h3>Ownership History</h3>`;

    data.history.forEach(item => {
        html += `
            <div class="history-card">
                <p><strong>Order:</strong> ${item.ownership_order}</p>
                <p><strong>Owner Name:</strong> ${item.owner_name}</p>
                <p><strong>NIC:</strong> ${item.owner_nic || "-"}</p>
                <p><strong>Address:</strong> ${item.owner_address || "-"}</p>
                <p><strong>Phone:</strong> ${item.owner_phone || "-"}</p>
                <p><strong>Transfer Date:</strong> ${item.transfer_date}</p>
                <p><strong>Transaction Type:</strong> ${item.transaction_type}</p>
            </div>
        `;
    });

    resultDiv.innerHTML = html;
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
}

async function submitUpdateRequest() {
    const form = document.getElementById("updateForm");
<<<<<<< HEAD
    const resultDiv = document.getElementById("update-result");
    const formData = new FormData(form);

    resultDiv.innerHTML = renderLoadingState(
        "Submitting request...",
        "Please wait while we send your update request."
    );

    try {
        const response = await fetch("/request-transaction-history-update", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            resultDiv.innerHTML = `<div class="error-msg">${escapeHtml(data.error)}</div>`;
            return;
        }

        resultDiv.innerHTML = `<div class="success-msg">${escapeHtml(data.message || "Request submitted successfully.")}</div>`;
        form.reset();

        const fileName = document.getElementById("file-name");
        const fileBox = document.getElementById("customFileBox");
        if (fileName) fileName.textContent = "No file selected";
        if (fileBox) fileBox.classList.remove("active");
    } catch (error) {
        resultDiv.innerHTML = `<div class="error-msg">Something went wrong while submitting the update request.</div>`;
    }
}

document.addEventListener("DOMContentLoaded", function () {
    showSection("view");

    const fileInput = document.getElementById("proof_document");
    const fileName = document.getElementById("file-name");
    const fileBox = document.getElementById("customFileBox");

    if (fileInput && fileName && fileBox) {
        fileInput.addEventListener("change", function () {
            if (this.files && this.files.length > 0) {
                fileName.textContent = this.files[0].name;
                fileBox.classList.add("active");
            } else {
                fileName.textContent = "No file selected";
                fileBox.classList.remove("active");
            }
        });
    }
});
=======
    const formData = new FormData(form);
    const resultDiv = document.getElementById("update-result");

    resultDiv.innerHTML = "";

    const response = await fetch("/request-transaction-history-update", {
        method: "POST",
        body: formData
    });

    const data = await response.json();

    if (data.error) {
        resultDiv.innerHTML = `<div class="error-msg">${data.error}</div>`;
        return;
    }

    resultDiv.innerHTML = `<div class="success-msg">${data.message}</div>`;
    form.reset();
}
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
