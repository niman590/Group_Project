document.addEventListener("DOMContentLoaded", function () {
    const chartCanvas = document.getElementById("landValuationTrendChart");
    const emptyState = document.getElementById("landValuationEmptyState");

    const latestValuationMetric = document.getElementById("latestValuationMetric");
    const latestChangeMetric = document.getElementById("latestChangeMetric");
    const forecastSlopeMetric = document.getElementById("forecastSlopeMetric");
    const chartDescription = document.getElementById("valuationChartDescription");

    const totalValuationCountMetric = document.getElementById("totalValuationCountMetric");
    const selectedAreaCountMetric = document.getElementById("selectedAreaCountMetric");
    const supportedValuationCountMetric = document.getElementById("supportedValuationCountMetric");
    const unsupportedValuationCountMetric = document.getElementById("unsupportedValuationCountMetric");

    const forecastStatusBadge = document.getElementById("forecastStatusBadge");
    const valuationCityCounts = document.getElementById("valuationCityCounts");

    const granularitySelect = document.getElementById("valuationGranularity");
    const areaSelect = document.getElementById("valuationArea");

    let chart = null;

    function getInitialLandValuationData() {
        const jsonScript = document.getElementById("initialLandValuationDataJson");

        if (!jsonScript) {
            return {};
        }

        try {
            return JSON.parse(jsonScript.textContent || "{}");
        } catch (error) {
            console.error("Invalid initial land valuation JSON:", error);
            return {};
        }
    }

    function formatCurrency(value) {
        const numberValue = Number(value || 0);

        return `LKR ${numberValue.toLocaleString("en-LK", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })}`;
    }

    function formatCount(value) {
        return Number(value || 0).toLocaleString("en-LK");
    }

    function formatPercent(value) {
        if (value === null || value === undefined || value === "") {
            return "No comparison";
        }

        const numberValue = Number(value);

        if (Number.isNaN(numberValue)) {
            return "No comparison";
        }

        if (numberValue > 0) {
            return `+${numberValue.toFixed(2)}%`;
        }

        return `${numberValue.toFixed(2)}%`;
    }

    function formatSlope(value) {
        const numberValue = Number(value || 0);

        if (Math.abs(numberValue) < 1) {
            return "Stable";
        }

        if (numberValue > 0) {
            return "Increasing";
        }

        return "Decreasing";
    }

    function setText(element, value) {
        if (element) {
            element.textContent = value;
        }
    }

    function renderForecastStatus(data) {
        if (!forecastStatusBadge) return;

        if (!data || !data.has_data) {
            forecastStatusBadge.className = "forecast-status-badge warning";
            forecastStatusBadge.innerHTML = `<i class="fa-solid fa-circle-info"></i> No valuation data`;
            return;
        }

        if (data.forecast_available) {
            forecastStatusBadge.className = "forecast-status-badge success";
            forecastStatusBadge.innerHTML = `<i class="fa-solid fa-chart-line"></i> Forecast available`;
        } else {
            forecastStatusBadge.className = "forecast-status-badge warning";
            forecastStatusBadge.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> More data needed`;
        }
    }

    function renderCityCounts(data) {
        if (!valuationCityCounts) return;

        const cityCounts = data && Array.isArray(data.city_counts) ? data.city_counts : [];

        if (cityCounts.length === 0) {
            valuationCityCounts.innerHTML = `
                <div class="city-count-empty">
                    No city valuation count data available.
                </div>
            `;
            return;
        }

        valuationCityCounts.innerHTML = cityCounts.map((item) => {
            const count = Number(item.count || 0);
            const activeClass = count > 0 ? "has-data" : "no-data";

            return `
                <div class="city-count-pill ${activeClass}">
                    <span>${item.area}</span>
                    <strong>${formatCount(count)}</strong>
                </div>
            `;
        }).join("");
    }

    function buildDescription(data) {
        if (!data) {
            return "Unable to load land valuation trend data.";
        }

        const areaText = data.selected_area === "all" ? "all supported areas" : data.selected_area;
        const countText = formatCount(data.selected_area_count || 0);

        if (!data.has_data) {
            return `No valuation records found for ${areaText}.`;
        }

        if (!data.forecast_available) {
            return `${countText} valuation record(s) found for ${areaText}. ${data.forecast_reason || "More history is needed for forecasting."}`;
        }

        return `${countText} valuation record(s) found for ${areaText}. ${data.forecast_reason || "Forecast generated from historical valuation trend."}`;
    }

    function renderMetricCards(data) {
        setText(latestValuationMetric, formatCurrency(data.latest_value || 0));
        setText(latestChangeMetric, formatPercent(data.latest_change_percent));
        setText(forecastSlopeMetric, formatSlope(data.forecast_slope));

        setText(totalValuationCountMetric, formatCount(data.total_valuation_count || 0));
        setText(selectedAreaCountMetric, formatCount(data.selected_area_count || 0));
        setText(supportedValuationCountMetric, formatCount(data.supported_valuation_count || 0));
        setText(unsupportedValuationCountMetric, formatCount(data.unsupported_valuation_count || 0));

        setText(chartDescription, buildDescription(data));

        renderForecastStatus(data);
        renderCityCounts(data);
    }

    function destroyChart() {
        if (chart) {
            chart.destroy();
            chart = null;
        }
    }

    function renderEmptyState(message) {
        destroyChart();

        if (chartCanvas) {
            chartCanvas.style.display = "none";
        }

        if (emptyState) {
            emptyState.style.display = "flex";
            emptyState.textContent = message || "No land valuation records are available for the selected filter yet.";
        }
    }

    function renderChart(data) {
        if (!chartCanvas || !emptyState) return;

        renderMetricCards(data || {});

        if (!data || !data.labels || data.labels.length === 0 || !data.has_data) {
            renderEmptyState(
                data && data.forecast_reason
                    ? data.forecast_reason
                    : "No valuation records are available for the selected filter yet."
            );
            return;
        }

        chartCanvas.style.display = "block";
        emptyState.style.display = "none";

        destroyChart();

        const historicalValues = Array.isArray(data.historical_values) ? data.historical_values : [];
        const forecastValues = Array.isArray(data.forecast_values) ? data.forecast_values : [];

        chart = new Chart(chartCanvas, {
            type: "line",
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: "Historical Average",
                        data: historicalValues,
                        borderColor: "#2563eb",
                        backgroundColor: "rgba(37, 99, 235, 0.10)",
                        pointBackgroundColor: "#2563eb",
                        pointBorderColor: "#ffffff",
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        borderWidth: 3,
                        tension: 0.35,
                        fill: true,
                        spanGaps: false
                    },
                    {
                        label: "Forecast",
                        data: forecastValues,
                        borderColor: "#f59e0b",
                        backgroundColor: "rgba(245, 158, 11, 0.08)",
                        pointBackgroundColor: "#f59e0b",
                        pointBorderColor: "#ffffff",
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        borderWidth: 3,
                        borderDash: [8, 6],
                        tension: 0.35,
                        fill: false,
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
                        display: true,
                        position: "top",
                        labels: {
                            usePointStyle: true,
                            boxWidth: 8,
                            boxHeight: 8,
                            color: "#42526b",
                            font: {
                                weight: "700"
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const label = context.dataset.label || "";
                                const value = context.parsed.y;

                                if (value === null || value === undefined) {
                                    return `${label}: No value`;
                                }

                                return `${label}: ${formatCurrency(value)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: "#64748b",
                            font: {
                                weight: "600"
                            }
                        }
                    },
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: "rgba(148, 163, 184, 0.25)"
                        },
                        ticks: {
                            color: "#64748b",
                            callback: function (value) {
                                const numberValue = Number(value || 0);

                                if (numberValue >= 1000000) {
                                    return `LKR ${(numberValue / 1000000).toFixed(1)}M`;
                                }

                                if (numberValue >= 1000) {
                                    return `LKR ${(numberValue / 1000).toFixed(0)}K`;
                                }

                                return `LKR ${numberValue}`;
                            }
                        }
                    }
                }
            }
        });
    }

    async function loadChart() {
        if (!granularitySelect || !areaSelect) return;

        const granularity = encodeURIComponent(granularitySelect.value);
        const area = encodeURIComponent(areaSelect.value);
        const url = `${window.landValuationTrendsUrl}?granularity=${granularity}&area=${area}`;

        if (chartDescription) {
            chartDescription.textContent = "Loading valuation insights...";
        }

        try {
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error("Failed to load valuation trend data.");
            }

            const data = await response.json();
            renderChart(data);

        } catch (error) {
            console.error(error);
            renderEmptyState("Unable to load land valuation forecast data. Please refresh and try again.");
        }
    }

    const initialData = getInitialLandValuationData();
    renderChart(initialData);

    if (granularitySelect) {
        granularitySelect.addEventListener("change", loadChart);
    }

    if (areaSelect) {
        areaSelect.addEventListener("change", loadChart);
    }
});