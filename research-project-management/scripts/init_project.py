#!/usr/bin/env python3
"""Initialize a new POSIX research workspace without dependencies or overwrites."""
import argparse
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if os.name != "posix":
        parser.error("仅支持 Linux/macOS（POSIX 文件锁）；当前平台不受支持")
    if not args.name.strip() or "\n" in args.name or "\r" in args.name:
        parser.error("--name 必须是非空单行文本")
    target = args.target.expanduser().absolute()
    source = Path(__file__).resolve().parents[1] / "assets" / "project"
    files = sorted(path for path in source.rglob("*")
                   if path.is_file() and "__pycache__" not in path.parts
                   and path.suffix not in (".pyc", ".pyo"))
    if not files:
        parser.error("技能缺少 assets/project 模板")
    checker = Path(__file__).with_name("check_config.py")
    gate = Path(__file__).with_name("run_with_gate.py")
    skill = Path(__file__).resolve().parents[1] / "SKILL.md"
    if not checker.is_file():
        parser.error("技能缺少 scripts/check_config.py")
    if not gate.is_file():
        parser.error("技能缺少 scripts/run_with_gate.py")
    try:
        declared = re.search(r"^version:\s*(\S+)\s*$", skill.read_text(encoding="utf-8"), re.M)
    except OSError as exc:
        parser.error("无法读取 SKILL.md 版本: %s" % exc)
    if not declared:
        parser.error("SKILL.md 缺少 version")
    version = declared.group(1)
    sources = [(path, path.relative_to(source)) for path in files]
    sources.append((checker, Path("tools/check_config.py")))
    sources.append((gate, Path("tools/run_with_gate.py")))
    # Refuse the entire operation before making even a temporary directory.
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        parser.error("目标不是可初始化的普通目录: %s" % target)
    if target.exists() and any(target.iterdir()):
        parser.error("目标非空，整批拒绝；请使用新目录，既有项目只能显式增量迁移")
    parent = target.parent
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    if not parent.is_dir():
        parser.error("目标父路径不是目录: %s" % parent)
    print("%s: %s" % ("预览（不写入）" if args.dry_run else "初始化", target))
    for _, relative in sources:
        print("  " + relative.as_posix())
    if args.dry_run:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".research-init-", dir=str(target.parent)))
    try:
        for path, relative in sources:
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            text = (path.read_text(encoding="utf-8")
                    .replace("{{PROJECT_NAME}}", args.name)
                    .replace("{{SKILL_VERSION}}", version))
            destination.write_text(text, encoding="utf-8")
        # Recheck after staging; rename cannot replace a nonempty directory.
        if target.is_symlink() or (target.exists() and
                                  (not target.is_dir() or any(target.iterdir()))):
            parser.error("目标在初始化期间出现冲突；未写入目标")
        os.rename(str(stage), str(target))
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    print("完成；命令仅建档，训练不会自动启动。")


if __name__ == "__main__":
    try:
        main()
    except OSError as exc:
        print("初始化失败: %s" % exc, file=sys.stderr)
        sys.exit(1)
