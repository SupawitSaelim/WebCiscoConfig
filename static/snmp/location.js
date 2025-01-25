const snmp = require('net-snmp');

const host = process.argv[2];
const community = process.argv[3] || 'public'; 
const locationOID = '1.3.6.1.2.1.1.6.0'; // OID สำหรับ location

const session = snmp.createSession(host, community);

session.get([locationOID], (error, varbinds) => {
    if (error || varbinds.length === 0 || snmp.isVarbindError(varbinds[0])) {
        console.error("Error fetching location");
        console.log("Location is not configured on this device."); // ข้อความแสดงว่าข้อมูล location ยังไม่ได้ตั้งค่า
    } else {
        const location = varbinds[0].value.toString();
        if (!location || location.trim() === "") {
            console.log("Location is not configured on this device."); // ข้อความแสดงว่าข้อมูล location ยังไม่ได้ตั้งค่า
        } else {
            console.log(location);
        }
    }
    session.close();
});
