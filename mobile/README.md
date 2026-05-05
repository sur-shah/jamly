# Jamly Mobile

Expo React Native frontend for testing the Jamly MVP backend.

## Run Locally

Start the backend first:

```bash
cd ..
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then start the mobile app:

```bash
npm install
npm run start
```

By default the app calls:

```text
http://127.0.0.1:8000
```

For a physical phone, set `EXPO_PUBLIC_API_URL` to your computer's LAN address, for example:

```bash
EXPO_PUBLIC_API_URL=http://192.168.1.20:8000 npm run start
```

For Android Emulator, use:

```bash
EXPO_PUBLIC_API_URL=http://10.0.2.2:8000 npm run android
```
