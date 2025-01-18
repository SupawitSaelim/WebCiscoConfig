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
                    tbody.empty();

                    if (data.length > 0) {
                        $.each(data, function (index, device) {
                            var row = `
                                <tr>
                                    <td>${device.name}</td>
                                    <td>${device.device_info.ip}</td>
                                    <td style="align-items: center;">
                                        <div class="action-buttons" style="align-items: center;">
                                            <!-- ปุ่มลบ -->
                                            <form method="POST" action="/erase"
                                                onsubmit="return confirm('Are you sure you want to erase the configuration for ${device.name}?');">
                                                <input type="hidden" name="ip_address" value="${device.device_info.ip}">
                                                <button type="submit" class="action-button erase-button">
                                                    <i class="fas fa-trash-alt"></i>
                                                </button>
                                            </form>
                                            <!-- ปุ่มรีโหลด -->
                                            <form method="POST" action="/reload"
                                                onsubmit="return confirm('Are you sure you want to reload the configuration for ${device.name}?');">
                                                <input type="hidden" name="ip_address" value="${device.device_info.ip}">
                                                <button type="submit" class="action-button reload-button">
                                                    <i class="fas fa-redo"></i>
                                                </button>
                                            </form>
                                            <!-- ปุ่มบันทึก -->
                                            <form method="POST" action="/save"
                                                onsubmit="return confirm('Are you sure you want to save the configuration for ${device.name}?');">
                                                <input type="hidden" name="ip_address" value="${device.device_info.ip}">
                                                <button type="submit" class="action-button save-button">
                                                    <i class="fas fa-save"></i>
                                                </button>
                                            </form>
                                        </div>
                                    </td>
                                </tr>
                            `;
                            tbody.append(row);
                        });
                    } else {
                        tbody.append('<tr><td colspan="3" style="text-align: center;">No devices found.</td></tr>');
                    }

                    $(".pagination").hide();
                },
                error: function () {
                    console.error("Failed to fetch devices.");
                    $("table tbody").html('<tr><td colspan="3" style="text-align: center;">Error loading devices.</td></tr>');
                },
            });
        } else {
            $.ajax({
                url: "/search_devices",
                method: "GET",
                data: { search: "" },
                success: function (data) {
                    // ฟังก์ชันเหมือนเดิม
                },
                error: function () {
                    console.error("Failed to fetch devices.");
                },
            });

            $(".pagination").show();  // แสดง pagination
        }
    });
});
