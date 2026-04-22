document.addEventListener("DOMContentLoaded", function () {
    const siteHeader = document.getElementById("siteHeader");
    const mobileMenuToggle = document.getElementById("mobileMenuToggle");
    const primaryNav = document.getElementById("primaryNav");
    const scrollTopBtn = document.getElementById("scrollTopBtn");

    const modalButtons = document.querySelectorAll(".read-more-btn, .info-card-btn, .nav-help-btn, .footer-help-btn");
    const modals = document.querySelectorAll(".service-modal");
    const overlay = document.getElementById("modalOverlay");
    const closeButtons = document.querySelectorAll("[data-close]");
    const revealItems = document.querySelectorAll(".reveal-up");
    const navAnchors = document.querySelectorAll('.nav-links a[href^="#"]');

    let activeModal = null;
    let lastFocusedElement = null;

    function setHeaderState() {
        if (!siteHeader) return;
        if (window.scrollY > 10) {
            siteHeader.classList.add("scrolled");
        } else {
            siteHeader.classList.remove("scrolled");
        }
    }

    function toggleMobileMenu(forceOpen) {
        if (!primaryNav || !mobileMenuToggle) return;

        const shouldOpen = typeof forceOpen === "boolean"
            ? forceOpen
            : !primaryNav.classList.contains("open");

        primaryNav.classList.toggle("open", shouldOpen);
        mobileMenuToggle.setAttribute("aria-expanded", shouldOpen ? "true" : "false");
        document.body.classList.toggle("menu-open", shouldOpen);
    }

    function getFocusableElements(container) {
        if (!container) return [];
        return Array.from(
            container.querySelectorAll(
                'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
            )
        );
    }

    function closeMobileMenuOnDesktop() {
        if (window.innerWidth > 900) {
            toggleMobileMenu(false);
        }
    }

    function closeAllModals() {
        modals.forEach((modal) => modal.classList.remove("active"));
        if (overlay) {
            overlay.classList.remove("active");
        }

        document.body.classList.remove("modal-open");
        document.documentElement.classList.remove("modal-open");
        activeModal = null;

        if (lastFocusedElement) {
            lastFocusedElement.focus();
        }
    }

    function openModal(modalId, triggerElement) {
        const targetModal = document.getElementById(modalId);
        if (!targetModal || !overlay) return;

        closeAllModals();

        lastFocusedElement = triggerElement || document.activeElement;
        activeModal = targetModal;

        targetModal.scrollTop = 0;
        overlay.scrollTop = 0;
        targetModal.classList.add("active");
        overlay.classList.add("active");
        document.body.classList.add("modal-open");
        document.documentElement.classList.add("modal-open");

        const focusable = getFocusableElements(targetModal);
        if (focusable.length) {
            focusable[0].focus();
        } else {
            targetModal.setAttribute("tabindex", "-1");
            targetModal.focus();
        }
    }

    function handleFocusTrap(event) {
        if (!activeModal || event.key !== "Tab") return;

        const focusable = getFocusableElements(activeModal);
        if (!focusable.length) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    }

    function handleReveal() {
        revealItems.forEach((item) => {
            const rect = item.getBoundingClientRect();
            if (rect.top < window.innerHeight - 80) {
                item.classList.add("revealed");
            }
        });
    }

    function updateScrollTopButton() {
        if (!scrollTopBtn) return;
        if (window.scrollY > 300) {
            scrollTopBtn.classList.add("show");
        } else {
            scrollTopBtn.classList.remove("show");
        }
    }

    function updateActiveSectionLink() {
        const sections = [
            { id: "main-services", link: document.querySelector('.nav-links a[href="#main-services"]') },
            { id: "useful-information", link: document.querySelector('.nav-links a[href="#useful-information"]') }
        ];

        let currentSectionId = "";

        sections.forEach((section) => {
            const sectionElement = document.getElementById(section.id);
            if (!sectionElement) return;

            const rect = sectionElement.getBoundingClientRect();
            if (rect.top <= 140 && rect.bottom >= 140) {
                currentSectionId = section.id;
            }
        });

        navAnchors.forEach((link) => link.classList.remove("active"));

        if (currentSectionId) {
            const activeLink = document.querySelector(`.nav-links a[href="#${currentSectionId}"]`);
            if (activeLink) {
                activeLink.classList.add("active");
            }
        }
    }

    modalButtons.forEach((button) => {
        button.addEventListener("click", function () {
            const modalId = this.getAttribute("data-modal");
            openModal(modalId, this);
        });
    });

    closeButtons.forEach((button) => {
        button.addEventListener("click", closeAllModals);
    });

    if (overlay) {
        overlay.addEventListener("click", closeAllModals);
    }

    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener("click", function () {
            toggleMobileMenu();
        });
    }

    navAnchors.forEach((anchor) => {
        anchor.addEventListener("click", function () {
            if (window.innerWidth <= 900) {
                toggleMobileMenu(false);
            }
        });
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            if (activeModal) {
                closeAllModals();
            } else if (primaryNav && primaryNav.classList.contains("open")) {
                toggleMobileMenu(false);
            }
        }

        handleFocusTrap(event);
    });

    if (scrollTopBtn) {
        scrollTopBtn.addEventListener("click", function () {
            window.scrollTo({
                top: 0,
                behavior: "smooth"
            });
        });
    }

    window.addEventListener("scroll", function () {
        setHeaderState();
        handleReveal();
        updateScrollTopButton();
        updateActiveSectionLink();
    });

    window.addEventListener("resize", function () {
        closeMobileMenuOnDesktop();
    });

    setHeaderState();
    handleReveal();
    updateScrollTopButton();
    updateActiveSectionLink();
});