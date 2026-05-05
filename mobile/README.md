# Jamly Mobile

Expo (React Native) client for Jamly’s MVP. It speaks to the **same REST API** as Swagger: create a **custom chord exercise**, open a **practice session**, **upload** an audio take, tap **analyze**, then render the returned **feedback report** (score, summary, fixes, chord-level rows when present).

For what Jamly is end-to-end, see the **`../README.md`** at the backend project root.

## Prerequisites

- Jamly API running and reachable from the simulator or device (see below).
- Node.js and npm in this directory (`jamly/mobile`).

## Start the API first

From the **backend project root** (parent of `mobile/`, where `pyproject.toml` lives):

```bash
cd ..
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use `--host 0.0.0.0` if you test on a **physical phone** on Wi‑Fi.

## Start the Expo app

```bash
cd mobile
npm install
npm run start
```

Then open the app in a simulator (press `i` or `a` in the Expo CLI) or scan the QR code with **Expo Go**.

## Point the app at your API

The client defaults to `http://127.0.0.1:8000` unless you set **`EXPO_PUBLIC_API_URL`** when starting Metro.

| Where you run the app | Typical `EXPO_PUBLIC_API_URL` |
|------------------------|-------------------------------|
| iOS Simulator (Mac) | `http://127.0.0.1:8000` |
| Android Emulator | `http://10.0.2.2:8000` |
| Physical device (same Wi‑Fi as laptop) | `http://<your-laptop-LAN-IP>:8000` |

Examples:

```bash
EXPO_PUBLIC_API_URL=http://192.168.1.20:8000 npm run start
```

```bash
EXPO_PUBLIC_API_URL=http://10.0.2.2:8000 npm run android
```

Ensure the backend listens on `0.0.0.0` when the device must connect over the network, and that your OS firewall allows the chosen port (default **8000**).
