#!/usr/bin/env python3
"""Build a glossary dictionary from the CEDICT data in the Zhongwen extension.

Downloads cedict_ts.u8 from the Zhongwen Chrome extension repo, parses it,
converts pinyin to zhuyin (Bopomofo), and outputs a JSON dictionary keyed
by Traditional Chinese characters/words.

Usage:
    python3 scripts/build_dictionary.py [--output path]
    Default output: data/cedict_dictionary.json

The output file is ~15-25 MB and is listed in .gitignore (regenerable).
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO / "data" / "cedict_dictionary.json"

CEDICT_URL = (
    "https://raw.githubusercontent.com/cschiller/zhongwen/master/data/cedict_ts.u8"
)

# ---------------------------------------------------------------------------
# Pinyin → Zhuyin (Bopomofo) conversion tables
# ---------------------------------------------------------------------------

# Tone number → Bopomofo tone mark
# Tone 1 = unmarked (first tone), Tone 5 = neutral tone (˙ placed before syllable)
TONE_MARKS = {
    "1": "",      # first tone: unmarked in zhuyin
    "2": "ˊ",
    "3": "ˇ",
    "4": "ˋ",
    "5": "˙",     # neutral tone
}

# Pinyin syllable → Bopomofo mapping
# This covers all standard Mandarin syllables
# Built from the official pinyin-zhuyin correspondence table
PINYIN_TO_ZHUYIN = {
    # Zero-initial syllables (mapped by final)
    "a": "ㄚ", "o": "ㄛ", "e": "ㄜ", "ei": "ㄟ", "ai": "ㄞ", "ao": "ㄠ",
    "ou": "ㄡ", "an": "ㄢ", "en": "ㄣ", "ang": "ㄤ", "eng": "ㄥ", "er": "ㄦ",

    # Yi- syllables
    "yi": "ㄧ", "ya": "ㄧㄚ", "yo": "ㄧㄛ", "ye": "ㄧㄝ", "yai": "ㄧㄞ",
    "yao": "ㄧㄠ", "you": "ㄧㄡ", "yan": "ㄧㄢ", "yin": "ㄧㄣ",
    "yang": "ㄧㄤ", "ying": "ㄧㄥ",

    # Wu- syllables
    "wu": "ㄨ", "wa": "ㄨㄚ", "wo": "ㄨㄛ", "wai": "ㄨㄞ", "wei": "ㄨㄟ",
    "wan": "ㄨㄢ", "wen": "ㄨㄣ", "wang": "ㄨㄤ", "weng": "ㄨㄥ",

    # Yu- syllables
    "yu": "ㄩ", "yue": "ㄩㄝ", "yuan": "ㄩㄢ", "yun": "ㄩㄣ", "yong": "ㄩㄥ",

    # B- initial
    "ba": "ㄅㄚ", "bo": "ㄅㄛ", "bai": "ㄅㄞ", "bei": "ㄅㄟ", "bao": "ㄅㄠ",
    "ban": "ㄅㄢ", "ben": "ㄅㄣ", "bang": "ㄅㄤ", "beng": "ㄅㄥ",
    "bi": "ㄅㄧ", "bie": "ㄅㄧㄝ", "biao": "ㄅㄧㄠ", "bian": "ㄅㄧㄢ",
    "bin": "ㄅㄧㄣ", "bing": "ㄅㄧㄥ", "bu": "ㄅㄨ",

    # P- initial
    "pa": "ㄆㄚ", "po": "ㄆㄛ", "pai": "ㄆㄞ", "pei": "ㄆㄟ", "pao": "ㄆㄠ",
    "pou": "ㄆㄡ", "pan": "ㄆㄢ", "pen": "ㄆㄣ", "pang": "ㄆㄤ", "peng": "ㄆㄥ",
    "pi": "ㄆㄧ", "pie": "ㄆㄧㄝ", "piao": "ㄆㄧㄠ", "pian": "ㄆㄧㄢ",
    "pin": "ㄆㄧㄣ", "ping": "ㄆㄧㄥ", "pu": "ㄆㄨ",

    # M- initial
    "ma": "ㄇㄚ", "mo": "ㄇㄛ", "me": "ㄇㄜ", "mai": "ㄇㄞ", "mei": "ㄇㄟ",
    "mao": "ㄇㄠ", "mou": "ㄇㄡ", "man": "ㄇㄢ", "men": "ㄇㄣ",
    "mang": "ㄇㄤ", "meng": "ㄇㄥ",
    "mi": "ㄇㄧ", "mie": "ㄇㄧㄝ", "miao": "ㄇㄧㄠ", "miu": "ㄇㄧㄡ",
    "mian": "ㄇㄧㄢ", "min": "ㄇㄧㄣ", "ming": "ㄇㄧㄥ", "mu": "ㄇㄨ",

    # F- initial
    "fa": "ㄈㄚ", "fo": "ㄈㄛ", "fei": "ㄈㄟ", "fou": "ㄈㄡ",
    "fan": "ㄈㄢ", "fen": "ㄈㄣ", "fang": "ㄈㄤ", "feng": "ㄈㄥ", "fu": "ㄈㄨ",

    # D- initial
    "da": "ㄉㄚ", "de": "ㄉㄜ", "dai": "ㄉㄞ", "dei": "ㄉㄟ", "dao": "ㄉㄠ",
    "dou": "ㄉㄡ", "dan": "ㄉㄢ", "den": "ㄉㄣ", "dang": "ㄉㄤ", "deng": "ㄉㄥ",
    "dong": "ㄉㄨㄥ",
    "di": "ㄉㄧ", "die": "ㄉㄧㄝ", "diao": "ㄉㄧㄠ", "diu": "ㄉㄧㄡ",
    "dian": "ㄉㄧㄢ", "ding": "ㄉㄧㄥ",
    "du": "ㄉㄨ", "duo": "ㄉㄨㄛ", "dui": "ㄉㄨㄟ", "duan": "ㄉㄨㄢ", "dun": "ㄉㄨㄣ",

    # T- initial
    "ta": "ㄊㄚ", "te": "ㄊㄜ", "tai": "ㄊㄞ", "tao": "ㄊㄠ", "tou": "ㄊㄡ",
    "tan": "ㄊㄢ", "tang": "ㄊㄤ", "teng": "ㄊㄥ", "tong": "ㄊㄨㄥ",
    "ti": "ㄊㄧ", "tie": "ㄊㄧㄝ", "tiao": "ㄊㄧㄠ", "tian": "ㄊㄧㄢ", "ting": "ㄊㄧㄥ",
    "tu": "ㄊㄨ", "tuo": "ㄊㄨㄛ", "tui": "ㄊㄨㄟ", "tuan": "ㄊㄨㄢ", "tun": "ㄊㄨㄣ",

    # N- initial
    "na": "ㄋㄚ", "ne": "ㄋㄜ", "nai": "ㄋㄞ", "nei": "ㄋㄟ", "nao": "ㄋㄠ",
    "nou": "ㄋㄡ", "nan": "ㄋㄢ", "nen": "ㄋㄣ", "nang": "ㄋㄤ", "neng": "ㄋㄥ",
    "nong": "ㄋㄨㄥ",
    "ni": "ㄋㄧ", "nie": "ㄋㄧㄝ", "niao": "ㄋㄧㄠ", "niu": "ㄋㄧㄡ",
    "nian": "ㄋㄧㄢ", "nin": "ㄋㄧㄣ", "niang": "ㄋㄧㄤ", "ning": "ㄋㄧㄥ",
    "nu": "ㄋㄨ", "nuo": "ㄋㄨㄛ", "nuan": "ㄋㄨㄢ",
    "nv": "ㄋㄩ", "nve": "ㄋㄩㄝ",
    "nu:": "ㄋㄩ", "nu:e": "ㄋㄩㄝ",

    # L- initial
    "la": "ㄌㄚ", "le": "ㄌㄜ", "lai": "ㄌㄞ", "lei": "ㄌㄟ", "lao": "ㄌㄠ",
    "lou": "ㄌㄡ", "lan": "ㄌㄢ", "lang": "ㄌㄤ", "leng": "ㄌㄥ", "long": "ㄌㄨㄥ",
    "li": "ㄌㄧ", "lie": "ㄌㄧㄝ", "liao": "ㄌㄧㄠ", "liu": "ㄌㄧㄡ",
    "lian": "ㄌㄧㄢ", "lin": "ㄌㄧㄣ", "liang": "ㄌㄧㄤ", "ling": "ㄌㄧㄥ",
    "lu": "ㄌㄨ", "luo": "ㄌㄨㄛ", "luan": "ㄌㄨㄢ", "lun": "ㄌㄨㄣ",
    "lv": "ㄌㄩ", "lve": "ㄌㄩㄝ",
    "lu:": "ㄌㄩ", "lu:e": "ㄌㄩㄝ",

    # G- initial
    "ga": "ㄍㄚ", "ge": "ㄍㄜ", "gai": "ㄍㄞ", "gei": "ㄍㄟ", "gao": "ㄍㄠ",
    "gou": "ㄍㄡ", "gan": "ㄍㄢ", "gen": "ㄍㄣ", "gang": "ㄍㄤ", "geng": "ㄍㄥ",
    "gong": "ㄍㄨㄥ",
    "gu": "ㄍㄨ", "gua": "ㄍㄨㄚ", "guo": "ㄍㄨㄛ", "guai": "ㄍㄨㄞ",
    "gui": "ㄍㄨㄟ", "guan": "ㄍㄨㄢ", "gun": "ㄍㄨㄣ", "guang": "ㄍㄨㄤ",

    # K- initial
    "ka": "ㄎㄚ", "ke": "ㄎㄜ", "kai": "ㄎㄞ", "kei": "ㄎㄟ", "kao": "ㄎㄠ",
    "kou": "ㄎㄡ", "kan": "ㄎㄢ", "ken": "ㄎㄣ", "kang": "ㄎㄤ", "keng": "ㄎㄥ",
    "kong": "ㄎㄨㄥ",
    "ku": "ㄎㄨ", "kua": "ㄎㄨㄚ", "kuo": "ㄎㄨㄛ", "kuai": "ㄎㄨㄞ",
    "kui": "ㄎㄨㄟ", "kuan": "ㄎㄨㄢ", "kun": "ㄎㄨㄣ", "kuang": "ㄎㄨㄤ",

    # H- initial
    "ha": "ㄏㄚ", "he": "ㄏㄜ", "hai": "ㄏㄞ", "hei": "ㄏㄟ", "hao": "ㄏㄠ",
    "hou": "ㄏㄡ", "han": "ㄏㄢ", "hen": "ㄏㄣ", "hang": "ㄏㄤ", "heng": "ㄏㄥ",
    "hong": "ㄏㄨㄥ",
    "hu": "ㄏㄨ", "hua": "ㄏㄨㄚ", "huo": "ㄏㄨㄛ", "huai": "ㄏㄨㄞ",
    "hui": "ㄏㄨㄟ", "huan": "ㄏㄨㄢ", "hun": "ㄏㄨㄣ", "huang": "ㄏㄨㄤ",

    # J- initial
    "ji": "ㄐㄧ", "jia": "ㄐㄧㄚ", "jie": "ㄐㄧㄝ", "jiao": "ㄐㄧㄠ",
    "jiu": "ㄐㄧㄡ", "jian": "ㄐㄧㄢ", "jin": "ㄐㄧㄣ", "jiang": "ㄐㄧㄤ",
    "jing": "ㄐㄧㄥ", "jiong": "ㄐㄩㄥ",
    "ju": "ㄐㄩ", "jue": "ㄐㄩㄝ", "juan": "ㄐㄩㄢ", "jun": "ㄐㄩㄣ",

    # Q- initial
    "qi": "ㄑㄧ", "qia": "ㄑㄧㄚ", "qie": "ㄑㄧㄝ", "qiao": "ㄑㄧㄠ",
    "qiu": "ㄑㄧㄡ", "qian": "ㄑㄧㄢ", "qin": "ㄑㄧㄣ", "qiang": "ㄑㄧㄤ",
    "qing": "ㄑㄧㄥ", "qiong": "ㄑㄩㄥ",
    "qu": "ㄑㄩ", "que": "ㄑㄩㄝ", "quan": "ㄑㄩㄢ", "qun": "ㄑㄩㄣ",

    # X- initial
    "xi": "ㄒㄧ", "xia": "ㄒㄧㄚ", "xie": "ㄒㄧㄝ", "xiao": "ㄒㄧㄠ",
    "xiu": "ㄒㄧㄡ", "xian": "ㄒㄧㄢ", "xin": "ㄒㄧㄣ", "xiang": "ㄒㄧㄤ",
    "xing": "ㄒㄧㄥ", "xiong": "ㄒㄩㄥ",
    "xu": "ㄒㄩ", "xue": "ㄒㄩㄝ", "xuan": "ㄒㄩㄢ", "xun": "ㄒㄩㄣ",

    # Zh- initial
    "zha": "ㄓㄚ", "zhe": "ㄓㄜ", "zhi": "ㄓ", "zhai": "ㄓㄞ", "zhei": "ㄓㄟ",
    "zhao": "ㄓㄠ", "zhou": "ㄓㄡ", "zhan": "ㄓㄢ", "zhen": "ㄓㄣ",
    "zhang": "ㄓㄤ", "zheng": "ㄓㄥ", "zhong": "ㄓㄨㄥ",
    "zhu": "ㄓㄨ", "zhua": "ㄓㄨㄚ", "zhuo": "ㄓㄨㄛ", "zhuai": "ㄓㄨㄞ",
    "zhui": "ㄓㄨㄟ", "zhuan": "ㄓㄨㄢ", "zhun": "ㄓㄨㄣ", "zhuang": "ㄓㄨㄤ",

    # Ch- initial
    "cha": "ㄔㄚ", "che": "ㄔㄜ", "chi": "ㄔ", "chai": "ㄔㄞ",
    "chao": "ㄔㄠ", "chou": "ㄔㄡ", "chan": "ㄔㄢ", "chen": "ㄔㄣ",
    "chang": "ㄔㄤ", "cheng": "ㄔㄥ", "chong": "ㄔㄨㄥ",
    "chu": "ㄔㄨ", "chua": "ㄔㄨㄚ", "chuo": "ㄔㄨㄛ", "chuai": "ㄔㄨㄞ",
    "chui": "ㄔㄨㄟ", "chuan": "ㄔㄨㄢ", "chun": "ㄔㄨㄣ", "chuang": "ㄔㄨㄤ",

    # Sh- initial
    "sha": "ㄕㄚ", "she": "ㄕㄜ", "shi": "ㄕ", "shai": "ㄕㄞ", "shei": "ㄕㄟ",
    "shao": "ㄕㄠ", "shou": "ㄕㄡ", "shan": "ㄕㄢ", "shen": "ㄕㄣ",
    "shang": "ㄕㄤ", "sheng": "ㄕㄥ",
    "shu": "ㄕㄨ", "shua": "ㄕㄨㄚ", "shuo": "ㄕㄨㄛ", "shuai": "ㄕㄨㄞ",
    "shui": "ㄕㄨㄟ", "shuan": "ㄕㄨㄢ", "shun": "ㄕㄨㄣ", "shuang": "ㄕㄨㄤ",

    # R- initial
    "ra": "ㄖㄚ", "re": "ㄖㄜ", "ri": "ㄖ", "rao": "ㄖㄠ", "rou": "ㄖㄡ",
    "ran": "ㄖㄢ", "ren": "ㄖㄣ", "rang": "ㄖㄤ", "reng": "ㄖㄥ", "rong": "ㄖㄨㄥ",
    "ru": "ㄖㄨ", "ruo": "ㄖㄨㄛ", "rui": "ㄖㄨㄟ", "ruan": "ㄖㄨㄢ", "run": "ㄖㄨㄣ",

    # Z- initial
    "za": "ㄗㄚ", "ze": "ㄗㄜ", "zi": "ㄗ", "zai": "ㄗㄞ", "zei": "ㄗㄟ",
    "zao": "ㄗㄠ", "zou": "ㄗㄡ", "zan": "ㄗㄢ", "zen": "ㄗㄣ",
    "zang": "ㄗㄤ", "zeng": "ㄗㄥ", "zong": "ㄗㄨㄥ",
    "zu": "ㄗㄨ", "zuo": "ㄗㄨㄛ", "zui": "ㄗㄨㄟ", "zuan": "ㄗㄨㄢ", "zun": "ㄗㄨㄣ",

    # C- initial
    "ca": "ㄘㄚ", "ce": "ㄘㄜ", "ci": "ㄘ", "cai": "ㄘㄞ",
    "cao": "ㄘㄠ", "cou": "ㄘㄡ", "can": "ㄘㄢ", "cen": "ㄘㄣ",
    "cang": "ㄘㄤ", "ceng": "ㄘㄥ", "cong": "ㄘㄨㄥ",
    "cu": "ㄘㄨ", "cuo": "ㄘㄨㄛ", "cui": "ㄘㄨㄟ", "cuan": "ㄘㄨㄢ", "cun": "ㄘㄨㄣ",

    # S- initial
    "sa": "ㄙㄚ", "se": "ㄙㄜ", "si": "ㄙ", "sai": "ㄙㄞ",
    "sao": "ㄙㄠ", "sou": "ㄙㄡ", "san": "ㄙㄢ", "sen": "ㄙㄣ",
    "sang": "ㄙㄤ", "seng": "ㄙㄥ", "song": "ㄙㄨㄥ",
    "su": "ㄙㄨ", "suo": "ㄙㄨㄛ", "sui": "ㄙㄨㄟ", "suan": "ㄙㄨㄢ", "sun": "ㄙㄨㄣ",
}


def pinyin_syllable_to_zhuyin(syllable: str) -> str | None:
    """Convert a single numbered pinyin syllable to zhuyin.

    E.g., "zhong1" → "ㄓㄨㄥ", "ma5" → "˙ㄇㄚ"
    """
    if not syllable:
        return None

    # Extract tone number (last char if digit)
    tone = "5"  # default neutral
    base = syllable.lower()
    if base and base[-1].isdigit():
        tone = base[-1]
        base = base[:-1]

    if not base:
        return None

    # Handle u: notation (CEDICT uses u: for ü)
    base = base.replace("u:", "v")

    # Look up in table
    zhuyin = PINYIN_TO_ZHUYIN.get(base)
    if zhuyin is None:
        return None

    # Apply tone
    tone_mark = TONE_MARKS.get(tone, "")
    if tone == "5":
        # Neutral tone mark goes before the syllable
        return "˙" + zhuyin
    else:
        return zhuyin + tone_mark


def pinyin_to_zhuyin(pinyin_str: str) -> str | None:
    """Convert a CEDICT pinyin string (space-separated syllables) to zhuyin.

    E.g., "Tai2 ji1 dian4" → "ㄊㄞˊ ㄐㄧ ㄉㄧㄢˋ"
    """
    syllables = pinyin_str.strip().split()
    result = []
    for s in syllables:
        z = pinyin_syllable_to_zhuyin(s)
        if z is None:
            return None  # Can't convert this entry
        result.append(z)
    return " ".join(result)


# ---------------------------------------------------------------------------
# CEDICT parsing
# ---------------------------------------------------------------------------

def parse_cedict_line(line: str) -> tuple[str, str, str, str] | None:
    """Parse a CEDICT line into (traditional, simplified, pinyin, english).

    Format: 傳統 简体 [pin1 yin1] /english 1/english 2/
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    # Match: traditional simplified [pinyin] /english/
    m = re.match(r"^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/$", line)
    if not m:
        return None

    traditional = m.group(1)
    simplified = m.group(2)
    pinyin = m.group(3)
    english = m.group(4).replace("/", "; ")

    return traditional, simplified, pinyin, english


def download_cedict() -> str:
    """Download CEDICT from the Zhongwen extension repo."""
    print(f"Downloading CEDICT from {CEDICT_URL}...")
    req = urllib.request.Request(CEDICT_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read().decode("utf-8")
    print(f"Downloaded {len(data)} bytes")
    return data


def build_dictionary(cedict_text: str) -> dict:
    """Parse CEDICT and build the dictionary with zhuyin."""
    dictionary = {}
    total_lines = 0
    converted = 0
    failed_conversions = 0

    for line in cedict_text.split("\n"):
        parsed = parse_cedict_line(line)
        if parsed is None:
            continue

        total_lines += 1
        traditional, simplified, pinyin, english = parsed

        zhuyin = pinyin_to_zhuyin(pinyin)
        if zhuyin is None:
            failed_conversions += 1
            continue

        converted += 1

        # Use traditional characters as key
        # For entries with multiple pronunciations, keep the first one
        # (the glossary agents will disambiguate using article context)
        if traditional not in dictionary:
            dictionary[traditional] = {
                "zhuyin": zhuyin,
                "english": english,
            }
        else:
            # Append additional meanings
            existing = dictionary[traditional]["english"]
            if english not in existing:
                dictionary[traditional]["english"] = existing + "; " + english

    print(f"CEDICT lines parsed: {total_lines}")
    print(f"Successfully converted: {converted}")
    print(f"Failed pinyin→zhuyin conversions: {failed_conversions}")
    print(f"Unique dictionary entries: {len(dictionary)}")

    return dictionary


def validate_zhuyin(dictionary: dict) -> int:
    """Validate that all zhuyin entries contain Bopomofo characters."""
    bopomofo_range = re.compile(r"[\u3100-\u312f\u31a0-\u31bf]")
    bad_count = 0
    to_remove = []

    for key, entry in dictionary.items():
        zhuyin = entry["zhuyin"]
        # Remove tone marks and spaces for checking
        cleaned = zhuyin.replace(" ", "").replace("ˊ", "").replace("ˇ", "").replace("ˋ", "").replace("˙", "")
        if cleaned and not bopomofo_range.search(cleaned):
            bad_count += 1
            to_remove.append(key)

    for key in to_remove:
        del dictionary[key]

    if bad_count:
        print(f"Removed {bad_count} entries with invalid zhuyin")

    return bad_count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build glossary dictionary from CEDICT")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Output JSON path")
    parser.add_argument("--input", type=Path, default=None,
                        help="Use local CEDICT file instead of downloading")
    parser.add_argument("--force", action="store_true",
                        help="Rebuild even if output file already exists")
    args = parser.parse_args()

    # Idempotent: skip if output already exists (unless --force)
    if not args.force and args.output.exists():
        size_mb = args.output.stat().st_size / (1024 * 1024)
        print(f"Dictionary already exists at {args.output} ({size_mb:.1f} MB), skipping. Use --force to rebuild.")
        return

    if args.input:
        cedict_text = args.input.read_text(encoding="utf-8")
    else:
        cedict_text = download_cedict()

    dictionary = build_dictionary(cedict_text)
    validate_zhuyin(dictionary)

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = args.output.stat().st_size / (1024 * 1024)
    print(f"\nDictionary written to {args.output} ({size_mb:.1f} MB)")
    print(f"Total entries: {len(dictionary)}")


if __name__ == "__main__":
    main()
