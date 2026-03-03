# -*- coding: utf-8 -*-
import subprocess
import os
import datetime


def run_git_command(command, cwd=None):
    """执行 git 命令"""
    try:
        result = subprocess.run(
            command, cwd=cwd, shell=True,
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Git 命令失败: {command}")
        print(e.stderr)
        return False


def auto_commit(repo_path):
    """
    检查本地未提交修改，如果有则自动添加并提交
    """
    print("📝 检查本地未提交修改...")
    # 查看修改状态
    result = subprocess.run("git status --porcelain", cwd=repo_path, shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.stdout.strip():
        print("⚠️ 本地有未提交修改，正在自动提交...")
        run_git_command("git add .", cwd=repo_path)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        run_git_command(f'git commit -m "Auto commit {timestamp}"', cwd=repo_path)
        print("✅ 本地修改已提交")
    else:
        print("✅ 本地没有未提交修改")


def backup_remote(repo_path, backup_root):
    """
    备份远程仓库到本地指定目录
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_root, f"backup_{timestamp}")
    os.makedirs(backup_path, exist_ok=True)

    print(f"📦 正在备份远程仓库到 {backup_path} ...")
    # 获取远程 URL
    remote_url_result = subprocess.run(
        "git config --get remote.origin.url",
        cwd=repo_path,
        shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    remote_url = remote_url_result.stdout.strip()
    if not remote_url:
        print("❌ 无法获取远程仓库 URL，备份失败")
        return False

    run_git_command(f"git clone {remote_url} {backup_path}")
    print("✅ 远程仓库备份完成")
    return True


def git_pull_force(repo_path):
    """
    拉取远程代码，如果失败则用远程状态重置本地
    """
    print("🔄 尝试拉取远程仓库...")
    success = run_git_command("git pull --rebase origin main", cwd=repo_path)
    if not success:
        print("⚠️ 拉取失败，可能有冲突，尝试重置本地仓库到远程状态...")
        run_git_command("git fetch origin", cwd=repo_path)
        run_git_command("git reset --hard origin/main", cwd=repo_path)
        print("✅ 已重置本地仓库")


def git_push_force(repo_path):
    """
    推送本地代码到远程，如果失败则强制覆盖
    """
    print("📤 尝试推送本地代码到远程...")
    success = run_git_command("git push origin main", cwd=repo_path)
    if not success:
        print("⚠️ 推送失败，尝试强制覆盖远程...")
        run_git_command("git push -f origin main", cwd=repo_path)
    print("✅ 推送完成")


def main():
    # 仓库路径，改成你的本地仓库
    repo_path = r"C:\Users\11598\PycharmProjects\pythonProject\.project\gpt_git_files"
    # 备份目录，可以改成你希望存放备份的位置
    backup_root = r"C:\Users\11598\PycharmProjects\pythonProject\.project\gpt_git_backups"

    if not os.path.isdir(repo_path):
        print(f"❌ 仓库路径不存在: {repo_path}")
        return

    # 自动提交本地修改
    auto_commit(repo_path)

    # 先备份远程仓库
    backup_remote(repo_path, backup_root)

    # 拉取远程更新
    git_pull_force(repo_path)

    # 推送本地提交（必要时强制覆盖远程）
    git_push_force(repo_path)


if __name__ == "__main__":
    main()