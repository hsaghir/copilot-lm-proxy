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
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    if (req.method !== 'POST') {
        res.writeHead(405, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Method not allowed' }));
        return;
    }

    if (req.url === '/v1/models') {
        await handleListModels(res);
    } else if (req.url === '/v1/chat/completions') {
        await handleChatCompletion(req, res);
    } else {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Not found' }));
    }
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

            const selectedModel = models[0];
            const vscodeMessages = messages.map((m: { role: string; content: string }) => {
                if (m.role === 'user') {
                    return vscode.LanguageModelChatMessage.User(m.content);
                } else if (m.role === 'assistant') {
                    return vscode.LanguageModelChatMessage.Assistant(m.content);
                } else {
                    return vscode.LanguageModelChatMessage.User(`[System] ${m.content}`);
                }
            });

            if (stream) {
                res.writeHead(200, {
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive'
                });

                const response = await selectedModel.sendRequest(vscodeMessages, {});
                for await (const chunk of response.text) {
                    const data = JSON.stringify({ choices: [{ delta: { content: chunk } }] });
                    res.write(`data: ${data}\n\n`);
                }
                res.write('data: [DONE]\n\n');
                res.end();
            } else {
                const response = await selectedModel.sendRequest(vscodeMessages, {});
                let fullResponse = '';
                for await (const chunk of response.text) {
                    fullResponse += chunk;
                }

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

function startServer() {
    if (server) {
        vscode.window.showInformationMessage(`Copilot Proxy already running on port ${PORT}`);
        return;
    }

    server = http.createServer(handleRequest);
    server.listen(PORT, '127.0.0.1', () => {
        vscode.window.showInformationMessage(`Copilot Proxy started on http://127.0.0.1:${PORT}`);
        console.log(`Copilot Proxy listening on port ${PORT}`);
    });

    server.on('error', (err) => {
        vscode.window.showErrorMessage(`Copilot Proxy error: ${err.message}`);
        server = null;
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
