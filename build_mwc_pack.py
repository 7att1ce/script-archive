from __future__ import annotations

# csv：
# 用于正确读取 CSV 文件。
# 不能使用 line.split(",")，因为部分歌曲名本身包含逗号。
import csv

# re：
# Python 的正则表达式库。
# 用于识别 osu! 文件中的字段和背景事件。
import re

# shutil：
# 用于复制文件，并保留源文件的时间等元数据。
import shutil

# unicodedata：
# 用于统一处理 Unicode 字符，例如全角字符和半角字符。
import unicodedata

# difflib：
# Python 标准库中的文本相似度比较工具。
# SequenceMatcher 可以计算两个字符串的相似程度。
from difflib import SequenceMatcher

# pathlib：
# 推荐用于处理文件路径，比手动拼接字符串更安全。
from pathlib import Path


# __file__ 是当前 Python 脚本自身的路径。
# resolve() 可以得到绝对路径。
# parent 表示脚本所在的文件夹。
#
# 如果脚本位于：
# c:\Users\user\Desktop\mwcpack\build_mwc_pack.py
#
# 那么 ROOT 就是：
# c:\Users\user\Desktop\mwcpack
ROOT = Path(__file__).resolve().parent


# 比赛谱面 CSV 文件
CSV_PATH = ROOT / "beatmaps_info.csv"

# 存放原始谱面文件夹的目录
SOURCE_DIR = ROOT / "beatmaps"

# 输出目录
OUTPUT_DIR = ROOT / "output"

# 输出谱面包的名称
PACK_NAME = "osu!mania 4K World Cup 2026 Pack"

def normalize(value: str) -> str:
    """
    将字符串转换成适合比较的形式。

    例如：

        "OCTAGRAM ~Dai Happyaku"
        "OCTAGRAM _Dai Happyaku"

    经过处理后，可以得到更加接近的字符串。

    这里不直接修改实际文件名，只用于计算相似度。
    """

    # NFKC 会把部分全角字符转换为对应的半角字符，
    # 也可以统一一些 Unicode 表示形式。
    value = unicodedata.normalize("NFKC", value)

    # 不区分大小写。
    value = value.lower()

    # 源文件夹名中有些特殊字符会被替换成下划线。
    # 因此将下划线视为空格。
    value = value.replace("_", " ")

    # Windows 文件名中，单引号和撇号的表现可能不同。
    # 比较时直接去掉它们。
    value = value.replace("'", "")

    # 部分文件夹名使用下划线代替波浪号。
    # 这里将波浪号视为空格。
    value = value.replace("~", " ")

    # 将 & 和 and 视作近似写法。
    value = value.replace("&", " and ")

    # 只保留英文字母和数字。
    #
    # 例如：
    # "Hyadain's Jojo Yujo"
    # 会变成：
    # "hyadainsjojoyujo"
    #
    # 这样可以忽略空格、括号、冒号、感叹号等符号差异。
    return re.sub(r"[^a-z0-9]+", "", value)


def similarity(left: str, right: str) -> float:
    """
    计算两个字符串的相似度。

    返回值范围是 0 到 1：

        1.0  表示完全相同
        0.0  表示完全不同

    SequenceMatcher 是 Python 标准库提供的基础文本比较工具，
    不需要安装第三方库。
    """

    # 先将两个字符串规范化，再进行比较。
    normalized_left = normalize(left)
    normalized_right = normalize(right)

    return SequenceMatcher(
        None,
        normalized_left,
        normalized_right,
    ).ratio()


def find_case_insensitive(directory: Path, filename: str) -> Path:
    """
    在目录中查找文件名相同、但不区分大小写的文件。

    osu! 文件中的背景可能写成：

        BG.png

    实际文件名可能是：

        bg.png

    Windows 通常不区分大小写，但 Python 的路径比较仍然可能受到
    实际文件名大小写影响，所以这里手动进行大小写无关匹配。
    """

    # casefold() 比 lower() 更适合进行不区分大小写的字符串比较。
    target_name = filename.casefold()

    # directory.iterdir() 会遍历目录下的所有文件和文件夹。
    for path in directory.iterdir():
        if path.name.casefold() == target_name:
            return path

    # 找不到时抛出异常，停止处理并显示具体目录。
    raise FileNotFoundError(
        f"在目录 {directory} 中找不到文件：{filename}"
    )


def parse_osu_sections(lines: list[str]) -> dict[str, list[int]]:
    """
    分析 osu! 文件的区块结构。

    osu! 文件通常由以下区块组成：

        [General]
        [Editor]
        [Metadata]
        [Difficulty]
        [Events]
        [TimingPoints]
        [HitObjects]

    返回值是一个字典，例如：

        {
            "General": [2, 3, 4, ...],
            "Metadata": [20, 21, 22, ...],
            "Events": [35, 36, 37, ...],
        }

    数字表示这些行在整个文件中的行号索引。
    """

    sections: dict[str, list[int]] = {}

    # current_section 保存当前正在读取的区块名称。
    current_section = ""

    # enumerate() 同时提供：
    # index：行号索引，从 0 开始
    # line：当前行内容
    for index, line in enumerate(lines):
        stripped_line = line.strip()

        # 判断当前行是否是区块标题。
        if (
            stripped_line.startswith("[")
            and stripped_line.endswith("]")
        ):
            # 去掉左右方括号。
            #
            # [Metadata]
            # 会变成：
            # Metadata
            current_section = stripped_line[1:-1]

            # 为新区块创建一个空的行号列表。
            sections[current_section] = []

        elif current_section:
            # 如果当前已经进入某个区块，
            # 就记录当前行属于哪个区块。
            sections[current_section].append(index)

    return sections


def get_osu_value(
    lines: list[str],
    sections: dict[str, list[int]],
    section: str,
    key: str,
) -> str:
    """
    从指定 osu! 区块中读取字段值。

    例如：

        get_osu_value(lines, sections, "General", "AudioFilename")

    会读取：

        AudioFilename: audio.mp3

    并返回：

        audio.mp3
    """

    # 只检查指定区块中的行，不扫描整个文件。
    for index in sections.get(section, []):
        line = lines[index]

        # osu! 文件的字段格式通常是：
        #
        # Key:Value
        #
        # 例如：
        # AudioFilename: audio.mp3
        if line.startswith(key + ":"):
            # split(":", 1) 只切割第一个冒号。
            # 这样可以避免字段值中包含冒号时被错误切割。
            value = line.split(":", 1)[1]

            # strip() 去除字段值两侧的空格和换行符。
            return value.strip()

    # 找不到字段时直接报错。
    # 这样可以避免程序静默生成错误谱包。
    raise ValueError(
        f"在 [{section}] 区块中找不到字段：{key}"
    )


def replace_osu_value(
    lines: list[str],
    sections: dict[str, list[int]],
    section: str,
    key: str,
    value: str,
) -> None:
    """
    修改 osu! 文件中的指定字段。

    例如：

        replace_osu_value(
            lines,
            sections,
            "Metadata",
            "Title",
            "osu!mania 4K World Cup 2026 Pack",
        )

    会将：

        Title:Extragalactic

    修改成：

        Title:osu!mania 4K World Cup 2026 Pack
    """

    for index in sections.get(section, []):
        if lines[index].startswith(key + ":"):
            # 保留原来的换行风格。
            # Windows 文件通常使用 \r\n，
            # Linux 文件通常使用 \n。
            newline = "\n" if lines[index].endswith("\n") else ""

            lines[index] = f"{key}:{value}{newline}"
            return

    raise ValueError(
        f"在 [{section}] 区块中找不到字段：{key}"
    )


def find_background_filename(
    lines: list[str],
    sections: dict[str, list[int]],
) -> str:
    """
    从 osu! 文件的 [Events] 区块中寻找背景图片文件名。

    常见格式：

        0,0,"bg.jpg",0,0

    也可能是：

        0,0,"BG.png",0,0

    这里只接受常见的图片扩展名，不会把视频或其他资源当成背景。
    """

    # ^ 表示从行首开始匹配。
    # \s* 允许行首存在空格。
    # 0,\d+ 匹配类似 0,0 或 0,1234。
    # ([^"]+\.(...)) 捕获带图片扩展名的文件名。
    image_pattern = re.compile(
        r'^\s*0,\d+,"([^"]+\.(?:jpg|jpeg|png|gif|webp))"',
        re.IGNORECASE,
    )

    for index in sections.get("Events", []):
        match = image_pattern.match(lines[index])

        if match:
            # Path(...).name 可以去掉可能存在的路径部分。
            #
            # 例如：
            # "folder/bg.jpg"
            # 会变成：
            # "bg.jpg"
            return Path(match.group(1)).name

    raise ValueError("在 [Events] 区块中找不到背景图片")


def replace_background_filename(
    lines: list[str],
    sections: dict[str, list[int]],
    new_filename: str,
) -> None:
    """
    修改 [Events] 中背景事件引用的文件名。

    例如：

        0,0,"bg.jpg",0,0

    修改为：

        0,0,"roundof16rc1.jpg",0,0
    """

    # 将一行拆分为三部分：
    #
    # group(1)：开头和第一个引号
    # group(2)：旧图片文件名
    # group(3)：文件名后面的内容
    image_pattern = re.compile(
        r'^(\s*0,\d+,\")([^\"]+)(\".*)$',
        re.IGNORECASE,
    )

    for index in sections.get("Events", []):
        match = image_pattern.match(lines[index])

        if not match:
            continue

        old_filename = match.group(2)

        # 只修改图片事件。
        # 这样不会误修改视频或其他 Events 行。
        if Path(old_filename).suffix.lower() in {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
        }:
            newline = "\n" if lines[index].endswith("\n") else ""

            lines[index] = (
                f"{match.group(1)}"
                f"{new_filename}"
                f"{match.group(3)}"
                f"{newline}"
            )


def choose_folder(beatmap: str) -> Path:
    """
    根据 CSV 中的 beatmap 文本选择最相似的源文件夹。

    例如 CSV 中的 beatmap：

        katter - DOPA BRAT (hi19hi19) [Stage 1: Absorption]

    可能对应文件夹：

        2600425 katter - DOPA BRAT

    因为源文件夹名称通常包含谱面 ID，
    所以这里使用相似度，而不是完全匹配。
    """

    # 只获取 mwc4k2026 目录下的一级文件夹。
    folders = [
        path
        for path in SOURCE_DIR.iterdir()
        if path.is_dir()
    ]

    if not folders:
        raise FileNotFoundError(
            f"源目录中没有找到文件夹：{SOURCE_DIR}"
        )

    # max(..., key=...) 会返回相似度最高的文件夹。
    return max(
        folders,
        key=lambda folder: similarity(beatmap, folder.name),
    )


def choose_osu_file(folder: Path, beatmap: str) -> Path:
    """
    在已经选中的谱面文件夹中选择最相似的 .osu 文件。

    同一个文件夹可能存在多个难度，例如：

        song [Hard].osu
        song [Hard 1.05x].osu

    因此不能只选择第一个 .osu 文件。
    """

    osu_files = list(folder.glob("*.osu"))

    if not osu_files:
        raise FileNotFoundError(
            f"文件夹中没有找到 .osu 文件：{folder}"
        )

    # 使用谱面文件名和 CSV 中 beatmap 的相似度进行选择。
    return max(
        osu_files,
        key=lambda osu_file: similarity(
            beatmap,
            osu_file.stem,
        ),
    )


def compact_round(round_name: str) -> str:
    """
    生成音频和背景文件的新文件名主体。

    规则：

        Round of 16 RC1
        -> roundof16rc1

    split() 会按照任意空白字符切分，
    join() 再把所有部分连接起来。
    """

    return "".join(round_name.split()).lower()

def check_similarity(left, right):
    score = similarity(left, right)

    if score < 0.5:
        raise ValueError(
            f"匹配度过低：{left} -> "
            f"{right} ({score:.3f})"
        )

def process_one(round_name: str, beatmap: str) -> None:
    """
    处理 CSV 中的一行谱面。

    处理流程：

    1. 找到最相似的源文件夹。
    2. 找到最相似的 .osu 文件。
    3. 读取 .osu 中的音频和背景引用。
    4. 将三个文件复制到 output。
    5. 重命名复制后的文件。
    6. 修改 output 中的 .osu 文件内容。
    """

    # 第一步：选择源文件夹。
    source_folder = choose_folder(beatmap)
    # check_similarity(beatmap, source_folder.name)

    # 第二步：选择具体 .osu 文件。
    source_osu = choose_osu_file(
        source_folder,
        beatmap,
    )
    # check_similarity(beatmap, source_osu.stem)

    # 以 UTF-8 读取 osu! 文件。
    #
    # utf-8-sig 可以兼容普通 UTF-8 和带 BOM 的 UTF-8 文件。
    #
    # splitlines(keepends=True) 会保留每行结尾的换行符，
    # 这样修改文件后不会破坏原本的行结构。
    osu_lines = source_osu.read_text(
        encoding="utf-8-sig",
    ).splitlines(keepends=True)

    # 分析 osu! 文件中的区块。
    osu_sections = parse_osu_sections(osu_lines)

    # 从 [General] 中读取音频文件名。
    source_audio_name = get_osu_value(
        osu_lines,
        osu_sections,
        "General",
        "AudioFilename",
    )

    # 从 [Events] 中读取背景图片文件名。
    source_background_name = find_background_filename(
        osu_lines,
        osu_sections,
    )

    # 根据 osu! 文件中的引用，在同一个源文件夹中寻找实际文件。
    source_audio = find_case_insensitive(
        source_folder,
        Path(source_audio_name).name,
    )

    source_background = find_case_insensitive(
        source_folder,
        source_background_name,
    )

    # 生成新文件名主体。
    #
    # 例如：
    # Round of 16 RC1
    # -> roundof16rc1
    round_filename = compact_round(round_name)

    # 音频和背景保留原扩展名。
    output_audio_name = (
        round_filename + source_audio.suffix
    )

    output_background_name = (
        round_filename + source_background.suffix
    )

    # output 中三个文件的目标路径。
    output_audio = OUTPUT_DIR / output_audio_name
    output_background = OUTPUT_DIR / output_background_name

    output_osu = OUTPUT_DIR / (
        f"Various Artists - {PACK_NAME} "
        f"(Various Mappers) [{round_name}].osu"
    )

    # 先复制源文件。
    #
    # 这一步非常重要：
    # 之后只修改 output 中的副本，不修改 mwc4k2026 中的源文件。
    shutil.copy2(source_audio, output_audio)
    shutil.copy2(source_background, output_background)
    shutil.copy2(source_osu, output_osu)

    # 重新读取 output 中的 .osu 文件。
    # 后续所有修改都针对这个副本。
    output_lines = output_osu.read_text(
        encoding="utf-8-sig",
    ).splitlines(keepends=True)

    output_sections = parse_osu_sections(output_lines)

    # 修改 [General] 中的音频文件引用。
    replace_osu_value(
        output_lines,
        output_sections,
        "General",
        "AudioFilename",
        output_audio_name,
    )

    # 修改 [Metadata] 中的固定字段。
    replace_osu_value(
        output_lines,
        output_sections,
        "Metadata",
        "Title",
        PACK_NAME,
    )

    replace_osu_value(
        output_lines,
        output_sections,
        "Metadata",
        "TitleUnicode",
        PACK_NAME,
    )

    replace_osu_value(
        output_lines,
        output_sections,
        "Metadata",
        "Artist",
        "Various Artists",
    )

    replace_osu_value(
        output_lines,
        output_sections,
        "Metadata",
        "ArtistUnicode",
        "Various Artists",
    )

    replace_osu_value(
        output_lines,
        output_sections,
        "Metadata",
        "Creator",
        "Various Mappers",
    )

    # Version 使用：
    #
    # <round>: <beatmap>
    #
    # 例如：
    #
    # Round of 16 RC1:
    # Isekaijoucho x KAF - Shin'en (Hylotl) [Nadir]
    replace_osu_value(
        output_lines,
        output_sections,
        "Metadata",
        "Version",
        f"{round_name}: {beatmap}",
    )

    # 将谱面 ID 修改为自定义谱包使用的固定值。
    replace_osu_value(
        output_lines,
        output_sections,
        "Metadata",
        "BeatmapID",
        "0",
    )

    replace_osu_value(
        output_lines,
        output_sections,
        "Metadata",
        "BeatmapSetID",
        "-1",
    )

    # 修改 [Events] 中背景图片的引用。
    replace_background_filename(
        output_lines,
        output_sections,
        output_background_name,
    )

    # 将修改后的内容写回 output 中的 .osu 文件。
    output_osu.write_text(
        "".join(output_lines),
        encoding="utf-8",
    )

    # 输出当前处理结果，方便检查匹配是否正确。
    print(f"已处理：{round_name}")
    print(f"  CSV beatmap：{beatmap}")
    print(f"  源文件夹：{source_folder.name}")
    print(f"  源谱面：{source_osu.name}")
    print(f"  输出谱面：{output_osu.name}")
    print()


def main() -> None:
    """
    程序入口。

    负责：

    1. 创建 output 文件夹。
    2. 读取 CSV。
    3. 逐行调用 process_one()。
    """

    # exist_ok=True 表示：
    # 如果 output 已经存在，不会报错。
    OUTPUT_DIR.mkdir(exist_ok=True)

    # newline="" 是 csv 官方推荐写法，
    # 可以避免 Windows 换行符导致空行或解析异常。
    with CSV_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:

        # DictReader 会把第一行作为字段名。
        #
        # CSV 第一行是：
        # round,beatmap
        #
        # 每一行会变成：
        # {
        #     "round": "...",
        #     "beatmap": "..."
        # }
        rows = csv.DictReader(csv_file)

        # enumerate(..., start=2) 是为了让错误提示中的行号
        # 与文本编辑器中的实际 CSV 行号一致。
        # 第一行是表头，所以数据从第 2 行开始。
        for row_number, row in enumerate(rows, start=2):
            # get() 可以避免字段不存在时直接触发 KeyError。
            # strip() 去掉字段前后的空格和换行。
            round_name = (row.get("round") or "").strip()
            beatmap = (row.get("beatmap") or "").strip()

            # CSV 中如果存在空行或缺失字段，直接报错。
            if not round_name or not beatmap:
                raise ValueError(
                    f"CSV 第 {row_number} 行内容无效：{row}"
                )

            # 处理当前谱面。
            process_one(
                round_name,
                beatmap,
            )


# 只有直接运行这个脚本时，才会执行 main()。
#
# 如果以后从其他 Python 文件 import 这个脚本，
# main() 不会自动执行。
if __name__ == "__main__":
    main()