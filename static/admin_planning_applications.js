document.addEventListener("DOMContentLoaded", function () {
    const revealItems = document.querySelectorAll(".reveal-up");
    const actionButtons = document.querySelectorAll(".action-btn");
    const searchInput = document.getElementById("applicationSearch");
    const rows = document.querySelectorAll(".application-row");
    const visibleCount = document.getElementById("visibleCount");
    const clientEmptyState = document.getElementById("clientEmptyState");
    const emptyRow = document.getElementById("emptyRow");

    function revealOnScroll() {
        revealItems.forEach((item) => {
            const rect = item.getBoundingClientRect();
            if (rect.top < window.innerHeight - 70) {
                item.classList.add("revealed");
            }
        });
    }

    function updateVisibleCount(count) {
        if (visibleCount) {
            visibleCount.textContent = `${count} visible`;
        }
    }

    function filterRows(query) {
        const normalizedQuery = query.trim().toLowerCase();
        let visibleRows = 0;

        rows.forEach((row) => {
            const searchableText = [
                row.dataset.id || "",
                row.dataset.applicant || "",
                row.dataset.email || "",
                row.dataset.status || "",
                row.dataset.step || ""
            ].join(" ").toLowerCase();

            const matches = normalizedQuery === "" || searchableText.includes(normalizedQuery);
            row.style.display = matches ? "" : "none";

            if (matches) {
                visibleRows += 1;
            }
        });

        updateVisibleCount(visibleRows);

        if (clientEmptyState) {
            clientEmptyState.style.display = visibleRows === 0 && rows.length > 0 ? "flex" : "none";
        }

        if (emptyRow) {
            emptyRow.style.display = normalizedQuery === "" ? "" : "none";
        }
    }

    actionButtons.forEach((button) => {
        button.addEventListener("click", function () {
            this.classList.add("loading");
        });
    });

    if (searchInput) {
        searchInput.addEventListener("input", function () {
            filterRows(this.value);
        });
    }

    document.addEventListener("keydown", function (event) {
        const activeTag = document.activeElement ? document.activeElement.tagName : "";
        if (event.key === "/" && searchInput && activeTag !== "INPUT" && activeTag !== "TEXTAREA") {
            event.preventDefault();
            searchInput.focus();
        }
    });

    window.addEventListener("scroll", revealOnScroll);
    revealOnScroll();
    filterRows("");
});