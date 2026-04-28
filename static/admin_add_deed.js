let ownerRowCounter = 0;

function pad2(value) {
    return String(value).padStart(2, "0");
}

function getCurrentYear() {
    return Number(window.ADD_DEED_CURRENT_YEAR || new Date().getFullYear());
}

function buildYearOptions() {
    const currentYear = getCurrentYear();
    let options = '<option value="">Year</option>';

    for (let year = currentYear; year >= 1900; year--) {
        options += `<option value="${year}">${year}</option>`;
    }

    return options;
}

function buildMonthOptions() {
    let options = '<option value="">Month</option>';

    for (let month = 1; month <= 12; month++) {
        const value = pad2(month);
        options += `<option value="${value}">${value}</option>`;
    }

    return options;
}

function buildDayOptions() {
    let options = '<option value="">Day</option>';

    for (let day = 1; day <= 31; day++) {
        const value = pad2(day);
        options += `<option value="${value}">${value}</option>`;
    }

    return options;
}

function buildDateSelector(index) {
    return `
        <input type="hidden" name="transfer_date[]" class="transfer-date-hidden" required>

        <div class="deed-date-select-row" data-date-row="${index}">
            <div class="deed-select-wrap">
                <select class="deed-date-select" data-date-part="month" required>
                    ${buildMonthOptions()}
                </select>
                <i class="fa-solid fa-chevron-down"></i>
            </div>

            <div class="deed-select-wrap">
                <select class="deed-date-select" data-date-part="day" required>
                    ${buildDayOptions()}
                </select>
                <i class="fa-solid fa-chevron-down"></i>
            </div>

            <div class="deed-select-wrap">
                <select class="deed-date-select" data-date-part="year" required>
                    ${buildYearOptions()}
                </select>
                <i class="fa-solid fa-chevron-down"></i>
            </div>
        </div>
    `;
}

function isValidDateParts(year, month, day) {
    if (!year || !month || !day) return false;

    const numericYear = Number(year);
    const numericMonth = Number(month);
    const numericDay = Number(day);

    const date = new Date(numericYear, numericMonth - 1, numericDay);

    return (
        date.getFullYear() === numericYear &&
        date.getMonth() === numericMonth - 1 &&
        date.getDate() === numericDay
    );
}

function isFutureDate(year, month, day) {
    const selectedDate = new Date(Number(year), Number(month) - 1, Number(day));
    selectedDate.setHours(0, 0, 0, 0);

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    return selectedDate > today;
}

function updateTransferDate(row) {
    const ownerCard = row.closest(".owner-card");
    const hiddenInput = ownerCard ? ownerCard.querySelector(".transfer-date-hidden") : null;

    if (!hiddenInput) return;

    const monthSelect = row.querySelector('[data-date-part="month"]');
    const daySelect = row.querySelector('[data-date-part="day"]');
    const yearSelect = row.querySelector('[data-date-part="year"]');

    const month = monthSelect ? monthSelect.value : "";
    const day = daySelect ? daySelect.value : "";
    const year = yearSelect ? yearSelect.value : "";

    row.querySelectorAll(".deed-date-select").forEach(function (select) {
        select.classList.remove("invalid");
    });

    if (!month && !day && !year) {
        hiddenInput.value = "";
        return;
    }

    if (isValidDateParts(year, month, day) && !isFutureDate(year, month, day)) {
        hiddenInput.value = `${year}-${pad2(month)}-${pad2(day)}`;
        return;
    }

    hiddenInput.value = "";

    row.querySelectorAll(".deed-date-select").forEach(function (select) {
        select.classList.add("invalid");
    });
}

function bindDateSelectorEvents(card) {
    const row = card.querySelector(".deed-date-select-row");

    if (!row) return;

    row.querySelectorAll(".deed-date-select").forEach(function (select) {
        select.addEventListener("change", function () {
            updateTransferDate(row);
        });
    });
}

function buildOwnerRow(index) {
    const isFirst = index === 1;

    return `
        <div class="owner-card" data-owner-row="${index}">
            <div class="owner-card-top">
                <div>
                    <span class="owner-badge">Owner ${index}</span>
                    <h3>${isFirst ? "Original Owner / Registration" : "Ownership Transfer Record"}</h3>
                </div>

                <button type="button" class="btn-remove-owner" data-remove-owner="${index}">
                    <i class="fa-solid fa-trash"></i>
                    Remove
                </button>
            </div>

            <div class="form-grid">
                <div class="form-group">
                    <label>Owner Name</label>
                    <input type="text" name="owner_name[]" placeholder="Enter owner name" required>
                </div>

                <div class="form-group">
                    <label>Owner NIC</label>
                    <input type="text" name="owner_nic[]" placeholder="Enter owner NIC">
                </div>

                <div class="form-group">
                    <label>Owner Phone</label>
                    <input type="text" name="owner_phone[]" placeholder="Enter owner phone">
                </div>

                <div class="form-group">
                    <label>Transfer Date</label>
                    ${buildDateSelector(index)}
                    <small class="field-help">Select month, day, and year. Future dates are not allowed.</small>
                </div>

                <div class="form-group full-span">
                    <label>Owner Address</label>
                    <input type="text" name="owner_address[]" placeholder="Enter owner address">
                </div>

                <div class="form-group">
                    <label>Transaction Type</label>
                    <select name="transaction_type[]" required>
                        <option value="Original Registration" ${isFirst ? "selected" : ""}>Original Registration</option>
                        <option value="Sale">Sale</option>
                        <option value="Gift">Gift</option>
                        <option value="Inheritance">Inheritance</option>
                        <option value="Court Transfer">Court Transfer</option>
                        <option value="Correction">Correction</option>
                        <option value="New Registration">New Registration</option>
                    </select>
                </div>
            </div>
        </div>
    `;
}

function addOwnerRow() {
    ownerRowCounter += 1;

    const container = document.getElementById("owners-container");
    if (!container) return;

    container.insertAdjacentHTML("beforeend", buildOwnerRow(ownerRowCounter));

    const newCard = container.querySelector(`[data-owner-row="${ownerRowCounter}"]`);
    if (newCard) {
        bindDateSelectorEvents(newCard);
    }

    refreshOwnerLabels();
}

function removeOwnerRow(index) {
    const row = document.querySelector(`[data-owner-row="${index}"]`);

    if (row) {
        row.remove();
        refreshOwnerLabels();
    }
}

function refreshOwnerLabels() {
    const cards = document.querySelectorAll(".owner-card");

    cards.forEach(function (card, idx) {
        const badge = card.querySelector(".owner-badge");
        const title = card.querySelector("h3");
        const select = card.querySelector('select[name="transaction_type[]"]');

        if (badge) badge.textContent = "Owner " + (idx + 1);

        if (title) {
            title.textContent = idx === 0 ? "Original Owner / Registration" : "Ownership Transfer Record";
        }

        if (idx === 0 && select && !select.value) {
            select.value = "Original Registration";
        }
    });

    const removeButtons = document.querySelectorAll(".btn-remove-owner");

    removeButtons.forEach(function (btn) {
        btn.style.display = cards.length > 1 ? "inline-flex" : "none";
    });
}

document.addEventListener("DOMContentLoaded", function () {
    const addButton = document.getElementById("addOwnerRowBtn");
    const form = document.getElementById("addDeedForm");

    if (addButton) {
        addButton.addEventListener("click", addOwnerRow);
    }

    document.addEventListener("click", function (event) {
        const removeButton = event.target.closest("[data-remove-owner]");

        if (!removeButton) return;

        const index = removeButton.getAttribute("data-remove-owner");
        removeOwnerRow(index);
    });

    if (form) {
        form.addEventListener("submit", function (event) {
            let hasInvalidDate = false;

            document.querySelectorAll(".deed-date-select-row").forEach(function (row) {
                updateTransferDate(row);

                const selects = row.querySelectorAll(".deed-date-select");
                const values = Array.from(selects).map(function (select) {
                    return select.value;
                });

                const hasAllValues = values.every(Boolean);

                if (!hasAllValues || row.querySelector(".deed-date-select.invalid")) {
                    hasInvalidDate = true;

                    selects.forEach(function (select) {
                        select.classList.add("invalid");
                    });
                }
            });

            if (hasInvalidDate) {
                event.preventDefault();
            }
        });
    }

    addOwnerRow();
});