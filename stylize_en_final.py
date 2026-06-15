# ANONYMOUS 
import json
import re

def to_ascii(text):
    # Comprehensive mapping for stylized characters
    for i in range(26):
        text = text.replace(chr(0x1D400 + i), chr(ord('A') + i))

    sc_map = {
        '\u1d00': 'a', '\u0299': 'b', '\u1d04': 'c', '\u1d05': 'd', '\u1d07': 'e',
        '\u0493': 'f', '\u0262': 'g', '\u029c': 'h', '\u026a': 'i', '\u1d0a': 'j',
        '\u1d0b': 'k', '\u029f': 'l', '\u1d0d': 'm', '\u0274': 'n', '\u1d0f': 'o',
        '\u1d18': 'p', '\u01eb': 'q', '\u0280': 'r', 's': 's', '\u1d1b': 't',
        '\u1d1c': 'u', '\u1d20': 'v', '\u1d21': 'w', 'x': 'x', '\u028f': 'y',
        '\u1d22': 'z', '\u1d19': 'q',
        '\u0454': 'e', '\u03b7': 'n', '\u03c3': 'o', '\u03c5': 'u',
        '\u0443': 'y', '\u043d': 'h', '\u044f': 'r',
        '\u0404': 'e', '\u041d': 'h',
    }
    for stylized, plain in sc_map.items():
        if stylized != plain:
            text = text.replace(stylized, plain)
    return text

def to_bold_serif(c):
    c = c.upper()
    if 'A' <= c <= 'Z':
        return chr(ord(c) - ord('A') + 0x1D400)
    return c

def to_small_caps(c):
    c = c.lower()
    small_caps = {
        'a': '\u1d00', 'b': '\u0299', 'c': '\u1d04', 'd': '\u1d05', 'e': '\u1d07',
        'f': '\u0493', 'g': '\u0262', 'h': '\u029c', 'i': '\u026a', 'j': '\u1d0a',
        'k': '\u1d0b', 'l': '\u029f', 'm': '\u1d0d', 'n': '\u0274', 'o': '\u1d0f',
        'p': '\u1d18', 'q': '\u01eb', 'r': '\u0280', 's': 's', 't': '\u1d1b',
        'u': '\u1d1c', 'v': '\u1d20', 'w': '\u1d21', 'x': 'x', 'y': '\u028f',
        'z': '\u1d22'
    }
    return small_caps.get(c, c)

def stylize_word(word):
    if not word:
        return ""
    word = to_ascii(word)
    if not any(c.isalpha() for c in word):
        return word

    res = ""
    found_first = False
    for c in word:
        if c.isalpha() and not found_first:
            res += to_bold_serif(c)
            found_first = True
        elif c.isalpha():
            res += to_small_caps(c)
        else:
            res += c
    return res

def stylize_text(text):
    pattern = re.compile(r'(<[^>]+>|\{[^}]+\}|/[a-zA-Z_]+|-[a-zA-Z]+)')
    parts = pattern.split(text)

    normalized_parts = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            normalized_parts.append(to_ascii(part))
        else:
            normalized_parts.append(part)

    text = "".join(normalized_parts)

    parts = pattern.split(text)
    new_parts = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Sub-split by anything that isn't a sequence of English letters
            # We want to catch everything that is an alphabetical character or can be part of a word
            # But the logic was splitting by [^a-zA-Z]+
            sub_parts = re.split(r'([^a-zA-Z]+)', part)
            for sp in sub_parts:
                if sp and any(c.isalpha() for c in sp):
                    new_parts.append(stylize_word(sp))
                else:
                    new_parts.append(sp)
        else:
            new_parts.append(part)

    return "".join(new_parts)

def main():
    filepath = 'AloneX/locales/en.json'
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    new_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            new_data[key] = stylize_text(value)
        else:
            new_data[key] = value

    if "play_queued" in new_data:
        new_data["play_queued"] = new_data["play_queued"].replace("𝐏ʟᴀʏᴇᴅ 𝐁ʏ :</b> {3}</b></blockquote>", "𝐏ʟᴀʏᴇᴅ 𝐁ʏ :</b> {4}</b></blockquote>")

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=4, ensure_ascii=False)
        f.write('\n')

    print(f"Successfully stylized {filepath}")

if __name__ == "__main__":
    main()
