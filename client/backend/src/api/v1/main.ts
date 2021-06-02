import express from 'express';
import { SocketHandler } from '../../utils/socket-handler';
import dockerode from 'dockerode';
import { SeedContainerInfo, Emulator } from '../../utils/seedsim-meta';
import { Sniffer } from '../../utils/sniffer';
import WebSocket from 'ws';

const router = express.Router();
const docker = new dockerode();
const socketHandler = new SocketHandler(docker);
const sniffer = new Sniffer(docker);

const getContainers: () => Promise<SeedContainerInfo[]> = async function() {
    var containers: dockerode.ContainerInfo[] = await docker.listContainers();

    var _containers: SeedContainerInfo[] = containers.map(c => {
        var withMeta = c as SeedContainerInfo;

        withMeta.meta = {
            hasSession: socketHandler.getSessionManager().hasSession(c.Id),
            nodeInfo: Emulator.ParseMeta(c.Labels)
        };

        return withMeta;
    });

    // filter out undefine (not our nodes)
    return _containers.filter(c => c.meta.nodeInfo.name);;
} 

socketHandler.getLoggers().forEach(logger => logger.setSettings({
    minLevel: 'debug'
}));

sniffer.getLoggers().forEach(logger => logger.setSettings({
    minLevel: 'debug'
}));

router.get('/container', async function(req, res, next) {
    try {
        let containers = await getContainers();

        res.json({
            ok: true,
            result: containers
        });
    } catch (e) {
        res.json({
            ok: false,
            result: e.toString()
        });
    }

    next();
});

router.get('/container/:id', async function(req, res, next) {
    var id = req.params.id;

    var candidates = (await docker.listContainers())
        .filter(c => c.Id.startsWith(id));

    if (candidates.length != 1) {
        res.json({
            ok: false,
            result: `no match or multiple match for container ID ${id}.`
        });
    } else {
        var result: any = candidates[0];
        result.meta = {
            hasSession: socketHandler.getSessionManager().hasSession(result.Id),
            nodeInfo: Emulator.ParseMeta(result.Labels)
        };
        res.json({
            ok: true, result
        });
    }

    next();
});

router.ws('/console/:id', async function(ws, req, next) {
    try {
        await socketHandler.handleSession(ws, req.params.id);
    } catch (e) {
        if (ws.readyState == 1) {
            ws.send(`error creating session: ${e}\r\n`);
            ws.close();
        }
    }
    
    next();
});

var currentSnifferSocket: WebSocket = undefined;

router.post('/sniff', express.text(), async function(req, res, next) {
    sniffer.setListener((nodeId, data) => {
        if (currentSnifferSocket) {
            currentSnifferSocket.send(JSON.stringify({
                source: nodeId, data
            }));
        }
    });

    sniffer.sniff((await getContainers()).map(c => c.Id), req.body);

    next();
})

router.ws('/sniff', async function(ws, req, next) {
    currentSnifferSocket = ws;
    ws.on('close', () => {
        currentSnifferSocket = undefined;
    })
});

export = router;