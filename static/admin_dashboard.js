document.addEventListener("DOMContentLoaded", function () {

    const chartCanvas = document.getElementById("landValuationTrendChart");
    const emptyState = document.getElementById("landValuationEmptyState");

    const latestValuationMetric = document.getElementById("latestValuationMetric");
    const latestChangeMetric = document.getElementById("latestChangeMetric");
    const forecastSlopeMetric = document.getElementById("forecastSlopeMetric");
    const chartDescription = document.getElementById("valuationChartDescription");

    const granularitySelect = document.getElementById("valuationGranularity");
    const areaSelect = document.getElementById("valuationArea");

    let chart = null;

    function formatCurrency(val) {
        return `LKR ${Number(val || 0).toLocaleString()}`;
    }

    function renderChart(data) {

        if (!data || !data.labels || data.labels.length === 0) {
            chartCanvas.style.display = "none";
            emptyState.style.display = "block";
            return;
        }

        chartCanvas.style.display = "block";
        emptyState.style.display = "none";

        latestValuationMetric.textContent = formatCurrency(data.latest_value);
        latestChangeMetric.textContent = data.latest_change_percent ?? "No comparison";
        forecastSlopeMetric.textContent = data.forecast_slope ?? "Stable";

        chartDescription.textContent = "Land valuation trend";

        if (chart) chart.destroy();

        chart = new Chart(chartCanvas, {
            type: "line",
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: "Historical",
                        data: data.historical_values,
                        borderColor: "#2563eb"
                    },
                    {
                        label: "Forecast",
                        data: data.forecast_values,
                        borderColor: "#f59e0b"
                    }
                ]
            }
        });
    }

    async function loadChart() {

        const url = `${window.landValuationTrendsUrl}?granularity=${granularitySelect.value}&area=${areaSelect.value}`;

        try {
            const res = await fetch(url);
            const data = await res.json();
            renderChart(data);
        } catch {
            emptyState.style.display = "block";
        }
    }

    renderChart(window.initialLandValuationData);

    granularitySelect.addEventListener("change", loadChart);
    areaSelect.addEventListener("change", loadChart);
});