document.addEventListener("DOMContentLoaded", function () {
    const sidebar = document.getElementById("adminSidebar");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const mobileSidebarToggle = document.getElementById("mobileSidebarToggle");
    const sidebarOverlay = document.getElementById("sidebarOverlay");
    const navLinks = document.querySelectorAll("#adminSidebar .nav-link");
    const mobileBreakpoint = 980;

    if (!sidebar) return;

    function isMobileView() {
        return window.innerWidth <= mobileBreakpoint;
    }

    function openMobileSidebar() {
        if (!isMobileView()) return;
        sidebar.classList.add("sidebar-open");
        if (sidebarOverlay) {
            sidebarOverlay.classList.add("active");
        }
        document.body.style.overflow = "hidden";
    }

    function closeMobileSidebar() {
        sidebar.classList.remove("sidebar-open");
        if (sidebarOverlay) {
            sidebarOverlay.classList.remove("active");
        }
        document.body.style.overflow = "";
    }

    function toggleDesktopSidebar() {
        if (isMobileView()) return;
        sidebar.classList.toggle("sidebar-collapsed");

        const isCollapsed = sidebar.classList.contains("sidebar-collapsed");
        localStorage.setItem("adminSidebarCollapsed", isCollapsed ? "true" : "false");
    }

    function applySavedSidebarState() {
        if (isMobileView()) {
            sidebar.classList.remove("sidebar-collapsed");
            closeMobileSidebar();
            return;
        }

        const savedState = localStorage.getItem("adminSidebarCollapsed");
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

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeMobileSidebar();
        }
    });

    window.addEventListener("resize", function () {
        applySavedSidebarState();
    });

    applySavedSidebarState();
});