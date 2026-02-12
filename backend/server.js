const mqtt = require('mqtt');
const WebSocket = require('ws');
const http = require('http');
const fs = require('fs');
const path = require('path');

// Configuration
// On VPS, we connect to local mosquitto. On PC, we might want to connect to VPS IP?
// For Backend (running on VPS), it should connect to localhost (its own mosquitto).
const MQTT_BROKER = 'mqtt://157.173.101.159';
const TEAM_ID = 'team313';
const MQTT_TOPIC_VS = `vision/${TEAM_ID}/movement`;
const WS_PORT = 9002;
const HTTP_PORT = 8080; // Port for Dashboard HTML

// --- MQTT Client ---
console.log(`Connecting to MQTT Broker: ${MQTT_BROKER}...`);
const mqttClient = mqtt.connect(MQTT_BROKER);

mqttClient.on('connect', () => {
    console.log(`Connected to MQTT Broker.`);
    mqttClient.subscribe(MQTT_TOPIC_VS, (err) => {
        if (!err) {
            console.log(`Subscribed to topic: ${MQTT_TOPIC_VS}`);
        } else {
            console.error('MQTT Subscription Error:', err);
        }
    });
});

mqttClient.on('message', (topic, message) => {
    const msgString = message.toString();
    console.log(`MQTT IN [${topic}]: ${msgString}`);

    // Broadcast to all WS clients
    broadcast(msgString);
});

// --- WebSocket Server ---
const wss = new WebSocket.Server({ port: WS_PORT });

console.log(`WebSocket Server started on port ${WS_PORT}`);

wss.on('connection', (ws) => {
    console.log('New WebSocket Client connected');

    // Send initial status
    ws.send(JSON.stringify({ type: 'STATUS', message: 'Connected to Vision Backend' }));

    ws.on('close', () => {
        console.log('Client disconnected');
    });
});

function broadcast(data) {
    wss.clients.forEach((client) => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(data);
        }
    });
}

// --- HTTP Server for Dashboard ---
const server = http.createServer((req, res) => {
    if (req.url === '/' || req.url === '/index.html') {
        fs.readFile(path.join(__dirname, '../dashboard/index.html'), (err, data) => {
            if (err) {
                res.writeHead(500);
                res.end('Error loading dashboard');
                return;
            }
            res.writeHead(200, { 'Content-Type': 'text/html' });
            res.end(data);
        });
    } else {
        res.writeHead(404);
        res.end('Not Found');
    }
});

server.listen(HTTP_PORT, () => {
    console.log(`HTTP Dashboard running on http://localhost:${HTTP_PORT}`);
});
