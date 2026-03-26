# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Do not open a public issue.**

Instead, email the maintainer directly or use [GitHub's private vulnerability reporting](https://github.com/hsaghir/copilot-lm-proxy/security/advisories/new).

## Scope

This project runs a local HTTP server on `127.0.0.1:19823` (localhost only). It does not:
- Accept connections from external networks
- Store or transmit credentials
- Authenticate requests (it trusts localhost)

If you find a way to exploit the proxy server, please report it.
