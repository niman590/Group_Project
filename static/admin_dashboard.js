document.addEventListener("DOMContentLoaded", function () {
    if ("scrollRestoration" in history) {
        history.scrollRestoration = "manual";
    }

    const savedScrollY = sessionStorage.getItem("exactDashboardScrollY");
    if (savedScrollY !== null) {
        window.scrollTo(0, parseInt(savedScrollY, 10));
        sessionStorage.removeItem("exactDashboardScrollY");
    }

    const filterForm = document.querySelector(".dashboard-filter-card");
    if (filterForm) {
        filterForm.addEventListener("submit", function () {
            sessionStorage.setItem("exactDashboardScrollY", String(window.scrollY));
        });
    }

    const clearBtn = document.querySelector(".clear-search");
    if (clearBtn) {
        clearBtn.addEventListener("click", function () {
            sessionStorage.setItem("exactDashboardScrollY", String(window.scrollY));
        });
    }

    const initialValuationData = window.initialLandValuationData || null;
    const landValuationTrendsUrl = window.landValuationTrendsUrl || "";
    const granularitySelect = document.getElementById("valuationGranularity");
    const areaSelect = document.getElementById("valuationArea");
    const latestValuationMetric = document.getElementById("latestValuationMetric");
    const latestChangeMetric = document.getElementById("latestChangeMetric");
    const forecastSlopeMetric = document.getElementById("forecastSlopeMetric");
    const chartDescription = document.getElementById("valuationChartDescription");
    const emptyState = document.getElementById("landValuationEmptyState");
    const chartCanvas = document.getElementById("landValuationTrendChart");

    let landValuationChart = null;

    function formatCurrency(value) {
        const numericValue = Number(value || 0);
        return `LKR ${numericValue.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })}`;
    }

    function formatPercent(value) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) {
            return "No comparison";
        }
        const numericValue = Number(value);
        const prefix = numericValue > 0 ? "+" : "";
        return `${prefix}${numericValue.toFixed(2)}%`;
    }

    function resolveTrendLabel(value) {
        const numericValue = Number(value || 0);
        if (numericValue > 0) return "Upward";
        if (numericValue < 0) return "Downward";
        return "Stable";
    }

    function renderLandValuationChart(payload) {
        const hasData = payload && payload.has_data && Array.isArray(payload.labels) && payload.labels.length;

        if (!hasData) {
            if (chartCanvas) chartCanvas.style.display = "none";
            if (emptyState) emptyState.style.display = "flex";
            if (latestValuationMetric) latestValuationMetric.textContent = "LKR 0.00";
            if (latestChangeMetric) latestChangeMetric.textContent = "No comparison";
            if (forecastSlopeMetric) forecastSlopeMetric.textContent = "Stable";
            if (chartDescription) {
                chartDescription.textContent = "No valuation history found for the selected area and time view.";
            }
            if (landValuationChart) {
                landValuationChart.destroy();
                landValuationChart = null;
            }
            return;
        }

        if (chartCanvas) chartCanvas.style.display = "block";
        if (emptyState) emptyState.style.display = "none";

        if (latestValuationMetric) latestValuationMetric.textContent = formatCurrency(payload.latest_value);
        if (latestChangeMetric) latestChangeMetric.textContent = formatPercent(payload.latest_change_percent);
        if (forecastSlopeMetric) forecastSlopeMetric.textContent = resolveTrendLabel(payload.forecast_slope);

        const areaLabel = payload.selected_area && payload.selected_area !== "all"
            ? payload.selected_area
            : "all recorded areas";

        if (chartDescription) {
            chartDescription.textContent =
                `Showing ${payload.granularity} land valuation movement for ${areaLabel}, including forecasted ${payload.forecast_period_label}.`;
        }

        if (!chartCanvas) return;

        const ctx = chartCanvas.getContext("2d");
        if (landValuationChart) {
            landValuationChart.destroy();
        }

        landValuationChart = new Chart(ctx, {
            type: "line",
            data: {
                labels: payload.labels,
                datasets: [
                    {
                        label: "Historical",
                        data: payload.historical_values,
                        borderColor: "#2563eb",
                        backgroundColor: "rgba(37, 99, 235, 0.14)",
                        borderWidth: 3,
                        tension: 0.35,
                        fill: false,
                        pointRadius: 4,
                        pointHoverRadius: 5,
                        spanGaps: false
                    },
                    {
                        label: "Forecast",
                        data: payload.forecast_values,
                        borderColor: "#f59e0b",
                        backgroundColor: "rgba(245, 158, 11, 0.12)",
                        borderDash: [7, 6],
                        borderWidth: 3,
                        tension: 0.35,
                        fill: false,
                        pointRadius: 4,
                        pointHoverRadius: 5,
                        spanGaps: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: "index",
                    intersect: false
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const value = context.raw;
                                if (value === null || value === undefined) {
                                    return `${context.dataset.label}: No data`;
                                }
                                return `${context.dataset.label}: ${formatCurrency(value)}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (value) {
                                return `LKR ${Number(value).toLocaleString()}`;
                            }
                        }
                    }
                }
            }
        });
    }

    async function loadLandValuationChart() {
        if (!granularitySelect || !areaSelect || !landValuationTrendsUrl) return;

        const params = new URLSearchParams({
            granularity: granularitySelect.value,
            area: areaSelect.value
        });

        if (chartDescription) {
            chartDescription.textContent = "Updating valuation insights...";
        }

        try {
            const response = await fetch(`${landValuationTrendsUrl}?${params.toString()}`);
            const payload = await response.json();
            renderLandValuationChart(payload);
        } catch (error) {
            if (chartCanvas) chartCanvas.style.display = "none";
            if (emptyState) {
                emptyState.style.display = "flex";
                emptyState.textContent = "Unable to load land valuation trend data right now.";
            }
            if (chartDescription) {
                chartDescription.textContent = "There was a problem loading the valuation chart.";
            }
        }
    }

    if (granularitySelect && areaSelect && chartCanvas) {
        renderLandValuationChart(initialValuationData);
        granularitySelect.addEventListener("change", loadLandValuationChart);
        areaSelect.addEventListener("change", loadLandValuationChart);
    }
});