$(document).ready(function() {
    var API_URL = "http://127.0.0.1:5001/api/analyze";
    var licenseChart = null;
    var originalData = []; // Store original full dataset

    // Handle file selection
    $('#logFile').on('change', function() {
        var file = this.files[0];
        if (file) {
            $('#fileName').text(file.name);
            uploadAndAnalyze(file);
        }
    });

    function uploadAndAnalyze(file) {
        var formData = new FormData();
        formData.append('file', file);

        $('#loading').show();
        $('#error').hide();
        $('#results').hide();

        $.ajax({
            url: API_URL,
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(data) {
                $('#loading').hide();
                if (data && data.length > 0) {
                    originalData = processData(data);
                    renderResults(originalData);
                    $('#results').show();
                } else {
                    showError("日志文件中未找到有效的许可证数据。");
                }
            },
            error: function(jqXHR, textStatus, errorThrown) {
                $('#loading').hide();
                var errorMsg = "分析失败: " + (jqXHR.responseJSON ? jqXHR.responseJSON.error : errorThrown);
                showError(errorMsg);
            }
        });
    }

    function showError(message) {
        $('#error').text(message).show();
    }

    function processData(data) {
        // Calculate duration for each user
        data.forEach(function(feature) {
            feature.users.forEach(function(user) {
                user.duration = calculateDuration(user.startTime);
            });
        });
        return data;
    }

    function renderResults(data) {
        renderChart(data);
        renderTable(data);
    }

    function renderChart(data) {
        var ctx = document.getElementById('licenseChart').getContext('2d');
        
        if (licenseChart) {
            licenseChart.destroy();
        }

        var labels = data.map(function(f) { return f.featureName; });
        var issuedData = data.map(function(f) { return f.licensesIssued; });
        var inUseData = data.map(function(f) { return f.licensesInUse; });

        licenseChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '已使用 (In Use)',
                        data: inUseData,
                        backgroundColor: 'rgba(231, 76, 60, 0.8)',
                        borderColor: 'rgba(192, 57, 43, 1)',
                        borderWidth: 1
                    },
                    {
                        label: '总数 (Issued)',
                        data: issuedData,
                        backgroundColor: 'rgba(52, 152, 219, 0.8)',
                        borderColor: 'rgba(41, 128, 185, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                scales: {
                    xAxes: [{
                        ticks: {
                            autoSkip: false,
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }],
                    yAxes: [{
                        type: 'logarithmic',
                        ticks: {
                            // This callback prevents scientific notation on the Y axis
                            callback: function(value, index, values) {
                                if (value === 0) return 0;
                                // Show labels for 1 and powers of 10
                                if (value === 1 || Math.log10(value) % 1 === 0) {
                                    return value;
                                }
                                // Return null to hide other labels and prevent clutter
                                return null;
                            }
                        }
                    }]
                },
                tooltips: {
                    mode: 'index',
                    intersect: false
                },
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    function renderTable(data) {
        var tableBody = $('#tableBody');
        tableBody.empty();

        var allUsers = [];
        data.forEach(function(feature) {
            feature.users.forEach(function(user) {
                allUsers.push({
                    featureName: feature.featureName,
                    username: user.username,
                    hostname: user.hostname,
                    startTime: user.startTime,
                    duration: user.duration,
                    durationSeconds: parseDurationToSeconds(user.duration)
                });
            });
        });

        // Store the flattened data for sorting and filtering
        tableBody.data('users', allUsers);

        populateTable(allUsers);
    }
    
    function populateTable(users) {
        var tableBody = $('#tableBody');
        tableBody.empty();
        if (users.length === 0) {
            tableBody.append('<tr><td colspan="5" style="text-align:center;">当前无正在使用的许可证。</td></tr>');
            return;
        }
        users.forEach(function(user) {
            var row = '<tr>' +
                '<td>' + user.featureName + '</td>' +
                '<td>' + user.username + '</td>' +
                '<td>' + user.hostname + '</td>' +
                '<td>' + user.startTime + '</td>' +
                '<td>' + user.duration + '</td>' +
                '</tr>';
            tableBody.append(row);
        });
    }

    // Search functionality
    $('#searchInput').on('keyup', function() {
        var searchTerm = $(this).val().toLowerCase();
        var allUsers = $('#tableBody').data('users');
        
        var filteredUsers = allUsers.filter(function(user) {
            return user.featureName.toLowerCase().indexOf(searchTerm) > -1 ||
                   user.username.toLowerCase().indexOf(searchTerm) > -1;
        });
        
        populateTable(filteredUsers);
    });

    // Sorting functionality
    var sortState = {};
    $('#licenseTable thead').on('click', 'th', function() {
        var column = $(this).data('sort');
        if (!column) return;

        var direction = sortState[column] === 'asc' ? 'desc' : 'asc';
        sortState = {}; // Reset other column sorts
        sortState[column] = direction;

        var allUsers = $('#tableBody').data('users');
        
        allUsers.sort(function(a, b) {
            var valA, valB;
            if (column === 'duration') {
                valA = a.durationSeconds;
                valB = b.durationSeconds;
            } else {
                valA = a[column].toLowerCase();
                valB = b[column].toLowerCase();
            }

            if (valA < valB) {
                return direction === 'asc' ? -1 : 1;
            }
            if (valA > valB) {
                return direction === 'asc' ? 1 : -1;
            }
            return 0;
        });

        populateTable(allUsers);
    });

    // --- Helper Functions ---

    function calculateDuration(startTimeStr) {
        // FlexLM start time format: "Mon 7/7 9:47"
        // This is tricky because it lacks year and seconds.
        // We'll parse it as best we can and assume the current year.
        // Note: This will have issues if the checkout spans across a new year.
        
        var now = new Date();
        // The date format from FlexLM is non-standard. We need to make it parsable.
        // Example: "Mon 7/7 9:47" -> "7/7 9:47"
        var cleanTimeStr = startTimeStr.substring(startTimeStr.indexOf(' ') + 1);
        
        // Append current year to make it a full date string
        var fullDateStr = cleanTimeStr + '/' + now.getFullYear(); // e.g., "7/7/2023 9:47"
        
        var startDate = new Date(fullDateStr);
        
        // Check if the parsed date is in the future (e.g., log is from Dec, now is Jan)
        if (startDate > now) {
            startDate.setFullYear(now.getFullYear() - 1);
        }

        var diffMs = now - startDate;
        if (isNaN(diffMs) || diffMs < 0) {
            return "无法计算";
        }

        var diffSecs = Math.floor(diffMs / 1000);
        var days = Math.floor(diffSecs / 86400);
        diffSecs -= days * 86400;
        var hours = Math.floor(diffSecs / 3600) % 24;
        diffSecs -= hours * 3600;
        var minutes = Math.floor(diffSecs / 60) % 60;

        var durationStr = "";
        if (days > 0) durationStr += days + "天 ";
        if (hours > 0) durationStr += hours + "小时 ";
        durationStr += minutes + "分钟";
        
        return durationStr.trim();
    }
    
    function parseDurationToSeconds(durationStr) {
        if (durationStr === "无法计算") return -1;
        
        var totalSeconds = 0;
        var parts = durationStr.split(' ');

        parts.forEach(function(part) {
            if (part.indexOf('天') > -1) {
                totalSeconds += parseInt(part, 10) * 86400;
            } else if (part.indexOf('小时') > -1) {
                totalSeconds += parseInt(part, 10) * 3600;
            } else if (part.indexOf('分钟') > -1) {
                totalSeconds += parseInt(part, 10) * 60;
            }
        });
        
        return totalSeconds;
    }

    // Update durations every minute
    setInterval(function() {
        var allUsers = $('#tableBody').data('users');
        if (allUsers && allUsers.length > 0) {
            // We need to re-render the table to show updated durations
            // This is a simple approach. A more complex one would update cells in place.
            allUsers.forEach(function(user) {
                user.duration = calculateDuration(user.startTime);
                user.durationSeconds = parseDurationToSeconds(user.duration);
            });
            populateTable(allUsers);
        }
    }, 60000);
});