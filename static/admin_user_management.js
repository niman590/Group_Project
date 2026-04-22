document.addEventListener("DOMContentLoaded", function () {
    const flashMessages = document.querySelectorAll("[data-flash]");
    const flashCloseButtons = document.querySelectorAll("[data-flash-close]");
    const deleteForms = document.querySelectorAll(".delete-user-form");
    const makeAdminForms = document.querySelectorAll(".make-admin-form");
    const searchForm = document.getElementById("userSearchForm");
    const searchInput = document.getElementById("userSearchInput");
    const clearSearchInputBtn = document.getElementById("clearSearchInput");
    const userRows = Array.from(document.querySelectorAll(".user-row"));
    const visibleUserCount = document.getElementById("visibleUserCount");
    const liveSearchInfo = document.getElementById("liveSearchInfo");
    const serverSearchInfo = document.getElementById("serverSearchInfo");
    const actionButtons = document.querySelectorAll(".action-submit-btn");
    const copyEmailElements = document.querySelectorAll(".copy-email");
    const copyUserIdElements = document.querySelectorAll(".copy-user-id");
    const toggleUsersViewBtn = document.getElementById("toggleUsersViewBtn");

    const toggleAddAdminBtn = document.getElementById("toggleAddAdminBtn");
    const cancelAddAdminBtn = document.getElementById("cancelAddAdminBtn");
    const addAdminFormWrap = document.getElementById("addAdminFormWrap");

    const employeeIdModal = document.getElementById("employeeIdModal");
    const employeeIdModalText = document.getElementById("employeeIdModalText");
    const employeeIdModalInput = document.getElementById("employeeIdModalInput");
    const employeeIdModalError = document.getElementById("employeeIdModalError");
    const employeeIdModalCancel = document.getElementById("employeeIdModalCancel");
    const employeeIdModalConfirm = document.getElementById("employeeIdModalConfirm");

    const DEFAULT_VISIBLE_ROWS = 5;
    let showAllRows = false;
    let pendingMakeAdminForm = null;

    function hideElementWithAnimation(element, duration = 250) {
        if (!element) return;
        element.style.transition = `opacity ${duration}ms ease, transform ${duration}ms ease`;
        element.style.opacity = "0";
        element.style.transform = "translateY(-6px)";
        setTimeout(() => {
            if (element.parentNode) {
                element.remove();
            }
        }, duration);
    }

    function showToast(message) {
        let toast = document.querySelector(".copy-toast");

        if (!toast) {
            toast = document.createElement("div");
            toast.className = "copy-toast";
            document.body.appendChild(toast);
        }

        toast.textContent = message;
        toast.classList.add("show");

        clearTimeout(toast.hideTimeout);
        toast.hideTimeout = setTimeout(() => {
            toast.classList.remove("show");
        }, 1800);
    }

    async function copyText(text, successMessage) {
        try {
            await navigator.clipboard.writeText(text);
            showToast(successMessage);
        } catch (error) {
            showToast("Copy failed");
        }
    }

    function updateVisibleCount(count, queryText = "") {
        if (visibleUserCount) {
            visibleUserCount.textContent = `${count} visible`;
        }

        if (liveSearchInfo) {
            if (queryText.trim() === "") {
                liveSearchInfo.style.display = "none";
                return;
            }

            liveSearchInfo.style.display = "block";
            liveSearchInfo.innerHTML = `Live filter: <strong>${count}</strong> user${count === 1 ? "" : "s"} shown for "<strong>${queryText}</strong>"`;
        }
    }

    function updateToggleButton(totalMatchedRows) {
        if (!toggleUsersViewBtn) return;

        if (totalMatchedRows <= DEFAULT_VISIBLE_ROWS) {
            toggleUsersViewBtn.style.display = "none";
            return;
        }

        toggleUsersViewBtn.style.display = "inline-flex";
        const icon = toggleUsersViewBtn.querySelector("i");
        const label = toggleUsersViewBtn.querySelector("span");

        if (showAllRows) {
            if (icon) icon.className = "fa-solid fa-eye-slash";
            if (label) label.textContent = "Show Less";
        } else {
            if (icon) icon.className = "fa-solid fa-eye";
            if (label) label.textContent = "View All";
        }
    }

    function updateRowNumbers() {
        let rowNumber = 1;

        userRows.forEach((row) => {
            if (row.style.display === "none") return;

            const rowNumberCell = row.querySelector(".row-number");
            if (rowNumberCell) {
                rowNumberCell.textContent = rowNumber;
                rowNumber += 1;
            }
        });
    }

    function filterRows(query) {
        const normalizedQuery = query.trim().toLowerCase();
        let matchedRows = [];

        userRows.forEach((row) => {
            const name = row.dataset.name || "";
            const nic = row.dataset.nic || "";
            const email = row.dataset.email || "";
            const employeeId = row.dataset.employeeId || "";
            const role = row.dataset.role || "";
            const status = row.dataset.status || "";
            const userId = row.dataset.userId || "";

            const combinedText = `${name} ${nic} ${email} ${employeeId} ${role} ${status} ${userId}`;

            if (normalizedQuery === "" || combinedText.includes(normalizedQuery)) {
                matchedRows.push(row);
            }
        });

        matchedRows.forEach((row, index) => {
            const shouldShow = showAllRows || index < DEFAULT_VISIBLE_ROWS;
            row.style.display = shouldShow ? "" : "none";
        });

        userRows.forEach((row) => {
            if (!matchedRows.includes(row)) {
                row.style.display = "none";
            }
        });

        const shownCount = showAllRows ? matchedRows.length : Math.min(matchedRows.length, DEFAULT_VISIBLE_ROWS);

        updateVisibleCount(shownCount, query);
        updateToggleButton(matchedRows.length);
        updateRowNumbers();

        if (serverSearchInfo && normalizedQuery !== "") {
            serverSearchInfo.style.display = "none";
        } else if (serverSearchInfo && normalizedQuery === "") {
            serverSearchInfo.style.display = "";
        }
    }

    function openAdminForm() {
        if (!addAdminFormWrap || !toggleAddAdminBtn) return;
        addAdminFormWrap.classList.add("open");
        toggleAddAdminBtn.innerHTML = '<i class="fa-solid fa-chevron-up"></i><span>Hide Form</span>';
    }

    function closeAdminForm() {
        if (!addAdminFormWrap || !toggleAddAdminBtn) return;
        addAdminFormWrap.classList.remove("open");
        toggleAddAdminBtn.innerHTML = '<i class="fa-solid fa-user-plus"></i><span>Add Admin</span>';
    }

    function openEmployeeIdModal(userName, form) {
        if (!employeeIdModal || !employeeIdModalInput) return;

        pendingMakeAdminForm = form;
        employeeIdModalText.textContent = `Enter an employee ID for ${userName}.`;
        employeeIdModalInput.value = "";
        employeeIdModalError.textContent = "";
        employeeIdModal.classList.add("open");

        setTimeout(() => {
            employeeIdModalInput.focus();
        }, 50);
    }

    function closeEmployeeIdModal() {
        if (!employeeIdModal) return;

        employeeIdModal.classList.remove("open");
        employeeIdModalError.textContent = "";
        employeeIdModalInput.value = "";
        pendingMakeAdminForm = null;
    }

    function validateEmployeeIdModalValue() {
        const value = employeeIdModalInput.value.trim().toUpperCase();
        const pattern = /^[A-Z0-9\-_\/]{3,30}$/i;

        if (!value) {
            employeeIdModalError.textContent = "Employee ID is required.";
            return null;
        }

        if (!pattern.test(value)) {
            employeeIdModalError.textContent =
                "Employee ID must be 3 to 30 characters and can only contain letters, numbers, hyphens, underscores, or slashes.";
            return null;
        }

        employeeIdModalError.textContent = "";
        return value;
    }

    flashMessages.forEach((flash) => {
        setTimeout(() => {
            if (flash.parentNode) {
                hideElementWithAnimation(flash, 300);
            }
        }, 5000);
    });

    flashCloseButtons.forEach((button) => {
        button.addEventListener("click", function () {
            const flash = this.closest("[data-flash]");
            hideElementWithAnimation(flash, 250);
        });
    });

    deleteForms.forEach((form) => {
        form.addEventListener("submit", function (event) {
            const userName = this.dataset.userName || "this user";
            const confirmed = window.confirm(`Are you sure you want to delete ${userName}?`);
            if (!confirmed) {
                event.preventDefault();
            }
        });
    });

    makeAdminForms.forEach((form) => {
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            const userName = this.dataset.userName || "this user";
            openEmployeeIdModal(userName, this);
        });
    });

    if (employeeIdModalCancel) {
        employeeIdModalCancel.addEventListener("click", function () {
            closeEmployeeIdModal();
        });
    }

    if (employeeIdModalConfirm) {
        employeeIdModalConfirm.addEventListener("click", function () {
            if (!pendingMakeAdminForm) return;

            const cleanedEmployeeId = validateEmployeeIdModalValue();
            if (!cleanedEmployeeId) return;

            const hiddenInput = pendingMakeAdminForm.querySelector(".employee-id-hidden-input");
            if (hiddenInput) {
                hiddenInput.value = cleanedEmployeeId;
            }

            pendingMakeAdminForm.submit();
        });
    }

    if (employeeIdModalInput) {
        employeeIdModalInput.addEventListener("input", function () {
            if (employeeIdModalError.textContent) {
                validateEmployeeIdModalValue();
            }
        });

        employeeIdModalInput.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                if (employeeIdModalConfirm) {
                    employeeIdModalConfirm.click();
                }
            }
        });
    }

    if (employeeIdModal) {
        employeeIdModal.addEventListener("click", function (event) {
            if (event.target === employeeIdModal) {
                closeEmployeeIdModal();
            }
        });
    }

    actionButtons.forEach((button) => {
        button.addEventListener("click", function () {
            const buttonLabel = this.querySelector("span");
            this.classList.add("loading");

            if (buttonLabel) {
                buttonLabel.dataset.originalText = buttonLabel.textContent;
                buttonLabel.textContent = "Processing...";
            }
        });
    });

    if (searchForm && searchInput) {
        searchForm.addEventListener("submit", function () {
            searchInput.value = searchInput.value.trim();
        });

        searchInput.addEventListener("input", function () {
            showAllRows = false;
            filterRows(this.value);
        });
    }

    if (clearSearchInputBtn && searchInput) {
        clearSearchInputBtn.addEventListener("click", function () {
            searchInput.value = "";
            searchInput.focus();
            showAllRows = false;
            filterRows("");
        });
    }

    if (toggleUsersViewBtn) {
        toggleUsersViewBtn.addEventListener("click", function () {
            showAllRows = !showAllRows;
            filterRows(searchInput ? searchInput.value : "");
        });
    }

    if (toggleAddAdminBtn) {
        toggleAddAdminBtn.addEventListener("click", function () {
            if (!addAdminFormWrap) return;

            if (addAdminFormWrap.classList.contains("open")) {
                closeAdminForm();
            } else {
                openAdminForm();
            }
        });
    }

    if (cancelAddAdminBtn) {
        cancelAddAdminBtn.addEventListener("click", function () {
            closeAdminForm();
        });
    }

    copyEmailElements.forEach((element) => {
        element.addEventListener("click", function () {
            copyText(this.textContent.trim(), "Email copied");
        });
    });

    copyUserIdElements.forEach((element) => {
        element.addEventListener("click", function () {
            copyText(this.textContent.trim(), "User ID copied");
        });
    });

    document.addEventListener("keydown", function (event) {
        const isSlashPressed = event.key === "/";
        const isEscapePressed = event.key === "Escape";
        const activeTag = document.activeElement ? document.activeElement.tagName : "";
        const isTypingInInput = ["INPUT", "TEXTAREA", "SELECT"].includes(activeTag);

        if (isSlashPressed && !isTypingInInput && searchInput) {
            event.preventDefault();
            searchInput.focus();
        }

        if (isEscapePressed && searchInput && document.activeElement === searchInput) {
            searchInput.value = "";
            showAllRows = false;
            filterRows("");
            searchInput.blur();
        }

        if (isEscapePressed && addAdminFormWrap && addAdminFormWrap.classList.contains("open")) {
            closeAdminForm();
        }

        if (isEscapePressed && employeeIdModal && employeeIdModal.classList.contains("open")) {
            closeEmployeeIdModal();
        }
    });

    if (searchInput) {
        filterRows(searchInput.value);
    } else {
        updateToggleButton(userRows.length);
        updateRowNumbers();
    }
});

// Phone number validation (numbers only, max 10)
const phoneInput = document.getElementById("phone_number");

if (phoneInput) {
    phoneInput.addEventListener("input", function () {
        // Remove non-numeric characters
        this.value = this.value.replace(/[^0-9]/g, "");

        // Limit to 10 digits
        if (this.value.length > 10) {
            this.value = this.value.slice(0, 10);
        }
    });
}