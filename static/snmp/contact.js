const snmp = require('net-snmp');

const host = process.argv[2];
const community = process.argv[3] || 'public'; 
const contactOID = '1.3.6.1.2.1.1.4.0'; // OID สำหรับ contact

const session = snmp.createSession(host, community);

session.get([contactOID], (error, varbinds) => {
    if (error || varbinds.length === 0 || snmp.isVarbindError(varbinds[0])) {
        console.error("Error fetching contact");
        console.log("Contact information is not configured on this device."); // ข้อความที่แสดงเมื่อไม่มีการตั้งค่าข้อมูล contact
    } else {
        const contact = varbinds[0].value.toString();
        if (!contact || contact.trim() === "") {
            console.log("Contact information is not configured on this device."); // ข้อความที่แสดงเมื่อไม่มีการตั้งค่าข้อมูล contact
        } else {
            console.log(contact);
        }
    }
    session.close();
});
