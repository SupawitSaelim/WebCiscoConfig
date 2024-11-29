function suggestHostnames() {
    var input = document.getElementById("many_hostname").value;
    var suggestionsDiv = document.getElementById("suggestions");

    // ถ้า input มีข้อมูล
    if (input.length > 0) {
        // แยกคำที่พิมพ์จากเครื่องหมาย comma
        var query = input.split(',').pop().trim();  // รับคำสุดท้ายที่ผู้ใช้พิมพ์ (หลังเครื่องหมาย comma)

        // ถ้ามีคำที่พิมพ์อยู่
        if (query.length > 0) {
            fetch('/search_hostname?query=' + query)
                .then(response => response.json())
                .then(data => {
                    suggestionsDiv.innerHTML = '';  // เคลียร์ผลลัพธ์ก่อนหน้า
                    if (data.length > 0) {
                        suggestionsDiv.classList.add('visible');  // แสดงคำแนะนำ
                        data.forEach(function (device) {
                            var suggestionItem = document.createElement("div");
                            suggestionItem.textContent = device;
                            suggestionItem.onclick = function () {
                                // แยกคำทั้งหมดที่พิมพ์ใน input โดยใช้ comma
                                var parts = input.split(',').map(function (part) {
                                    return part.trim(); // ลบช่องว่างจากแต่ละคำ
                                }).filter(function (part) {
                                    return part !== '';  // กรองคำที่ว่าง
                                });

                                // แทนที่คำสุดท้าย (คำที่พิมพ์ล่าสุด) ด้วยคำแนะนำที่เลือก
                                if (parts.length > 0) {
                                    parts[parts.length - 1] = device; // แทนที่คำสุดท้าย
                                } else {
                                    parts.push(device); // ถ้าไม่มีคำพิมพ์ใดๆ ให้เพิ่มคำแนะนำลงไป
                                }

                                // สร้างค่าที่จะใส่ลงใน input โดยใช้ comma
                                var newValue = parts.join(', ');

                                // ตรวจสอบว่า input มี comma อยู่ท้ายสุดหรือไม่
                                if (input.endsWith(',')) {
                                    newValue += ','; // ถ้ามี comma อยู่แล้ว ก็เพิ่ม comma ต่อท้าย
                                }

                                document.getElementById("many_hostname").value = newValue;

                                // ซ่อนคำแนะนำหลังจากเลือก
                                suggestionsDiv.innerHTML = '';
                                suggestionsDiv.classList.remove('visible');
                            };
                            suggestionsDiv.appendChild(suggestionItem);
                        });
                    } else {
                        suggestionsDiv.classList.remove('visible');  // ซ่อนคำแนะนำถ้าไม่มีข้อมูล
                    }
                });
        } else {
            suggestionsDiv.innerHTML = '';  // เคลียร์คำแนะนำเมื่อไม่มีการพิมพ์
            suggestionsDiv.classList.remove('visible');
        }
    } else {
        suggestionsDiv.innerHTML = '';  // เคลียร์คำแนะนำเมื่อไม่มีการพิมพ์
        suggestionsDiv.classList.remove('visible');
    }
}