#!/usr/bin/env python3
"""Gate a command behind the declared-vs-effective configuration check.

Runs check_config.py first and only launches the wrapped command when the
declared fields match. Exit codes: the command's own status after a pass;
1 when conditions mismatch or a field is missing; 2 when inputs are invalid,
the receipt cannot be written, or no command was given. The gate never edits
inputs and cannot authenticate where the effective export came from.
"""
import argparse
from pathlib import Path
import subprocess
import sys

CHECKER = Path(__file__).with_name("check_config.py")


def write(message):
    sys.stderr.write(message + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--expected", required=True, type=Path,
                        help="本次实验的声明（含 experiment_id 与非空 changes）")
    parser.add_argument("--effective", required=True, type=Path,
                        help="真实执行入口导出的最终生效配置")
    parser.add_argument("--receipt", type=Path,
                        help="检查报告另存为新文件；拒绝覆盖旧报告")
    parser.add_argument("--export-cmd",
                        help="先执行该 shell 命令生成 --effective；失败则不检查也不启动")
    parser.add_argument("command", nargs=argparse.REMAINDER,
                        help="通过后用 `--` 分隔的启动命令")
    args = parser.parse_args(argv)

    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        write("错误: 缺少启动命令；只做核验请直接调用 check_config.py")
        return 2
    if not CHECKER.is_file():
        write("错误: 找不到同目录的 check_config.py")
        return 2

    if args.export_cmd:
        exported = subprocess.run(args.export_cmd, shell=True)
        if exported.returncode != 0:
            write("门禁未通过: 生效配置导出失败（退出码 %d），未启动命令"
                  % exported.returncode)
            return 2

    check = [sys.executable, str(CHECKER), "--expected", str(args.expected),
             "--effective", str(args.effective)]
    if args.receipt:
        check += ["--receipt", str(args.receipt)]
    verified = subprocess.run(check)
    if verified.returncode != 0:
        code = verified.returncode if verified.returncode in (1, 2) else 2
        write("门禁未通过（退出码 %d），未启动命令" % code)
        return code

    write("门禁通过；启动命令")
    started = subprocess.run(command)
    if started.returncode < 0:  # terminated by a signal
        return 128 - started.returncode
    return started.returncode


if __name__ == "__main__":
    sys.exit(main())
