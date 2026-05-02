document.addEventListener("DOMContentLoaded", function () {
    const chatbotButton = document.getElementById("chatbotButton");
    const chatbotBox = document.getElementById("chatbotBox");
    const chatInput = document.getElementById("chatInput");
    const chatMessages = document.getElementById("chatMessages");
    const chatSendBtn = document.getElementById("chatSendBtn");
    const chatVoiceBtn = document.getElementById("chatVoiceBtn");
    const chatbotCloseBtn = document.getElementById("chatbotCloseBtn");
    const revealItems = document.querySelectorAll(".reveal-up");
    const statNumbers = document.querySelectorAll(".stat-card h3, .value-number");
    const topbar = document.querySelector(".topbar");

    const notificationToggle = document.getElementById("notificationToggle");
    const notificationPanel = document.getElementById("notificationPanel");
    const markAllReadBtn = document.getElementById("markAllReadBtn");
    const notificationCount = document.getElementById("notificationCount");

    let isDragging = false;
    let hasMoved = false;
    let dragOffsetX = 0;
    let dragOffsetY = 0;

    function clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
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
            : !chatbotBox.classList.contains("chat-open");

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

        if (chatbotBox && chatbotBox.classList.contains("chat-open")) {
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
        if (chatbotBox && chatbotBox.classList.contains("chat-open")) return false;
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

    function appendMessage(className, html) {
        if (!chatMessages) return null;

        const wrapper = document.createElement("div");
        wrapper.className = className;
        wrapper.innerHTML = html;
        chatMessages.appendChild(wrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return wrapper;
    }

    function appendLoadingMessage() {
        return appendMessage(
            "bot-msg loading",
            `<span class="typing-indicator" aria-label="Assistant is typing"><span></span><span></span><span></span></span>`
        );
    }

    function removeLoadingMessage(loadingMessage) {
        if (loadingMessage && loadingMessage.parentNode) {
            loadingMessage.remove();
        }
    }

    function sanitizeChatReply(reply, fallback) {
        const rawReply = String(reply || fallback || "Sorry, something went wrong. Please try again.");
        const noisyError = /\b(503|429|UNAVAILABLE|high demand|quota|rate limit|Traceback|Exception|\{'error'|\"error\")\b/i;

        if (noisyError.test(rawReply)) {
            return "The assistant is taking longer than usual right now. Please try again in a moment.";
        }

        return rawReply;
    }

    function setChatLoading(isLoading) {
        if (chatSendBtn) {
            chatSendBtn.disabled = isLoading;
            chatSendBtn.textContent = isLoading ? "Sending..." : "Send";
        }

        if (chatInput) {
            chatInput.disabled = isLoading;
            chatInput.setAttribute("aria-busy", isLoading ? "true" : "false");
        }

        if (chatVoiceBtn) {
            chatVoiceBtn.disabled = isLoading;
        }
    }

    function renderDataPayload(payload) {
        if (!payload || !payload.kind) return "";

        if (payload.kind === "application_summary" && payload.summary) {
            const s = payload.summary;
            return `
                <div style="margin-top:8px; padding:10px; border:1px solid #e5e7eb; border-radius:10px;">
                    <div><strong>Total Applications:</strong> ${escapeHtml(s.total_applications)}</div>
                    <div><strong>Approved:</strong> ${escapeHtml(s.approved_cases)}</div>
                    <div><strong>Pending Review:</strong> ${escapeHtml(s.pending_reviews)}</div>
                    <div><strong>Drafts:</strong> ${escapeHtml(s.draft_applications)}</div>
                </div>
            `;
        }

        if (payload.kind === "alerts_summary" && payload.summary) {
            return `
                <div style="margin-top:8px; padding:10px; border:1px solid #e5e7eb; border-radius:10px;">
                    <div><strong>Alerts Count:</strong> ${escapeHtml(payload.summary.alerts_count)}</div>
                </div>
            `;
        }

        if (payload.kind === "property_summary" && payload.summary) {
            return `
                <div style="margin-top:8px; padding:10px; border:1px solid #e5e7eb; border-radius:10px;">
                    <div><strong>Property Records Linked:</strong> ${escapeHtml(payload.summary.property_records_count)}</div>
                </div>
            `;
        }

        if (payload.kind === "valuation_summary" && payload.summary && payload.summary.latest_valuation) {
            const v = payload.summary.latest_valuation;
            return `
                <div style="margin-top:8px; padding:10px; border:1px solid #e5e7eb; border-radius:10px;">
                    <div><strong>Property:</strong> ${escapeHtml(v.property_label)}</div>
                    <div><strong>Estimated Current Value:</strong> LKR ${Number(v.current_value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                </div>
            `;
        }

        if (payload.kind === "transaction_history" && payload.record) {
            const record = payload.record;
            const historyHtml = (record.history || []).map((item) => `
                <div style="margin-top:8px; padding-top:8px; border-top:1px solid #f0f0f0;">
                    <div><strong>Owner:</strong> ${escapeHtml(item.owner_name)}</div>
                    <div><strong>Transaction:</strong> ${escapeHtml(item.transaction_type)}</div>
                    <div><strong>Date:</strong> ${escapeHtml(item.transfer_date)}</div>
                    <div><strong>Order:</strong> ${escapeHtml(item.ownership_order)}</div>
                </div>
            `).join("");

            return `
                <div style="margin-top:8px; padding:10px; border:1px solid #e5e7eb; border-radius:10px;">
                    <div><strong>Deed Number:</strong> ${escapeHtml(record.deed_number)}</div>
                    <div><strong>Property Address:</strong> ${escapeHtml(record.property_address || "N/A")}</div>
                    <div><strong>Location:</strong> ${escapeHtml(record.location || "N/A")}</div>
                    <div><strong>Current Owner:</strong> ${escapeHtml(record.current_owner_name || "N/A")}</div>
                    ${historyHtml}
                </div>
            `;
        }

        if (payload.kind === "application_attention") {
            const items = Array.isArray(payload.items) ? payload.items : [];

            if (!items.length) {
                return `
                    <div class="chatbot-data-card">
                        <div><strong>No pending action found.</strong></div>
                        <div>Please open My Applications for the complete official list.</div>
                    </div>
                `;
            }

            const itemHtml = items.map((item) => `
                <div class="chatbot-application-card">
                    <div><strong>Application #${escapeHtml(item.application_id)}</strong></div>
                    <div><strong>Status:</strong> ${escapeHtml(item.status || "N/A")}</div>
                    <div><strong>Reason:</strong> ${escapeHtml(item.reason || "Check application details for latest updates.")}</div>
                    <div><strong>Next action:</strong> ${escapeHtml(item.next_action || "Open My Applications.")}</div>
                    ${item.missing_documents ? `<div><strong>Requested/Missing documents:</strong> ${escapeHtml(item.missing_documents)}</div>` : ""}
                    ${item.comments ? `<div><strong>Officer comments:</strong> ${escapeHtml(item.comments)}</div>` : ""}
                </div>
            `).join("");

            return `<div class="chatbot-data-card">${itemHtml}</div>`;
        }

        return "";
    }

    function renderQuickActions(actions) {
        if (!Array.isArray(actions) || !actions.length) return "";

        const buttons = actions.map((action) => {
            const label = escapeHtml(action.label || "Open");
            const target = action.target ? encodeURI(action.target) : "#";
            return `<a class="chatbot-quick-action" href="${target}">${label}</a>`;
        }).join("");

        return `<div class="chatbot-quick-actions">${buttons}</div>`;
    }

    function renderBotResponse(data) {
        const reply = escapeHtml(sanitizeChatReply(data?.reply, "Sorry, I could not understand that."));
        let extraHtml = "";

        if (data?.payload) {
            extraHtml += renderDataPayload(data.payload);
        }

        if (data?.quick_actions) {
            extraHtml += renderQuickActions(data.quick_actions);
        }

        if (data?.action === "open_page" && data?.target) {
            extraHtml += `
                <div style="margin-top:10px;">
                    <a href="${encodeURI(data.target)}" class="chatbot-quick-action">
                        Open page
                    </a>
                </div>
            `;
        }

        appendMessage("bot-msg", `<div>${reply}</div>${extraHtml}`);
    }

    async function sendMessage() {
        if (!chatInput || !chatMessages) return;

        const text = chatInput.value.trim();
        if (!text) return;

        appendMessage("user-msg", escapeHtml(text));
        chatInput.value = "";
        setChatLoading(true);
        const loadingMessage = appendLoadingMessage();

        try {
            const res = await fetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    message: text,
                    context: "user_dashboard"
                })
            });

            let data = {};
            try {
                data = await res.json();
            } catch (jsonError) {
                data = {};
            }

            removeLoadingMessage(loadingMessage);

            if (!res.ok && !data.reply) {
                data.reply = "Sorry, something went wrong. Please try again.";
            }

            renderBotResponse(data);
        } catch (error) {
            removeLoadingMessage(loadingMessage);
            appendMessage("bot-msg", escapeHtml("Sorry, I could not connect to the assistant right now. Please try again."));
        } finally {
            setChatLoading(false);
            if (chatInput) chatInput.focus();
        }
    }

    async function markNotificationRead(notificationId) {
        try {
            const response = await fetch(`/notifications/${notificationId}/read`, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            });
            return response.ok;
        } catch (error) {
            console.error("Failed to mark notification as read", error);
            return false;
        }
    }

    async function markAllNotificationsRead() {
        try {
            const response = await fetch("/notifications/read-all", {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            });
            return response.ok;
        } catch (error) {
            console.error("Failed to mark all notifications as read", error);
            return false;
        }
    }

    function updateUnreadCount(deltaMode = "clearOne") {
        if (!notificationCount) return;

        const current = parseInt(notificationCount.textContent || "0", 10) || 0;
        let next = current;

        if (deltaMode === "clearOne") {
            next = Math.max(0, current - 1);
        } else if (deltaMode === "clearAll") {
            next = 0;
        }

        if (next <= 0) {
            notificationCount.remove();
        } else {
            notificationCount.textContent = next;
        }
    }

    function openNotificationsFromQuery() {
        const params = new URLSearchParams(window.location.search);
        if (params.get("open_notifications") === "1" && notificationPanel) {
            notificationPanel.classList.remove("hidden");
        }
    }

    if (notificationToggle && notificationPanel) {
        notificationToggle.addEventListener("click", function (e) {
            e.stopPropagation();
            notificationPanel.classList.toggle("hidden");
        });

        document.addEventListener("click", function (e) {
            if (!notificationPanel.contains(e.target) && !notificationToggle.contains(e.target)) {
                notificationPanel.classList.add("hidden");
            }
        });

        document.querySelectorAll(".notification-item").forEach((item) => {
            item.addEventListener("click", async function () {
                const notificationId = item.dataset.id;
                const applicationId = item.dataset.applicationId;
                const wasUnread = item.classList.contains("unread");

                if (notificationId) {
                    const ok = await markNotificationRead(notificationId);
                    if (ok && wasUnread) {
                        item.classList.remove("unread");
                        updateUnreadCount("clearOne");
                    }
                }

                if (applicationId) {
                    window.location.href = `/planning-approval/${applicationId}`;
                }
            });
        });

        if (markAllReadBtn) {
            markAllReadBtn.addEventListener("click", async function (e) {
                e.stopPropagation();
                const ok = await markAllNotificationsRead();
                if (!ok) return;

                document.querySelectorAll(".notification-item.unread").forEach((item) => {
                    item.classList.remove("unread");
                });

                updateUnreadCount("clearAll");
            });
        }
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let chatRecognition = null;
    let isListening = false;

    function setVoiceListening(listening) {
        isListening = listening;
        if (!chatVoiceBtn) return;

        chatVoiceBtn.classList.toggle("listening", listening);
        chatVoiceBtn.setAttribute("aria-label", listening ? "Stop voice input" : "Start voice input");
        chatVoiceBtn.setAttribute("title", listening ? "Stop voice input" : "Speak your question");
        chatVoiceBtn.innerHTML = listening
            ? '<i class="fa-solid fa-microphone-lines"></i>'
            : '<i class="fa-solid fa-microphone"></i>';
    }

    function setupVoiceInput() {
        if (!chatVoiceBtn) return;

        if (!SpeechRecognition) {
            chatVoiceBtn.disabled = true;
            chatVoiceBtn.setAttribute("title", "Voice input is not supported in this browser");
            return;
        }

        chatRecognition = new SpeechRecognition();
        chatRecognition.lang = "en-US";
        chatRecognition.interimResults = false;
        chatRecognition.continuous = false;

        chatRecognition.addEventListener("result", function (event) {
            const transcript = Array.from(event.results || [])
                .map((result) => result[0]?.transcript || "")
                .join(" ")
                .trim();

            if (transcript && chatInput) {
                chatInput.value = transcript;
                chatInput.focus();
            }
        });

        chatRecognition.addEventListener("end", function () {
            setVoiceListening(false);
        });

        chatRecognition.addEventListener("error", function () {
            setVoiceListening(false);
        });

        chatVoiceBtn.addEventListener("click", function () {
            if (!chatRecognition || chatVoiceBtn.disabled) return;

            if (isListening) {
                chatRecognition.stop();
                setVoiceListening(false);
                return;
            }

            try {
                chatRecognition.start();
                setVoiceListening(true);
            } catch (error) {
                setVoiceListening(false);
            }
        });
    }

    setupVoiceInput();

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
        if (chatbotBox && chatbotBox.classList.contains("chat-open")) {
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
    openNotificationsFromQuery();

    window.toggleChat = toggleChat;
    window.sendMessage = sendMessage;
});