const snmp = require('net-snmp');

const host = process.argv[2]; // IP address หรือ hostname ของอุปกรณ์
const community = 'public'; // community string ที่ใช้ในการเชื่อมต่อ
const sysNameOID = '1.3.6.1.2.1.1.5.0'; // OID สำหรับ sysName

const session = snmp.createSession(host, community);

session.get([sysNameOID], (error, varbinds) => {
    if (error || varbinds.length === 0 || snmp.isVarbindError(varbinds[0])) {
        console.error("Error fetching sysName");
        console.log("System name is not available on this device."); // ข้อความที่แสดงเมื่อไม่สามารถดึง sysName ได้
    } else {
        const sysName = varbinds[0].value.toString();
        if (!sysName || sysName.trim() === "") {
            console.log("System name is not available on this device."); // ข้อความเมื่อ sysName ว่าง
        } else {
            console.log(sysName); // แสดงค่า sysName
        }
    }
    session.close();
});
