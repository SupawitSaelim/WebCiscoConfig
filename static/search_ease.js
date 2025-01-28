$(document).ready(function () {
  function initializePagination() {
    $(".pagination .page-number")
      .off("click")
      .on("click", function (e) {
        e.preventDefault();
        const page = $(this).data("page");
        if (page) {
          updateTable(page, currentSort.column, currentSort.direction);
        }
      });
  }

  initializePagination();
  let currentSearchQuery = "";
  let isLoading = false;
  // เพิ่มตัวแปรเก็บ state การ sort
  let currentSort = {
    column: null,
    direction: null,
  };

  function showLoader() {
    isLoading = true;
    $("#loader").show();
  }

  function hideLoader() {
    isLoading = false;
    $("#loader").hide();
  }

  function updateTable(page = 1, sortColumn = null, sortDirection = null) {
    if (isLoading) return;

    // อัพเดท current sort state ถ้ามีการส่งมา
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
        sort_column: currentSort.column,
        sort_direction: currentSort.direction,
      },
      success: function (response) {
        var tbody = $("table tbody");
        tbody.empty();

        if (response.devices.length > 0) {
          $.each(response.devices, function (index, device) {
            var row = `
    <tr style="border-bottom: 1px solid #dddddd; background-color: ${
      index % 2 === 0 ? "#ffffff" : "#f8f9fc"
    }"
        onmouseover="this.style.backgroundColor='#f2f2f2'" 
        onmouseout="this.style.backgroundColor='${
          index % 2 === 0 ? "#ffffff" : "#f8f9fc"
        }'">
        <td style="padding: 12px 15px; border: 1px solid #ddd;">${
          device.name
        }</td>
        <td style="padding: 12px 15px; border: 1px solid #ddd;">${
          device.device_info.ip
        }</td>
        <td style="padding: 12px 15px; border: 1px solid #ddd; text-align: center;">
            <div class="action-buttons" style="display: flex; justify-content: center; gap: 10px;">
                <!-- ปุ่มลบ -->
                <form method="POST" action="/erase"
                    onsubmit="showLoader(); return confirm('Are you sure you want to erase the configuration for ${
                      device.name
                    }?');">
                    <input type="hidden" name="ip_address" value="${
                      device.device_info.ip
                    }">
                    <button type="submit" class="action-button erase-button" title="Erase"
                            style="background: none; border: none; color: #dc3545; cursor: pointer; padding: 5px;">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </form>
                <!-- ปุ่มรีโหลด -->
                <form method="POST" action="/reload"
                    onsubmit="showLoader(); return confirm('Are you sure you want to reload the configuration for ${
                      device.name
                    }?');">
                    <input type="hidden" name="ip_address" value="${
                      device.device_info.ip
                    }">
                    <button type="submit" class="action-button reload-button" title="Reload"
                            style="background: none; border: none; color: #ffc107; cursor: pointer; padding: 5px;">
                        <i class="fas fa-redo"></i>
                    </button>
                </form>
                <!-- ปุ่มบันทึก -->
                <form method="POST" action="/save"
                    onsubmit="showLoader(); return confirm('Are you sure you want to save the configuration for ${
                      device.name
                    }?');">
                    <input type="hidden" name="ip_address" value="${
                      device.device_info.ip
                    }">
                    <button type="submit" class="action-button save-button" title="Save"
                            style="background: none; border: none; color: #28a745; cursor: pointer; padding: 5px;">
                        <i class="fas fa-save"></i>
                    </button>
                </form>
            </div>
        </td>
    </tr>
`;
            tbody.append(row);
          });

          updatePagination(response.total_pages, response.current_page);
          $(".pagination").show();
        } else {
          tbody.append(
            '<tr><td colspan="3" style="text-align: center;">No devices found.</td></tr>'
          );
          $(".pagination").hide();
        }
      },
      error: function (xhr, status, error) {
        console.error("Failed to fetch devices:", error);
        $("table tbody").append(
          '<tr><td colspan="3" style="text-align: center;">Error loading data. Please try again.</td></tr>'
        );
      },
      complete: function () {
        setTimeout(hideLoader, 100);
      },
    });
  }

  function updatePagination(totalPages, currentPage) {
    const pagination = $(".pagination");
    pagination.empty();

    for (let i = 1; i <= totalPages; i++) {
      if (i === currentPage) {
        pagination.append(`<span class="page-number current">${i}</span>`);
      } else {
        pagination.append(
          `<a href="#" class="page-number" data-page="${i}">${i}</a>`
        );
      }
    }

    // Re-attach pagination click handlers
    $(".pagination .page-number")
      .off("click")
      .on("click", function (e) {
        e.preventDefault();
        const page = $(this).data("page");
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

    searchTimeout = setTimeout(function () {
      if (searchValue !== currentSearchQuery) {
        currentSearchQuery = searchValue;
        updateTable(1); // Always reset to page 1 when search query changes
      }
    }, 300);
  });

  // Auto-trim whitespace when focusing out of search input
  $("#search-input").on("blur", function () {
    const trimmedValue = $(this).val().trim();
    $(this).val(trimmedValue);
  });

  // Export สำหรับใช้ใน sortable.js
  window.updateTableWithSort = function (column, direction) {
    currentSort.column = column;
    currentSort.direction = direction;
    updateTable(1, column, direction);
  };
});
