function showSection(type) {
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
}

async function submitUpdateRequest() {
    const form = document.getElementById("updateForm");
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