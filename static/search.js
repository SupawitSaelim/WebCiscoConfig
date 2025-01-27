$(document).ready(function () {
    function initializePagination() {
        $(".pagination .page-number").off('click').on('click', function(e) {
            e.preventDefault();
            const page = $(this).data('page');
            if (page) {
                updateTable(page, currentSort.column, currentSort.direction);
            }
        });
    }

    initializePagination();
    let currentSearchQuery = '';
    let isLoading = false; // เพิ่มตัวแปรเช็คสถานะ loading

    let currentSort = {
        column: null,
        direction: null
    };

    function showLoader() {
        isLoading = true;
        $('#loader').show();
    }

    function hideLoader() {
        isLoading = false;
        $('#loader').hide();
    }

    // ฟังก์ชันสำหรับอัพเดตตารางทั้งกรณี search และ sort
    function updateTable(page = 1, sortColumn = null, sortDirection = null) {
        // ถ้ากำลัง loading อยู่ให้ return ออกไป
        if (isLoading) return;

        if (sortColumn !== null && sortDirection !== null) {
            currentSort.column = sortColumn;
            currentSort.direction = sortDirection;
        }

        const searchValue = $("#search-input").val().toLowerCase().trim();
        showLoader();
        
        $.ajax({
            url: "/search_devices",
            method: "GET",
            data: { 
                search: searchValue,
                page: page,
                sort_column: sortColumn,
                sort_direction: sortDirection
            },
            success: function (response) {
                var tbody = $("table tbody");
                tbody.empty();

                if (response.devices.length > 0) {
                    $.each(response.devices, function (index, device) {
                        var row = `
                            <tr>
                                <td>${device.name}</td>
                                <td>${device.device_info.ip}</td>
                                <td>${device.device_info.username}</td>
                                <td>
                                    <span class="password-toggle" data-password="${device.device_info.password}">•••••••</span>
                                </td>
                                <td>
                                    <span class="password-toggle" data-password="${device.device_info.secret}">•••••••</span>
                                </td>
                                <td>${device.timestamp}</td>
                                <td>
                                    <div class="action-buttons" style="align-items: center;">
                                        <form method="POST" action="/delete" onsubmit="return confirm('Are you sure you want to delete this device?');" style="display: inline-block; margin-right: 10px;">
                                            <input type="hidden" name="ip_address" value="${device.device_info.ip}">
                                            <input type="hidden" name="device_index" value="${index}">
                                            <button type="submit" title="Delete" style="background: none; border: none; cursor: pointer;">
                                                <i class="fas fa-trash" style="color: tomato; font-size: 20px;"></i>
                                            </button>
                                        </form>
                                        <form method="GET" action="/edit/${device.device_info.ip}" style="display: inline-block;">
                                            <button type="submit" title="Edit" style="background: none; border: none; cursor: pointer;">
                                                <i class="fas fa-edit" style="color: #2e4ead; font-size: 20px;"></i>
                                            </button>
                                        </form>
                                        <form class="ping-form" style="display: inline-block; margin-left: 10px;">
                                            <input type="hidden" class="ip-address" value="${device.device_info.ip}">
                                            <button type="submit" class="ping-button" title="Ping" style="background: none; border: none; cursor: pointer;">
                                                <i class="fas fa-network-wired" style="color: green; font-size: 20px;"></i>
                                            </button>
                                        </form>
                                        <button onclick="openSshConnection('${device.device_info.ip}', '${device.device_info.username}', '${device.device_info.password}')" title="Connect via SSH" style="background: none; border: none; cursor: pointer; margin-left: 10px;">
                                            <i class="fas fa-terminal" style="color: #007bff; font-size: 20px;"></i>
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        `;
                        tbody.append(row);
                    });

                    updatePagination(response.total_pages, response.current_page);
                } else {
                    tbody.append('<tr><td colspan="7" style="text-align: center;">No data available.</td></tr>');
                    $(".pagination").empty();
                }
            },
            error: function (xhr, status, error) {
                console.error("Failed to fetch devices:", error);
                tbody.append('<tr><td colspan="7" style="text-align: center;">Error loading data. Please try again.</td></tr>');
            },
            complete: function() {
                setTimeout(hideLoader, 100);
            }
        });
    }

    function updatePagination(totalPages, currentPage) {
        const pagination = $(".pagination");
        pagination.empty();

        for (let i = 1; i <= totalPages; i++) {
            if (i === currentPage) {
                pagination.append(`<span class="page-number current">${i}</span>`);
            } else {
                pagination.append(`<a href="#" class="page-number" data-page="${i}">${i}</a>`);
            }
        }

        $(".pagination .page-number").off('click').on('click', function(e) {
            e.preventDefault();
            const page = $(this).data('page');
            if (page) {
                updateTable(page, currentSort.column, currentSort.direction);
            }
        });
    }

    // Event handler for search input with debouncing
    let searchTimeout;
    $("#search-input").on("keyup", function () {
        const searchValue = $(this).val().toLowerCase().trim();
        
        clearTimeout(searchTimeout);
        
        searchTimeout = setTimeout(function() {
            if (searchValue !== currentSearchQuery) {
                currentSearchQuery = searchValue;
                updateTable(1);  // Always reset to page 1 when search query changes
            }
        }, 300);
    });

    // Auto-trim whitespace when focusing out of search input
    $("#search-input").on("blur", function() {
        const trimmedValue = $(this).val().trim();
        $(this).val(trimmedValue);
    });

    // Ping functionality
    $("table").on("submit", ".ping-form", function (e) {
        e.preventDefault();
        if (isLoading) return; // ป้องกันการ ping ขณะกำลัง loading

        var ipAddress = $(this).find(".ip-address").val();
        showLoader();
        
        $.ajax({
            url: "/ping",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({ ip_address: ipAddress }),
            success: function (response) {
                if (response.success) {
                    alert("Ping successful: " + response.message);
                } else {
                    alert("Ping failed: " + response.message);
                }
            },
            error: function () {
                alert("Ping request failed.");
            },
            complete: function() {
                hideLoader();
            }
        });
    });

    // Export updateTable function for use in sortable.js
    window.updateTableWithSort = function(column, direction) {
        currentSort.column = column;
        currentSort.direction = direction;
        updateTable(1, column, direction);
    };
});