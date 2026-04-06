const searchInput = document.getElementById("documentSearch");
const categoryFilter = document.getElementById("categoryFilter");
const audienceFilter = document.getElementById("audienceFilter");
const documentCards = document.querySelectorAll(".document-card");
const emptyState = document.getElementById("emptyState");

const modal = document.getElementById("docModal");
const closeModalBtn = document.getElementById("closeModalBtn");
const modalTitle = document.getElementById("modalTitle");
const modalDescription = document.getElementById("modalDescription");
const modalCategory = document.getElementById("modalCategory");
const modalAudience = document.getElementById("modalAudience");
const modalStatus = document.getElementById("modalStatus");

const modalActions = document.getElementById("modalActions");
const modalViewLink = document.getElementById("modalViewLink");
const modalDownloadLink = document.getElementById("modalDownloadLink");

function filterDocuments() {
    const searchValue = (searchInput?.value || "").toLowerCase().trim();
    const selectedCategory = categoryFilter?.value || "all";
    const selectedAudience = audienceFilter?.value || "all";

    let visibleCount = 0;

    documentCards.forEach((card) => {
        const title = (card.dataset.title || "").toLowerCase();
        const description = (card.dataset.description || "").toLowerCase();
        const category = card.dataset.category || "";
        const audience = card.dataset.audience || "";

        const matchesSearch =
            searchValue === "" ||
            title.includes(searchValue) ||
            description.includes(searchValue);

        const matchesCategory =
            selectedCategory === "all" || category === selectedCategory;

        const matchesAudience =
            selectedAudience === "all" || audience === selectedAudience;

        if (matchesSearch && matchesCategory && matchesAudience) {
            card.classList.remove("hidden");
            visibleCount += 1;
        } else {
            card.classList.add("hidden");
        }
    });

    if (visibleCount === 0) {
        emptyState?.classList.remove("hidden");
    } else {
        emptyState?.classList.add("hidden");
    }
}

function openModal(button) {
    if (!button) return;

    modalTitle.textContent = button.dataset.title || "Document";
    modalDescription.textContent = button.dataset.description || "";
    modalCategory.textContent = button.dataset.category || "";
    modalAudience.textContent = button.dataset.audience || "";
    modalStatus.textContent = button.dataset.status || "";

    const viewUrl = button.dataset.viewUrl || "";
    const downloadUrl = button.dataset.downloadUrl || "";

    if (viewUrl && downloadUrl) {
        modalViewLink.href = viewUrl;
        modalDownloadLink.href = downloadUrl;
        modalActions.classList.remove("hidden");
    } else if (viewUrl) {
        modalViewLink.href = viewUrl;
        modalDownloadLink.href = "#";
        modalActions.classList.remove("hidden");
        modalDownloadLink.classList.add("hidden");
        modalViewLink.innerHTML = `<i class="fa-solid fa-book-open-reader"></i> Open Document`;
    } else {
        modalViewLink.href = "#";
        modalDownloadLink.href = "#";
        modalDownloadLink.classList.remove("hidden");
        modalActions.classList.add("hidden");
    }

    modal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
}

function closeModal() {
    modal.classList.add("hidden");
    modalDownloadLink.classList.remove("hidden");
    modalViewLink.innerHTML = `<i class="fa-solid fa-book-open-reader"></i> Open Document`;
    document.body.style.overflow = "";
}

if (searchInput) {
    searchInput.addEventListener("input", filterDocuments);
}

if (categoryFilter) {
    categoryFilter.addEventListener("change", filterDocuments);
}

if (audienceFilter) {
    audienceFilter.addEventListener("change", filterDocuments);
}

document.querySelectorAll(".view-btn").forEach((button) => {
    button.addEventListener("click", function () {
        openModal(this);
    });
});

if (closeModalBtn) {
    closeModalBtn.addEventListener("click", closeModal);
}

if (modal) {
    modal.addEventListener("click", function (event) {
        if (event.target === modal) {
            closeModal();
        }
    });
}

document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && modal && !modal.classList.contains("hidden")) {
        closeModal();
    }
});

document.addEventListener("DOMContentLoaded", function () {
    filterDocuments();
});