import * as vscode from 'vscode';
import * as http from 'http';

let server: http.Server | null = null;
let statusBarItem: vscode.StatusBarItem;
let standbyTimer: ReturnType<typeof setInterval> | null = null;

function getPort(): number {
    const config = vscode.workspace.getConfiguration('copilot-lm-proxy');
    return config.get<number>('port', 19823);
}

type ProxyState = 'running' | 'standby' | 'stopped' | 'error';
let currentState: ProxyState = 'stopped';

export function activate(context: vscode.ExtensionContext) {
    console.log('Copilot LM Proxy extension activated');

    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'copilot-lm-proxy.start';
    context.subscriptions.push(statusBarItem);
    updateStatusBar('stopped');

    startServer();

    context.subscriptions.push(
        vscode.commands.registerCommand('copilot-lm-proxy.start', () => startServer()),
        vscode.commands.registerCommand('copilot-lm-proxy.stop', stopServer)
    );
}

async function handleRequest(req: http.IncomingMessage, res: http.ServerResponse) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    if (req.url === '/health' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok', pid: process.pid }));
        return;
    }

    if (req.url === '/v1/models' && (req.method === 'GET' || req.method === 'POST')) {
        await handleListModels(res);
        return;
    }

    if (req.method !== 'POST') {
        res.writeHead(405, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Method not allowed' }));
        return;
    }

    if (req.url === '/v1/chat/completions') {
        await handleChatCompletion(req, res);
    } else if (req.url === '/v1/debug') {
        await handleDebug(req, res);
    } else {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Not found' }));
    }
}

async function handleDebug(req: http.IncomingMessage, res: http.ServerResponse) {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
        try {
            const { model } = body ? JSON.parse(body) : {};
            const selector: vscode.LanguageModelChatSelector = model ? { id: model } : {};
            const models = await vscode.lm.selectChatModels(selector);
            
            if (models.length === 0) {
                res.writeHead(404, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'No models found. Is Copilot signed in?' }));
                return;
            }

            const msg = vscode.LanguageModelChatMessage.User('Say "test" and nothing else.');
            console.log('Copilot LM Proxy Debug: Attempting sendRequest with model:', models[0]?.id);
            
            const response = await models[0].sendRequest([msg], {});
            console.log('Copilot LM Proxy Debug: sendRequest returned:', typeof response);
            console.log('Copilot LM Proxy Debug: response keys:', Object.keys(response));
            
            let text = '';
            let chunks = 0;
            for await (const part of response.stream) {
                if (part instanceof vscode.LanguageModelTextPart) {
                    chunks++;
                    text += part.value;
                    console.log(`Copilot LM Proxy Debug: chunk ${chunks}: "${part.value}"`);
                } else {
                    console.log(`Copilot LM Proxy Debug: non-text part:`, typeof part, JSON.stringify(part));
                }
            }
            
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ model: models[0].id, chunks, text, responseKeys: Object.keys(response) }));
        } catch (error: any) {
            console.error('Copilot LM Proxy Debug error:', error);
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: String(error), code: error?.code, cause: String(error?.cause) }));
        }
    });
}

async function handleListModels(res: http.ServerResponse) {
    try {
        const models = await vscode.lm.selectChatModels({});
        const modelList = models.map(m => ({
            id: m.id,
            object: 'model',
            family: m.family,
            vendor: m.vendor,
            version: m.version,
            maxInputTokens: m.maxInputTokens
        }));
        res.writeHead(200, { 'Content-Type': 'application/json' });
        // Return both OpenAI format (data) and legacy format (models)
        res.end(JSON.stringify({ object: 'list', data: modelList, models: modelList }));
    } catch (error) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: String(error) }));
    }
}

async function handleChatCompletion(req: http.IncomingMessage, res: http.ServerResponse) {
    let body = '';
    req.on('data', chunk => { body += chunk; });

    req.on('end', async () => {
        try {
            const parsed = JSON.parse(body);
            const { model, messages, stream } = parsed;

            if (!messages || !Array.isArray(messages)) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: '"messages" is required and must be an array' }));
                return;
            }

            const selector: vscode.LanguageModelChatSelector = model ? { id: model } : {};
            const models = await vscode.lm.selectChatModels(selector);

            if (models.length === 0) {
                res.writeHead(404, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'No models available. Is Copilot signed in?' }));
                return;
            }

            // Prefer 'copilot' vendor, then others
            const selectedModel = models.find(m => m.vendor === 'copilot') || models[0];
            const vscodeMessages = messages.map((m: { role: string; content: string }) => {
                if (m.role === 'user') {
                    return vscode.LanguageModelChatMessage.User(m.content);
                } else if (m.role === 'assistant') {
                    return vscode.LanguageModelChatMessage.Assistant(m.content);
                } else {
                    return vscode.LanguageModelChatMessage.User(`[System] ${m.content}`);
                }
            });

            console.log(`Copilot LM Proxy: Using model id=${selectedModel.id} family=${selectedModel.family} vendor=${selectedModel.vendor}`);
            console.log(`Copilot LM Proxy: Sending ${vscodeMessages.length} messages, stream=${stream}`);

            const tokenSource = new vscode.CancellationTokenSource();

            // Cancel LLM request if HTTP client disconnects
            req.on('close', () => {
                tokenSource.cancel();
            });

            if (stream) {
                res.writeHead(200, {
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive'
                });

                const response = await selectedModel.sendRequest(vscodeMessages, {}, tokenSource.token);
                let chunkCount = 0;
                for await (const part of response.stream) {
                    if (part instanceof vscode.LanguageModelTextPart) {
                        chunkCount++;
                        const data = JSON.stringify({ choices: [{ delta: { content: part.value } }] });
                        res.write(`data: ${data}\n\n`);
                    }
                }
                console.log(`Copilot LM Proxy: Stream finished with ${chunkCount} chunks`);
                res.write('data: [DONE]\n\n');
                res.end();
                tokenSource.dispose();
            } else {
                console.log(`Copilot LM Proxy: Calling sendRequest...`);
                let response;
                try {
                    response = await selectedModel.sendRequest(
                        vscodeMessages,
                        {},
                        tokenSource.token
                    );
                    console.log(`Copilot LM Proxy: sendRequest returned, response type: ${typeof response}, keys: ${Object.keys(response)}`);
                } catch (sendErr: any) {
                    console.error(`Copilot LM Proxy: sendRequest threw:`, sendErr);
                    console.error(`Copilot LM Proxy: cause:`, sendErr?.cause);
                    console.error(`Copilot LM Proxy: code:`, sendErr?.code);
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: `sendRequest failed: ${sendErr}`, code: sendErr?.code }));
                    return;
                }
                let fullResponse = '';
                let chunkCount = 0;
                try {
                    for await (const part of response.stream) {
                        if (part instanceof vscode.LanguageModelTextPart) {
                            chunkCount++;
                            fullResponse += part.value;
                        }
                    }
                } catch (iterErr: any) {
                    console.error(`Copilot LM Proxy: stream iteration error after ${chunkCount} chunks:`, iterErr);
                    // Still return what we got
                }
                console.log(`Copilot LM Proxy: Non-stream finished with ${chunkCount} chunks, response length=${fullResponse.length}`);

                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                    id: `chatcmpl-${Date.now()}`,
                    object: 'chat.completion',
                    model: selectedModel.id,
                    choices: [{
                        index: 0,
                        message: { role: 'assistant', content: fullResponse },
                        finish_reason: 'stop'
                    }]
                }));
                tokenSource.dispose();
            }
        } catch (error) {
            console.error('Copilot LM Proxy error:', error);
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: String(error) }));
        }
    });
}

function updateStatusBar(state: ProxyState) {
    currentState = state;
    switch (state) {
        case 'running':
            statusBarItem.text = '$(radio-tower) Copilot LM Proxy';
            statusBarItem.tooltip = `Copilot LM Proxy running on port ${getPort()}`;
            statusBarItem.backgroundColor = undefined;
            break;
        case 'standby':
            statusBarItem.text = '$(eye) Copilot LM Proxy (standby)';
            statusBarItem.tooltip = `Another VS Code window is serving on port ${getPort()}. Click to retry.`;
            statusBarItem.backgroundColor = undefined;
            break;
        case 'stopped':
            statusBarItem.text = '$(circle-slash) Copilot LM Proxy';
            statusBarItem.tooltip = 'Copilot LM Proxy stopped. Click to start.';
            statusBarItem.backgroundColor = undefined;
            break;
        case 'error':
            statusBarItem.text = '$(error) Copilot LM Proxy';
            statusBarItem.tooltip = `Port ${getPort()} blocked. Click to retry.`;
            statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
            break;
    }
    statusBarItem.show();
}

/**
 * Check if something is already listening on the port and responding to requests.
 * Returns true if another healthy proxy is running.
 */
function checkExistingProxy(): Promise<boolean> {
    return new Promise((resolve) => {
        const req = http.get(`http://127.0.0.1:${getPort()}/health`, { timeout: 2000 }, (res) => {
            let data = '';
            res.on('data', chunk => { data += chunk; });
            res.on('end', () => {
                try {
                    const parsed = JSON.parse(data);
                    resolve(parsed.status === 'ok');
                } catch {
                    resolve(false);
                }
            });
        });
        req.on('error', () => resolve(false));
        req.on('timeout', () => { req.destroy(); resolve(false); });
    });
}

/**
 * Enter standby mode: periodically check if the port becomes available,
 * and take over when it does.
 */
function enterStandby() {
    stopStandby();
    updateStatusBar('standby');
    console.log('Copilot LM Proxy: Entering standby mode (another instance is serving)');

    standbyTimer = setInterval(async () => {
        const alive = await checkExistingProxy();
        if (!alive) {
            console.log('Copilot LM Proxy: Existing proxy gone, attempting to take over...');
            stopStandby();
            startServer();
        }
    }, 10000); // Check every 10 seconds
}

function stopStandby() {
    if (standbyTimer) {
        clearInterval(standbyTimer);
        standbyTimer = null;
    }
}

function startServer(retries = 3) {
    if (server) {
        server.close();
        server = null;
    }
    stopStandby();

    server = http.createServer(handleRequest);
    server.listen(getPort(), '127.0.0.1', () => {
        updateStatusBar('running');
        vscode.window.showInformationMessage(`Copilot LM Proxy started on http://127.0.0.1:${getPort()}`);
        console.log(`Copilot LM Proxy listening on port ${getPort()}`);
    });

    server.on('error', async (err: NodeJS.ErrnoException) => {
        server = null;
        if (err.code === 'EADDRINUSE') {
            // Check if a healthy proxy is already running (another window)
            const alive = await checkExistingProxy();
            if (alive) {
                // Another window is serving — go into standby silently
                enterStandby();
                return;
            }

            // Port is held by a dead process
            if (retries > 0) {
                const delay = (4 - retries) * 1000; // 1s, 2s, 3s
                console.log(`Copilot LM Proxy: Port ${getPort()} held by dead process, retrying in ${delay}ms (${retries} left)...`);
                updateStatusBar('error');
                setTimeout(() => startServer(retries - 1), delay);
            } else {
                updateStatusBar('error');
                vscode.window.showErrorMessage(
                    `Copilot LM Proxy: Port ${getPort()} is blocked by a dead process. ` +
                    `Run: lsof -ti:${getPort()} | xargs kill -9`,
                    'Retry'
                ).then(choice => {
                    if (choice === 'Retry') { startServer(); }
                });
            }
        } else {
            updateStatusBar('error');
            vscode.window.showErrorMessage(`Copilot LM Proxy error: ${err.message}`);
        }
    });
}

function stopServer() {
    stopStandby();
    if (server) {
        server.close();
        server = null;
    }
    updateStatusBar('stopped');
    vscode.window.showInformationMessage('Copilot LM Proxy stopped');
}

export function deactivate() {
    stopStandby();
    if (server) {
        server.close();
        server = null;
    }
}
