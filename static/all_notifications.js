document.addEventListener("DOMContentLoaded", function () {
    const revealItems = document.querySelectorAll(".reveal-up");
    const markAllReadBtn = document.getElementById("markAllReadPageBtn");
    const notificationCards = document.querySelectorAll(".notification-card");

    function revealOnScroll() {
        revealItems.forEach((item, index) => {
            const rect = item.getBoundingClientRect();
            if (rect.top < window.innerHeight - 70) {
                item.style.transitionDelay = `${Math.min(index * 60, 300)}ms`;
                item.classList.add("revealed");
            }
        });
    }

    notificationCards.forEach((card) => {
        card.addEventListener("click", async function () {
            const applicationId = this.dataset.applicationId;
            const notificationId = this.dataset.id;

            if (notificationId) {
                try {
                    await fetch(`/notifications/${notificationId}/read`, {
                        method: "POST"
                    });
                } catch (error) {}
            }

            this.classList.remove("unread");
            const unreadDot = this.querySelector(".unread-dot");
            if (unreadDot) unreadDot.remove();

            if (applicationId) {
                window.location.href = `/planning-approval/${applicationId}`;
            }
        });
    });

    if (markAllReadBtn) {
        markAllReadBtn.addEventListener("click", async function () {
            this.disabled = true;
            this.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Marking...`;

            try {
                const response = await fetch("/notifications/read-all", {
                    method: "POST"
                });

                if (response.ok) {
                    document.querySelectorAll(".notification-card.unread").forEach((card) => {
                        card.classList.remove("unread");
                    });

                    document.querySelectorAll(".unread-dot").forEach((dot) => {
                        dot.remove();
                    });

                    this.innerHTML = `<i class="fa-solid fa-check"></i> All marked as read`;
                } else {
                    this.disabled = false;
                    this.innerHTML = `<i class="fa-solid fa-check-double"></i> Mark all as read`;
                }
            } catch (error) {
                this.disabled = false;
                this.innerHTML = `<i class="fa-solid fa-check-double"></i> Mark all as read`;
            }
        });
    }

    window.addEventListener("scroll", revealOnScroll);
    revealOnScroll();
});