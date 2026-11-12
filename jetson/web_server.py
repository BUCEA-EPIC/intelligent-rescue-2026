#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 文件：web_server.py
# 功能：网页画面传输与状态监控
# 团队：北京建筑大学光启Ray-space工作室

import cv2
import threading
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Optional

# 全局状态管理
_frame_lock = threading.Lock()
_latest_frame: Optional[cv2.Mat] = None
_last_frame_time: float = 0.0

_status_lock = threading.Lock()
_status_data = {
    "state": "等待指令",
    "claw_state": "open",
    "cmd": 0xAA,
    "team": "blue",
    "fps": 0.0,
    "frame_count": 0,
    "start_time": time.time(),
    "last_update": time.time()
}

_server_instance: Optional[HTTPServer] = None
_server_thread: Optional[threading.Thread] = None


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """支持多线程处理请求的 HTTP 服务器"""
    allow_reuse_address = True
    daemon_threads = True


class StreamingHandler(BaseHTTPRequestHandler):
    """请求处理器，支持主页仪表盘、MJPEG流及JSON API"""
    
    def log_message(self, format, *args):
        # 禁用默认的请求日志输出，防止干扰终端调试信息
        pass

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self._get_dashboard_html().encode('utf-8'))
            
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', '0')
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            try:
                while True:
                    # 控制帧率，防止过度消耗CPU与带宽 (约 25 FPS)
                    time.sleep(0.04)
                    
                    with _frame_lock:
                        if _latest_frame is None:
                            continue
                        frame = _latest_frame.copy()
                    
                    # 编码为 JPEG 格式
                    ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                    if not ret:
                        continue
                        
                    self.wfile.write(b'--frame\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(jpeg)))
                    self.end_headers()
                    self.wfile.write(jpeg.tobytes())
                    self.wfile.write(b'\r\n')
            except Exception:
                pass
                
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            with _status_lock:
                data = _status_data.copy()
                data["uptime"] = f"{time.time() - data['start_time']:.1f}s"
            self.wfile.write(json.dumps(data).encode('utf-8'))
            
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def _get_dashboard_html(self) -> str:
        """返回高级、炫酷的机器人监控仪表盘 HTML"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>光启Ray-space智能救援赛项 - 画面传输与遥测监测仪表盘</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #020617;
            --panel-bg: rgba(15, 23, 42, 0.45);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-cyan: #06b6d4;
            --accent-green: #10b981;
            --accent-purple: #a855f7;
            --accent-red: #ef4444;
            --accent-yellow: #eab308;
            --shadow-glow: 0 0 20px rgba(6, 182, 212, 0.15);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            background-image: radial-gradient(circle at 50% 50%, #0f172a 0%, #020617 100%);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 40px;
            background: rgba(15, 23, 42, 0.2);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border-color);
        }

        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .header-title h1 {
            font-size: 22px;
            font-weight: 800;
            letter-spacing: 0.5px;
            background: linear-gradient(135deg, #06b6d4, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .pulse-dot {
            width: 10px;
            height: 10px;
            background-color: var(--accent-green);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--accent-green);
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.9); opacity: 0.6; }
            50% { transform: scale(1.1); opacity: 1; box-shadow: 0 0 15px var(--accent-green); }
            100% { transform: scale(0.9); opacity: 0.6; }
        }

        .system-info {
            display: flex;
            gap: 20px;
            font-size: 14px;
            color: var(--text-secondary);
        }

        .system-info span strong {
            color: var(--text-primary);
        }

        .container {
            display: grid;
            grid-template-columns: 1fr 400px;
            gap: 30px;
            padding: 30px 40px;
            flex-grow: 1;
            max-width: 1600px;
            width: 100%;
            margin: 0 auto;
        }

        @media (max-width: 1024px) {
            .container {
                grid-template-columns: 1fr;
            }
        }

        .panel {
            background: var(--panel-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .panel-header {
            padding: 16px 24px;
            border-bottom: 1px solid var(--border-color);
            font-weight: 600;
            font-size: 15px;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(255,255,255,0.02);
        }

        .video-panel {
            min-height: 480px;
        }

        .video-container {
            flex-grow: 1;
            display: flex;
            justify-content: center;
            align-items: center;
            background-color: #050505;
            position: relative;
            min-height: 400px;
        }

        .video-stream {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            border-radius: 8px;
            box-shadow: 0 0 30px rgba(0, 0, 0, 0.5);
        }

        .overlay-indicator {
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(0, 0, 0, 0.65);
            backdrop-filter: blur(5px);
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 11px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            align-items: center;
            gap: 6px;
            letter-spacing: 1px;
            font-weight: 600;
        }

        .overlay-indicator::before {
            content: '';
            display: inline-block;
            width: 7px;
            height: 7px;
            background-color: var(--accent-red);
            border-radius: 50%;
            animation: blink 0.8s infinite alternate;
        }

        @keyframes blink {
            from { opacity: 0.2; }
            to { opacity: 1; box-shadow: 0 0 8px var(--accent-red); }
        }

        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 30px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            padding: 24px;
        }

        .stat-card {
            background: rgba(255, 255, 255, 0.015);
            border: 1px solid rgba(255, 255, 255, 0.03);
            border-radius: 14px;
            padding: 16px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .stat-card:hover {
            border-color: rgba(6, 182, 212, 0.3);
            background: rgba(255, 255, 255, 0.03);
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(6, 182, 212, 0.05);
        }

        .stat-label {
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }

        .stat-value {
            font-size: 18px;
            font-weight: 800;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-primary);
        }

        .stat-value.active-state {
            color: var(--accent-cyan);
            font-size: 15px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .stat-value.team-red {
            color: var(--accent-red);
            text-shadow: 0 0 10px rgba(239, 68, 68, 0.3);
        }

        .stat-value.team-blue {
            color: var(--accent-cyan);
            text-shadow: 0 0 10px rgba(6, 182, 212, 0.3);
        }

        .log-panel {
            flex-grow: 1;
            min-height: 250px;
        }

        .log-terminal {
            flex-grow: 1;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 0 0 20px 20px;
            padding: 16px 20px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            line-height: 1.6;
            overflow-y: auto;
            max-height: 320px;
            color: #cbd5e1;
            border-top: 1px solid var(--border-color);
        }

        .log-item {
            margin-bottom: 6px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.015);
            padding-bottom: 4px;
            display: flex;
        }

        .log-time {
            color: var(--accent-purple);
            margin-right: 8px;
            flex-shrink: 0;
        }

        .log-type {
            color: var(--accent-cyan);
            margin-right: 8px;
            font-weight: 700;
            flex-shrink: 0;
        }

        .log-message {
            word-break: break-all;
        }

        footer {
            text-align: center;
            padding: 20px;
            font-size: 12px;
            color: var(--text-secondary);
            border-top: 1px solid var(--border-color);
            margin-top: auto;
            background: rgba(15, 23, 42, 0.1);
        }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <div class="pulse-dot"></div>
            <h1>光启Ray-space智能救援赛项监测端</h1>
        </div>
        <div class="system-info">
            <span>在线时长: <strong id="uptime">0.0s</strong></span>
            <span>当前帧数: <strong id="frame-count">0</strong></span>
        </div>
    </header>

    <div class="container">
        <!-- Video Stream View -->
        <div class="panel video-panel">
            <div class="panel-header">
                <span>实时画面传输 (YOLO 识别与区域标注)</span>
                <span style="color: var(--accent-cyan); font-family: 'JetBrains Mono', monospace;" id="fps-val">FPS: --</span>
            </div>
            <div class="video-container">
                <div class="overlay-indicator">LIVE FEED</div>
                <img class="video-stream" src="/stream.mjpg" alt="等待摄像头数据流传输..." onerror="this.src='https://via.placeholder.com/640x480/020617/cbd5e1/?text=Camera+Stream+Disconnected'">
            </div>
        </div>

        <!-- Sidebar telemetry -->
        <div class="sidebar">
            <div class="panel">
                <div class="panel-header">
                    <span>底盘遥测数据</span>
                </div>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-label">所处队伍</div>
                        <div class="stat-value" id="team-val">--</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">串口命令 (CMD)</div>
                        <div class="stat-value" id="cmd-val">0x00</div>
                    </div>
                    <div class="stat-card" style="grid-column: span 2;">
                        <div class="stat-label">状态机当前状态</div>
                        <div class="stat-value active-state" id="state-val">--</div>
                    </div>
                    <div class="stat-card" style="grid-column: span 2;">
                        <div class="stat-label">爪子当前状态</div>
                        <div class="stat-value" id="claw-val" style="color: var(--accent-green);">--</div>
                    </div>
                </div>
            </div>

            <!-- Event log terminal -->
            <div class="panel log-panel">
                <div class="panel-header">
                    <span>系统运行日志</span>
                    <span style="cursor: pointer; color: var(--accent-cyan); font-size: 11px;" onclick="clearLogs()">清除</span>
                </div>
                <div class="log-terminal" id="log-terminal">
                </div>
            </div>
        </div>
    </div>

    <footer>
        北京建筑大学光启Ray-space工作室 &copy; 2026
    </footer>

    <script>
        let lastState = '';
        let lastClaw = '';
        let lastCmd = '';

        function addLog(type, message) {
            const terminal = document.getElementById('log-terminal');
            const item = document.createElement('div');
            item.className = 'log-item';
            
            const now = new Date();
            const timeStr = now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0');
            
            item.innerHTML = `<span class="log-time">[${timeStr}]</span><span class="log-type">[${type}]</span><span class="log-message">${message}</span>`;
            terminal.appendChild(item);
            terminal.scrollTop = terminal.scrollHeight;
            
            while (terminal.childElementCount > 50) {
                terminal.removeChild(terminal.firstChild);
            }
        }

        function clearLogs() {
            document.getElementById('log-terminal').innerHTML = '';
            addLog('SYSTEM', '日志控制台已清空。');
        }

        function updateTelemetry() {
            fetch('/api/status')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('uptime').textContent = data.uptime;
                    document.getElementById('frame-count').textContent = data.frame_count;
                    document.getElementById('fps-val').textContent = `FPS: ${data.fps.toFixed(1)}`;
                    
                    // Team color mapping
                    const teamVal = document.getElementById('team-val');
                    teamVal.textContent = data.team.toUpperCase();
                    if (data.team.toLowerCase() === 'red') {
                        teamVal.className = 'stat-value team-red';
                    } else if (data.team.toLowerCase() === 'blue') {
                        teamVal.className = 'stat-value team-blue';
                    } else {
                        teamVal.className = 'stat-value';
                    }

                    // Hex cmd conversion
                    let hexCmd = '0x' + Number(data.cmd).toString(16).toUpperCase().padStart(2, '0');
                    document.getElementById('cmd-val').textContent = hexCmd;

                    // State display
                    document.getElementById('state-val').textContent = data.state;

                    // Claw State
                    const clawVal = document.getElementById('claw-val');
                    clawVal.textContent = data.claw_state.toUpperCase();
                    if (data.claw_state.toLowerCase() === 'close') {
                        clawVal.style.color = 'var(--accent-red)';
                    } else {
                        clawVal.style.color = 'var(--accent-green)';
                    }

                    // Smart event logs on transitions
                    if (data.state !== lastState) {
                        if (lastState !== '') {
                            addLog('STATE', `状态转换: ${lastState} &rarr; ${data.state}`);
                        } else {
                            addLog('SYSTEM', `系统开始监控。当前状态: ${data.state}`);
                        }
                        lastState = data.state;
                    }

                    if (data.claw_state !== lastClaw) {
                        if (lastClaw !== '') {
                            addLog('CLAW', `爪子状态: ${lastClaw} &rarr; ${data.claw_state}`);
                        }
                        lastClaw = data.claw_state;
                    }

                    if (hexCmd !== lastCmd) {
                        if (lastCmd !== '') {
                            addLog('UART', `下位机按键指令更改: ${hexCmd}`);
                        }
                        lastCmd = hexCmd;
                    }
                })
                .catch(err => {
                    console.error('Error fetching robot telemetry:', err);
                });
        }

        addLog('SYSTEM', '监测面板初始化完成，等待后台接收数据...');
        updateTelemetry();
        setInterval(updateTelemetry, 250);
    </script>
</body>
</html>
"""


def update_frame(frame: cv2.Mat):
    """
    更新最新画面帧（由主循环调用）
    """
    global _latest_frame, _last_frame_time, _status_data
    current_time = time.time()
    
    with _frame_lock:
        _latest_frame = frame.copy()
        
    with _status_lock:
        _status_data["frame_count"] += 1
        
        # 估算并滤波平滑当前帧率 (FPS)
        if _last_frame_time > 0:
            diff = current_time - _last_frame_time
            if diff > 0:
                instant_fps = 1.0 / diff
                # 平滑滤波
                _status_data["fps"] = 0.9 * _status_data["fps"] + 0.1 * instant_fps
        _last_frame_time = current_time


def update_status(state: str, claw_state: str, cmd: int, team: str):
    """
    更新机器人当前运行状态和遥测属性
    """
    global _status_data
    with _status_lock:
        _status_data["state"] = state
        _status_data["claw_state"] = claw_state
        _status_data["cmd"] = cmd
        _status_data["team"] = team
        _status_data["last_update"] = time.time()


def start_server(host: str = '0.0.0.0', port: int = 8080):
    """
    启动后台网络画面传输和遥测服务器
    """
    global _server_instance, _server_thread
    
    if _server_instance is not None:
        return
        
    def run():
        global _server_instance
        try:
            _server_instance = ThreadedHTTPServer((host, port), StreamingHandler)
            print(f"[WEB] 画面传输服务器启动成功，访问地址: http://{host}:{port}")
            _server_instance.serve_forever()
        except Exception as e:
            print(f"[WEB] 画面传输服务器启动失败: {e}")
            
    _server_thread = threading.Thread(target=run, daemon=True)
    _server_thread.start()


def stop_server():
    """
    停止画面传输服务器
    """
    global _server_instance, _server_thread
    if _server_instance is not None:
        print("[WEB] 正在停止画面传输服务器...")
        _server_instance.shutdown()
        _server_instance.server_close()
        _server_instance = None
    if _server_thread is not None:
        _server_thread.join(timeout=1.0)
        _server_thread = None
        print("[WEB] 服务器已停止")
