document.addEventListener("DOMContentLoaded", function () {
    const sidebar = document.getElementById("userSidebar");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const mobileSidebarToggle = document.getElementById("mobileSidebarToggle");
    const sidebarOverlay = document.getElementById("sidebarOverlay");
    const navLinks = document.querySelectorAll("#userSidebar .nav-link");
    const mobileBreakpoint = 980;

    const notificationToggle = document.getElementById("notificationToggle");
    const notificationPanel = document.getElementById("notificationPanel");
    const notificationItems = document.querySelectorAll(".notification-item");
    const markAllReadBtn = document.getElementById("markAllReadBtn");
    const notificationCount = document.getElementById("notificationCount");

    const chatbotButton = document.getElementById("chatbotButton");
    const chatbotBox = document.getElementById("chatbotBox");
    const chatbotCloseBtn = document.getElementById("chatbotCloseBtn");

    const revealItems = document.querySelectorAll(".reveal-up");

    function revealOnScroll() {
        revealItems.forEach((item, index) => {
            const rect = item.getBoundingClientRect();
            if (rect.top < window.innerHeight - 70) {
                item.style.transitionDelay = `${Math.min(index * 50, 250)}ms`;
                item.classList.add("revealed");
            }
        });
    }

    function isMobileView() {
        return window.innerWidth <= mobileBreakpoint;
    }

    function openMobileSidebar() {
        if (!sidebar || !isMobileView()) return;
        sidebar.classList.add("sidebar-open");
        if (sidebarOverlay) {
            sidebarOverlay.classList.add("active");
        }
        document.body.style.overflow = "hidden";
    }

    function closeMobileSidebar() {
        if (!sidebar) return;
        sidebar.classList.remove("sidebar-open");
        if (sidebarOverlay) {
            sidebarOverlay.classList.remove("active");
        }
        document.body.style.overflow = "";
    }

    function toggleDesktopSidebar() {
        if (!sidebar || isMobileView()) return;
        sidebar.classList.toggle("sidebar-collapsed");

        const isCollapsed = sidebar.classList.contains("sidebar-collapsed");
        localStorage.setItem("userSidebarCollapsed", isCollapsed ? "true" : "false");
    }

    function applySavedSidebarState() {
        if (!sidebar) return;

        if (isMobileView()) {
            sidebar.classList.remove("sidebar-collapsed");
            closeMobileSidebar();
            return;
        }

        const savedState = localStorage.getItem("userSidebarCollapsed");
        if (savedState === "true") {
            sidebar.classList.add("sidebar-collapsed");
        } else {
            sidebar.classList.remove("sidebar-collapsed");
        }
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", toggleDesktopSidebar);
    }

    if (mobileSidebarToggle) {
        mobileSidebarToggle.addEventListener("click", openMobileSidebar);
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener("click", closeMobileSidebar);
    }

    navLinks.forEach((link) => {
        link.addEventListener("click", function () {
            if (isMobileView()) {
                closeMobileSidebar();
            }
        });
    });

    if (notificationToggle && notificationPanel) {
        notificationToggle.addEventListener("click", function (e) {
            e.stopPropagation();
            notificationPanel.classList.toggle("hidden");
        });

        document.addEventListener("click", function (e) {
            const clickedInsidePanel = notificationPanel.contains(e.target);
            const clickedToggle = notificationToggle.contains(e.target);

            if (!clickedInsidePanel && !clickedToggle) {
                notificationPanel.classList.add("hidden");
            }
        });
    }

    notificationItems.forEach((item) => {
        item.addEventListener("click", async function () {
            const notificationId = this.dataset.id;
            const applicationId = this.dataset.applicationId;

            if (notificationId && this.classList.contains("unread")) {
                try {
                    const response = await fetch(`/notifications/${notificationId}/read`, {
                        method: "POST"
                    });

                    if (response.ok) {
                        this.classList.remove("unread");

                        const unreadItems = document.querySelectorAll(".notification-item.unread").length;
                        if (notificationCount) {
                            if (unreadItems > 0) {
                                notificationCount.textContent = unreadItems;
                            } else {
                                notificationCount.remove();
                            }
                        }
                    }
                } catch (error) {}
            }

            if (applicationId) {
                window.location.href = `/planning-approval/${applicationId}`;
            }
        });
    });

    if (markAllReadBtn) {
        markAllReadBtn.addEventListener("click", async function (e) {
            e.stopPropagation();
            this.disabled = true;
            this.textContent = "Marking...";

            try {
                const response = await fetch("/notifications/read-all", {
                    method: "POST"
                });

                if (response.ok) {
                    document.querySelectorAll(".notification-item.unread").forEach((item) => {
                        item.classList.remove("unread");
                    });

                    if (notificationCount) {
                        notificationCount.remove();
                    }

                    this.textContent = "All marked";
                } else {
                    this.disabled = false;
                    this.textContent = "Mark all as read";
                }
            } catch (error) {
                this.disabled = false;
                this.textContent = "Mark all as read";
            }
        });
    }

    if (chatbotButton && chatbotBox) {
        chatbotButton.addEventListener("click", function () {
            chatbotBox.classList.toggle("chat-open");
        });
    }

    if (chatbotCloseBtn && chatbotBox) {
        chatbotCloseBtn.addEventListener("click", function () {
            chatbotBox.classList.remove("chat-open");
        });
    }

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeMobileSidebar();
            if (notificationPanel) {
                notificationPanel.classList.add("hidden");
            }
            if (chatbotBox) {
                chatbotBox.classList.remove("chat-open");
            }
        }
    });

    window.addEventListener("resize", function () {
        applySavedSidebarState();
    });

    window.addEventListener("scroll", revealOnScroll);

    applySavedSidebarState();
    revealOnScroll();
});