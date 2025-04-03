"""
MiniLuma Web界面启动脚本
用于快速启动MiniLuma的Web界面服务
"""
import os
import sys
import argparse
import threading
import webbrowser
import time
import requests
import asyncio
from requests.exceptions import ConnectionError

# 添加项目根目录到PATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入Web服务器模块
from ui.web.server import run_web_server
from api.api_server import start_api_server

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='启动MiniLuma Web界面')
    parser.add_argument('--web-host', default='0.0.0.0', help='Web服务器主机地址 (默认: 0.0.0.0)')
    parser.add_argument('--web-port', type=int, default=9787, help='Web服务器端口 (默认: 9787)')
    parser.add_argument('--api-host', default='0.0.0.0', help='API服务器主机地址 (默认: 0.0.0.0)')
    parser.add_argument('--api-port', type=int, default=9788, help='API服务器端口 (默认: 9788)')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    return parser.parse_args()

def open_browser(host, port, delay=2):
    """延迟几秒后打开浏览器"""
    def _open_browser():
        time.sleep(delay)
        url = f"http://localhost:{port}" if host in ['0.0.0.0', '127.0.0.1'] else f"http://{host}:{port}"
        webbrowser.open(url)
    
    browser_thread = threading.Thread(target=_open_browser)
    browser_thread.daemon = True
    browser_thread.start()

def start_api_server_thread(host, port, debug=False):
    """在单独的线程中启动API服务器"""
    def _start_api():
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行异步API服务器
            loop.run_until_complete(start_api_server(host=host, port=port, workers=1, use_signals=False))
            loop.run_forever()
        except Exception as e:
            print(f"API服务器启动失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
    
    api_thread = threading.Thread(target=_start_api)
    api_thread.daemon = True
    api_thread.start()
    print(f"正在尝试启动API服务器: http://{host}:{port}")
    return api_thread

def wait_for_api_server(host, port, max_retries=10, retry_interval=1):
    """等待API服务器启动完成，返回是否成功连接"""
    api_url = f"http://{host if host != '0.0.0.0' else 'localhost'}:{port}/health"
    retry_count = 0
    
    print("等待API服务器就绪...")
    while retry_count < max_retries:
        try:
            response = requests.get(api_url, timeout=2)
            if response.status_code == 200:
                print("API服务器已就绪")
                return True
        except ConnectionError:
            pass
        except Exception as e:
            print(f"连接API服务器时发生错误: {str(e)}")
        
        retry_count += 1
        if retry_count < max_retries:
            print(f"等待API服务器就绪 (重试 {retry_count}/{max_retries})...")
            time.sleep(retry_interval)
    
    print("无法连接到API服务器，请确保API服务器已经启动")
    return False

def main():
    """主函数，启动Web服务和API服务"""
    args = parse_arguments()
    
    # 打印欢迎信息
    print("+--------------------------------------+")
    print("|       MiniLuma Web界面启动器        |")
    print("+--------------------------------------+")
    print(f"| 版本: 1.0.0                         |")
    print(f"| Web服务: http://localhost:{args.web_port} |")
    print(f"| API服务: http://localhost:{args.api_port} |")
    print("+--------------------------------------+")
    
    # 检查目录结构
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "results")
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        print(f"创建results目录: {results_dir}")
    
    # 先检查API服务器是否已经在运行
    api_url = f"http://localhost:{args.api_port}/health"
    try:
        requests.get(api_url, timeout=1)
        print("API服务器已在运行")
        api_running = True
    except Exception:
        # API服务器未运行，需要启动
        print("API服务器未运行，正在启动...")
        api_thread = start_api_server_thread(args.api_host, args.api_port, args.debug)
        
        # 等待API服务器启动
        api_running = wait_for_api_server("localhost", args.api_port)
    
    if not api_running:
        print("警告: API服务器可能未正确启动，Web界面可能无法正常工作")
        user_input = input("是否仍要继续启动Web界面? (y/n): ")
        if user_input.lower() != 'y':
            print("已取消启动")
            sys.exit(1)
    
    # 如果需要，启动浏览器
    if not args.no_browser:
        open_browser(args.web_host, args.web_port)
        print("Web界面将在浏览器中自动打开...")
    
    # 启动Web服务器（这会阻塞当前线程）
    print("正在启动Web服务器...")
    run_web_server(host=args.web_host, port=args.web_port, debug=args.debug)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n接收到中断信号，停止服务...")
        sys.exit(0)
