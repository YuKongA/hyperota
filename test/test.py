#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64, json, re, requests, os

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from gooey import Gooey, GooeyParser


# 生成上传数据
def generate_json(device, version, android, userId):
    data = {  # After testing, the commented out parts do not need to be assigned values.
        # "obv": "OS1.0", # ro.mi.os.version.name
        # "channel":"",  # Unknown
        # "sys": "0",  # Unknown
        # "bv": "816",  # bigversion
        "id": f"{userId}",  # userId
        # "sn": "0x0000000000000000",  # SN
        # "a": "0",  # Unknown
        # "b": "F" if "DEV" not in version else "X",  # MIUI branch
        "c": f"{android}",  # android version Build.VERSION.RELEASE
        # "unlock": "0",  # 1: bootloader is unlocked. 0: bootloader locked.
        "d": f"{device}",  # PRODUCT_DEVICE
        # "lockZoneChannel": "",  # Unknown
        "f": "1",  # Unknown, necessary
        "ov": f"{version}",  # ro.mi.os.version.incremental
        # "g": "00000000000000000000000000000000",  # Unknown, 32
        # "i": "0000000000000000000000000000000000000000000000000000000000000000",  # Unknown, 64
        # "i2": "0000000000000000000000000000000000000000000000000000000000000000",  # Unknown, 64
        # "isR": "0",  # ro.debuggable
        "l": "zh_CN",  # The locale. (for changelog)
        # "n": "ct",  # ro.carrier.name
        # "p": device,  # PRODUCT_DEVICE
        # "pb": "Xiaomi",  # "Redmi", PRODUCT_BRAND
        # "r": "CN",  # Sales regions.
        # MIUI version "MIUI-" + Build.VERSION.INCREMENTAL
        "v": f"miui-{version.replace('OS1', 'V816')}",
        # "sdk": "34" if android == "14" else "33",  # Android SDK
        # "pn": device,  # PRODUCT_NAME
        # "options": {
        # "zone": "1" if "_global" not in device else "2",  # ro.rom.zone
        # "hashId":"0000000000000000",
        # "ab": "1",  # Whether to support A/B update
        # "previewPlan": "0",
        # "sv": 3,
        # "av": "8.4.0", # com.android.update application version
        # "cv": version.replace('OS1', 'V816')
        # }
    }
    return json.dumps(data).replace(" ", "").replace("'", '"')


# AES加密
def miui_encrypt(json_request, securityKey, iv):
    cipher = AES.new(securityKey, AES.MODE_CBC, iv)
    padded_text = pad(json_request.encode("utf-8"), cipher.block_size)
    encrypted_text = cipher.encrypt(padded_text)
    encrypted_text = base64.urlsafe_b64encode(encrypted_text).decode("utf-8")
    return encrypted_text


# AES解密
def miui_decrypt(encrypted_text, securityKey, iv):
    cipher = AES.new(securityKey, AES.MODE_CBC, iv)
    encrypted_text = base64.urlsafe_b64decode(encrypted_text)
    decrypted_text = cipher.decrypt(encrypted_text)
    unpadded_text = unpad(decrypted_text, cipher.block_size).decode("utf-8")
    return json.loads(unpadded_text)


# 获取返回参数
def request(data):
    url = "https://update.miui.com/updates/miotaV3.php"
    response = requests.post(url=url, data=data).text
    return response


# 分析返回参数
def choose(name, s):
    current_rom_info = name.get("CurrentRom", {})
    rom_device = current_rom_info.get("device", "Unknown")
    rom_name = current_rom_info.get("name", "Unknown")
    rom_bigversion = current_rom_info.get("bigversion", "Unknown")
    rom_codebase = current_rom_info.get("codebase", "Unknown")
    rom_branch = current_rom_info.get("branch", "Unknown")
    rom_md5 = current_rom_info.get("md5", "Unknown")
    rom_filename = current_rom_info.get("filename", "Unknown")
    rom_filesize = current_rom_info.get("filesize", "Unknown")
    rom_changelog = current_rom_info.get("changelog", "Unknown")

    latset_rom_info = name.get("LatestRom", {})
    latset_rom_md5 = latset_rom_info.get("md5", "Unknown")
    latset_rom_filename = latset_rom_info.get("filename", "Unknown")

    if rom_branch == "F":
        rom_branch_log = "正式版 (每月构建, 末尾版本不为 0 的为内部测试构建)"
    elif rom_branch == "X":
        rom_branch_log = "开发版 (每周构建)"
    elif rom_branch == "D":
        rom_branch_log = "开发版内测 (每日构建, 有时候会转到开发版)"
    elif rom_branch == "T":
        rom_branch_log = "绝密版 (曾经的内测版及未通过测试的版本)"
    elif rom_branch == "I":
        rom_branch_log = "内部构建 (内部测试使用, 有时候会转到开发版)"
    else:
        rom_branch_log = "其他版本"

    if (rom_branch == "F" or rom_branch == "X") and rom_bigversion == "816":
        rom_name = "OS" + rom_name

    if rom_bigversion == "816":
        rom_bigversion = "HyperOS 1.0"

    if s == "1":
        s = "v1"
    else:
        s = "v2"

    rom_changelog = re.sub(
        r"\n\s*\n",
        "\n",
        json.dumps(rom_changelog, indent=2, ensure_ascii=False, allow_nan=True)
        .replace("[", "")
        .replace("]", "")
        .replace("{", "")
        .replace("}", "")
        .replace('"', "")
        .replace("txt:", ""),
    )

    if rom_name == "Unknown":
        result = "\n\n未获取到相关 ROM 信息\n\n"
    elif rom_filename == "Unknown":
        result = f"\ndevice: {rom_device}\nname: {rom_name}\ncodebase: Android {rom_codebase}\nbranch: {rom_branch_log}\ninterface: {s}\n"
    elif rom_md5 == latset_rom_md5:
        result = f"\ndevice: {rom_device}\nname: {rom_name}\nbigversion: {rom_bigversion}\ncodebase: Android {rom_codebase}\nbranch: {rom_branch_log}\ninterface: {s}\n\nfilename: {rom_filename}\nfilesize: {rom_filesize}\ndownload: https://ultimateota.d.miui.com/{rom_name}/{latset_rom_filename}\nchangelog:\n{rom_changelog}\n"
    else:
        result = f"\ndevice: {rom_device}\nname: {rom_name}\nbigversion: {rom_bigversion}\ncodebase: Android {rom_codebase}\nbranch: {rom_branch_log}\ninterface: {s}\n\nfilename: {rom_filename}\nfilesize: {rom_filesize}\ndownload: https://bigota.d.miui.com/{rom_name}/{rom_filename}\nchangelog:\n{rom_changelog}\n"

    print(result)


# 使用提示
def usage():
    print(
        "\nUsage: XiaomiUpdateInfo.py codename rom_version android_version\n\nExample: \n(1) XiaomiUpdateInfo.py houji OS1.0.20.0.UNCCNXM 14\n(2) XiaomiUpdateInfo.py fuxi V14.0.5.0.UMCCNXM 14\n"
    )
    exit()


# 主程序
@Gooey(
    program_name="Xiaomi Update Info",
    show_restart_button=False,
    header_show_title=False,
    language="Chinese",
    terminal_font_family="微软雅黑",
)
def main():
    settings_msg = "  一个简单的 HyperOS/MIUI 更新链接获取脚本"
    parser = GooeyParser(description=settings_msg)
    parser.add_argument(
        "设备代号",
        widget="FilterableDropdown",
        choices=[
            "garnet",
            "zircon",
            "gold",
            "sapphiren",
            "sapphire",
            "aurora",
            "manet",
            "vermeer",
            "aristotle",
            "corot",
            "river",
            "xun",
            "babylon",
            "fire",
            "sky",
            "heat",
            "garnet",
            "houji",
            "shennong",
            "pipa",
            "yudi",
            "yuechu",
            "pearl",
            "ishtar",
            "sweet_k6a",
            "liuqin",
            "marble",
            "water",
            "tapas",
            "topaz",
            "monet",
            "vangogh",
            "thyme",
            "venus",
            "courbet",
            "star",
            "renoir",
            "agate",
            "vili",
            "lisa",
            "pissarroin",
            "cupid",
            "zeus",
            "psyche",
            "daumier",
            "mayfly",
            "unicorn",
            "thor",
            "taoyao",
            "plato",
            "fuxi",
            "nuwa",
            "toco",
            "cetus",
            "odin",
            "zizhan",
            "nabu",
            "elish",
            "enuma",
            "dagu",
            "mona",
            "zijin",
            "ziyi",
            "merlin",
            "lancelot",
            "dandelion",
            "angelica",
            "angelican",
            "cattail",
            "selene",
            "dandelion_c3l2",
            "fog",
            "rock",
            "earth",
            "biloba",
            "lime",
            "cannon",
            "gauguin",
            "joyeuse",
            "excalibur",
            "curtana",
            "mojito",
            "curtana_in_rf",
            "sweet",
            "camellia",
            "chopin",
            "rosemary",
            "lilac",
            "evergo",
            "pissarro",
            "spes",
            "spesn",
            "veux",
            "fleur",
            "viva",
            "vida",
            "light",
            "lightcm",
            "opal",
            "xaga",
            "sunstone",
            "ruby",
            "redwood",
            "apollo",
            "alioth",
            "haydn",
            "ares",
            "munch",
            "ingres",
            "rubens",
            "matisse",
            "diting",
            "mondrian",
            "socrates",
            "rembrandt",
            "yunluo",
            "ice",
            "angelicain",
            "frost",
            "citrus",
            "evergreen",
            "rosemary_p",
            "surya",
            "vayu",
            "moonstone",
        ],
    )
    parser.add_argument("系统版本", widget="TextField")
    parser.add_argument(
        "安卓版本", widget="Dropdown", choices=["12", "13", "14"], default="14"
    )
    parser.add_argument("接口版本", widget="Dropdown", choices=["v1", "v2"], default="v1")
    parser.add_argument("response", widget="FileChooser", help="v2 接口需要",default="null")
    parser.add_argument("cookies", widget="FileChooser", help="v2 接口需要",default="null")
    
    argv = parser.parse_args()
    device = argv.设备代号
    version = argv.系统版本
    android = argv.安卓版本
    interface = argv.接口版本.replace("v", "")
    userId = ""
    securityKey = b"miuiotavalided11"
    iv = b"0102030405060708"
    if interface == "2" and os.path.isfile(argv.response):
        with open(argv.response, "r", encoding="utf-8") as file:
            response = json.load(file)
            userId = response["userId"]
            securityKey = base64.b64decode(response["ssecurity"])
    json_data = generate_json(device, version, android, userId)
    q = miui_encrypt(json_data, securityKey, iv)
    t = ""
    if interface == "2" and os.path.isfile(argv.cookies):
        with open(argv.cookies, "r", encoding="utf-8") as file:
            cookies = json.load(file)
            t = cookies["serviceToken"]
    if t == "":
        interface = "1"
    print(q, t, interface)
    post_data = {"q": q, "t": t, "s": interface}
    encrypted_text = request(post_data)
    decrypted_text = miui_decrypt(encrypted_text, securityKey, iv)
    choose(decrypted_text, interface)


if __name__ == "__main__":
    main()