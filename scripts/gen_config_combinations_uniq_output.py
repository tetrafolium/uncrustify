from __future__ import print_function  # python >= 2.6
from os import makedirs, path, listdir, rename, remove
from subprocess import Popen
from filecmp import cmp
from glob import iglob
from shutil import rmtree
from json import loads as json_loads, dump as json_dump
from sys import stderr, argv, path as sys_path
"""
gen_config_combinations_uniq_output.py

Creates from a given set of options all possible option settings
combinations, formats files with those and displays how much non equal
formatted outputs have been created.

Expects arg1 to be a filepath to a json config file
  (see config example below)

:author:  Daniel Chumak
:license: GPL v2+
"""

# config = {
#     "option_settings": {
#         "AT_BOOL": ["False", "True"],
#         "AT_IARF": ["ignore", "add", "remove", "force"],
#         "AT_POS": ["ignore", "join", "lead", "lead_break", "lead_force",
#                    "trail", "trail_break", "trail_force"],
#         "AT_LINE": ["auto", "lf", "crlf", "cr"],
#         "AT_NUM": [-2, -1, 0, 1, 2, 3],
#         "AT_UNUM": [0, 1, 2, 3]
#     },
#     "options": [{
#         "name": "nl_func_type_name",
#         "type": "AT_IARF"
#     }, {
#         "name": "nl_template_class",
#         "type": "AT_IARF"
#     }],
#     "out_dir": "./Out",
#     "in_files": ["./t.cpp", "./t2.cpp"],
#     "unc_bin": "../build/uncrustify",
#     "cleanup_lvl": 2,
#     "force_cleanup": false,
#     "json_output": false
# }
#


def len_index_combinations(max_indices):
    """generator function that yields a list starting from
       n_0 = 0,       ... n_m-1 = 0,         n_m = 0
       ...
       n_0 = 0,       ... n_m-1 = 0,         n_m = n_m_max
       ...
       n_0 = 0,       ... n_m-1 = 1,         n_m = 0
       n_0 = 0,       ... n_m-1 = 1,         n_m = 1
       ...
       n_0 = 0,       ... n_m-1 = n_m-1_max, n_m = n_m_max
       ...
       n_0 = n_0_max, ... n_m-1 = n_m-1_max, n_m = n_m_max


    :param max_indices: list of max values every position is going to reach

    :yield: list of values at the current step
    """

    fields = len(max_indices)
    accu = [0] * fields

    # increment last position n, on max val move pos by one (n-1) and increment
    # if (n-1) is max move again (n-2) and increment, ...
    pos = fields
    while pos >= 0:
        yield (accu)

        pos = fields - 1
        accu[pos] += 1

        # on reaching max reset value, move pos and increment at pos
        while pos >= 0 and accu[pos] >= max_indices[pos]:
            accu[pos] = 0
            pos -= 1

            if pos >= 0:
                accu[pos] += 1


def write_config_files(config):
    """Writes a configuration file for each possible combination of 'option'
       settings

    :param config: configuration object, expects that it was processed by
                   check_config
    """

    options_len = len(config["options"])

    # populate len_options with amount of settings for the types of each option
    len_options = [0] * options_len
    for i in range(options_len):
        option_setting = config["options"][i]["type"]
        len_options[i] = len(config["option_settings"][option_setting])

    # write configuration files, one per possible combination
    for combination in len_index_combinations(len_options):
        len_indices = len(combination)

        # generate output filepath
        file_path = config['out_dir'] + "/"
        for i in range(len_indices):
            option_name = config["options"][i]["name"]
            file_path += ("%s__" % option_name)
        for i in range(len_indices):
            option_type = config["options"][i]["type"]
            option_setting = combination[i]
            file_path += ("%d__" % option_setting)
        file_path += "unc.cfg"

        # write configuration file
        with open(file_path, 'w') as f:
            for i in range(len_indices):
                option_name = config["options"][i]["name"]
                option_type = config["options"][i]["type"]
                option_setting = config["option_settings"][option_type][
                    combination[i]]

                f.write("%s = %s\n" % (option_name, option_setting))


def gen_equal_output_map(config):
    """Formats 'in_files' with configs inside the 'out_dir' with Uncrustify and
       groups formatted files with equal content together.
       Expects config filename format generated by write_config_files

    :param config: configuration object, expects that it was processed by
                   check_config
    :return: dict of files with equal content
                     key   -- group index
                     value -- filepath list
    """

    # maps that will hold configurations that produce the same formatted files
    equal_output_map = {}
    # map len counter
    map_val_idx = 0

    # iterate through all generated config file names

    for cfg_path in sorted(iglob('%s/*.cfg' % config["out_dir"])):
        for in_file_idx in range(len(config["in_files"])):
            # extract substring form config gile name (removes __unc.cfg)
            splits_file = cfg_path.split("__unc")
            if len(splits_file) < 1:
                raise Exception('split with "__unc" | Wrong split len: %d' %
                                len(splits_file))

            out_path = ("%s__%d" % (splits_file[0], in_file_idx))

            # gen formatted files with uncrustify binary
            proc = Popen([
                config["unc_bin"],
                "-c",
                cfg_path,
                "-f",
                config["in_files"][in_file_idx],
                "-o",
                out_path,
            ])
            proc.wait()
            if proc.returncode != 0:
                continue

            # populate 'equal_output_map' map
            if len(equal_output_map) == 0:
                equal_output_map[0] = [out_path]
                map_val_idx += 1
            else:
                found_flag = False
                for i in range(map_val_idx):
                    # compare first file of group i with the generated file
                    if cmp(equal_output_map[i][0], out_path):
                        equal_output_map[i].append(out_path)
                        found_flag = True
                        break
                # create new group if files do not match
                if not found_flag:
                    equal_output_map[map_val_idx] = [out_path]
                    map_val_idx += 1

    return equal_output_map


def gen_output_dict(config, equal_output_map):
    """Makes an output dict with the generated results.

    :param config: configuration object, expects that it was processed by
                   check_config

    :param equal_output_map: dict of files with equal content,
                             expects format generated by gen_equal_output_map
    :return: output dict, format:
             copies objects option_settings, options and in_files (renamed as
             files) from the config object. Additionally has the object groups
             that holds gourp - file - settings combination data
             format:
                groups = [ [fileIdx0[
                               [settingIdx0, settingIdx1, ...],
                               [settingIdx0, settingIdx1, ...] ] ]
                           [fileIdx1[
                               [settingIdx0, settingIdx1, ...],
                               [settingIdx0, settingIdx1, ...] ] ]
                         ]
    """

    output_dict = {
        "option_settings": config["option_settings"],
        "options": config["options"],
        "files": config["in_files"],
        "groups": []
    }

    options_len = len(output_dict["options"])
    files_len = len(output_dict["files"])

    for key in equal_output_map:
        group_dict = []
        for file_arr_idx in range(files_len):
            group_dict.append([])

        for list_value in equal_output_map[key]:
            split = list_value.rsplit("/", 1)
            split = split[len(split) - 1].split("__")
            split_len = len(split)

            # n option names + n option values + file idx
            if split_len < options_len * 2 + 1:
                print(" wrong split len on  %s\n" % list_value, file=stderr)
                continue

            file_idx = int(split[split_len - 1])
            file_combinations = [
                int(i) for i in split[options_len:split_len - 1]
            ]

            group_dict[file_idx].append(file_combinations)

        output_dict["groups"].append(group_dict)

    return output_dict


def write_output_dict_pretty(out_dict, out_path):
    """pretty prints the output dict into a file

    :param out_dict: dict that will be printed, expects format generated by
                     gen_output_dict

    :param out_path: output filepath
    """

    group_id = 0
    options_len = len(out_dict["options"])

    with open(out_path, 'w') as f:

        f.write("Files:\n")
        for in_file_idx in range(len(out_dict["files"])):
            f.write("    %d: %s\n" %
                    (in_file_idx, out_dict["files"][in_file_idx]))

        f.write("\nOptions:\n")
        for option_idx in range(options_len):
            f.write("    %d: %s\n" %
                    (option_idx, out_dict["options"][option_idx]["name"]))
        f.write("\n\n")

        for group in out_dict["groups"]:
            f.write("Group: %d\n" % group_id)
            group_id += 1

            for file_idx in range(len(group)):
                file = group[file_idx]

                for combinations in file:
                    combination_strings = []
                    for combination_idx in range(len(combinations)):

                        combination_id = combinations[combination_idx]
                        combination_string = out_dict["option_settings"][
                            out_dict["options"][combination_idx]
                            ["type"]][combination_id]
                        combination_strings.append(str(combination_string))
                    f.write("    (%s: %s)\n" %
                            (file_idx, " - ".join(combination_strings)))
            f.write("\n")


def load_config(file_path):
    """reads a file and parses it as json

    :param file_path: path to the json file

    :return: json object
    """

    with open(file_path, 'r') as f:
        string = f.read()
        json = json_loads(string)

    return json


def make_abs_path(basis_abs_path, rel_path):
    return path.normpath(path.join(basis_abs_path, rel_path))


def check_config(config, cfg_path=""):
    """checks if the provided config has all needed options, sets default
       settings for optional options and transform relative paths into absolute
       paths.

    :param config: config dict that will be checked

    :param cfg_path: if not empty transforms relative to absolute paths,
                     paths will be based upon the cfg_path.
    """

    extend_relative_paths = True if len(cfg_path) > 0 else False
    cfg_path = path.abspath(path.dirname(cfg_path))

    # --------------------------------------------------------------------------

    if "option_settings" not in config:
        raise Exception("config file: 'option_settings' missing")

    if len(config["option_settings"]) == 0:
        raise Exception("config file: 'option_settings' values missing")

    # --------------------------------------------------------------------------

    if "options" not in config:
        raise Exception("config file: 'options' missing")

    if len(config["options"]) < 2:
        raise Exception("config file: 'options' min. two options needed")

    for option_obj in config["options"]:
        if "name" not in option_obj:
            raise Exception("config file: 'options[{}]' name missing")
        if "type" not in option_obj:
            raise Exception("config file: 'options[{}]' type missing")
        if option_obj["type"] not in config["option_settings"]:
            raise Exception(
                "config file: 'options[{type='%s'}]' not in option_"
                "settings" % option_obj["type"])

    # --------------------------------------------------------------------------

    if "out_dir" not in config:
        raise Exception("config file: 'out_dir' missing")

    if len(config['out_dir']) == 0:
        raise Exception("config file: 'out_dir' value missing")

    if extend_relative_paths and not path.isabs(config['out_dir']):
        config['out_dir'] = make_abs_path(cfg_path, config['out_dir'])

    # --------------------------------------------------------------------------

    if "in_files" not in config:
        raise Exception("config file: 'in_files' missing")

    if len(config['in_files']) == 0:
        raise Exception("config file: 'in_files' values missing")

    for file_idx in range(len(config['in_files'])):
        if extend_relative_paths and not path.isabs(
                config['in_files'][file_idx]):
            config['in_files'][file_idx] = make_abs_path(
                cfg_path, config['in_files'][file_idx])

        if not path.isfile(config['in_files'][file_idx]):
            raise Exception("config file: '%s' is not a file" %
                            config['in_files'][file_idx])

    # --------------------------------------------------------------------------

    if "unc_bin" not in config:
        raise Exception("config file: 'in_files' missing")

    if extend_relative_paths and not path.isabs(config['unc_bin']):
        config['unc_bin'] = make_abs_path(cfg_path, config['unc_bin'])

    if not path.isfile(config['unc_bin']):
        raise Exception("config file: '%s' is not a file" % config['unc_bin'])

    # Optional -----------------------------------------------------------------

    if "cleanup_lvl" not in config:
        config["cleanup_lvl"] = 1

    if "force_cleanup" not in config:
        config["force_cleanup"] = False

    if "json_output" not in config:
        config["json_output"] = False


def cleanup(level, eq_map, clean_target_dir, keep_files=()):
    """cleans up output_dir

    :param level: 0 - do nothing,
                  1 - keep `keep_files` and 1 file for each group,
                  2 - remove everything

    :param equal_output_map: dict of files with equal content,
                             expects format generated by gen_equal_output_map

    :param clean_target_dir: directory which content will be cleaned

    :param keep_files: list of files should not be removed
    """

    if level == 0:
        return

    if level == 2:
        rmtree(clean_target_dir)

    if level == 1:
        rm_files = [
            clean_target_dir + "/" + f for f in listdir(clean_target_dir)
        ]

        for f in keep_files:
            rm_files.remove(f)

        for idx in eq_map:
            old_path = eq_map[idx][0]
            new_path = ("%s/g_%d" %
                        (path.dirname(path.abspath(old_path)), idx))
            rename(old_path, new_path)

            try:
                rm_files.remove(old_path)
            except ValueError:
                pass  # ignore that it is missing

            try:
                rm_files.remove(new_path)
            except ValueError:
                pass  # ignore that it is missing

        for f in rm_files:
            remove(f)


def main(args):
    config = load_config(args[0])
    check_config(config, args[0])

    # gen output directory
    if path.isfile(config["out_dir"]):
        raise Exception("%s is a file" % config["out_dir"])

    if not path.isdir(config["out_dir"]):
        makedirs(config["out_dir"])
    elif not config["force_cleanup"] and config["cleanup_lvl"] > 0:
        raise Exception("cleanup_lvl > 0 on an existing directory: %s" %
                        config["out_dir"])

    write_config_files(config)
    eq_map = gen_equal_output_map(config)
    output_dict = gen_output_dict(config, eq_map)

    # write output as txt file
    output_dict_path = path.join(config["out_dir"], "out.txt")
    write_output_dict_pretty(output_dict, output_dict_path)

    # read ouput txt file to print it
    with open(output_dict_path, 'r') as f:
        print()
        print(f.read())

    keep_files = [output_dict_path]

    # write output as json file
    if config["json_output"]:
        output_dict_json_path = path.join(config["out_dir"], "out.json")
        with open(output_dict_json_path, 'w') as f:
            json_dump(output_dict, f)
        keep_files.append(output_dict_json_path)

    # clean output directory
    cleanup(config["cleanup_lvl"], eq_map, config["out_dir"], keep_files)


if __name__ == "__main__":
    main(argv[1:])
