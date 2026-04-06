document.addEventListener("DOMContentLoaded", function () {
    const revealItems = document.querySelectorAll(".reveal-up");
    const actionButtons = document.querySelectorAll(".action-btn");

    function revealOnScroll() {
        revealItems.forEach((item) => {
            const rect = item.getBoundingClientRect();
            if (rect.top < window.innerHeight - 70) {
                item.classList.add("revealed");
            }
        });
    }

    actionButtons.forEach((button) => {
        button.addEventListener("click", function () {
            this.classList.add("loading");
        });
    });

    window.addEventListener("scroll", revealOnScroll);
    revealOnScroll();
});