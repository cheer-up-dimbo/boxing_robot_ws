"""Start dashboard server with localhost.run tunnel and QR code."""
import subprocess
import socket
import time
import sys
import os
import logging

logger = logging.getLogger(__name__)

WS = '/home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws'
URL_FILE = '/tmp/boxbunny_dashboard_url.txt'
os.chdir(WS)


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return 'localhost'


def start_server() -> subprocess.Popen:
    env = os.environ.copy()
    # Include ROS paths so rclpy is available for direct height publishing
    ros_python = '/opt/ros/humble/lib/python3.10/dist-packages'
    ros_local = '/opt/ros/humble/local/lib/python3.10/dist-packages'
    ws_install = f'{WS}/install/local/lib/python3.10/dist-packages'
    env['PYTHONPATH'] = (
        f'{WS}/src/boxbunny_dashboard:'
        f'{WS}/src/boxbunny_core:'
        f'{WS}/install/boxbunny_msgs/local/lib/python3.10/dist-packages:'
        f'{ros_python}:{ros_local}:{ws_install}:'
        + env.get('PYTHONPATH', '')
    )
    # Ensure ROS middleware libs are findable
    ros_lib = '/opt/ros/humble/lib'
    env['LD_LIBRARY_PATH'] = (
        f'{ros_lib}:' + env.get('LD_LIBRARY_PATH', '')
    )
    proc = subprocess.Popen(
        [sys.executable, '-c',
         'import uvicorn; '
         'from boxbunny_dashboard.server import create_app; '
         'uvicorn.run(create_app(), host="0.0.0.0", port=8080, '
         'log_level="warning")'],
        env=env,
    )
    time.sleep(2)
    if proc.poll() is not None:
        raise RuntimeError('Server failed to start. Check dependencies.')
    return proc


def start_tunnel() -> tuple[subprocess.Popen, str | None]:
    """Start localhost.run SSH tunnel with retry. Returns (process, url)."""
    for attempt in range(3):
        if attempt > 0:
            print(f'Tunnel retry {attempt + 1}/3...')
            time.sleep(2)

        proc = subprocess.Popen(
            ['ssh', '-o', 'StrictHostKeyChecking=no',
             '-o', 'ServerAliveInterval=30',
             '-o', 'ConnectTimeout=10',
             '-R', '80:localhost:8080', 'nokey@localhost.run'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )

        deadline = time.time() + 20
        while time.time() < deadline:
            line = proc.stdout.readline().decode('utf-8', errors='ignore')
            if not line:
                break
            if '.lhr.life' in line:
                for word in line.split():
                    if word.startswith('https://'):
                        return proc, word.strip().rstrip(',')

        # Failed this attempt - kill and retry
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

    return None, None


def show_qr(url: str) -> None:
    try:
        import qrcode
        from IPython.display import display, Image as IPImage
        from io import BytesIO
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='white', back_color='#0A0A0A')
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        print('Scan with your phone:')
        display(IPImage(data=buf.read(), width=350))
    except Exception:
        print(f'Open: {url}')


def _server_already_running() -> bool:
    """Check if the dashboard is already listening on port 8080."""
    try:
        import urllib.request
        urllib.request.urlopen('http://localhost:8080/api/health', timeout=2)
        return True
    except Exception:
        return False


def main() -> None:
    os.system('pkill -f localhost.run 2>/dev/null')
    time.sleep(1)

    ip = get_local_ip()

    # Reuse the server started by the ROS launch if it's already up
    server = None
    if _server_already_running():
        print('Dashboard server already running on :8080 (from launch)')
    else:
        os.system('fuser -k 8080/tcp 2>/dev/null')
        time.sleep(0.5)
        server = start_server()
        print(f'Server started (PID {server.pid})')
    print(f'Local: http://{ip}:8080')
    print()

    tunnel, tunnel_url = start_tunnel()

    print('=' * 50)
    if tunnel_url:
        print(f'PUBLIC URL: {tunnel_url}')
        print(f'(also local: http://{ip}:8080)')
    else:
        print(f'Tunnel failed - using LOCAL only: http://{ip}:8080')
        print('Phone must be on the same WiFi network.')
    print('=' * 50)
    print('Logins: alex/boxing123 | maria/boxing123 '
          '| jake/boxing123 | sarah/coaching123')
    print()

    active_url = tunnel_url or f'http://{ip}:8080'

    # Write URL to shared file so the GUI QR popup can use it
    try:
        with open(URL_FILE, 'w') as f:
            f.write(active_url)
    except OSError as exc:
        logger.warning('Could not write URL file: %s', exc)

    show_qr(active_url)

    print()
    print('=' * 50)
    print('RUNNING — Press STOP to shut down')
    print('=' * 50)

    try:
        if server:
            server.wait()
        else:
            # Keep alive until interrupted (server managed by launch)
            import signal
            signal.pause()
    except KeyboardInterrupt:
        pass
    finally:
        if tunnel:
            tunnel.terminate()
            try:
                tunnel.wait(timeout=3)
            except Exception:
                tunnel.kill()
        if server:
            server.terminate()
            try:
                server.wait(timeout=3)
            except Exception:
                server.kill()
            os.system('fuser -k 8080/tcp 2>/dev/null')
        os.system('pkill -f localhost.run 2>/dev/null')
        try:
            os.remove(URL_FILE)
        except OSError:
            pass
        print('\nTunnel stopped.')


if __name__ == '__main__':
    main()
