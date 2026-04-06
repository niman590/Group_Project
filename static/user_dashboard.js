document.addEventListener("DOMContentLoaded", function () {
    const chatbotButton = document.getElementById("chatbotButton");
    const chatbotBox = document.getElementById("chatbotBox");
    const chatInput = document.getElementById("chatInput");
    const chatMessages = document.getElementById("chatMessages");
    const chatSendBtn = document.getElementById("chatSendBtn");
    const chatbotCloseBtn = document.getElementById("chatbotCloseBtn");
    const revealItems = document.querySelectorAll(".reveal-up");
    const statNumbers = document.querySelectorAll(".stat-card h3, .value-number");
    const topbar = document.querySelector(".topbar");

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
            chatbotBox.classList.remove("chat-open");
            setTimeout(() => {
                if (!chatbotBox.classList.contains("chat-open")) {
                    chatbotBox.style.display = "none";
                }
            }, 220);
            return;
        }

        chatbotBox.style.display = "flex";
        requestAnimationFrame(() => {
            chatbotBox.classList.add("chat-open");
            positionChatBox();
            chatInput.focus();
        });
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

    function shouldRefreshOnReturn() {
        if (chatbotBox && chatbotBox.style.display === "flex") return false;
        if (document.activeElement === chatInput) return false;
        return true;
    }

    function refreshDashboardOnReturn() {
        if (!shouldRefreshOnReturn()) return;

        const alreadyRefreshed = sessionStorage.getItem("dashboardReturnRefreshDone");
        if (alreadyRefreshed === "1") return;

        sessionStorage.setItem("dashboardReturnRefreshDone", "1");
        saveDashboardScroll();
        window.location.reload();
    }

    function revealOnScroll() {
        revealItems.forEach((item, index) => {
            const rect = item.getBoundingClientRect();
            if (rect.top < window.innerHeight - 70) {
                item.style.transitionDelay = `${Math.min(index * 50, 280)}ms`;
                item.classList.add("revealed");
            }
        });
    }

    function animateCount(el) {
        if (!el || el.dataset.counted === "1") return;

        const rawText = (el.textContent || "").trim();
        const number = parseFloat(rawText.replace(/[^0-9.]/g, ""));

        if (Number.isNaN(number)) {
            el.dataset.counted = "1";
            return;
        }

        el.dataset.counted = "1";

        const duration = 900;
        const start = performance.now();

        function frame(now) {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = Math.round(number * eased);

            if (rawText.startsWith("LKR")) {
                el.textContent = `LKR ${current.toLocaleString()}`;
            } else {
                el.textContent = current.toLocaleString();
            }

            if (progress < 1) {
                requestAnimationFrame(frame);
            } else {
                el.textContent = rawText;
            }
        }

        requestAnimationFrame(frame);
    }

    function runCounterAnimations() {
        statNumbers.forEach((el) => {
            const rect = el.getBoundingClientRect();
            if (rect.top < window.innerHeight - 40) {
                animateCount(el);
            }
        });
    }

    function handleTopbarScroll() {
        if (!topbar) return;
        if (window.scrollY > 14) {
            topbar.classList.add("topbar-scrolled");
        } else {
            topbar.classList.remove("topbar-scrolled");
        }
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
        sessionStorage.removeItem("dashboardReturnRefreshDone");
    });

    window.addEventListener("pageshow", function (event) {
        restoreDashboardScroll();

        if (event.persisted) {
            refreshDashboardOnReturn();
        }
    });

    document.addEventListener("visibilitychange", function () {
        if (!document.hidden) {
            refreshDashboardOnReturn();
        }
    });

    window.addEventListener("scroll", function () {
        revealOnScroll();
        runCounterAnimations();
        handleTopbarScroll();
    });

    restoreDashboardScroll();
    sessionStorage.removeItem("dashboardReturnRefreshDone");
    revealOnScroll();
    runCounterAnimations();
    handleTopbarScroll();

    window.toggleChat = toggleChat;
    window.sendMessage = sendMessage;
});