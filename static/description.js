const snmp = require('net-snmp');

const host = process.argv[2];
const community = 'public';
const sysDescOID = '1.3.6.1.2.1.1.1.0'; // OID สำหรับ System Description

const session = snmp.createSession(host, community);

session.get([sysDescOID], (error, varbinds) => {
    if (error || varbinds.length === 0 || snmp.isVarbindError(varbinds[0])) {
        console.error("Error fetching system description");
    } else {
        const sysDesc = varbinds[0].value.toString();
        console.log(sysDesc); // แสดงรายละเอียดระบบ
    }
    session.close();
});
