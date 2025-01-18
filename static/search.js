$(document).ready(function () {
    $("#search-input").on("keyup", function () {
        var value = $(this).val().toLowerCase();

        if (value) {
            $.ajax({
                url: "/search_devices",
                method: "GET",
                data: { search: value },
                success: function (data) {
                    var tbody = $("table tbody");
                    tbody.empty(); // ล้างข้อมูลเก่าในตาราง

                    if (data.length > 0) {
                        $.each(data, function (index, device) {
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
                    } else {
                        tbody.append('<tr><td colspan="7" style="text-align: center;">No data available.</td></tr>');
                    }

                    $(".pagination").hide();
                },
                error: function () {
                    console.error("Failed to fetch devices.");
                },
            });
        } else {
            location.reload();
        }
    });

    // ใช้ event delegation สำหรับปุ่ม ping
    $("table").on("submit", ".ping-form", function (e) {
        e.preventDefault(); // ป้องกันไม่ให้ฟอร์มถูกส่งแบบดั้งเดิม

        var ipAddress = $(this).find(".ip-address").val();

        showLoader(); // แสดง loader
        $.ajax({
            url: "/ping",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({ ip_address: ipAddress }),
            success: function (response) {
                hideLoader(); // ซ่อน loader

                if (response.success) {
                    alert("Ping successful: " + response.message);
                } else {
                    alert("Ping failed: " + response.message);
                }
            },
            error: function () {
                hideLoader(); // ซ่อน loader หากเกิดข้อผิดพลาด
                alert("Ping request failed.");
            }
        });
    });
});
