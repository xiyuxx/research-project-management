#!/usr/bin/env python3
"""Portable scalar-front-matter research ledger; never launches commands."""
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import date
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import quote


def configure_output():
    """Emit UTF-8 regardless of the console codepage; never crash on CJK."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            pass


configure_output()


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "experiments"
STATUSES = ("planned", "running", "done", "blocked", "abandoned")
LOCK_BACKENDS = ("flock", "sqlite")
REPEATED = {"next", "next_done", "constraint", "question", "decision"}
RECORD = re.compile(r"^EXP-(\d{4,})-(.+)\.md$")
GROUP = re.compile(r"^GRP-(\d{3,})-([a-z0-9]+(?:-[a-z0-9]+)*)$")
KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


def fail(message):
    raise ValueError(message)


def scalar(value):
    if "\n" in value or "\r" in value or "\x00" in value:
        fail("front matter 值必须为单行标量")
    return value.strip()


def values(fm, key):
    value = fm.get(key, [])
    return list(value) if isinstance(value, list) else [value]


def append(fm, key, items):
    items = [scalar(item) for item in items]
    if any(not item for item in items):
        fail("重复字段不能追加空值")
    fm[key] = values(fm, key) + items


def parse(path):
    text = path.read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not match:
        fail("%s: 缺少 front matter" % path)
    fm = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not sep or not KEY.fullmatch(key):
            fail("%s: 非标量键值行 %r" % (path, line))
        if value:
            if key in fm:
                fm[key] = values(fm, key) + [value]
            else:
                fm[key] = value
    return fm, text[match.end():]


def render(fm, body):
    lines = ["---"]
    for key, value in fm.items():
        if not KEY.fullmatch(key):
            fail("无效字段名: %s" % key)
        for item in value if isinstance(value, list) else [value]:
            lines.append("%s: %s" % (key, scalar(item)))
    return "\n".join(lines + ["---", ""]) + body


def atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".ledger-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content if isinstance(content, bytes) else content.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, str(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def lock_backend():
    """Linux/macOS use flock; Windows uses a SQLite write transaction.

    flock is the native POSIX advisory lock: kernel-level, released on process
    death, no extra file beyond the lock handle. Windows has no flock
    equivalent in the standard library; msvcrt.locking only locks a byte range
    and gives up after a short fixed retry, so this uses SQLite's blocking
    BEGIN IMMEDIATE instead. RESEARCH_LOCK=flock|sqlite overrides the routing
    (tests use it to exercise both paths on one machine).
    """
    chosen = os.environ.get("RESEARCH_LOCK", "auto")
    if chosen == "auto":
        chosen = "sqlite" if os.name == "nt" else "flock"
    if chosen not in LOCK_BACKENDS:
        fail("RESEARCH_LOCK 只能是 auto、flock 或 sqlite: " + chosen)
    return chosen


@contextmanager
def locked():
    if lock_backend() == "flock":
        try:
            import fcntl
        except ImportError:
            fail("当前平台没有 fcntl；请使用 RESEARCH_LOCK=sqlite")
        with (LEDGER / ".ledger.lock").open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
        return
    import sqlite3
    connection = sqlite3.connect(str(LEDGER / ".ledger.lock.db"), timeout=30)
    try:
        try:
            connection.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            fail("等待台账写锁超时（sqlite）: %s" % exc)
        yield
        connection.commit()
    finally:
        connection.close()


def groups():
    result, seen = [], set()
    for path in sorted(LEDGER.glob("GRP-*")):
        match = GROUP.fullmatch(path.name)
        if not match or path.is_symlink() or not path.is_dir():
            fail("无法识别或冲突的研究组路径: %s" % path)
        number = int(match.group(1))
        if number < 1 or path.name.split("-", 2)[0:2] != ["GRP", "%03d" % number] or number in seen:
            fail("研究组编号无效或重复: %s" % path)
        if not (path / "README.md").is_file():
            fail("研究组缺少 README.md: %s" % path)
        seen.add(number)
        result.append(path)
    return result


def next_number(counter, used):
    minimum = max(used, default=0) + 1
    if not counter.exists():
        return minimum
    value = counter.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[1-9][0-9]*", value):
        fail("编号高水位标记损坏: %s" % counter)
    return max(minimum, int(value))


def normalize_slug(value):
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        fail("slug 至少需要一个 ASCII 字母或数字")
    return slug


def group_new(args):
    slug = normalize_slug(args.slug)
    title = scalar(args.title)
    if not title:
        fail("研究组标题不能为空")
    with locked():
        existing = groups()
        counter = LEDGER / ".next-group-id"
        number = next_number(counter, [int(GROUP.fullmatch(p.name).group(1)) for p in existing])
        path = LEDGER / ("GRP-%03d-%s" % (number, slug))
        if path.exists() or path.is_symlink():
            fail("研究组路径冲突: %s" % path)
        atomic(counter, str(number + 1) + "\n")
        template = (LEDGER / "_group_template.md").read_text(encoding="utf-8-sig")
        text = re.sub(r"\A# [^\n]*", lambda _: "# " + title, template, count=1)
        if "<!-- ledger:group:start -->" not in text or "<!-- ledger:group:end -->" not in text:
            fail("研究组模板缺少生成区标记")
        with tempfile.TemporaryDirectory(prefix=".group-", dir=str(LEDGER)) as temporary:
            staged = Path(temporary) / path.name
            staged.mkdir()
            atomic(staged / "README.md", text)
            os.rename(staged, path)
    print(path.relative_to(ROOT))


def group_path(identifier, existing):
    match = re.fullmatch(r"GRP-(\d{3,})(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?", identifier)
    if not match:
        fail("无效研究组: " + identifier)
    number = int(match.group(1))
    matches = [path for path in existing if int(GROUP.fullmatch(path.name).group(1)) == number]
    if len(matches) != 1 or ("-" in identifier[4:] and matches[0].name != identifier):
        fail("未找到研究组: " + identifier)
    return matches[0]


def records():
    result, seen = [], set()
    paths = list(LEDGER.glob("EXP-*.md"))
    for group in groups():
        paths.extend(group.glob("EXP-*.md"))
    for path in sorted(paths):
        match = RECORD.fullmatch(path.name)
        if not match:
            fail("无法识别实验文件名: %s" % path.name)
        fm, body = parse(path)
        expected = "EXP-%04d" % int(match.group(1))
        if fm.get("id") != expected or expected in seen:
            fail("实验编号与文件名不符或重复: %s" % path.name)
        for key in ("id", "slug", "status", "review_status", "run_dir"):
            if isinstance(fm.get(key), list):
                fail("%s: %s 必须为单一标量" % (path.name, key))
        seen.add(expected)
        result.append((path, fm, body))
    return sorted(result, key=lambda row: int(row[1]["id"].split("-")[1]))


def find(rows, identifier):
    number = re.sub(r"^EXP-", "", identifier.upper())
    if not number.isdigit():
        fail("无效 EXP 编号: %s" % identifier)
    name = "EXP-%04d" % int(number)
    for row in rows:
        if row[1]["id"] == name:
            return row
    fail("未找到 " + name)


def region(text, kind, content):
    start, end = "<!-- ledger:%s:start -->" % kind, "<!-- ledger:%s:end -->" % kind
    if start not in text and end not in text:
        return text.rstrip() + "\n\n" + start + "\n" + content.rstrip() + "\n" + end + "\n"
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) > text.index(end):
        fail("%s 生成区标记不完整/重复；未写入，请先人工修复" % kind)
    left = text.index(start) + len(start)
    right = text.index(end)
    return text[:left] + "\n" + content.rstrip() + "\n" + text[right:]


def table(value):
    if isinstance(value, list):
        value = "; ".join(value)
    return str(value).replace("|", "\\|").replace("\n", " ")


def derived(rows):
    index = ["# 实验索引（派生）", "", "权威记录是 EXP-*.md；执行 done 不等于科研解释闭环。", "",
             "| EXP | 标题 | 执行状态 | 人工解释 | question | decision |",
             "| --- | --- | --- | --- | --- | --- |"]
    pending = ["# 后续工作（派生）", "", "next 是开放任务；next_done 是完成记录；constraint 是边界。done 不会自动清空 next。", ""]
    registry = []
    for path, fm, _ in rows:
        index.append("| [%s](%s) | %s | %s | %s | %s | %s |" % (
            fm["id"], quote(path.relative_to(LEDGER).as_posix()), table(fm.get("title", "")), table(fm.get("status", "未记录")),
            table(fm.get("review_status", "pending（未记录）")), table(fm.get("question", "")),
            table(fm.get("decision", ""))))
        registry.append(dict(fm, record=path.relative_to(ROOT).as_posix()))
        pending.extend(["## [%s](%s)" % (fm["id"], quote(path.relative_to(LEDGER).as_posix())), ""])
        for key, label in (("next", "开放"), ("next_done", "完成"), ("constraint", "边界")):
            for item in values(fm, key):
                pending.append("- %s：%s" % (label, item))
        pending.extend(["- 人工解释：%s" % fm.get("review_status", "pending（未记录）"), ""])
    if not rows:
        index.extend(["", "尚无实验记录。"])
        pending.append("尚无实验记录；没有派生任务。")
    counts = Counter(fm.get("status", "未记录") for _, fm, _ in rows)
    summary = ["台账实验数：%d。此摘要不是进程存活检查。" % len(rows)]
    summary.extend("- %s：%d" % item for item in sorted(counts.items()))
    summary.append("- 人工解释待闭环：%d" % sum(fm.get("review_status", "pending") != "done" for _, fm, _ in rows))
    current_path = ROOT / "CURRENT.md"
    current = current_path.read_text(encoding="utf-8-sig")
    documents = {
        LEDGER / "INDEX.md": "\n".join(index) + "\n",
        LEDGER / "NEXT.md": "\n".join(pending) + "\n",
        LEDGER / "registry.json": json.dumps({"schema_version": 1, "experiments": registry}, ensure_ascii=False, indent=2) + "\n",
        current_path: region(current, "current", "\n".join(summary)),
    }
    for group in groups():
        readme = group / "README.md"
        links = ["- [%s](%s)［%s］%s" % (
            path.stem, quote(path.name), fm.get("status", "未记录"), table(fm.get("title", "")))
                 for path, fm, _ in rows if path.parent == group]
        documents[readme] = region(readme.read_text(encoding="utf-8-sig"), "group",
                                   "\n".join(links) if links else "尚无实验记录。")
    return documents


def write_derived(documents):
    for path, text in documents.items():
        atomic(path, text)


def validate(fm):
    if fm.get("status") not in STATUSES:
        fail("status 必须是 " + ", ".join(STATUSES))
    if fm.get("review_status", "pending") not in ("pending", "done"):
        fail("review_status 必须是 pending 或 done")


def configuration(fm, record_path):
    """Return a real immutable snapshot, never a synthetic config."""
    if not fm.get("config"):
        fm.pop("config_hash", None)
        fm.pop("config_snapshot", None)
        return None
    code = Path(fm.get("code", ".")).expanduser()
    code = code if code.is_absolute() else ROOT / code
    config = Path(fm["config"]).expanduser()
    config = config if config.is_absolute() else code / config
    if not config.is_file():
        fail("真实配置文件不存在: %s" % config)
    content = config.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    destination = record_path.with_suffix("") / ("config-" + digest + ".snapshot")
    fm["config_hash"] = digest
    fm["config_snapshot"] = destination.relative_to(ROOT).as_posix()
    return destination, content
def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("重复 JSON 键: " + key)
        result[key] = value
    return result


def finite_float(text):
    value = float(text)
    if not math.isfinite(value):
        fail("JSON 数值超出有限浮点范围: " + text)
    return value


def reject_constant(text):
    fail("不允许非有限 JSON 数值: " + text)


def expected_document(path, identifier):
    document = json.loads(Path(path).expanduser().read_text(encoding="utf-8-sig"),
                          object_pairs_hook=unique_object, parse_float=finite_float,
                          parse_constant=reject_constant)
    if not isinstance(document, dict):
        fail("预期声明必须是 JSON 对象")
    if document.get("experiment_id") not in ("auto", identifier):
        fail("预期 experiment_id 必须为 auto 或本次分配的 " + identifier)
    changes = document.get("changes")
    if not isinstance(changes, dict) or not changes:
        fail("预期声明的 changes 必须是非空字段映射")
    for field in changes:
        if not field or any(not part for part in field.split(".")):
            fail("无效的点分字段路径: " + repr(field))
    document["experiment_id"] = identifier
    return document


def name_token(text):
    # Escape separators and case, so distinct paths and categories stay distinct.
    return "".join(chr(byte) if chr(byte) in "abcdefghijklmnopqrstuvwyz0123456789"
                   else "-" if byte == 46 else "x%02x" % byte
                   for byte in text.encode("utf-8"))


def name_value(value):
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        number = Decimal(str(value))
        if not number:
            return "0"
        sign = "neg-" if number.is_signed() else ""
        with localcontext() as context:
            context.prec = len(number.as_tuple().digits)
            number = abs(number).normalize()
        digits = "".join(str(digit) for digit in number.as_tuple().digits)
        exponent = number.adjusted()
        coefficient = digits[0] + ("p" + digits[1:] if len(digits) > 1 else "")
        return sign + coefficient + ("e%d" % exponent if exponent else "")
    if isinstance(value, str) and value.strip():
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", value) and value.lower() not in ("true", "false"):
            return value.lower()
        readable = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return "str-" + ((readable + "-") if readable else "") + "x" + value.encode("utf-8").hex()
    fail("自动命名字段必须是非空标量；用 --name-field 选择其他标量字段")


def expected_slug(document, fields, labels):
    changes = document["changes"]
    fields = fields or list(changes)
    if len(fields) != len(set(fields)):
        fail("--name-field 不能重复")
    aliases = {}
    for label in labels:
        field, separator, alias = label.partition("=")
        if not separator or field not in fields or not alias.strip() or field in aliases:
            fail("--label 需要唯一的已选择字段=非空别名: " + label)
        aliases[field] = alias.strip()
    if any(field not in changes for field in fields):
        fail("--name-field 必须是 changes 中的完整字段路径")
    tokens = [name_token(aliases.get(field, field)) for field in fields]
    if len(tokens) != len(set(tokens)):
        fail("命名字段的别名不能重复")
    return "-".join("%s-%s" % (token, name_value(changes[field]))
                    for field, token in zip(fields, tokens))


def new(args):
    if bool(args.slug) == bool(args.expected):
        fail("必须且只能指定 --slug 或 --expected；预期命名不能使用手工 slug")
    if not args.expected and (args.name_field or args.label):
        fail("--name-field 和 --label 需要 --expected")
    with locked():
        rows = records()
        counter = LEDGER / ".next-id"
        number = next_number(counter, [int(fm["id"].split("-")[1]) for _, fm, _ in rows])
        identifier = "EXP-%04d" % number
        document = expected_document(args.expected, identifier) if args.expected else None
        slug = expected_slug(document, args.name_field, args.label) if document else normalize_slug(args.slug)
        stem = identifier + "-" + slug
        if len((stem + ".md").encode("utf-8")) > 255:
            fail("实验名称过长；使用 --name-field 和 --label 缩短名称")
        directory = group_path(args.group, groups()) if args.group else LEDGER
        path = directory / (stem + ".md")
        if path.exists() or path.is_symlink() or path.with_suffix("").exists() or path.with_suffix("").is_symlink():
            fail("实验路径冲突: " + stem)
        fm = {"id": identifier, "slug": slug, "title": scalar(args.title),
              "status": args.status, "review_status": "pending", "created": date.today().isoformat(),
              "updated": date.today().isoformat(), "run_dir": "runs/" + stem}
        expected_snapshot = None
        if document is not None:
            destination = path.with_suffix("") / "config.expected.json"
            fm["expected_snapshot"] = destination.relative_to(ROOT).as_posix()
            expected_snapshot = (destination, json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        for key in ("hypothesis", "command", "code", "config", "owner"):
            value = getattr(args, key)
            if value:
                fm[key] = scalar(value)
        if args.next:
            append(fm, "next", args.next)
        validate(fm)
        template = LEDGER / "_template.md"
        _, body = parse(template)
        snapshot = configuration(fm, path)
        text = render(fm, body)
        documents = derived(rows + [(path, fm, body)])
        # Reserve first: a failed write may skip an ID but never reuses one.
        atomic(counter, str(number + 1) + "\n")
        if expected_snapshot:
            atomic(*expected_snapshot)
        if snapshot:
            atomic(*snapshot)
        atomic(path, text)
        write_derived(documents)
    print(path.relative_to(ROOT))


def set_record(args):
    with locked():
        rows = records()
        path, fm, body = find(rows, args.id)
        changed_config = False
        for pair in args.field:
            key, separator, value = pair.partition("=")
            key, value = key.strip(), scalar(value)
            if not separator or not KEY.fullmatch(key):
                fail("需要 key=value: %s" % pair)
            if key in ("id", "slug", "config_hash", "config_snapshot", "expected_snapshot"):
                fail("不可直接修改编号、slug 或派生快照字段: " + key)
            changed_config = changed_config or key in ("code", "config")
            if not value:
                fm.pop(key, None)
            elif key in REPEATED:
                append(fm, key, [value])
            else:
                fm[key] = value
        if args.clear_next:
            fm.pop("next", None)
        if args.next:
            append(fm, "next", args.next)
        for item in args.complete_next:
            item = scalar(item)
            opened = values(fm, "next")
            if item not in opened:
                fail("没有精确匹配的开放任务: " + item)
            opened.remove(item)
            fm["next"] = opened
            if not fm["next"]:
                fm.pop("next")
            append(fm, "next_done", [item])
        if args.result is not None:
            if any(pair.partition("=")[0].strip() == "review_status" for pair in args.field):
                fail("--result 不能与显式 review_status 同时使用")
            updated_body = region(body, "result", args.result)
            if updated_body != body:
                fm["review_status"] = "pending"
            body = updated_body
        fm["updated"] = date.today().isoformat()
        validate(fm)
        snapshot = configuration(fm, path) if changed_config else None
        text = render(fm, body)
        rows = [(p, fm, body) if p == path else (p, metadata, content) for p, metadata, content in rows]
        documents = derived(rows)
        if snapshot:
            atomic(*snapshot)
        atomic(path, text)
        write_derived(documents)
    print("已更新 " + str(path.relative_to(ROOT)))


def run_path(path, fm):
    if fm.get("run_dir"):
        selected = Path(fm["run_dir"]).expanduser()
        return selected if selected.is_absolute() else ROOT / selected
    stem = path.stem
    slug = fm.get("slug") or stem.split("-", 2)[-1]
    roots = [ROOT]
    if fm.get("code"):
        code = Path(fm["code"]).expanduser()
        code = code if code.is_absolute() else ROOT / code
        if code != ROOT:
            roots.append(code)
    candidates = [root / "runs" / name for root in roots for name in (stem, slug)]
    candidates.extend([LEDGER / "runs" / stem, LEDGER / stem])
    return next((candidate for candidate in candidates if candidate.is_dir()), candidates[0])


def status(args):
    rows = records()
    if args.id:
        rows = [find(rows, args.id)]
    print("仅报告台账与文件现场，不判断进程存活。")
    if not rows:
        print("尚无实验记录。")
    for path, fm, _ in rows:
        directory = run_path(path, fm)
        print("%s [%s] review=%s" % (fm["id"], fm.get("status", "未记录"), fm.get("review_status", "pending（未记录）")))
        print("  run_dir=%s (%s)" % (directory, "目录存在" if directory.is_dir() else "目录不存在"))
        if directory.is_dir():
            shown = 0
            for base, directories, files in os.walk(str(directory)):
                directories.sort()
                for name in sorted(files):
                    shown += 1
                    if shown > 20:
                        break
                    print("  产物: " + str((Path(base) / name).relative_to(directory)))
                if shown > 20:
                    print("  其余产物未列出（最多展示20项）。")
                    break
            if not shown:
                print("  尚无文件产物。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    p = commands.add_parser("group-new", help="分配研究组编号并创建主题目录")
    p.add_argument("--slug", required=True)
    p.add_argument("--title", required=True)
    p.set_defaults(func=group_new)
    p = commands.add_parser("new", help="分配编号并建档；不执行 command")
    p.add_argument("--slug", help="旧式手工命名（不能与 --expected 同用）")
    p.add_argument("--group", help="研究组编号或完整目录名")
    p.add_argument("--expected", help="包含 experiment_id 和 changes 的预期 JSON")
    p.add_argument("--name-field", action="append", default=[], help="用于命名的 changes 字段路径，可重复")
    p.add_argument("--label", action="append", default=[], help="命名字段的短别名：字段=别名，可重复")
    for key in ("title", "hypothesis", "command", "code", "config", "owner"):
        p.add_argument("--" + key, default="")
    p.add_argument("--status", choices=STATUSES, default="planned")
    p.add_argument("--next", action="append", default=[])
    p.set_defaults(func=new)
    p = commands.add_parser("set", help="修改标量字段与后续工作")
    p.add_argument("id")
    p.add_argument("field", nargs="*")
    p.add_argument("--next", action="append", default=[])
    p.add_argument("--complete-next", action="append", default=[])
    p.add_argument("--clear-next", action="store_true")
    p.add_argument("--result")
    p.set_defaults(func=set_record)
    p = commands.add_parser("list")
    p.add_argument("--json", action="store_true")
    p.add_argument("--status", choices=STATUSES)
    commands.add_parser("reindex")
    p = commands.add_parser("show")
    p.add_argument("id")
    p = commands.add_parser("status")
    p.add_argument("id", nargs="?")
    p.set_defaults(func=status)
    # argparse normally stops collecting a '*' positional after the first option.
    # Preserve the legacy-friendly `set ID --next TEXT metric=value` spelling.
    args, extra = parser.parse_known_args()
    if extra:
        if args.action != "set" or any(item.startswith("-") or "=" not in item for item in extra):
            parser.error("无法识别的参数: " + " ".join(extra))
        args.field.extend(extra)
    if not LEDGER.is_dir():
        fail("缺少 experiments 目录；先使用初始化器")
    if args.action == "list":
        rows = [row for row in records() if not args.status or row[1].get("status") == args.status]
        if args.json:
            print(json.dumps([dict(fm, record=str(path.relative_to(ROOT))) for path, fm, _ in rows], ensure_ascii=False, indent=2))
        else:
            for _, fm, _ in rows:
                print("%s\t%s\t%s" % (fm["id"], fm.get("status", "未记录"), fm.get("title", "")))
    elif args.action == "show":
        print(find(records(), args.id)[0].read_text(encoding="utf-8-sig"), end="")
    elif args.action == "reindex":
        with locked():
            rows = records()
            write_derived(derived(rows))
        print("已派生 %d 条实验记录。" % len(rows))
    else:
        args.func(args)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        print("错误: %s" % exc, file=sys.stderr)
        sys.exit(1)
