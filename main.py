import os
import sys
import time
import base64
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# =========================================================================
# FAIL-SAFE DESKTOP & ONEDRIVE STORAGE SETUP
# =========================================================================
def resolve_xeon_directory():
    home = os.path.expanduser('~')
    
    # Check common Desktop locations (OneDrive vs Standard)
    candidates = [
        os.path.join(home, 'OneDrive', 'Desktop'),
        os.path.join(home, 'Desktop'),
        os.path.join(home, 'OneDrive - Personal', 'Desktop')
    ]
    
    selected_desktop = None
    for path in candidates:
        if os.path.exists(path):
            selected_desktop = path
            break
            
    # Fallback to local working directory if Desktop isn't accessible
    if not selected_desktop:
        selected_desktop = os.getcwd()
        
    return os.path.join(selected_desktop, 'Xeon')

xeon_dir = resolve_xeon_directory()
PHOTOS_DIR = os.path.join(xeon_dir, 'photos')
VIDEOS_DIR = os.path.join(xeon_dir, 'videos')

# Automatically create target directories
os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

# Data store for active devices & WebRTC signaling
devices = {}

# Output active directory resolution to console
print("\n" + "="*60)
print("📁 XEON STORAGE ACTIVE:")
print(f"📸 PHOTOS: {os.path.abspath(PHOTOS_DIR)}")
print(f"🎥 VIDEOS: {os.path.abspath(VIDEOS_DIR)}")
print("="*60 + "\n")

# =========================================================================
# BROADCASTER HTML (Mobile & PC Client with Hardware-Optimized REC)
# =========================================================================
BROADCAST_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Xeon WebRTC Node</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #070811;
            --card-bg: rgba(18, 22, 41, 0.85);
            --neon-blue: #00f2fe;
            --neon-purple: #7928ca;
            --neon-green: #00ff87;
            --neon-red: #ff0055;
            --border-color: rgba(0, 242, 254, 0.25);
        }
        
        * { box-sizing: border-box; font-family: 'Inter', sans-serif; -webkit-tap-highlight-color: transparent; }
        
        body { 
            background: var(--bg-dark); 
            color: white; 
            padding: 10px; 
            margin: 0; 
            height: 100dvh; 
            width: 100vw;
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            justify-content: space-between; 
            overflow: hidden;
        }
        
        .brand-header { margin: 2px 0; text-align: center; }
        .brand-title { font-family: 'Orbitron', sans-serif; font-size: 20px; font-weight: 900; letter-spacing: 2px; background: linear-gradient(135deg, var(--neon-blue), var(--neon-purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .brand-sub { font-size: 9px; color: #6b7280; letter-spacing: 1.5px; text-transform: uppercase; }
        
        .glass-card { 
            background: var(--card-bg); 
            backdrop-filter: blur(16px); 
            border: 1px solid var(--border-color); 
            border-radius: 18px; 
            padding: 10px; 
            width: 100%; 
            max-width: 680px; 
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5); 
        }

        .type-badge { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 20px; font-size: 10px; font-weight: 700; background: rgba(0, 242, 254, 0.1); border: 1px solid var(--neon-blue); color: var(--neon-blue); margin-bottom: 6px; text-transform: uppercase; }
        
        input { width: 100%; background: rgba(10, 13, 26, 0.8); border: 1px solid var(--border-color); border-radius: 10px; padding: 8px; color: var(--neon-blue); font-size: 13px; font-weight: 600; text-align: center; margin-bottom: 8px; outline: none; }
        
        .video-container {
            width: 100%;
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            border-radius: 14px;
            background: #000;
            border: 1px solid var(--border-color);
            position: relative;
        }

        video { 
            width: 100%; 
            height: 100%; 
            object-fit: contain; 
            transition: opacity 0.15s ease;
        }

        .res-tag {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(7, 8, 17, 0.85);
            border: 1px solid var(--neon-green);
            color: var(--neon-green);
            font-family: 'Orbitron', monospace;
            font-size: 10px;
            font-weight: 700;
            padding: 4px 8px;
            border-radius: 8px;
            z-index: 5;
        }

        .rec-tag {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255, 0, 85, 0.9);
            border: 1px solid var(--neon-red);
            color: #fff;
            font-family: 'Orbitron', sans-serif;
            font-size: 10px;
            font-weight: 800;
            padding: 4px 8px;
            border-radius: 8px;
            z-index: 5;
            animation: pulse 1.2s infinite alternate;
        }
        
        .tab-bar-container {
            width: 100%;
            max-width: 680px;
            margin-top: 8px;
            margin-bottom: 4px;
        }

        .tab-bar {
            display: flex;
            align-items: center;
            justify-content: space-around;
            background: rgba(10, 13, 26, 0.95);
            border: 1px solid var(--border-color);
            backdrop-filter: blur(20px);
            border-radius: 22px;
            padding: 5px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
            gap: 2px;
        }

        .tab-btn {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: transparent;
            border: none;
            color: #8a99ad;
            padding: 6px 2px;
            border-radius: 16px;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            font-weight: 600;
        }

        .tab-btn .tab-icon { font-size: 16px; margin-bottom: 2px; }
        .tab-btn .tab-label { font-size: 9px; font-family: 'Orbitron', sans-serif; letter-spacing: 0.3px; }

        .tab-btn:hover { color: #fff; background: rgba(255, 255, 255, 0.05); }
        .tab-btn:active { transform: scale(0.92); }

        .tab-btn.active-primary {
            background: linear-gradient(135deg, var(--neon-blue), #0077ff);
            color: #000 !important;
            box-shadow: 0 0 12px rgba(0, 242, 254, 0.4);
        }

        .tab-btn.active-snap {
            background: linear-gradient(135deg, var(--neon-green), #009955);
            color: #000 !important;
        }

        .tab-btn.btn-danger {
            background: rgba(255, 0, 85, 0.15);
            color: var(--neon-red);
            border: 1px solid rgba(255, 0, 85, 0.3);
        }

        .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--neon-green); display: inline-block; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 0.3; } 50% { opacity: 1; } 100% { opacity: 0.3; } }
    </style>
</head>
<body>

    <div style="width: 100%; display: flex; flex-direction: column; align-items: center; flex: 1; min-height: 0;">
        <div class="brand-header">
            <div class="brand-title">⚡ XEON WEBRTC</div>
            <div class="brand-sub">Mobile Auto-Scale Node</div>
        </div>

        <div class="glass-card">
            <div style="text-align: center;">
                <div class="type-badge" id="deviceBadge">Detecting Device...</div>
            </div>

            <input type="text" id="deviceName" placeholder="Enter Device Label" />
            
            <div class="video-container">
                <div class="res-tag" id="localResTag">0 × 0 px</div>
                <div class="rec-tag" id="localRecBadge" style="display:none;">🔴 REC</div>
                <video id="preview" autoplay playsinline muted></video>
            </div>
        </div>
    </div>

    <div class="tab-bar-container">
        <div class="tab-bar" id="tabDock">
            <button id="startBtn" class="tab-btn active-primary" onclick="startBroadcasting()">
                <span class="tab-icon">⚡</span>
                <span class="tab-label">START</span>
            </button>
            <button id="snapBtn" class="tab-btn active-snap" style="display:none;" onclick="takePhotoToPC()">
                <span class="tab-icon">📸</span>
                <span class="tab-label">SNAP</span>
            </button>
            <button id="recBtn" class="tab-btn btn-danger" style="display:none;" onclick="toggleLocalRecording()">
                <span class="tab-icon" id="recIcon">🔴</span>
                <span class="tab-label" id="recLabel">REC</span>
            </button>
            <button id="muteBtn" class="tab-btn" style="display:none;" onclick="toggleMute()">
                <span class="tab-icon" id="muteIcon">🎙️</span>
                <span class="tab-label" id="muteLabel">MIC ON</span>
            </button>
            <button id="flipCamBtn" class="tab-btn" style="display:none;" onclick="flipCamera()">
                <span class="tab-icon">🔄</span>
                <span class="tab-label">FLIP</span>
            </button>
            <button id="stopBtn" class="tab-btn btn-danger" style="display:none;" onclick="stopBroadcasting()">
                <span class="tab-icon">⏹️</span>
                <span class="tab-label">STOP</span>
            </button>
        </div>
    </div>

    <script>
        const video = document.getElementById('preview');
        const nameInput = document.getElementById('deviceName');

        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const deviceType = isMobile ? 'mobile' : 'pc';

        document.getElementById('deviceBadge').innerHTML = isMobile ? '<span class="status-dot"></span> 📱 Mobile Node' : '<span class="status-dot"></span> 💻 PC Node';
        nameInput.value = (isMobile ? "Xeon-Mobile-" : "Xeon-PC-") + Math.floor(1000 + Math.random() * 9000);

        let localStream = null;
        let peerConnections = {};
        let currentDeviceId = "";
        let facingMode = "user";
        let heartbeatInterval = null;
        let signalPollInterval = null;

        let localMediaRecorder = null;
        let localRecordedChunks = [];
        let isLocalRecording = false;

        const rtcConfig = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

        video.addEventListener('loadedmetadata', updateLocalResolutionDisplay);
        video.addEventListener('resize', updateLocalResolutionDisplay);

        function updateLocalResolutionDisplay() {
            if (video.videoWidth && video.videoHeight) {
                document.getElementById('localResTag').innerText = `${video.videoWidth} × ${video.videoHeight} px`;
            }
        }

        async function startBroadcasting() {
            currentDeviceId = nameInput.value.trim().replace(/[^a-zA-Z0-9_-]/g, "") || "Xeon-Node";
            nameInput.disabled = true;

            try {
                // OPTIMIZATION: 720p @ 30fps lock prevents frame drops
                localStream = await navigator.mediaDevices.getUserMedia({
                    video: { 
                        facingMode: facingMode, 
                        width: { ideal: 1280 }, 
                        height: { ideal: 720 },
                        frameRate: { ideal: 30, max: 30 }
                    },
                    audio: true
                });

                video.srcObject = localStream;
                
                document.getElementById('startBtn').style.display = 'none';
                document.getElementById('snapBtn').style.display = 'flex';
                document.getElementById('recBtn').style.display = 'flex';
                document.getElementById('muteBtn').style.display = 'flex';
                if (isMobile) document.getElementById('flipCamBtn').style.display = 'flex';
                document.getElementById('stopBtn').style.display = 'flex';

                sendHeartbeat();
                heartbeatInterval = setInterval(sendHeartbeat, 2000);
                signalPollInterval = setInterval(pollSignals, 1000);

            } catch (err) {
                alert("Media Capture Error: " + err.message);
                nameInput.disabled = false;
            }
        }

        function toggleLocalRecording() {
            if (!isLocalRecording) {
                startLocalRecording();
            } else {
                stopLocalRecording();
            }
        }

        function startLocalRecording() {
            if (!localStream) return;
            localRecordedChunks = [];

            // OPTIMIZATION: Prefer H.264 / VP8 over high-CPU VP9
            let options = { mimeType: 'video/webm;codecs=h264,opus' };
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                options = { mimeType: 'video/webm;codecs=vp8,opus' };
            }
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                options = { mimeType: 'video/webm' };
            }

            try {
                localMediaRecorder = new MediaRecorder(localStream, options);
            } catch (e) {
                localMediaRecorder = new MediaRecorder(localStream);
            }

            localMediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    localRecordedChunks.push(event.data);
                }
            };

            localMediaRecorder.onstop = () => {
                const blob = new Blob(localRecordedChunks, { type: 'video/webm' });
                const formData = new FormData();
                formData.append('video', blob);
                formData.append('device_id', currentDeviceId);

                fetch('/upload_video', {
                    method: 'POST',
                    body: formData
                })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert("🔴 Video uploaded & saved to Desktop/Xeon/videos!");
                    }
                })
                .catch(err => alert("Upload error: " + err.message));
            };

            // OPTIMIZATION: Removed timeslice interval argument to reduce buffer stutter
            localMediaRecorder.start();
            isLocalRecording = true;

            document.getElementById('recLabel').innerText = "STOP";
            document.getElementById('recIcon').innerText = "⏹️";
            document.getElementById('localRecBadge').style.display = 'block';
        }

        function stopLocalRecording() {
            if (localMediaRecorder && localMediaRecorder.state !== 'inactive') {
                localMediaRecorder.stop();
            }
            isLocalRecording = false;

            document.getElementById('recLabel').innerText = "REC";
            document.getElementById('recIcon').innerText = "🔴";
            document.getElementById('localRecBadge').style.display = 'none';
        }

        function takePhotoToPC() {
            if (!localStream) return;

            video.style.opacity = '0.2';
            setTimeout(() => video.style.opacity = '1', 150);

            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth || 1280;
            canvas.height = video.videoHeight || 720;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            const photoDataUrl = canvas.toDataURL('image/jpeg', 0.92);

            for (let viewerId in peerConnections) {
                sendSignal(viewerId, {
                    type: 'snapshot',
                    image: photoDataUrl,
                    filename: `Xeon_Photo_${currentDeviceId}_${Date.now()}.jpg`
                });
            }
        }

        async function sendHeartbeat() {
            fetch('/heartbeat?device=' + encodeURIComponent(currentDeviceId) + '&type=' + deviceType, { method: 'POST' });
        }

        async function pollSignals() {
            try {
                const res = await fetch('/get_signals?device=' + encodeURIComponent(currentDeviceId));
                const signals = await res.json();
                
                for (let signal of signals) {
                    if (signal.type === 'offer') {
                        handleOffer(signal.from, signal.sdp);
                    } else if (signal.type === 'candidate' && peerConnections[signal.from]) {
                        await peerConnections[signal.from].addIceCandidate(new RTCIceCandidate(signal.candidate));
                    } else if (signal.type === 'cmd') {
                        if (signal.cmd === 'flip_cam' && isMobile) flipCamera();
                        if (signal.cmd === 'take_snap') takePhotoToPC();
                    }
                }
            } catch(e) {}
        }

        async function handleOffer(viewerId, offerSdp) {
            const pc = new RTCPeerConnection(rtcConfig);
            peerConnections[viewerId] = pc;

            localStream.getTracks().forEach(track => pc.addTrack(track, localStream));

            pc.onicecandidate = (event) => {
                if (event.candidate) {
                    sendSignal(viewerId, { type: 'candidate', candidate: event.candidate });
                }
            };

            await pc.setRemoteDescription(new RTCSessionDescription(offerSdp));
            const answer = await pc.createAnswer();
            await pc.setLocalDescription(answer);

            sendSignal(viewerId, { type: 'answer', sdp: pc.localDescription });
        }

        function sendSignal(targetId, data) {
            fetch('/send_signal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ from: currentDeviceId, to: targetId, payload: data })
            });
        }

        async function flipCamera() {
            if (!isMobile || !localStream) return;
            
            facingMode = (facingMode === "user") ? "environment" : "user";

            const oldVideoTrack = localStream.getVideoTracks()[0];
            if (oldVideoTrack) {
                oldVideoTrack.stop();
                localStream.removeTrack(oldVideoTrack);
            }

            try {
                const newStream = await navigator.mediaDevices.getUserMedia({
                    video: { 
                        facingMode: facingMode, 
                        width: { ideal: 1280 }, 
                        height: { ideal: 720 },
                        frameRate: { ideal: 30, max: 30 }
                    }
                });
                const newVideoTrack = newStream.getVideoTracks()[0];

                localStream.addTrack(newVideoTrack);
                video.srcObject = localStream;

                for (let viewerId in peerConnections) {
                    const pc = peerConnections[viewerId];
                    const videoSender = pc.getSenders().find(s => s.track && s.track.kind === 'video');
                    if (videoSender) {
                        await videoSender.replaceTrack(newVideoTrack);
                    }
                }
            } catch (err) {
                console.error("Camera Flip Error:", err);
            }
        }

        function toggleMute() {
            if (!localStream) return;
            const audioTrack = localStream.getAudioTracks()[0];
            if (audioTrack) {
                audioTrack.enabled = !audioTrack.enabled;
                document.getElementById('muteIcon').innerText = audioTrack.enabled ? "🎙️" : "🔇";
                document.getElementById('muteLabel').innerText = audioTrack.enabled ? "MIC ON" : "MUTED";
            }
        }

        function stopBroadcasting() {
            if (isLocalRecording) stopLocalRecording();
            if (heartbeatInterval) clearInterval(heartbeatInterval);
            if (signalPollInterval) clearInterval(signalPollInterval);
            if (localStream) localStream.getTracks().forEach(track => track.stop());
            video.srcObject = null;

            document.getElementById('startBtn').style.display = 'flex';
            document.getElementById('snapBtn').style.display = 'none';
            document.getElementById('recBtn').style.display = 'none';
            document.getElementById('muteBtn').style.display = 'none';
            document.getElementById('flipCamBtn').style.display = 'none';
            document.getElementById('stopBtn').style.display = 'none';
            nameInput.disabled = false;
        }
    </script>
</body>
</html>
"""

# =========================================================================
# COMMAND CENTER DASHBOARD HTML (Admin Viewer)
# =========================================================================
VIEWER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Xeon Command Center Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #05060f;
            --card-bg: rgba(13, 17, 33, 0.85);
            --panel-bg: rgba(18, 24, 46, 0.9);
            --neon-blue: #00f2fe;
            --neon-purple: #7928ca;
            --neon-green: #00ff87;
            --neon-red: #ff0055;
            --border-color: rgba(0, 242, 254, 0.25);
        }

        * { box-sizing: border-box; font-family: 'Inter', sans-serif; }
        body { background: var(--bg-dark); color: white; padding: 16px; margin: 0; min-height: 100vh; display: flex; flex-direction: column; }
        
        .header { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            max-width: 1480px; 
            width: 100%;
            margin: 0 auto 16px auto; 
            border-bottom: 1px solid var(--border-color); 
            padding-bottom: 12px; 
        }
        .brand-box { display: flex; align-items: center; gap: 12px; }
        .brand-logo { font-size: 24px; filter: drop-shadow(0 0 10px var(--neon-blue)); }
        .brand-title { font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: 900; letter-spacing: 2px; background: linear-gradient(135deg, var(--neon-blue), var(--neon-purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .brand-badge { background: rgba(0, 242, 254, 0.1); border: 1px solid var(--neon-blue); color: var(--neon-blue); padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; letter-spacing: 1px; font-family: 'Orbitron'; }

        .main-grid { display: grid; grid-template-columns: 1fr 320px; gap: 16px; max-width: 1480px; width: 100%; margin: 0 auto; flex: 1; }

        .video-box { 
            background: var(--card-bg); 
            backdrop-filter: blur(20px); 
            border: 1px solid var(--border-color); 
            border-radius: 24px; 
            padding: 14px; 
            text-align: center; 
            box-shadow: 0 15px 35px rgba(0,0,0,0.6); 
            display: flex; 
            flex-direction: column; 
            justify-content: space-between;
        }
        
        .video-wrapper { 
            position: relative; 
            width: 100%; 
            border-radius: 18px; 
            overflow: hidden; 
            background: #000; 
            flex: 1;
            min-height: 68vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            border: 1px solid rgba(0, 242, 254, 0.15);
        }

        video { 
            width: 100%; 
            height: 68vh; 
            object-fit: contain; 
            background: #000;
        }

        .telemetry-overlay {
            position: absolute;
            top: 16px;
            left: 16px;
            background: rgba(5, 6, 15, 0.85);
            backdrop-filter: blur(12px);
            border: 1px solid var(--neon-blue);
            border-radius: 12px;
            padding: 10px 16px;
            font-family: 'Orbitron', monospace;
            font-size: 11px;
            color: var(--neon-blue);
            display: grid;
            grid-template-columns: auto auto;
            gap: 6px 18px;
            text-align: left;
            box-shadow: 0 4px 20px rgba(0, 242, 254, 0.25);
            z-index: 10;
        }
        .stat-label { color: #8a99ad; font-family: 'Inter', sans-serif; font-size: 10px; text-transform: uppercase; font-weight: 600; }
        .stat-val { font-weight: 700; color: #fff; }
        .stat-val.highlight { color: var(--neon-green); }

        .rec-indicator {
            position: absolute;
            top: 16px;
            right: 16px;
            background: rgba(255, 0, 85, 0.95);
            color: #fff;
            padding: 6px 14px;
            border-radius: 20px;
            font-family: 'Orbitron', sans-serif;
            font-size: 11px;
            font-weight: 800;
            display: none;
            align-items: center;
            gap: 8px;
            box-shadow: 0 0 15px rgba(255, 0, 85, 0.6);
            animation: pulse 1.2s infinite alternate;
            z-index: 10;
        }

        .action-dock {
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(10, 13, 26, 0.95);
            border: 1px solid var(--border-color);
            backdrop-filter: blur(20px);
            border-radius: 22px;
            padding: 8px 16px;
            margin-top: 12px;
            gap: 12px;
            flex-wrap: wrap;
        }

        .dock-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #b0c4de;
            padding: 9px 18px;
            border-radius: 14px;
            cursor: pointer;
            transition: all 0.25s ease;
            font-weight: 700;
            font-size: 12px;
            font-family: 'Orbitron', sans-serif;
        }

        .dock-btn:hover { color: #fff; background: rgba(0, 242, 254, 0.15); border-color: var(--neon-blue); box-shadow: 0 0 12px rgba(0,242,254,0.3); }
        .dock-btn:active { transform: scale(0.95); }

        .dock-btn.btn-purple { background: linear-gradient(135deg, var(--neon-purple), #4a00e0); color: white; border: none; }
        .dock-btn.btn-green { background: linear-gradient(135deg, var(--neon-green), #009955); color: #000; border: none; }
        .dock-btn.btn-red { background: linear-gradient(135deg, var(--neon-red), #990033); color: white; border: none; }
        .dock-btn.is-recording { animation: pulse 1.2s infinite alternate; box-shadow: 0 0 15px rgba(255,0,85,0.7); }

        .side-panel { display: flex; flex-direction: column; gap: 16px; }

        .panel-card {
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }

        .panel-title { 
            font-family: 'Orbitron', sans-serif; 
            font-size: 12px; 
            font-weight: 800; 
            color: var(--neon-blue); 
            letter-spacing: 1.5px; 
            margin-bottom: 12px; 
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .device-card { 
            background: rgba(10, 13, 26, 0.7); 
            border: 1px solid rgba(255, 255, 255, 0.08); 
            border-radius: 14px; 
            padding: 12px; 
            margin-bottom: 8px; 
            cursor: pointer; 
            transition: all 0.25s ease; 
        }
        .device-card:hover { border-color: var(--neon-blue); transform: translateX(3px); }
        .device-card.active { border-color: var(--neon-blue); background: rgba(0, 242, 254, 0.12); box-shadow: 0 0 15px rgba(0, 242, 254, 0.25); }
        
        .dev-header { display: flex; justify-content: space-between; align-items: center; font-weight: 700; font-size: 13px; margin-bottom: 4px; }
        .dev-type { font-size: 10px; color: #9ca3af; text-transform: uppercase; font-weight: 600; }
        .live-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--neon-green); display: inline-block; margin-right: 4px; }

        .photo-gallery {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            max-height: 200px;
            overflow-y: auto;
            padding-right: 4px;
        }
        .photo-thumb {
            width: 100%;
            height: 75px;
            object-fit: cover;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            cursor: pointer;
            transition: transform 0.2s;
        }
        .photo-thumb:hover { transform: scale(1.05); border-color: var(--neon-green); }

        .toast-notification {
            position: fixed;
            bottom: 25px;
            right: 25px;
            background: linear-gradient(135deg, var(--neon-green), #00b359);
            color: #000;
            padding: 12px 22px;
            border-radius: 14px;
            font-weight: 800;
            font-family: 'Orbitron', sans-serif;
            font-size: 12px;
            box-shadow: 0 10px 30px rgba(0,255,135,0.4);
            z-index: 999;
            animation: slideUp 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }

        @keyframes slideUp { from { transform: translateY(50px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        @keyframes pulse { 0% { opacity: 0.3; } 50% { opacity: 1; } 100% { opacity: 0.3; } }

        @media (max-width: 900px) {
            .main-grid { grid-template-columns: 1fr; }
            .video-wrapper, video { height: 50vh; }
        }
    </style>
</head>
<body>

    <div class="header">
        <div class="brand-box">
            <div class="brand-logo">⚡</div>
            <div>
                <div class="brand-title">XEON COMMAND CENTER</div>
            </div>
        </div>
        <div class="brand-badge">ULTRA-LOW LATENCY DASHBOARD</div>
    </div>

    <div class="main-grid">
        <div class="video-box">
            <div class="video-wrapper">
                <div class="rec-indicator" id="recBadge">🔴 REC (SAVING TO DESKTOP/XEON/VIDEOS)</div>

                <div class="telemetry-overlay" id="telemetryOverlay">
                    <div><span class="stat-label">EXACT RES:</span> <span class="stat-val highlight" id="statRes">0 × 0 px</span></div>
                    <div><span class="stat-label">FPS:</span> <span class="stat-val" id="statFps">0</span></div>
                    <div><span class="stat-label">PING:</span> <span class="stat-val" id="statPing">0 ms</span></div>
                    <div><span class="stat-label">BITRATE:</span> <span class="stat-val" id="statBitrate">0.0 Mbps</span></div>
                </div>

                <video id="remoteVideo" autoplay playsinline></video>
            </div>

            <div class="action-dock">
                <button class="dock-btn btn-green" id="remoteSnapBtn" onclick="sendAdminCommand('take_snap')">
                    📸 REMOTE SNAPSHOT
                </button>
                <button class="dock-btn btn-red" id="pcRecBtn" onclick="togglePCRecording()">
                    🔴 REMOTE RECORD (PC)
                </button>
                <button class="dock-btn btn-purple" id="remoteFlipBtn" style="display:none;" onclick="sendAdminCommand('flip_cam')">
                    🔄 FLIP PHONE CAM
                </button>
                <button class="dock-btn" id="audioToggleBtn" onclick="toggleAudioOutput()">
                    🔊 AUDIO ON
                </button>
                <button class="dock-btn" onclick="toggleFullscreen()">
                    📺 FULLSCREEN
                </button>
            </div>
        </div>

        <div class="side-panel">
            <div class="panel-card">
                <div class="panel-title">
                    <span>ACTIVE NODES</span>
                    <span style="color: var(--neon-green);" id="devCount">0</span>
                </div>
                <div id="deviceList">
                    <div style="color: #6b7280; font-size: 12px; font-style: italic;">Scanning network for WebRTC nodes...</div>
                </div>
            </div>

            <div class="panel-card">
                <div class="panel-title">CAPTURED PHOTOS</div>
                <div class="photo-gallery" id="galleryContainer">
                    <div style="color: #6b7280; font-size: 11px; font-style: italic; grid-column: span 2;">No snapshots taken yet</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const viewerId = "Viewer-" + Math.floor(1000 + Math.random() * 9000);
        let currentDevice = null;
        let deviceMap = {};
        let pc = null;
        let signalPollInterval = null;
        let statsInterval = null;

        let prevBytesReceived = 0;
        let prevTimestamp = 0;

        let mediaRecorder = null;
        let recordedChunks = [];
        let isRecording = false;
        let isAudioMuted = false;

        const rtcConfig = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };
        const remoteVideo = document.getElementById('remoteVideo');

        remoteVideo.addEventListener('loadedmetadata', updateExactVideoResolution);
        remoteVideo.addEventListener('resize', updateExactVideoResolution);

        function updateExactVideoResolution() {
            if (remoteVideo.videoWidth && remoteVideo.videoHeight) {
                document.getElementById('statRes').innerText = `${remoteVideo.videoWidth} × ${remoteVideo.videoHeight} px`;
            }
        }

        async function refreshDeviceList() {
            try {
                const res = await fetch('/list_devices_info');
                const activeDevices = await res.json();
                const container = document.getElementById('deviceList');
                
                deviceMap = {};
                activeDevices.forEach(d => deviceMap[d.id] = d.type);

                document.getElementById('devCount').innerText = activeDevices.length;

                if (activeDevices.length === 0) {
                    container.innerHTML = '<div style="color: #6b7280; font-size: 12px; font-style: italic;">No active WebRTC nodes found</div>';
                    updateAdminButtons();
                    return;
                }

                if (!currentDevice || !deviceMap[currentDevice]) {
                    connectToDevice(activeDevices[0].id);
                }

                let html = '';
                activeDevices.forEach(dev => {
                    const isActive = dev.id === currentDevice ? 'active' : '';
                    const icon = dev.type === 'mobile' ? '📱' : '💻';
                    html += `
                        <div class="device-card ${isActive}" onclick="connectToDevice('${dev.id}')">
                            <div class="dev-header">
                                <span>${icon} ${dev.id}</span>
                                <span style="color: #00ff87; font-size: 10px;"><span class="live-dot"></span>LIVE</span>
                            </div>
                            <div class="dev-type">${dev.type} node</div>
                        </div>
                    `;
                });
                container.innerHTML = html;
                updateAdminButtons();
            } catch (e) {
                console.error("Error refreshing devices:", e);
            }
        }

        function updateAdminButtons() {
            const currentType = deviceMap[currentDevice];
            const flipBtn = document.getElementById('remoteFlipBtn');

            if (currentType === 'mobile') {
                flipBtn.style.display = 'inline-flex';
            } else {
                flipBtn.style.display = 'none';
            }
        }

        async function connectToDevice(deviceId) {
            if (currentDevice === deviceId && pc) return;

            currentDevice = deviceId;
            if (pc) pc.close();
            if (signalPollInterval) clearInterval(signalPollInterval);
            if (statsInterval) clearInterval(statsInterval);

            pc = new RTCPeerConnection(rtcConfig);

            pc.ontrack = (event) => {
                if (remoteVideo.srcObject !== event.streams[0]) {
                    remoteVideo.srcObject = event.streams[0];
                }
            };

            pc.onicecandidate = (event) => {
                if (event.candidate) {
                    sendSignal(currentDevice, { type: 'candidate', candidate: event.candidate });
                }
            };

            pc.addTransceiver('video', { direction: 'recvonly' });
            pc.addTransceiver('audio', { direction: 'recvonly' });

            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);

            sendSignal(currentDevice, { type: 'offer', sdp: pc.localDescription });

            signalPollInterval = setInterval(pollViewerSignals, 1000);
            statsInterval = setInterval(updateTelemetry, 1000);

            refreshDeviceList();
        }

        async function pollViewerSignals() {
            try {
                const res = await fetch('/get_signals?device=' + encodeURIComponent(viewerId));
                const signals = await res.json();
                for (let signal of signals) {
                    if (signal.type === 'answer' && pc) {
                        await pc.setRemoteDescription(new RTCSessionDescription(signal.sdp));
                    } else if (signal.type === 'candidate' && pc) {
                        await pc.addIceCandidate(new RTCIceCandidate(signal.candidate));
                    } else if (signal.type === 'snapshot') {
                        handlePhotoReceived(signal.image);
                    }
                }
            } catch(e) {}
        }

        function handlePhotoReceived(dataUrl) {
            fetch('/upload_photo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: dataUrl, device_id: currentDevice })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast("📸 SNAPSHOT SAVED TO DESKTOP/XEON/PHOTOS!");
                }
            });

            const gallery = document.getElementById('galleryContainer');
            if (gallery.children[0] && gallery.children[0].innerText.includes("No snapshots")) {
                gallery.innerHTML = '';
            }

            const img = document.createElement('img');
            img.src = dataUrl;
            img.className = 'photo-thumb';
            img.onclick = () => window.open(dataUrl, '_blank');
            gallery.prepend(img);
        }

        function toggleAudioOutput() {
            isAudioMuted = !isAudioMuted;
            remoteVideo.muted = isAudioMuted;
            
            const btn = document.getElementById('audioToggleBtn');
            btn.innerHTML = isAudioMuted ? "🔇 AUDIO MUTED" : "🔊 AUDIO ON";
        }

        function showToast(msg) {
            const toast = document.createElement('div');
            toast.className = 'toast-notification';
            toast.innerHTML = msg;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3500);
        }

        function togglePCRecording() {
            if (!isRecording) {
                startPCRecording();
            } else {
                stopPCRecording();
            }
        }

        function startPCRecording() {
            if (!remoteVideo.srcObject) {
                alert("No active stream to record.");
                return;
            }

            recordedChunks = [];
            const stream = remoteVideo.srcObject;

            // OPTIMIZATION: H.264 / VP8 hardware encoding selection
            let options = { mimeType: 'video/webm;codecs=h264,opus' };
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                options = { mimeType: 'video/webm;codecs=vp8,opus' };
            }
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                options = { mimeType: 'video/webm' };
            }

            try {
                mediaRecorder = new MediaRecorder(stream, options);
            } catch (e) {
                mediaRecorder = new MediaRecorder(stream);
            }

            mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    recordedChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                const blob = new Blob(recordedChunks, { type: 'video/webm' });
                const formData = new FormData();
                formData.append('video', blob);
                formData.append('device_id', currentDevice);

                fetch('/upload_video', {
                    method: 'POST',
                    body: formData
                })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        showToast("🔴 VIDEO SAVED TO DESKTOP/XEON/VIDEOS!");
                    }
                });
            };

            // OPTIMIZATION: Removed timeslice argument for smooth uninterrupted recording
            mediaRecorder.start();
            isRecording = true;

            const recBtn = document.getElementById('pcRecBtn');
            recBtn.innerText = "⏹️ STOP RECORDING";
            recBtn.classList.add('is-recording');
            document.getElementById('recBadge').style.display = 'flex';
        }

        function stopPCRecording() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            isRecording = false;

            const recBtn = document.getElementById('pcRecBtn');
            recBtn.innerText = "🔴 REMOTE RECORD (PC)";
            recBtn.classList.remove('is-recording');
            document.getElementById('recBadge').style.display = 'none';
        }

        function sendSignal(targetId, data) {
            fetch('/send_signal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ from: viewerId, to: targetId, payload: data })
            });
        }

        async function sendAdminCommand(cmd) {
            if (!currentDevice) return;
            sendSignal(currentDevice, { type: 'cmd', cmd: cmd });
        }

        async function updateTelemetry() {
            updateExactVideoResolution();

            if (!pc) return;
            const stats = await pc.getStats();
            
            stats.forEach(report => {
                if (report.type === 'inbound-rtp' && report.kind === 'video') {
                    document.getElementById('statFps').innerText = report.framesPerSecond || 0;
                    
                    const bytes = report.bytesReceived;
                    const now = report.timestamp;
                    if (prevBytesReceived > 0) {
                        const bitrateMbps = (((bytes - prevBytesReceived) * 8) / (now - prevTimestamp) / 1000).toFixed(2);
                        document.getElementById('statBitrate').innerText = bitrateMbps + " Mbps";
                    }
                    prevBytesReceived = bytes;
                    prevTimestamp = now;

                    if (report.frameWidth && report.frameHeight) {
                        document.getElementById('statRes').innerText = `${report.frameWidth} × ${report.frameHeight} px`;
                    }
                }

                if (report.type === 'candidate-pair' && report.state === 'succeeded') {
                    if (report.currentRoundTripTime) {
                        const pingMs = Math.round(report.currentRoundTripTime * 1000);
                        document.getElementById('statPing').innerText = pingMs + " ms";
                    }
                }
            });
        }

        setInterval(refreshDeviceList, 2000);
        refreshDeviceList();

        function toggleFullscreen() {
            if (remoteVideo.requestFullscreen) remoteVideo.requestFullscreen();
            else if (remoteVideo.webkitRequestFullscreen) remoteVideo.webkitRequestFullscreen();
        }
    </script>
</body>
</html>
"""

# =========================================================================
# FLASK ENDPOINTS & FILE HANDLERS
# =========================================================================

@app.route('/')
def index():
    return render_template_string(BROADCAST_HTML)

@app.route('/watch')
def watch():
    return render_template_string(VIEWER_HTML)

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    device_id = request.args.get('device')
    device_type = request.args.get('type', 'pc')
    if device_id:
        if device_id not in devices:
            devices[device_id] = {'type': device_type, 'last_seen': time.time(), 'signals': []}
        else:
            devices[device_id]['last_seen'] = time.time()
            devices[device_id]['type'] = device_type
    return jsonify({'status': 'ok'})

@app.route('/list_devices_info')
def list_devices_info():
    now = time.time()
    active = [
        {'id': dev_id, 'type': data.get('type', 'pc')}
        for dev_id, data in devices.items()
        if now - data.get('last_seen', 0) < 5.0
    ]
    return jsonify(active)

@app.route('/send_signal', methods=['POST'])
def send_signal():
    data = request.json
    target_id = data.get('to')
    payload = data.get('payload')
    payload['from'] = data.get('from')

    if target_id not in devices:
        devices[target_id] = {'type': 'viewer', 'last_seen': time.time(), 'signals': []}

    devices[target_id]['signals'].append(payload)
    return jsonify({'status': 'sent'})

@app.route('/get_signals')
def get_signals():
    device_id = request.args.get('device')
    if device_id in devices:
        signals = devices[device_id]['signals']
        devices[device_id]['signals'] = []
        return jsonify(signals)
    return jsonify([])

# UPLOAD SNAPSHOT TO DESKTOP/XEON/PHOTOS
@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    data = request.json
    image_data = data.get('image')
    device_id = data.get('device_id', 'unknown')

    if image_data:
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        filename = f"Snapshot_{device_id}_{int(time.time())}.jpg"
        filepath = os.path.join(PHOTOS_DIR, filename)

        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(image_data))
            
        print(f"📸 Saved Snapshot: {filepath}")
        return jsonify({'status': 'success', 'path': filepath})
    return jsonify({'status': 'error', 'message': 'No image data'}), 400

# UPLOAD VIDEO TO DESKTOP/XEON/VIDEOS
@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'status': 'error', 'message': 'No video file provided'}), 400

    file = request.files['video']
    device_id = request.form.get('device_id', 'unknown')

    filename = f"Recording_{device_id}_{int(time.time())}.webm"
    filepath = os.path.join(VIDEOS_DIR, filename)
    
    file.save(filepath)
    print(f"🔴 Saved Recording: {filepath}")
    return jsonify({'status': 'success', 'path': filepath})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)