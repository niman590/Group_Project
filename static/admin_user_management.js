document.addEventListener("DOMContentLoaded", function () {
    const flashMessages = document.querySelectorAll("[data-flash]");
    const flashCloseButtons = document.querySelectorAll("[data-flash-close]");
    const deleteForms = document.querySelectorAll(".delete-user-form");
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

    const DEFAULT_VISIBLE_ROWS = 5;
    let showAllRows = false;

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
        const isTypingInInput = ["INPUT", "TEXTAREA"].includes(activeTag);

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
    });

    if (searchInput) {
        filterRows(searchInput.value);
    } else {
        updateToggleButton(userRows.length);
        updateRowNumbers();
    }
});