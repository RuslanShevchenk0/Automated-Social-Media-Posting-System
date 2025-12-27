/**
 * Chart utilities for Analytics page
 */

// Store chart instances to destroy them before re-rendering
let chartInstances = {};

/**
 * Destroy a chart instance if it exists
 */
function destroyChart(chartId) {
    if (chartInstances[chartId]) {
        chartInstances[chartId].destroy();
        delete chartInstances[chartId];
    }
}

/**
 * Destroy all chart instances
 */
function destroyAllCharts() {
    Object.keys(chartInstances).forEach(chartId => {
        destroyChart(chartId);
    });
}

/**
 * Initialize activity trend chart on Analytics page
 * Shows growth of likes, comments, and shares over time (grouped by date)
 */
async function initAnalyticsCharts() {
    try {
        const summaryData = await API.analytics.getSummary();
        const bestPosts = summaryData.best_posts || [];

        if (bestPosts.length === 0) {
            return;
        }

        // Sort all posts by publication date
        const sortedPosts = [...bestPosts].sort((a, b) =>
            new Date(a.published_at) - new Date(b.published_at)
        );

        // Group posts by date and accumulate metrics
        const dateMap = new Map();
        let cumulativeLikes = 0;
        let cumulativeComments = 0;
        let cumulativeShares = 0;
        let cumulativeImpressions = 0;

        sortedPosts.forEach(post => {
            const date = new Date(post.published_at);
            const dateKey = date.toISOString().split('T')[0]; // YYYY-MM-DD
            const formattedDate = date.toLocaleDateString('uk-UA', {
                day: 'numeric',
                month: 'short'
            });

            cumulativeLikes += post.total_likes || 0;
            cumulativeComments += post.total_comments || 0;
            cumulativeShares += post.total_shares || 0;
            cumulativeImpressions += post.total_impressions || 0;

            // Store only the last (cumulative) values for each date
            dateMap.set(dateKey, {
                label: formattedDate,
                likes: cumulativeLikes,
                comments: cumulativeComments,
                shares: cumulativeShares,
                impressions: cumulativeImpressions
            });
        });

        // Convert map to arrays
        const dates = [];
        const likes = [];
        const comments = [];
        const shares = [];

        Array.from(dateMap.values()).forEach(data => {
            dates.push(data.label);
            likes.push(data.likes);
            comments.push(data.comments);
            shares.push(data.shares);
        });

        // Initialize activity trend chart
        const activityCanvas = document.getElementById('activityChart');
        if (activityCanvas) {
            destroyChart('activity');

            const ctx = activityCanvas.getContext('2d');
            chartInstances['activity'] = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [
                        {
                            label: t('likes'),
                            data: likes,
                            borderColor: '#3b82f6',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            borderWidth: 3,
                            tension: 0.4,
                            fill: true,
                            pointRadius: 5,
                            pointHoverRadius: 7,
                            pointBackgroundColor: '#3b82f6',
                            pointBorderColor: '#ffffff',
                            pointBorderWidth: 2
                        },
                        {
                            label: t('comments'),
                            data: comments,
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            borderWidth: 3,
                            tension: 0.4,
                            fill: true,
                            pointRadius: 5,
                            pointHoverRadius: 7,
                            pointBackgroundColor: '#10b981',
                            pointBorderColor: '#ffffff',
                            pointBorderWidth: 2
                        },
                        {
                            label: t('shares'),
                            data: shares,
                            borderColor: '#f59e0b',
                            backgroundColor: 'rgba(245, 158, 11, 0.1)',
                            borderWidth: 3,
                            tension: 0.4,
                            fill: true,
                            pointRadius: 5,
                            pointHoverRadius: 7,
                            pointBackgroundColor: '#f59e0b',
                            pointBorderColor: '#ffffff',
                            pointBorderWidth: 2
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            align: 'end',
                            labels: {
                                padding: 15,
                                font: { size: 12, weight: '600' },
                                usePointStyle: true,
                                boxWidth: 8,
                                boxHeight: 8
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.9)',
                            padding: 14,
                            titleFont: { size: 13, weight: 'bold' },
                            bodyFont: { size: 12 },
                            bodySpacing: 6,
                            displayColors: true,
                            boxPadding: 6,
                            callbacks: {
                                title: function(context) {
                                    return t('accumulated_until') + ' ' + context[0].label;
                                },
                                label: function(context) {
                                    return context.dataset.label + ': ' + context.parsed.y.toLocaleString('uk-UA');
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                font: { size: 11 },
                                callback: function(value) {
                                    return value.toLocaleString('uk-UA');
                                }
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.06)',
                                drawBorder: false
                            }
                        },
                        x: {
                            ticks: {
                                font: { size: 11 },
                                maxRotation: 45,
                                minRotation: 0
                            },
                            grid: {
                                display: false,
                                drawBorder: false
                            }
                        }
                    }
                }
            });
        }

        // Initialize engagement distribution pie chart
        const distributionCanvas = document.getElementById('distributionChart');
        if (distributionCanvas) {
            destroyChart('distribution');

            // Get cumulative totals including impressions
            const totalLikes = Array.from(dateMap.values()).reduce((sum, d) => Math.max(sum, d.likes), 0);
            const totalComments = Array.from(dateMap.values()).reduce((sum, d) => Math.max(sum, d.comments), 0);
            const totalShares = Array.from(dateMap.values()).reduce((sum, d) => Math.max(sum, d.shares), 0);
            const totalImpressions = Array.from(dateMap.values()).reduce((sum, d) => Math.max(sum, d.impressions), 0);
            const total = totalLikes + totalComments + totalShares + totalImpressions;

            const ctx = distributionCanvas.getContext('2d');
            chartInstances['distribution'] = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: [t('impressions'), t('likes'), t('comments'), t('shares')],
                    datasets: [{
                        data: [totalImpressions, totalLikes, totalComments, totalShares],
                        backgroundColor: [
                            'rgba(203, 213, 225, 0.9)',
                            'rgba(59, 130, 246, 0.85)',
                            'rgba(16, 185, 129, 0.85)',
                            'rgba(245, 158, 11, 0.85)'
                        ],
                        borderWidth: 0,
                        hoverOffset: 8,
                        spacing: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    layout: {
                        padding: {
                            left: 0,
                            right: 20,
                            top: 10,
                            bottom: 10
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'right',
                            align: 'center',
                            onClick: function(e, legendItem, legend) {
                                const index = legendItem.datasetIndex !== undefined ? legendItem.datasetIndex : legendItem.index;
                                const chart = legend.chart;
                                const meta = chart.getDatasetMeta(0);

                                // Toggle visibility
                                meta.data[index].hidden = !meta.data[index].hidden;
                                chart.update();
                            },
                            labels: {
                                padding: 14,
                                font: { size: 14, weight: 'bold' },
                                color: '#64748b',
                                usePointStyle: true,
                                pointStyle: 'circle',
                                boxWidth: 11,
                                boxHeight: 11,
                                generateLabels: function(chart) {
                                    const data = chart.data;
                                    if (data.labels.length && data.datasets.length) {
                                        const meta = chart.getDatasetMeta(0);
                                        return data.labels.map((label, i) => {
                                            const value = data.datasets[0].data[i];
                                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                            const hidden = meta.data[i] && meta.data[i].hidden;

                                            return {
                                                text: `${label}: ${value.toLocaleString('uk-UA')} (${percentage}%)`,
                                                fillStyle: data.datasets[0].backgroundColor[i],
                                                strokeStyle: 'transparent',
                                                hidden: hidden,
                                                index: i,
                                                fontColor: hidden ? '#cbd5e1' : '#64748b',
                                                lineWidth: 0
                                            };
                                        });
                                    }
                                    return [];
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.85)',
                            padding: 12,
                            titleFont: { size: 13, weight: 'bold' },
                            bodyFont: { size: 12 },
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed || 0;
                                    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                    return `${label}: ${value.toLocaleString('uk-UA')} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error initializing analytics charts:', error);
    }
}

/**
 * Dashboard chart is removed - no chart needed there
 */
async function initDashboardChart() {
    // No chart on dashboard
}
