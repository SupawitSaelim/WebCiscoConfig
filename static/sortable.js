document.addEventListener('DOMContentLoaded', function() {
    // เพิ่ม CSS styles
    const styleSheet = document.createElement("style");
    styleSheet.textContent = `
        .sortable {
            cursor: pointer;
            position: relative;
            padding-right: 25px !important;
        }
        
        .sortable::after {
            content: '↕️';
            position: absolute;
            right: 8px;
            top: 50%;
            transform: translateY(-50%);
            opacity: 0.5;
            font-size: 14px;
        }
        
        .sortable.asc::after {
            content: '⬆️';
            opacity: 1;
        }
        
        .sortable.desc::after {
            content: '⬇️';
            opacity: 1;
        }
    `;
    document.head.appendChild(styleSheet);

    // หา table และ sortable headers
    const table = document.querySelector('table');
    if (!table) {
        console.error('Table not found');
        return;
    }

    const headers = table.querySelectorAll('th.sortable');
    if (headers.length === 0) {
        console.error('No sortable headers found');
        return;
    }

    let currentSort = {
        column: null,
        direction: null
    };

    // แก้ไขส่วน event listener สำหรับ headers
    headers.forEach(header => {
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            if (!column) return;

            // แก้ไขลำดับการ sort
            let direction;
            if (currentSort.column !== column) {
                // ถ้าเป็นคอลัมน์ใหม่ ให้เริ่มด้วย asc เสมอ
                direction = 'asc';
            } else {
                // ถ้าเป็นคอลัมน์เดิม ให้สลับตามลำดับ
                switch (currentSort.direction) {
                    case null:
                        direction = 'asc';  // จาก ↕️ ไป ⬆️
                        break;
                    case 'asc':
                        direction = 'desc'; // จาก ⬆️ ไป ⬇️
                        break;
                    case 'desc':
                        direction = null;   // จาก ⬇️ ไป ↕️
                        break;
                }
            }

            // อัพเดท CSS classes
            headers.forEach(h => h.classList.remove('asc', 'desc'));
            if (direction) {
                header.classList.add(direction);
            }

            // อัพเดท state ปัจจุบัน
            currentSort = { column, direction };

            // เรียกใช้ฟังก์ชัน updateTableWithSort จาก search.js
            if (typeof window.updateTableWithSort === 'function') {
                window.updateTableWithSort(column, direction);
            }
        });
    });
});