document.addEventListener("DOMContentLoaded", function () {
    const revealItems = document.querySelectorAll(".reveal-up");
    const actionButtons = document.querySelectorAll(".action-btn");
    const appCards = document.querySelectorAll(".app-card");

    function revealOnScroll() {
        revealItems.forEach((item, index) => {
            const rect = item.getBoundingClientRect();

            if (rect.top < window.innerHeight - 70) {
                item.style.transitionDelay = `${Math.min(index * 60, 320)}ms`;
                item.classList.add("revealed");
            }
        });
    }

    actionButtons.forEach((button) => {
        button.addEventListener("click", function () {
            this.classList.add("loading");
        });
    });

    appCards.forEach((card) => {
        card.addEventListener("mousemove", function (e) {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const rotateX = ((y / rect.height) - 0.5) * -3;
            const rotateY = ((x / rect.width) - 0.5) * 3;

            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-2px)`;
        });

        card.addEventListener("mouseleave", function () {
            card.style.transform = "";
        });
    });

    window.addEventListener("scroll", revealOnScroll);
    revealOnScroll();
});