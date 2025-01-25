const snmp = require('net-snmp');

const host = process.argv[2];        
const community = process.argv[3] || 'public'; 
const baseOID = '1.3.6.1.2.1.2.2.1.2'; 
const startIndex = 1;            

const session = snmp.createSession(host, community);

const fetchAllPorts = () => {
    return new Promise((resolve, reject) => {
        let output = '';
        let index = startIndex; 

        const fetchPort = () => {
            const currentOID = `${baseOID}.${index}`;

            session.get([currentOID], (error, varbinds) => {
                if (error) {
                        index++; 
                        fetchPort(); 
                        return;
                }

                if (varbinds.length > 0 && !snmp.isVarbindError(varbinds[0])) {
                    const portDescription = varbinds[0].value.toString();

                    if (portDescription && !/^(Null0|propVirtual)$/.test(portDescription)) {
                        output += `${portDescription}\n`;
                        index++; 
                        fetchPort(); 
                    } else {
                        resolve(output); 
                        session.close();
                    }
                } else {
                    resolve(output); 
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
