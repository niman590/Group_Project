document.addEventListener("DOMContentLoaded", function () {
    const chatbotButton = document.getElementById("chatbotButton");
    const chatbotBox = document.getElementById("chatbotBox");
    const chatInput = document.getElementById("chatInput");
    const chatMessages = document.getElementById("chatMessages");
    const chatSendBtn = document.getElementById("chatSendBtn");
    const chatbotCloseBtn = document.getElementById("chatbotCloseBtn");
    const revealItems = document.querySelectorAll(".reveal-up");
    const statNumbers = document.querySelectorAll(".count-up");

    let isDragging = false;
    let hasMoved = false;
    let dragOffsetX = 0;
    let dragOffsetY = 0;

    function clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }

    function positionChatBox() {
        if (!chatbotButton || !chatbotBox) return;

        const buttonRect = chatbotButton.getBoundingClientRect();
        const boxWidth = chatbotBox.offsetWidth || 360;
        const boxHeight = chatbotBox.offsetHeight || 500;
        const gap = 12;

        let left = buttonRect.right - boxWidth;
        let top = buttonRect.top - boxHeight - gap;

        left = clamp(left, 12, window.innerWidth - boxWidth - 12);

        if (top < 12) {
            top = buttonRect.bottom + gap;
        }

        top = clamp(top, 12, window.innerHeight - boxHeight - 12);

        chatbotBox.style.left = `${left}px`;
        chatbotBox.style.top = `${top}px`;
        chatbotBox.style.right = "auto";
        chatbotBox.style.bottom = "auto";
    }

    function toggleChat(forceState) {
        if (!chatbotBox || !chatInput) return;

        const shouldOpen = typeof forceState === "boolean"
            ? forceState
            : chatbotBox.style.display !== "flex";

        if (!shouldOpen) {
            chatbotBox.style.display = "none";
            return;
        }

        chatbotBox.style.display = "flex";
        positionChatBox();
        chatInput.focus();
    }

    function startDrag(clientX, clientY) {
        if (!chatbotButton) return;

        const rect = chatbotButton.getBoundingClientRect();
        isDragging = true;
        hasMoved = false;
        dragOffsetX = clientX - rect.left;
        dragOffsetY = clientY - rect.top;
        chatbotButton.classList.add("dragging");
    }

    function moveButton(clientX, clientY) {
        if (!isDragging || !chatbotButton) return;

        const maxLeft = window.innerWidth - chatbotButton.offsetWidth - 12;
        const maxTop = window.innerHeight - chatbotButton.offsetHeight - 12;
        const nextLeft = clamp(clientX - dragOffsetX, 12, maxLeft);
        const nextTop = clamp(clientY - dragOffsetY, 12, maxTop);

        chatbotButton.style.left = `${nextLeft}px`;
        chatbotButton.style.top = `${nextTop}px`;
        chatbotButton.style.right = "auto";
        chatbotButton.style.bottom = "auto";

        hasMoved = true;

        if (chatbotBox && chatbotBox.style.display === "flex") {
            positionChatBox();
        }
    }

    function endDrag() {
        if (!isDragging || !chatbotButton) return;
        chatbotButton.classList.remove("dragging");
        isDragging = false;
    }

    function saveDashboardScroll() {
        sessionStorage.setItem("dashboardScrollY", String(window.scrollY));
    }

    function restoreDashboardScroll() {
        const savedY = sessionStorage.getItem("dashboardScrollY");
        if (savedY !== null) {
            window.scrollTo(0, parseInt(savedY, 10) || 0);
        }
    }

    function animateCount(element) {
        if (!element || element.dataset.countAnimated === "true") return;

        const finalValue = parseInt(element.textContent.trim(), 10);
        if (isNaN(finalValue)) return;

        element.dataset.countAnimated = "true";
        const duration = 900;
        const startTime = performance.now();

        function updateCount(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const currentValue = Math.round(finalValue * eased);

            element.textContent = currentValue;

            if (progress < 1) {
                requestAnimationFrame(updateCount);
            } else {
                element.textContent = finalValue;
            }
        }

        requestAnimationFrame(updateCount);
    }

    function revealElement(element, index) {
        if (!element || element.classList.contains("revealed")) return;

        element.style.transitionDelay = `${index * 70}ms`;
        element.classList.add("revealed");

        const counter = element.querySelector(".count-up");
        if (counter) {
            animateCount(counter);
        }
    }

    function initRevealObserver() {
        if (!("IntersectionObserver" in window)) {
            revealItems.forEach((item, index) => revealElement(item, index));
            return;
        }

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    const index = Array.from(revealItems).indexOf(entry.target);
                    revealElement(entry.target, index);
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.12,
            rootMargin: "0px 0px -40px 0px"
        });

        revealItems.forEach((item) => observer.observe(item));
    }

    async function sendMessage() {
        if (!chatInput || !chatMessages) return;

        const text = chatInput.value.trim();
        if (!text) return;

        chatMessages.innerHTML += `<div class="user-msg">${text}</div>`;
        chatInput.value = "";
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const res = await fetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ message: text })
            });

            const data = await res.json();
            chatMessages.innerHTML += `<div class="bot-msg">${data.reply}</div>`;
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } catch (error) {
            chatMessages.innerHTML += `<div class="bot-msg">Sorry, something went wrong. Please try again.</div>`;
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    if (chatbotButton) {
        chatbotButton.addEventListener("click", function (e) {
            if (hasMoved) {
                e.preventDefault();
                e.stopPropagation();
                hasMoved = false;
                return;
            }
            toggleChat();
        });

        chatbotButton.addEventListener("mousedown", function (e) {
            startDrag(e.clientX, e.clientY);
        });

        chatbotButton.addEventListener("touchstart", function (e) {
            const touch = e.touches[0];
            startDrag(touch.clientX, touch.clientY);
        }, { passive: true });
    }

    if (chatbotCloseBtn) {
        chatbotCloseBtn.addEventListener("click", function () {
            toggleChat(false);
        });
    }

    if (chatSendBtn) {
        chatSendBtn.addEventListener("click", sendMessage);
    }

    if (chatInput) {
        chatInput.addEventListener("keypress", function (e) {
            if (e.key === "Enter") {
                sendMessage();
            }
        });
    }

    document.addEventListener("mousemove", function (e) {
        moveButton(e.clientX, e.clientY);
    });

    document.addEventListener("mouseup", function () {
        endDrag();
    });

    document.addEventListener("touchmove", function (e) {
        if (!isDragging) return;
        const touch = e.touches[0];
        moveButton(touch.clientX, touch.clientY);
        e.preventDefault();
    }, { passive: false });

    document.addEventListener("touchend", function () {
        endDrag();
    });

    window.addEventListener("resize", function () {
        if (chatbotBox && chatbotBox.style.display === "flex") {
            positionChatBox();
        }
    });

    window.addEventListener("beforeunload", function () {
        saveDashboardScroll();
    });

    window.addEventListener("pageshow", function () {
        restoreDashboardScroll();
    });

    restoreDashboardScroll();
    initRevealObserver();

    statNumbers.forEach((counter) => {
        counter.textContent = counter.textContent.trim();
    });

    window.toggleChat = toggleChat;
    window.sendMessage = sendMessage;
});