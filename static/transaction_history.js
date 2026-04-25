function showSection(type) {
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


// Safe HTML escape
function escapeHtml(value) {
    if (value === null || value === undefined) return "-";
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}


// =========================
// FETCH HISTORY
// =========================
async function fetchTransactionHistory() {

    const deedInput = document.getElementById("view_deed_number");
    const resultDiv = document.getElementById("history-result");

    const deedNumber = deedInput.value.trim();

    if (!deedNumber) {
        resultDiv.innerHTML = `<div class="error-msg">Enter deed number</div>`;
        return;
    }

    resultDiv.innerHTML = `<div>Loading...</div>`;

    try {
        const response = await fetch("/get-transaction-history", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ deed_number: deedNumber })
        });

        const data = await response.json();

        if (data.error) {
            resultDiv.innerHTML = `<div class="error-msg">${data.error}</div>`;
            return;
        }

        let html = `
            <div class="history-overview">
                <div><strong>Deed:</strong> ${escapeHtml(data.deed_number)}</div>
                <div><strong>Owner:</strong> ${escapeHtml(data.current_owner_name)}</div>
                <div><strong>Address:</strong> ${escapeHtml(data.property_address)}</div>
            </div>
        `;

        if (!data.history || data.history.length === 0) {
            html += `<div>No history found</div>`;
            resultDiv.innerHTML = html;
            return;
        }

        html += `<h3>History</h3>`;

        data.history.forEach(item => {
            html += `
                <div class="timeline-item">
                    <div><strong>${escapeHtml(item.owner_name)}</strong></div>
                    <div>${escapeHtml(item.transfer_date)}</div>
                    <div>${escapeHtml(item.transaction_type)}</div>
                </div>
            `;
        });

        resultDiv.innerHTML = html;

    } catch (err) {
        resultDiv.innerHTML = `<div class="error-msg">Error loading data</div>`;
    }
}


// =========================
// SUBMIT REQUEST (UPDATED)
// =========================
async function submitUpdateRequest() {

    const form = document.getElementById("updateForm");
    const resultDiv = document.getElementById("update-result");

    const formData = new FormData(form);

    const deedNumber = formData.get("deed_number");

    if (!deedNumber) {
        resultDiv.innerHTML = `<div class="error-msg">Deed number is required</div>`;
        return;
    }

    resultDiv.innerHTML = `<div>Submitting...</div>`;

    try {
        const response = await fetch("/request-transaction-history-update", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            resultDiv.innerHTML = `<div class="error-msg">${data.error}</div>`;
            return;
        }

        resultDiv.innerHTML = `
            <div class="success-msg">
                ${data.message}
            </div>
        `;

        form.reset();

    } catch (err) {
        resultDiv.innerHTML = `<div class="error-msg">Submission failed</div>`;
    }
}


// =========================
// INIT
// =========================
document.addEventListener("DOMContentLoaded", function () {
    showSection("view");
});