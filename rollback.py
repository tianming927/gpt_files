import paramiko, json, os

# 配置与 deploy.py 一致
SERVER_IP = "113.45.76.90"
SSH_USER = "root"
SSH_PWD = "HAIer19930927"
REMOTE_DIR = "/www/wwwroot/113.45.76.90_8001"


def rollback(target_version):
    print(f"⏪ 正在尝试回滚至版本: {target_version}...")

    # 构建回滚所需的 JSON 数据
    version_data = {
        "latest_version": target_version,
        "download_url": f"http://{SERVER_IP}:8001/history/update_{target_version}.zip",
        "update_log": "管理员执行了版本回滚，正在恢复至稳定版本。",
        "force_update": True
    }

    local_json = "rollback_version.json"
    with open(local_json, 'w', encoding='utf-8') as f:
        json.dump(version_data, f, ensure_ascii=False, indent=2)

    try:
        t = paramiko.Transport((SERVER_IP, 22))
        t.connect(username=SSH_USER, password=SSH_PWD)
        sftp = paramiko.SFTPClient.from_transport(t)

        # 检查该历史包是否存在
        remote_zip = f"{REMOTE_DIR}/history/update_{target_version}.zip"
        try:
            sftp.stat(remote_zip)
            # 覆盖根目录的 version.json，诱导客户端“更新”回旧版
            sftp.put(local_json, f"{REMOTE_DIR}/version.json")
            print(f"✅ 回滚成功！线上环境已切换回 {target_version}")
        except FileNotFoundError:
            print(f"❌ 回滚失败：服务器 history 目录下找不到 update_{target_version}.zip")

        sftp.close();
        t.close()
    except Exception as e:
        print(f"❌ 连接失败: {e}")


if __name__ == "__main__":
    ver = input("请输入要回滚的目标版本号 (例如 1.0.3): ")
    rollback(ver)