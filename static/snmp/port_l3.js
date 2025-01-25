const snmp = require('net-snmp');

const host = process.argv[2];  
const community = process.argv[3] || 'public'; 
const baseOID = '1.3.6.1.2.1.2.2.1.2'; 
const startIndex = 1;             // เริ่มต้นจาก index 1

const session = snmp.createSession(host, community);

const fetchAllPorts = () => {
    return new Promise((resolve, reject) => {
        let output = '';
        let index = startIndex;

        const fetchPort = () => {
            const currentOID = `${baseOID}.${index}`;
            session.get([currentOID], (error, varbinds) => {
                if (error) {
                    console.log(`No response for OID: ${currentOID}`);
                    index++;
                    fetchPort();
                    return;
                }

                if (varbinds.length > 0 && !snmp.isVarbindError(varbinds[0])) {
                    const portDescription = varbinds[0].value.toString();
                    if (currentOID === '1.3.6.1.2.1.2.2.1.3.1') {
                        resolve(output);  // เมื่อเจอแล้วหยุด
                        session.close();
                        return;
                    }

                    output += `${portDescription}\n`;

                    const nextOID = `${baseOID}.${index + 1}`;
                    session.get([nextOID], (nextError, nextVarbinds) => {
                        if (nextError || nextVarbinds.length === 0) {
                            // ถ้าไม่มีค่าตอบกลับจาก OID ถัดไป หรือมีข้อผิดพลาด
                            resolve(output);  // หยุดเมื่อไม่เจอค่าตอบกลับ
                            session.close();
                        } else {
                            index++; 
                            fetchPort(); // ลูปไปยัง OID ถัดไป
                        }
                    });
                } else {
                    resolve(output); // หยุดถ้าไม่มีข้อมูลจาก OID นี้
                    session.close();
                }
            });
        };

        fetchPort();
    });
};

fetchAllPorts()
    .then(output => {
        console.log(output); 
    })
    .catch(error => {
        console.error("Error fetching ports:", error);
    });
