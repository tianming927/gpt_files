# -*- coding: utf-8 -*-
import os, zipfile, json, paramiko, shutil, py_compile

# --- 配置信息 ---
SERVER_IP = "113.45.76.90"
SSH_USER = "root"
SSH_PWD = "HAIer19930927"
REMOTE_DIR = "/www/wwwroot/113.45.76.90_8001"
# 你的本地开发模块目录
LOCAL_MODULES_DIR = r"C:\Users\11598\PycharmProjects\pythonProject\.project\cloud_sevices\modules"

# 每次发布前修改这两个值
NEW_VERSION = "2.0.2"  # 确保这个版本号高于服务器上的版本
UPDATE_LOG = f"新版本{NEW_VERSION}发布。"

# 需要加密发布的模块列表（不含.py后缀）
PROTECT_MODULES = ["pdf_module", "tax_module", "rd_module"]


def deploy():
    # 1. 准备本地打包
    zip_name = f"update_{NEW_VERSION}.zip"
    # 获取 deploy.py 所在的当前目录，用于存放临时编译文件
    current_work_dir = os.path.dirname(os.path.abspath(__file__))
    temp_pyc_files = []

    print(f"🚀 开始发布版本: {NEW_VERSION}")

    try:
        # 创建压缩包
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as z:
            for m in PROTECT_MODULES:
                source_py = os.path.join(LOCAL_MODULES_DIR, f"{m}.py")
                if not os.path.exists(source_py):
                    print(f"⚠️ 找不到源文件: {source_py}，跳过该模块")
                    continue

                # 编译 py 为 pyc
                # 显式指定 cfile 的完整路径到当前目录下
                pyc_filename = f"{m}.pyc"
                pyc_full_path = os.path.join(current_work_dir, pyc_filename)

                print(f"📦 正在编译字节码: {m}...")
                py_compile.compile(source_py, cfile=pyc_full_path)
                temp_pyc_files.append(pyc_full_path)

                # 【关键修复】：将编译好的 pyc 写入压缩包
                # arcname 是在压缩包里的名字，main.py 加载时会找这个名字
                z.write(pyc_full_path, arcname=pyc_filename)

        # 2. 准备版本 JSON
        version_data = {
            "latest_version": NEW_VERSION,
            "download_url": f"http://{SERVER_IP}:8001/history/{zip_name}",
            "update_log": UPDATE_LOG,
            "force_update": True
        }
        with open("version.json", 'w', encoding='utf-8') as f:
            json.dump(version_data, f, ensure_ascii=False, indent=2)

        # 3. 上传服务器
        print(f"📡 正在连接服务器 {SERVER_IP}...")
        t = paramiko.Transport((SERVER_IP, 22))
        t.connect(username=SSH_USER, password=SSH_PWD)
        sftp = paramiko.SFTPClient.from_transport(t)

        # 确保服务器目录存在
        try:
            sftp.mkdir(f"{REMOTE_DIR}/history")
        except:
            pass

        print(f"📤 正在上传压缩包 {zip_name}...")
        sftp.put(zip_name, f"{REMOTE_DIR}/history/{zip_name}")

        print(f"📤 正在同步 version.json...")
        sftp.put("version.json", f"{REMOTE_DIR}/version.json")

        sftp.close()
        t.close()
        print(f"✅ 发布成功！版本号：{NEW_VERSION}")

    except Exception as e:
        print(f"❌ 部署失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 4. 清理本地临时文件
        print("🧹 清理临时编译文件...")
        for f in temp_pyc_files:
            if os.path.exists(f): os.remove(f)
        # 如果你想保留打包好的 zip，可以注释掉下面这行
        # if os.path.exists(zip_name): os.remove(zip_name)


if __name__ == "__main__":
    deploy()