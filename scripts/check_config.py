#!/usr/bin/env python3
"""Compare declared experiment conditions with an exported effective JSON config.

Exit 0: selected conditions match. Exit 1: mismatch or missing field.
Exit 2: invalid input or an unwritable/existing receipt. Never launches commands.

Expected JSON: {"experiment_id": "EXP-0001", "changes": {"optimizer.lr": 0.001}}
Effective JSON: {"experiment_id": "EXP-0001", "config": {"optimizer": {"lr": 1e-3}}}
Fields use dot paths relative to config; numeric path parts may index arrays.
Only declared fields are checked. Numeric spellings compare by value; types,
booleans, strings, array order and missing fields are not coerced.
The effective file must be exported from the real resolved execution config.
This checker cannot authenticate its source or verify implementation semantics.
Receipts are new files only and never replace previous evidence.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("重复 JSON 键: " + key)
        result[key] = value
    return result


def finite_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("JSON 数值超出有限浮点范围: " + text)
    return value


def reject_constant(text):
    raise ValueError("不允许非有限 JSON 数值: " + text)


def load_document(path):
    raw = path.read_bytes()
    document = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object,
                          parse_float=finite_float, parse_constant=reject_constant)
    if not isinstance(document, dict):
        raise ValueError("JSON 顶层必须为对象: " + str(path))
    identifier = document.get("experiment_id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("必须提供非空 experiment_id: " + str(path))
    return document, hashlib.sha256(raw).hexdigest()


def equal(expected, actual):
    """JSON numbers compare numerically; booleans are not numbers."""
    if type(expected) in (int, float) and type(actual) in (int, float):
        return expected == actual
    if type(expected) is not type(actual):
        return False
    if isinstance(expected, dict):
        return expected.keys() == actual.keys() and all(
            equal(value, actual[key]) for key, value in expected.items())
    if isinstance(expected, list):
        return len(expected) == len(actual) and all(
            equal(left, right) for left, right in zip(expected, actual))
    return expected == actual


def lookup(config, field):
    value = config
    for part in field.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isascii() and part.isdigit():
            index = int(part)
            if index >= len(value):
                return False, None
            value = value[index]
        else:
            return False, None
    return True, value


def check(expected_path, effective_path):
    if expected_path.resolve() == effective_path.resolve():
        raise ValueError("预期声明与生效配置必须是不同文件")
    expected, expected_hash = load_document(expected_path)
    effective, effective_hash = load_document(effective_path)
    if expected["experiment_id"].strip().lower() == "auto" or effective["experiment_id"].strip().lower() == "auto":
        raise ValueError("experiment_id 不能为 auto；请使用建档生成的实际编号")
    changes = expected.get("changes")
    if not isinstance(changes, dict) or not changes:
        raise ValueError("预期声明的 changes 必须是非空字段映射，拒绝空检查")
    if not isinstance(effective.get("config"), dict):
        raise ValueError("生效配置必须提供 config 对象")
    for field in changes:
        if not field or any(not part for part in field.split(".")):
            raise ValueError("无效的点分字段路径: " + repr(field))
    checks = []
    if expected["experiment_id"] != effective["experiment_id"]:
        checks.append({"field": "experiment_id", "status": "different",
                       "expected": expected["experiment_id"],
                       "actual": effective["experiment_id"]})
    for field, planned in changes.items():
        found, actual = lookup(effective["config"], field)
        item = {"field": field, "expected": planned,
                "status": "missing" if not found else
                          "match" if equal(planned, actual) else "different"}
        if found:
            item["actual"] = actual
        checks.append(item)
    passed = all(item["status"] == "match" for item in checks)
    report = {"status": "passed" if passed else "mismatch",
              "experiment_id": expected["experiment_id"],
              "expected_file": str(expected_path.resolve()),
              "expected_sha256": expected_hash,
              "effective_file": str(effective_path.resolve()),
              "effective_sha256": effective_hash,
              "checks": checks,
              "scope": "仅核对声明字段与输入文件；不证明配置来自真实进程或实现语义正确"}
    return report, 0 if passed else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", required=True, type=Path)
    parser.add_argument("--effective", required=True, type=Path)
    parser.add_argument("--receipt", type=Path,
                        help="将报告另存为新文件；拒绝覆盖任何已有报告")
    args = parser.parse_args(argv)
    try:
        report, code = check(args.expected, args.effective)
    except (ValueError, OSError, UnicodeError) as exc:
        report, code = {"status": "invalid", "error": str(exc)}, 2
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.receipt:
        try:
            # Exclusive creation keeps prior attempts and input files untouched.
            with args.receipt.open("x", encoding="utf-8") as handle:
                handle.write(text)
        except OSError as exc:
            report, code = {"status": "invalid", "error": "检查报告未保存: " + str(exc)}, 2
            text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    sys.stdout.write(text)
    return code


if __name__ == "__main__":
    sys.exit(main())
