document.addEventListener("DOMContentLoaded", function () {
    const revealItems = document.querySelectorAll(".reveal-up");
    const requestCards = document.querySelectorAll("[data-request-card]");
    const uploadButtons = document.querySelectorAll(".upload-btn");

    function revealOnScroll() {
        revealItems.forEach((item, index) => {
            const rect = item.getBoundingClientRect();
            if (rect.top < window.innerHeight - 70) {
                item.style.transitionDelay = `${Math.min(index * 50, 250)}ms`;
                item.classList.add("revealed");
            }
        });
    }

    requestCards.forEach((card, index) => {
        const toggle = card.querySelector(".request-toggle");
        if (!toggle) return;

        if (index === 0) {
            card.classList.add("open");
        }

        toggle.addEventListener("click", function () {
            card.classList.toggle("open");
        });
    });

    uploadButtons.forEach((button) => {
        button.addEventListener("click", function () {
            this.classList.add("loading");
            this.style.opacity = "0.82";
            this.style.pointerEvents = "none";
        });
    });

    window.addEventListener("scroll", revealOnScroll);
    revealOnScroll();
});