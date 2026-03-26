import * as vscode from 'vscode';
import * as http from 'http';

let server: http.Server | null = null;
const PORT = 19823;

export function activate(context: vscode.ExtensionContext) {
    console.log('Copilot Proxy extension activated');
    startServer();

    context.subscriptions.push(
        vscode.commands.registerCommand('copilot-proxy.start', startServer),
        vscode.commands.registerCommand('copilot-proxy.stop', stopServer)
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
            
            const msg = vscode.LanguageModelChatMessage.User('Say "test" and nothing else.');
            console.log('Copilot Proxy Debug: Attempting sendRequest with model:', models[0]?.id);
            
            const response = await models[0].sendRequest([msg], {});
            console.log('Copilot Proxy Debug: sendRequest returned:', typeof response);
            console.log('Copilot Proxy Debug: response keys:', Object.keys(response));
            
            let text = '';
            let chunks = 0;
            for await (const part of response.stream) {
                if (part instanceof vscode.LanguageModelTextPart) {
                    chunks++;
                    text += part.value;
                    console.log(`Copilot Proxy Debug: chunk ${chunks}: "${part.value}"`);
                } else {
                    console.log(`Copilot Proxy Debug: non-text part:`, typeof part, JSON.stringify(part));
                }
            }
            
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ model: models[0].id, chunks, text, responseKeys: Object.keys(response) }));
        } catch (error: any) {
            console.error('Copilot Proxy Debug error:', error);
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
            family: m.family,
            vendor: m.vendor,
            version: m.version,
            maxInputTokens: m.maxInputTokens
        }));
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ models: modelList }));
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
            const { model, messages, stream } = JSON.parse(body);

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

            console.log(`Copilot Proxy: Using model id=${selectedModel.id} family=${selectedModel.family} vendor=${selectedModel.vendor}`);
            console.log(`Copilot Proxy: Sending ${vscodeMessages.length} messages, stream=${stream}`);

            const tokenSource = new vscode.CancellationTokenSource();

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
                console.log(`Copilot Proxy: Stream finished with ${chunkCount} chunks`);
                res.write('data: [DONE]\n\n');
                res.end();
            } else {
                console.log(`Copilot Proxy: Calling sendRequest...`);
                let response;
                try {
                    response = await selectedModel.sendRequest(
                        vscodeMessages,
                        {},
                        tokenSource.token
                    );
                    console.log(`Copilot Proxy: sendRequest returned, response type: ${typeof response}, keys: ${Object.keys(response)}`);
                } catch (sendErr: any) {
                    console.error(`Copilot Proxy: sendRequest threw:`, sendErr);
                    console.error(`Copilot Proxy: cause:`, sendErr?.cause);
                    console.error(`Copilot Proxy: code:`, sendErr?.code);
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
                    console.error(`Copilot Proxy: stream iteration error after ${chunkCount} chunks:`, iterErr);
                    // Still return what we got
                }
                console.log(`Copilot Proxy: Non-stream finished with ${chunkCount} chunks, response length=${fullResponse.length}`);

                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                    model: selectedModel.id,
                    choices: [{
                        message: { role: 'assistant', content: fullResponse },
                        finish_reason: 'stop'
                    }]
                }));
            }
        } catch (error) {
            console.error('Copilot Proxy error:', error);
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: String(error) }));
        }
    });
}

function startServer(retries = 5) {
    if (server) {
        server.close();
        server = null;
    }

    server = http.createServer(handleRequest);
    server.listen(PORT, '127.0.0.1', () => {
        vscode.window.showInformationMessage(`Copilot Proxy started on http://127.0.0.1:${PORT}`);
        console.log(`Copilot Proxy listening on port ${PORT}`);
    });

    server.on('error', (err: NodeJS.ErrnoException) => {
        if (err.code === 'EADDRINUSE') {
            server = null;
            if (retries <= 0) {
                vscode.window.showErrorMessage(`Copilot Proxy: Port ${PORT} still in use after retries. Run "Copilot Proxy: Start" command to retry.`);
                return;
            }
            const delay = (6 - retries) * 1000; // 1s, 2s, 3s, 4s, 5s
            console.log(`Copilot Proxy: Port ${PORT} in use, retrying in ${delay}ms (${retries} retries left)...`);
            setTimeout(() => startServer(retries - 1), delay);
        } else {
            vscode.window.showErrorMessage(`Copilot Proxy error: ${err.message}`);
            server = null;
        }
    });
}

function stopServer() {
    if (server) {
        server.close();
        server = null;
        vscode.window.showInformationMessage('Copilot Proxy stopped');
    }
}

export function deactivate() {
    stopServer();
}
