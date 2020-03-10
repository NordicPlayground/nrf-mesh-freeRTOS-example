from sys import argv, version_info
import json
import re
import os.path
import xml.etree.ElementTree as et


FREERTOS_SOURCE_PATH_REGEX = r"\$\([^\)]*\)\/external\/freertos\/source\/include;"
FREERTOS_PATH_REGEX = r"\$\([^\)]*\)\/external\/freertos"
MESH_CORE_PATH_REGEX = r"(\.\.\/)+mesh\/core\/include;"


def load_config(config_file_path):
    with open(config_file_path, "r") as f:
        config = json.load(f)
    return config


def load_emproject(emproject_file_path):
    return et.parse(emproject_file_path)


def save_emproject(emproject_file_path, project_tree):
    with open(emproject_file_path, "w") as f:
        f.write("<!DOCTYPE CrossStudio_Project_File>\n")
        if version_info >= (3, 0):
            f.write(str(et.tostring(project_tree), "ascii"))
        else:
            f.write(et.tostring(project_tree))


def make_emproject_path(out_dir, config):
    return os.path.normpath(os.path.join(out_dir, config["target"]["name"].replace(".", "_")) + ".emProject")


def unix_path_get(path):
    return os.path.normpath(path).replace("\\", "/")

# - Remove mesh core and freertos source include paths from common config
# - Find any folders containing freertos files, add the correct include paths and set output directory
# - Set the correct include paths on any remaining folders


def main(config_file_path, out_dir, *args):
    config = load_config(config_file_path)
    emproject_path = make_emproject_path(out_dir, config)
    root = load_emproject(emproject_path)
    common_cfg = root.find("./project/configuration[@Name='Common']")
    debug_cfg = root.find("./configuration[@Name='Debug']")
    common_includes = common_cfg.attrib["c_user_include_directories"]
    obj_directory_base = debug_cfg.attrib["build_intermediate_directory"]  # Assume that this is used for all configs
    freertos_source_matches = re.search(FREERTOS_SOURCE_PATH_REGEX, common_includes)
    mesh_core_matches = re.search(MESH_CORE_PATH_REGEX, common_includes)
    mesh_core_path = mesh_core_matches.group(0)
    freertos_source_path = freertos_source_matches.group(0)
    cleaned_common_includes = re.sub(FREERTOS_SOURCE_PATH_REGEX + "|" + MESH_CORE_PATH_REGEX, "", common_includes)
    common_cfg.attrib["c_user_include_directories"] = cleaned_common_includes
    folders = root.findall("./project/folder")
    for folder in folders:
        is_freertos = False
        for file in folder.findall("./file"):
            if re.match(FREERTOS_PATH_REGEX, file.attrib["file_name"]) is not None:
                is_freertos = True
                break
        folder_config = folder.find("./configuration[@Name='Common']")
        if folder_config is None or len(folder_config) == 0:
            folder_config = et.SubElement(folder, "configuration")
            folder_config.attrib["Name"] = "Common"
        if "c_user_include_directories" not in folder_config.attrib:
            folder_config.attrib["c_user_include_directories"] = ""
        elif len(folder_config.attrib["c_user_include_directories"]) > 0:
            if folder_config.attrib["c_user_include_directories"] != ";":
                folder_config.attrib["c_user_include_directories"] += ";"
        if is_freertos:
            folder_config.attrib["c_user_include_directories"] += freertos_source_path + mesh_core_path
            folder_config.attrib["build_intermediate_directory"] = unix_path_get(
                os.path.join(obj_directory_base, "conflict"))
        else:
            folder_config.attrib["c_user_include_directories"] += mesh_core_path + freertos_source_path
    save_emproject(emproject_path, root.getroot())
    print("Patched: " + emproject_path)


if __name__ == "__main__":
    main(*argv[1:])
