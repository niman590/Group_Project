document.addEventListener("DOMContentLoaded", function () {
    const flashMessages = document.querySelectorAll("[data-flash]");
    const flashCloseButtons = document.querySelectorAll("[data-flash-close]");
    const deleteForms = document.querySelectorAll(".delete-user-form");
    const searchForm = document.getElementById("userSearchForm");
    const searchInput = document.getElementById("userSearchInput");
    const clearSearchInputBtn = document.getElementById("clearSearchInput");
    const userRows = document.querySelectorAll(".user-row");
    const visibleUserCount = document.getElementById("visibleUserCount");
    const liveSearchInfo = document.getElementById("liveSearchInfo");
    const serverSearchInfo = document.getElementById("serverSearchInfo");
    const actionButtons = document.querySelectorAll(".action-submit-btn");
    const copyEmailElements = document.querySelectorAll(".copy-email");
    const copyUserIdElements = document.querySelectorAll(".copy-user-id");

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
            liveSearchInfo.innerHTML = `Live filter: <strong>${count}</strong> user${count === 1 ? "" : "s"} match "<strong>${queryText}</strong>"`;
        }
    }

    function filterRows(query) {
        const normalizedQuery = query.trim().toLowerCase();
        let visibleCount = 0;

        userRows.forEach((row) => {
            const name = row.dataset.name || "";
            const nic = row.dataset.nic || "";
            const email = row.dataset.email || "";
            const role = row.dataset.role || "";
            const status = row.dataset.status || "";
            const userId = row.dataset.userId || "";

            const combinedText = `${name} ${nic} ${email} ${role} ${status} ${userId}`;

            if (normalizedQuery === "" || combinedText.includes(normalizedQuery)) {
                row.style.display = "";
                visibleCount += 1;
            } else {
                row.style.display = "none";
            }
        });

        updateVisibleCount(visibleCount, query);

        if (serverSearchInfo && normalizedQuery !== "") {
            serverSearchInfo.style.display = "none";
        } else if (serverSearchInfo && normalizedQuery === "") {
            serverSearchInfo.style.display = "";
        }
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
            filterRows(this.value);
        });
    }

    if (clearSearchInputBtn && searchInput) {
        clearSearchInputBtn.addEventListener("click", function () {
            searchInput.value = "";
            searchInput.focus();
            filterRows("");
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
            filterRows("");
            searchInput.blur();
        }
    });

    if (searchInput) {
        filterRows(searchInput.value);
    }
});