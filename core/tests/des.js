const snmp = require('net-snmp');

const host = '10.0.0.35';  // Fixed IP address
const community = 'Supawitadmin123_';
const sysDescOID = '1.3.6.1.2.1.1.1.0';

const session = snmp.createSession(host, community);

session.get([sysDescOID], (error, varbinds) => {
    if (error || varbinds.length === 0 || snmp.isVarbindError(varbinds[0])) {
        console.error("Error fetching system description");
    } else {
        const sysDesc = varbinds[0].value.toString();
        console.log(sysDesc);
    }
    session.close();
});