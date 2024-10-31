const snmp = require('net-snmp');

const host = process.argv[2];
const community = 'public';          
const uptimeOID = '1.3.6.1.2.1.1.3.0'; // OID สำหรับ uptime

const session = snmp.createSession(host, community);

session.get([uptimeOID], (error, varbinds) => {
    if (error || varbinds.length === 0 || snmp.isVarbindError(varbinds[0])) {
        console.error("Error fetching uptime");
    } else {
        const uptimeTicks = varbinds[0].value.toString();
        const totalSeconds = Math.floor(uptimeTicks / 100);
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;

        console.log(`Uptime: ${hours} hours, ${minutes} minutes, ${seconds} seconds`);
    }
    session.close();
});
